"""
Structured-output validation for AI insight responses.

Never trust raw AI output. This module enforces the JSON contract described
in prompts.py before anything from the AI is stored or shown to a teacher.
"""

MAX_ARRAY_ITEMS = 6
MAX_OVERVIEW_CHARS = 1000
MAX_STRING_CHARS = 500
ALLOWED_CONFIDENCE = {'high', 'medium', 'low'}

REQUIRED_TOP_LEVEL_FIELDS = {
    'overview': str,
    'learning_preferences': list,
    'strength_insights': list,
    'development_insights': list,
    'teaching_strategies': list,
    'communication': list,
    'classroom_recommendations': list,
    'potential_challenges': list,
    'teacher_actions': list,
}


class ValidationError(Exception):
    pass


def _clean_str(value, max_len=MAX_STRING_CHARS):
    if not isinstance(value, str):
        raise ValidationError(f"Expected string, got {type(value).__name__}")
    value = value.strip()
    if not value:
        raise ValidationError("Empty string not allowed")
    return value[:max_len]


def _validate_string_list(items, field_name):
    if not isinstance(items, list):
        raise ValidationError(f"{field_name} must be a list")
    cleaned = [_clean_str(item) for item in items[:MAX_ARRAY_ITEMS] if isinstance(item, str) and item.strip()]
    return cleaned


def _validate_learning_preferences(items):
    if not isinstance(items, list):
        raise ValidationError("learning_preferences must be a list")
    cleaned = []
    for item in items[:MAX_ARRAY_ITEMS]:
        if not isinstance(item, dict):
            continue
        title = item.get('title')
        description = item.get('description')
        if not title or not description:
            continue
        confidence = item.get('confidence', 'medium')
        if confidence not in ALLOWED_CONFIDENCE:
            confidence = 'medium'
        cleaned.append({
            'title': _clean_str(title, 120),
            'description': _clean_str(description),
            'confidence': confidence,
        })
    return cleaned


def _validate_strength_insights(items, allowed_strengths):
    if not isinstance(items, list):
        raise ValidationError("strength_insights must be a list")
    allowed = {s.lower() for s in allowed_strengths}
    cleaned = []
    for item in items[:MAX_ARRAY_ITEMS]:
        if not isinstance(item, dict):
            continue
        strength = item.get('strength')
        interpretation = item.get('interpretation')
        if not strength or not interpretation:
            continue
        # Guard against the model inventing strengths not in Phase 2 data.
        if allowed and strength.lower() not in allowed:
            continue
        cleaned.append({
            'strength': _clean_str(strength, 120),
            'interpretation': _clean_str(interpretation),
        })
    return cleaned


def _validate_development_insights(items, allowed_areas):
    if not isinstance(items, list):
        raise ValidationError("development_insights must be a list")
    allowed = {a.lower() for a in allowed_areas}
    cleaned = []
    for item in items[:MAX_ARRAY_ITEMS]:
        if not isinstance(item, dict):
            continue
        area = item.get('area')
        interpretation = item.get('interpretation')
        suggestion = item.get('suggestion', '')
        if not area or not interpretation:
            continue
        if allowed and area.lower() not in allowed:
            continue
        cleaned.append({
            'area': _clean_str(area, 120),
            'interpretation': _clean_str(interpretation),
            'suggestion': _clean_str(suggestion) if suggestion else '',
        })
    return cleaned


def _validate_teaching_strategies(items):
    if not isinstance(items, list):
        raise ValidationError("teaching_strategies must be a list")
    cleaned = []
    for item in items[:MAX_ARRAY_ITEMS]:
        if not isinstance(item, dict):
            continue
        strategy = item.get('strategy')
        reason = item.get('reason')
        if not strategy or not reason:
            continue
        example = item.get('example', '')
        cleaned.append({
            'strategy': _clean_str(strategy, 200),
            'reason': _clean_str(reason),
            'example': _clean_str(example) if example else '',
        })
    return cleaned


# Language that should never appear in AI output (Phase 3 spec §2, §32).
_FORBIDDEN_PHRASES = [
    'diagnos', 'disorder', 'disability', 'mental health', 'adhd', 'autis',
    'is definitely', 'will always', 'cannot ever', 'iq of', 'intelligence quotient',
]


def _contains_forbidden_language(text):
    lowered = text.lower()
    return any(phrase in lowered for phrase in _FORBIDDEN_PHRASES)


def validate_ai_response(raw, allowed_strengths=None, allowed_development_areas=None):
    """
    Validate and sanitize a raw AI response dict against the required schema.

    Returns (is_valid: bool, result: dict_or_error_message).
    On success, `result` is the cleaned data ready to store.
    On failure, `result` is a short, safe-to-log error description.
    """
    allowed_strengths = allowed_strengths or []
    allowed_development_areas = allowed_development_areas or []

    if not isinstance(raw, dict):
        return False, "AI response was not a JSON object"

    for field, expected_type in REQUIRED_TOP_LEVEL_FIELDS.items():
        if field not in raw:
            return False, f"Missing required field: {field}"
        if not isinstance(raw[field], expected_type):
            return False, f"Field '{field}' has wrong type"

    try:
        overview = _clean_str(raw['overview'], MAX_OVERVIEW_CHARS)
        if _contains_forbidden_language(overview):
            return False, "Overview contained disallowed language"

        cleaned = {
            'overview': overview,
            'learning_preferences': _validate_learning_preferences(raw['learning_preferences']),
            'strength_insights': _validate_strength_insights(raw['strength_insights'], allowed_strengths),
            'development_insights': _validate_development_insights(
                raw['development_insights'], allowed_development_areas
            ),
            'teaching_strategies': _validate_teaching_strategies(raw['teaching_strategies']),
            'communication': _validate_string_list(raw['communication'], 'communication'),
            'classroom_recommendations': _validate_string_list(
                raw['classroom_recommendations'], 'classroom_recommendations'
            ),
            'potential_challenges': _validate_string_list(raw['potential_challenges'], 'potential_challenges'),
            'teacher_actions': _validate_string_list(raw['teacher_actions'], 'teacher_actions'),
        }
    except ValidationError as e:
        return False, str(e)

    # Final sweep for forbidden language across all free-text fields.
    all_text = ' '.join([
        cleaned['overview'],
        *[p['description'] for p in cleaned['learning_preferences']],
        *[s['interpretation'] for s in cleaned['strength_insights']],
        *[d['interpretation'] for d in cleaned['development_insights']],
    ])
    if _contains_forbidden_language(all_text):
        return False, "Response contained disallowed language"

    return True, cleaned
