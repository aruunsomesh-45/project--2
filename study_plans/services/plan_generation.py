"""
AI study-plan generation and adaptation. Reuses the exact same provider
abstraction as Phase 3 (ai_insights.services.provider.get_provider) —
nothing here talks to a specific AI SDK. Django validation
(validators.py) is the actual authority on what ends up in the database;
the AI only proposes.
"""

import json
import logging
from datetime import date

from django.db import transaction
from django.utils import timezone

from ai_insights.services.base import AIProviderError
from ai_insights.services.provider import get_provider
from assessment.models import LearningProfile
from ai_insights.models import StudentAIInsight

from ..models import PlanAdaptationDraft, StudyTask
from .prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_adaptation_prompt, build_study_plan_prompt
from .validators import validate_and_clean_tasks, validate_plan_structure
from .progress import calculate_progress

logger = logging.getLogger('study_plans')


def _parse_json_response(raw_text):
    text = raw_text.strip()
    if text.startswith('```'):
        text = text.strip('`')
        if text.lower().startswith('json'):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def build_structured_input(plan):
    """
    Controlled, PII-minimized input for plan generation — the student's
    learning profile (Phase 2) and AI insights (Phase 3, if available),
    plus only the plan's own configured fields. No email/username/IDs.
    """
    student = plan.student
    first_name = (student.profile.full_name or '').split(' ')[0] or 'The student'

    data = {
        'student': {'first_name': first_name},
        'subject': plan.subject,
        'goal': plan.goal,
        'start_date': plan.start_date.isoformat(),
        'end_date': plan.end_date.isoformat(),
        'exam_date': plan.exam_date.isoformat() if plan.exam_date else None,
        'daily_minutes': plan.daily_minutes,
        'available_days': plan.available_days,
        'difficulty': plan.difficulty,
        'teacher_instructions': plan.teacher_instructions,
    }

    try:
        profile = LearningProfile.objects.get(student=student)
        data['learning_profile'] = {
            'archetype': profile.archetype,
            'dimensions': dict(profile.dimension_scores),
            'strengths': list(profile.strengths),
            'development_areas': list(profile.challenges),
        }
    except LearningProfile.DoesNotExist:
        data['learning_profile'] = None

    insight = StudentAIInsight.objects.filter(student=student, status='ready').first()
    if insight:
        data['ai_insights'] = {
            'overview': insight.overview,
            'teaching_strategies': [t.get('strategy') for t in insight.teaching_strategies][:6],
        }
    else:
        data['ai_insights'] = None

    return data


def generate_plan_with_ai(plan):
    """
    Generate (or regenerate) tasks for a plan via AI, with Django
    validating everything before it's saved. Existing tasks for this plan
    are replaced (only called on draft plans — never on an active plan
    with student progress; use request_adaptation for that).

    Returns (success: bool, message: str, warnings: list[str]).
    """
    plan_data = build_structured_input(plan)
    provider = get_provider()

    for attempt_num in range(2):
        try:
            raw_text = provider.generate(SYSTEM_PROMPT, build_study_plan_prompt(plan_data))
        except AIProviderError as e:
            logger.warning("Study plan generation failed (attempt %s): %s", attempt_num + 1, e)
            continue

        try:
            raw_json = _parse_json_response(raw_text)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Study plan AI response was not valid JSON (attempt %s)", attempt_num + 1)
            continue

        is_valid, result = validate_plan_structure(raw_json)
        if not is_valid:
            logger.warning("Study plan structural validation failed (attempt %s): %s", attempt_num + 1, result)
            continue

        clean_tasks, warnings = validate_and_clean_tasks(plan, result['raw_tasks'])
        if not clean_tasks:
            logger.warning("Study plan had no valid tasks after business-rule validation (attempt %s)", attempt_num + 1)
            continue

        with transaction.atomic():
            plan.tasks.all().delete()
            if not plan.title:
                plan.title = result['title']
            if not plan.description:
                plan.description = result['overview']
            plan.ai_generated = True
            plan.prompt_version = PROMPT_VERSION
            plan.model_name = provider.model_name
            plan.save(update_fields=['title', 'description', 'ai_generated', 'prompt_version', 'model_name', 'updated_at'])
            StudyTask.objects.bulk_create([
                StudyTask(study_plan=plan, task_type=t['task_type'], title=t['title'], description=t['description'],
                           date=t['date'], estimated_minutes=t['estimated_minutes'], order=t['order'])
                for t in clean_tasks
            ])

        logger.info("Study plan generation succeeded for plan_id=%s (%d tasks)", plan.pk, len(clean_tasks))
        return True, "Plan generated.", warnings

    return False, "AI generation is temporarily unavailable. You can create the plan manually instead.", []


def request_adaptation(plan, teacher_instructions=''):
    """
    Propose an adaptation of a plan's *future* tasks only, based on the
    student's actual progress so far. Nothing in the database changes
    until a teacher explicitly applies the resulting draft — see
    apply_adaptation_draft.

    Returns (draft_or_None, message).
    """
    today = timezone.localdate()
    progress = calculate_progress(plan)
    plan_data = build_structured_input(plan)
    provider = get_provider()

    for attempt_num in range(2):
        try:
            raw_text = provider.generate(
                SYSTEM_PROMPT,
                build_adaptation_prompt(plan_data, {**progress, 'teacher_instructions': teacher_instructions}),
            )
        except AIProviderError:
            continue
        try:
            raw_json = _parse_json_response(raw_text)
        except (json.JSONDecodeError, ValueError):
            continue

        is_valid, result = validate_plan_structure(raw_json)
        if not is_valid:
            continue

        clean_tasks, warnings = validate_and_clean_tasks(plan, result['raw_tasks'], only_from_date=today)
        if not clean_tasks:
            continue

        serializable_tasks = [
            {**t, 'date': t['date'].isoformat()} for t in clean_tasks
        ]
        draft = PlanAdaptationDraft.objects.create(
            study_plan=plan,
            teacher_instructions=teacher_instructions,
            proposed_tasks=serializable_tasks,
            prompt_version=PROMPT_VERSION,
            model_name=provider.model_name,
        )
        return draft, "Adaptation proposed — review before applying."

    return None, "AI adaptation is temporarily unavailable right now."


def apply_adaptation_draft(draft):
    """
    Apply a reviewed adaptation draft: replaces ONLY future
    (date >= today) tasks that are still pending/in_progress. Completed
    and skipped tasks, and anything in the past, are never touched.
    """
    today = timezone.localdate()
    plan = draft.study_plan

    with transaction.atomic():
        plan.tasks.filter(date__gte=today, status__in=['pending', 'in_progress']).delete()
        StudyTask.objects.bulk_create([
            StudyTask(
                study_plan=plan, task_type=t['task_type'], title=t['title'], description=t['description'],
                date=date.fromisoformat(t['date']), estimated_minutes=t['estimated_minutes'], order=t['order'],
            )
            for t in draft.proposed_tasks
        ])
        draft.status = 'applied'
        draft.applied_at = timezone.now()
        draft.save(update_fields=['status', 'applied_at'])

    return plan
