"""
Adaptive Screening Test engine.

Part 1 adaptive routing per topic: every topic starts at Medium; a correct
answer routes to the Hard question next, an incorrect answer routes to
Easy — exactly as described in the source question bank, with no scoring
model involved in the routing itself. All state is *derived* from
ScreeningResponse rows rather than stored separately, so there's nothing
to fall out of sync.
"""

from collections import Counter
from statistics import mean

from django.utils import timezone

from ..models import (
    ADAPTIVE_TOPICS,
    LEARNING_STYLE_TAGS,
    ScreeningAttempt,
    ScreeningQuestion,
    ScreeningReport,
    ScreeningResponse,
    SelfReportQuestion,
    SelfReportResponse,
)

PART2_CATEGORY_ORDER = ['personality', 'interests', 'wellbeing', 'soft_skills', 'open_message']


# ---------------------------------------------------------------- Part 1 ---

def _topic_responses(attempt, section, topic):
    return list(
        ScreeningResponse.objects.filter(attempt=attempt, question__section=section, question__topic=topic)
    )


def _next_difficulty_for_topic(attempt, section, topic):
    """Returns 'medium', 'hard', 'easy', or None (topic complete)."""
    responses = _topic_responses(attempt, section, topic)
    if len(responses) == 0:
        return 'medium'
    if len(responses) == 1:
        return 'hard' if responses[0].is_correct else 'easy'
    return None


def get_next_part1_question(attempt):
    """Returns the next ScreeningQuestion to serve, or None if Part 1 is complete."""
    for section, topic in ADAPTIVE_TOPICS:
        difficulty = _next_difficulty_for_topic(attempt, section, topic)
        if difficulty is not None:
            question = ScreeningQuestion.objects.filter(
                tier=attempt.tier, section=section, topic=topic, difficulty=difficulty
            ).first()
            if question is not None:
                return question
            # Missing data for this tier/topic/difficulty — skip rather than
            # get the student stuck; this only happens if the bank wasn't
            # seeded for that tier.
            continue

    answered_ls_ids = ScreeningResponse.objects.filter(
        attempt=attempt, question__section='learning_style'
    ).values_list('question_id', flat=True)
    return (
        ScreeningQuestion.objects.filter(tier=attempt.tier, section='learning_style')
        .exclude(id__in=answered_ls_ids)
        .order_by('display_order')
        .first()
    )


def record_part1_answer(attempt, question, selected_option):
    is_correct = None
    if question.section in ('subject_knowledge', 'cognitive_aptitude'):
        is_correct = selected_option == question.correct_option

    ScreeningResponse.objects.update_or_create(
        attempt=attempt, question=question,
        defaults={'selected_option': selected_option, 'is_correct': is_correct},
    )

    if get_next_part1_question(attempt) is None:
        attempt.part1_status = 'completed'
        attempt.save(update_fields=['part1_status'])
    elif attempt.part1_status == 'not_started':
        attempt.part1_status = 'in_progress'
        attempt.save(update_fields=['part1_status'])


# ---------------------------------------------------------------- Part 2 ---

def get_next_part2_question(attempt):
    answered_ids = set(SelfReportResponse.objects.filter(attempt=attempt).values_list('question_id', flat=True))
    candidates = [q for q in SelfReportQuestion.objects.all() if q.applies_to_tier(attempt.tier)]
    candidates.sort(key=lambda q: (PART2_CATEGORY_ORDER.index(q.category), q.display_order))
    for q in candidates:
        if q.id not in answered_ids:
            return q
    return None


def record_part2_answer(attempt, question, selected_option='', free_text=''):
    SelfReportResponse.objects.update_or_create(
        attempt=attempt, question=question,
        defaults={'selected_option': selected_option, 'free_text': free_text},
    )

    if get_next_part2_question(attempt) is None:
        attempt.part2_status = 'completed'
        if attempt.completed_at is None:
            attempt.completed_at = timezone.now()
        attempt.save(update_fields=['part2_status', 'completed_at'])
        generate_report(attempt)
    elif attempt.part2_status == 'not_started':
        attempt.part2_status = 'in_progress'
        attempt.save(update_fields=['part2_status'])


# --------------------------------------------------------------- Report ----

def _majority_tag(tags):
    tags = [t for t in tags if t]
    if not tags:
        return ''
    return Counter(tags).most_common(1)[0][0]


def _option_tag(question, label):
    for opt in question.options:
        if opt.get('label') == label:
            return opt.get('tag')
    return None


def _topic_score(attempt, section, topic):
    responses = _topic_responses(attempt, section, topic)
    if not responses:
        return 0
    correct = sum(1 for r in responses if r.is_correct)
    return round(correct / len(responses) * 100)


def generate_report(attempt):
    """
    Deterministic report generation — no AI involved. Safe to call again;
    upserts the ScreeningReport for this attempt.
    """
    sk_topics = [t for s, t in ADAPTIVE_TOPICS if s == 'subject_knowledge']
    ca_topics = [t for s, t in ADAPTIVE_TOPICS if s == 'cognitive_aptitude']
    subject_knowledge_score = round(mean([_topic_score(attempt, 'subject_knowledge', t) for t in sk_topics]))
    cognitive_aptitude_score = round(mean([_topic_score(attempt, 'cognitive_aptitude', t) for t in ca_topics]))

    ls_responses = ScreeningResponse.objects.filter(attempt=attempt, question__section='learning_style')
    learning_style_tag = _majority_tag([LEARNING_STYLE_TAGS.get(r.selected_option) for r in ls_responses])

    personality_responses = SelfReportResponse.objects.filter(
        attempt=attempt, question__category='personality'
    ).select_related('question')
    personality_tag = _majority_tag([_option_tag(r.question, r.selected_option) for r in personality_responses])

    interest_responses = SelfReportResponse.objects.filter(
        attempt=attempt, question__category='interests'
    ).select_related('question')
    interest_tag = _majority_tag([_option_tag(r.question, r.selected_option) for r in interest_responses])

    wellbeing_responses = list(
        SelfReportResponse.objects.filter(attempt=attempt, question__category='wellbeing')
    )
    count_ab = sum(1 for r in wellbeing_responses if r.selected_option in ('A', 'B'))
    count_cd = sum(1 for r in wellbeing_responses if r.selected_option in ('C', 'D'))
    if count_ab >= 2:
        wellbeing_flag = 'Green'
    elif count_cd >= 2:
        wellbeing_flag = 'Red'
    else:
        wellbeing_flag = 'Amber'

    soft_skills_responses = SelfReportResponse.objects.filter(
        attempt=attempt, question__category='soft_skills'
    ).select_related('question')
    soft_skills_tags = {
        r.question.sub_key or str(r.question_id): _option_tag(r.question, r.selected_option)
        for r in soft_skills_responses
    }

    open_message_response = SelfReportResponse.objects.filter(
        attempt=attempt, question__category='open_message'
    ).first()
    open_message = open_message_response.free_text if open_message_response else ''

    report, _ = ScreeningReport.objects.update_or_create(
        attempt=attempt,
        defaults={
            'student': attempt.student,
            'subject_knowledge_score': subject_knowledge_score,
            'cognitive_aptitude_score': cognitive_aptitude_score,
            'personality_tag': personality_tag,
            'interest_tag': interest_tag,
            'learning_style_tag': learning_style_tag,
            'wellbeing_flag': wellbeing_flag,
            'soft_skills_tags': soft_skills_tags,
            'open_message': open_message,
        },
    )
    return report


def get_or_create_attempt(student, tier):
    """
    Resume an in-progress/incomplete attempt for this tier if one exists;
    otherwise start a new one. Completed attempts for a different tier
    don't block starting a new attempt in a new tier.
    """
    existing = (
        ScreeningAttempt.objects.filter(student=student, tier=tier)
        .exclude(part1_status='completed', part2_status='completed')
        .order_by('-started_at')
        .first()
    )
    if existing:
        return existing
    return ScreeningAttempt.objects.create(student=student, tier=tier)


def total_part1_progress(attempt):
    """(answered, total) across all Part 1 items for this attempt's tier."""
    total = ScreeningQuestion.objects.filter(tier=attempt.tier, section='learning_style').count() + len(ADAPTIVE_TOPICS) * 2
    answered = ScreeningResponse.objects.filter(attempt=attempt).count()
    return answered, total


def total_part2_progress(attempt):
    total = len([q for q in SelfReportQuestion.objects.all() if q.applies_to_tier(attempt.tier)])
    answered = SelfReportResponse.objects.filter(attempt=attempt).count()
    return answered, total
