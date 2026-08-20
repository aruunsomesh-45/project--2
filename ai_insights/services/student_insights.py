"""
Orchestration for generating a student's AI insights:

    Structured input  ->  Provider call  ->  Validate  ->  (retry once)  ->
    Store StudentAIInsight

Phase 2's LearningProfile remains the source of truth for scores; this
module only turns that data into a controlled, PII-minimized payload and
stores the AI's *interpretation* of it.
"""

import hashlib
import json
import logging

from django.db import transaction
from django.utils import timezone

from assessment.models import LearningProfile
from ..models import StudentAIInsight, StudentAIInsightHistory
from .base import AIProviderError
from .prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_student_insight_prompt
from .provider import get_provider
from .validators import validate_ai_response

logger = logging.getLogger('ai_insights')


class InsightGenerationError(Exception):
    """Raised when generation fails after all retries. Callers should catch
    this and fall back to the Phase 2 profile — never let it 500."""


def build_structured_input(student):
    """
    Build the controlled, minimal representation sent to the AI.

    Deliberately excludes: email, username, internal DB IDs, auth data,
    other students' data, teacher notes. Includes only what's needed to
    generate educational insights, per Phase 3 spec §5-6.
    """
    profile = LearningProfile.objects.get(student=student)

    # First name only — enough for natural phrasing ("Arun's responses
    # indicate..."), nowhere near enough to be a meaningful PII exposure.
    first_name = (student.profile.full_name or '').split(' ')[0] or 'The student'

    return {
        'student': {
            'first_name': first_name,
        },
        'learning_profile': {
            'archetype': profile.archetype,
        },
        'dimensions': dict(profile.dimension_scores),
        'strengths': list(profile.strengths),
        'development_areas': list(profile.challenges),
    }


def _profile_snapshot(profile_data):
    """Cheap fingerprint of the input data, used to detect when a student's
    underlying profile has changed since insights were last generated."""
    payload = json.dumps(profile_data, sort_keys=True)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:32]


def _parse_json_response(raw_text):
    """AI responses occasionally wrap JSON in markdown fences despite
    instructions not to — strip those defensively before parsing."""
    text = raw_text.strip()
    if text.startswith('```'):
        text = text.strip('`')
        if text.lower().startswith('json'):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def _call_and_validate(provider, profile_data):
    system_prompt = SYSTEM_PROMPT
    user_prompt = build_student_insight_prompt(profile_data)

    raw_text = provider.generate(system_prompt, user_prompt)

    try:
        raw_json = _parse_json_response(raw_text)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("AI response was not valid JSON: %s", e.__class__.__name__)
        return False, "AI response was not valid JSON"

    return validate_ai_response(
        raw_json,
        allowed_strengths=profile_data['strengths'],
        allowed_development_areas=profile_data['development_areas'],
    )


def generate_student_insights(student, force=False):
    """
    Generate (or reuse) AI insights for a student.

    Returns (insight, generated: bool) — `generated` is True only if a new
    AI result was actually produced and stored this call, so callers can
    tell "fresh success" apart from "reused" or "failed, old data kept".

    Important: a failed *regeneration* attempt never overwrites a good
    existing 'ready' insight — the teacher keeps seeing the last good
    result, with a failure noted via the caller's messaging, not a blanked
    -out AI section. Raises InsightGenerationError only for programmer
    -error style cases (e.g. no completed assessment yet).
    """
    if not LearningProfile.objects.filter(student=student).exists():
        raise InsightGenerationError("Student has no completed Learning Profile yet")

    profile_data = build_structured_input(student)
    snapshot = _profile_snapshot(profile_data)

    existing = StudentAIInsight.objects.filter(student=student).first()
    if not force and existing and existing.status == 'ready' and existing.source_profile_snapshot == snapshot:
        # Nothing changed since last generation — reuse it, avoid the API call.
        return existing, False

    provider = get_provider()
    logger.info("AI insight generation started for student_id=%s", student.pk)

    try:
        is_valid, result = _call_and_validate(provider, profile_data)
    except AIProviderError as e:
        is_valid, result = False, str(e)

    if not is_valid:
        logger.warning("AI insight generation/validation failed, retrying once: %s", result)
        try:
            is_valid, result = _call_and_validate(provider, profile_data)
        except AIProviderError as e:
            is_valid, result = False, str(e)

    if is_valid:
        with transaction.atomic():
            # Archive the previous ready result before overwriting (spec
            # §25: regeneration must not silently destroy the prior
            # interpretation).
            if existing and existing.status == 'ready':
                StudentAIInsightHistory.objects.create(
                    student=student,
                    overview=existing.overview,
                    learning_preferences=existing.learning_preferences,
                    strength_insights=existing.strength_insights,
                    development_insights=existing.development_insights,
                    teaching_strategies=existing.teaching_strategies,
                    communication=existing.communication,
                    classroom_recommendations=existing.classroom_recommendations,
                    potential_challenges=existing.potential_challenges,
                    teacher_actions=existing.teacher_actions,
                    prompt_version=existing.prompt_version,
                    model_name=existing.model_name,
                )

            logger.info("AI insight generation succeeded for student_id=%s", student.pk)
            insight, _ = StudentAIInsight.objects.update_or_create(
                student=student,
                defaults={
                    **result,
                    'source_profile_snapshot': snapshot,
                    'prompt_version': PROMPT_VERSION,
                    'model_name': provider.model_name,
                    'status': 'ready',
                    'error_message': '',
                },
            )
        return insight, True

    logger.warning("AI insight generation failed for student_id=%s: %s", student.pk, result)

    if existing and existing.status == 'ready':
        # Keep the last good result visible — don't blank it out over a
        # failed regeneration attempt. Caller's messaging communicates the
        # failure separately.
        return existing, False

    insight, _ = StudentAIInsight.objects.update_or_create(
        student=student,
        defaults={
            'source_profile_snapshot': snapshot,
            'prompt_version': PROMPT_VERSION,
            'model_name': provider.model_name,
            'status': 'failed',
            'error_message': str(result)[:500],
        },
    )
    return insight, False
