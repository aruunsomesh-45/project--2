"""
Validation for AI-generated study plans. Two layers, per Phase 4 spec §8:

1. Structural — is this valid JSON matching the schema at all?
2. Business rules — even if structurally valid, Django enforces every
   constraint itself (dates, available days, daily time budget) rather
   than trusting the AI to have respected them. Tasks that violate a rule
   are dropped (with a warning), never silently kept.
"""

from datetime import date, datetime

from ..models import TASK_TYPE_CHOICES

MAX_TITLE_CHARS = 200
MAX_DESCRIPTION_CHARS = 1000
MAX_OVERVIEW_CHARS = 800
VALID_TASK_TYPES = {code for code, _ in TASK_TYPE_CHOICES}


class ValidationError(Exception):
    pass


def _clean_str(value, max_len, field_name):
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise ValidationError(f"{field_name} is empty")
    return value[:max_len]


def validate_plan_structure(raw):
    """
    Layer 1: structural validation. Returns (is_valid, result) where
    result is either a flat list of raw task dicts (with title/overview
    attached to each for convenience) or an error string.
    """
    if not isinstance(raw, dict):
        return False, "AI response was not a JSON object"

    for field in ('title', 'overview', 'weeks'):
        if field not in raw:
            return False, f"Missing required field: {field}"

    if not isinstance(raw['weeks'], list) or not raw['weeks']:
        return False, "weeks must be a non-empty list"

    try:
        title = _clean_str(raw['title'], MAX_TITLE_CHARS, 'title')
        overview = _clean_str(raw['overview'], MAX_OVERVIEW_CHARS, 'overview')
    except ValidationError as e:
        return False, str(e)

    flat_tasks = []
    for week in raw['weeks']:
        if not isinstance(week, dict) or 'tasks' not in week or not isinstance(week['tasks'], list):
            continue
        for task in week['tasks']:
            if not isinstance(task, dict):
                continue
            flat_tasks.append(task)

    if not flat_tasks:
        return False, "AI response contained no usable tasks"

    return True, {'title': title, 'overview': overview, 'raw_tasks': flat_tasks}


def _parse_date(value):
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def validate_and_clean_tasks(plan, raw_tasks, only_from_date=None):
    """
    Layer 2: business-rule validation + cleaning against a specific
    StudyPlan's actual constraints. Never trusts the AI to have already
    respected dates/time budgets.

    Returns (clean_tasks, warnings) — clean_tasks is a list of dicts ready
    for StudyTask.objects.bulk_create(...), each with 'order' assigned.
    Tasks violating any rule are dropped, not silently kept; every drop is
    recorded in `warnings` (safe to show a teacher, never shown to the AI).

    `only_from_date`: if given, tasks dated before this are dropped too —
    used for adaptation, which must never touch the past.
    """
    warnings = []
    valid_range_start = plan.start_date if only_from_date is None else max(plan.start_date, only_from_date)
    valid_range_end = plan.end_date
    latest_allowed = min(valid_range_end, plan.exam_date) if plan.exam_date else valid_range_end
    available_days = set(plan.available_days or [])

    by_date = {}
    for raw in raw_tasks:
        title = raw.get('title')
        estimated_minutes = raw.get('estimated_minutes')
        task_type = raw.get('task_type')
        task_date = _parse_date(raw.get('date'))

        if not isinstance(title, str) or not title.strip():
            warnings.append("Dropped a task with no title")
            continue
        if task_date is None:
            warnings.append(f'Dropped "{title}" — invalid or missing date')
            continue
        if task_date < valid_range_start or task_date > valid_range_end:
            warnings.append(f'Dropped "{title}" — date {task_date} is outside the plan\'s date range')
            continue
        if task_date > latest_allowed:
            warnings.append(f'Dropped "{title}" — date {task_date} is after the exam date')
            continue
        if available_days and task_date.weekday() not in available_days:
            warnings.append(f'Dropped "{title}" — {task_date} is not one of the selected available days')
            continue
        if not isinstance(estimated_minutes, (int, float)) or estimated_minutes <= 0:
            warnings.append(f'Dropped "{title}" — duration must be greater than zero')
            continue
        if task_type not in VALID_TASK_TYPES:
            warnings.append(f'Dropped "{title}" — invalid task_type "{task_type}"')
            continue

        by_date.setdefault(task_date, []).append({
            'title': title.strip()[:MAX_TITLE_CHARS],
            'description': str(raw.get('description', '') or '')[:MAX_DESCRIPTION_CHARS],
            'date': task_date,
            'estimated_minutes': int(estimated_minutes),
            'task_type': task_type,
        })

    clean_tasks = []
    for task_date, day_tasks in by_date.items():
        running_total = 0
        order = 1
        for task in day_tasks:
            if running_total + task['estimated_minutes'] > plan.daily_minutes:
                warnings.append(
                    f'Dropped "{task["title"]}" on {task_date} — would exceed the {plan.daily_minutes}-minute daily limit'
                )
                continue
            running_total += task['estimated_minutes']
            task['order'] = order
            order += 1
            clean_tasks.append(task)

    return clean_tasks, warnings
