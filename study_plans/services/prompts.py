"""
Prompt construction for AI study-plan generation. Reuses the same
provider abstraction as Phase 3 (ai_insights.services.provider) — this
module only builds the prompt text and defines the expected JSON schema.
"""

import json

PROMPT_VERSION = 'study-plan-v1'

RESPONSE_SCHEMA_EXAMPLE = {
    "title": "string",
    "overview": "2-4 sentence plan summary",
    "weeks": [
        {
            "week_number": 1,
            "focus": "string",
            "tasks": [
                {
                    "date": "YYYY-MM-DD",
                    "title": "string",
                    "description": "string",
                    "estimated_minutes": 30,
                    "task_type": "learning|practice|revision|quiz|reflection|review|assessment",
                }
            ],
        }
    ],
}

SYSTEM_PROMPT = """You are an educational assistant helping a teacher build a personalized \
study plan for one student, based on structured, assessment-derived data.

STRICT RULES:

1. Base the plan ONLY on the data provided — the student's learning profile, AI \
learning insights (if given), subject, goal, exam date, available study time, \
available days, difficulty, and any teacher instructions. Do not invent facts \
about the student.
2. Respect the constraints exactly where possible: do not schedule tasks outside \
the given date range, on days not listed as available, or exceeding the daily \
time budget — Django will validate and trim anything that doesn't fit, but aim \
to already be compliant.
3. Never diagnose, never make claims about intelligence or guaranteed academic \
outcomes, never rank the student against others, never assume demographic \
traits. This is a suggestion for teacher review, not a decision.
4. Vary task types across the plan (learning, practice, revision, quiz, \
reflection, review, assessment) rather than repeating the same type daily.
5. Respond with ONLY a single valid JSON object matching the schema below — no \
markdown formatting, no prose before or after, no code fences.

REQUIRED JSON SCHEMA:
""" + json.dumps(RESPONSE_SCHEMA_EXAMPLE, indent=2) + """

Field limits: "overview" must be 2-4 sentences. Each task's "estimated_minutes" \
must be a positive integer. "task_type" must be exactly one of the listed values."""


def build_study_plan_prompt(plan_data):
    """
    `plan_data` is the controlled structured representation from
    study_plans/services/plan_generation.py — never raw model instances,
    never PII beyond an optional first name.
    """
    return (
        "Generate a personalized study plan for a teacher to review, based on this "
        "structured data. Follow every rule in your system instructions.\n\n"
        f"PLAN REQUEST:\n{json.dumps(plan_data, indent=2)}"
    )


def build_adaptation_prompt(plan_data, progress_summary):
    """Prompt for adapting only the *future* portion of an existing plan,
    informed by the student's actual progress so far."""
    payload = {**plan_data, 'progress_so_far': progress_summary}
    return (
        "The student is partway through this study plan. Propose an updated set of "
        "FUTURE tasks only (the remaining days), taking into account their progress "
        "so far. Do not reference or attempt to modify anything already completed. "
        "Follow every rule in your system instructions and return the same JSON "
        "schema (weeks/tasks) covering only the remaining date range.\n\n"
        f"PLAN REQUEST:\n{json.dumps(payload, indent=2)}"
    )
