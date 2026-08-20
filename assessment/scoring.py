"""
Scoring Engine — assessment/scoring.py

Deterministic, rule-based scoring for Stages 1–3.
No AI/LLM involvement. Every rule is documented here.

=== SCORING RULES (documented per code-standards.md) ===

1. DIMENSION SCORE CALCULATION:
   - Each dimension has multiple Likert questions (scale 1–5).
   - Raw score = average of all Likert answers for that dimension.
   - Normalized score = ((raw_average - 1) / 4) * 100, rounded to nearest integer.
   - This maps 1→0, 3→50, 5→100.

2. ARCHETYPE MAPPING:
   - The archetype is determined by the student's highest-scoring dimension.
   - In case of a tie, the first dimension alphabetically wins (deterministic).
   - Archetypes:
       "Analytical Thinking" → "The Analytical Thinker"
       "Creative Learning"   → "The Creative Explorer"
       "Practical Learning"  → "The Hands-On Builder"
       "Social Learning"     → "The Collaborative Learner"
       "Self-Discipline"     → "The Focused Achiever"

3. STRENGTHS:
   - Dimensions scoring >= 70 are strengths.
   - Each dimension has a predefined strength description (see DIMENSION_META below).

4. CHALLENGES:
   - Dimensions scoring <= 40 are challenges.
   - Each dimension has a predefined challenge description.

5. RECOMMENDATIONS:
   - Derived from the archetype + challenge dimensions.
   - Each archetype has a base recommendation set.
   - Additional recommendations are added per challenge dimension.
"""

from .models import AssessmentResponse, LearningProfile


# --- Score normalization (Phase 2) ---
# Configurable thresholds — edit here rather than scattering magic numbers
# throughout the app. Checked highest-first; a score matches the first
# threshold it meets or exceeds.
SCORE_LEVEL_THRESHOLDS = [
    (80, 'Very Strong'),
    (60, 'Strong'),
    (40, 'Developing'),
    (0, 'Low'),
]

# Neutral-language templates per level, per code-standards.md's rule of
# describing preferences/patterns rather than making claims about identity.
_LEVEL_INTERPRETATION_TEMPLATES = {
    'Very Strong': "The student's responses indicate a strong preference for {dim_lower}.",
    'Strong': "The student's responses show a solid tendency toward {dim_lower}.",
    'Developing': "The student's responses show a developing tendency toward {dim_lower}; this may strengthen with practice.",
    'Low': "The student's responses do not currently indicate {dim_lower} as a primary preference — this may be an area to explore or support.",
}


def get_score_level(score):
    """
    Map a 0–100 dimension score to a normalized level label
    ('Low' / 'Developing' / 'Strong' / 'Very Strong').
    """
    for threshold, label in SCORE_LEVEL_THRESHOLDS:
        if score >= threshold:
            return label
    return SCORE_LEVEL_THRESHOLDS[-1][1]


def get_dimension_interpretation(dimension, score):
    """
    Return a short, neutral-language interpretation of a student's score
    on a given dimension, for teacher-facing display.
    """
    level = get_score_level(score)
    template = _LEVEL_INTERPRETATION_TEMPLATES[level]
    return template.format(dim_lower=dimension.lower())


def get_assessment_status(student):
    """
    Determine a student's assessment status: 'not_started', 'in_progress',
    or 'completed'. A completed LearningProfile always means 'completed';
    otherwise it's based on how many questions have been answered.
    """
    if LearningProfile.objects.filter(student=student).exists():
        return 'completed'

    answered = AssessmentResponse.objects.filter(student=student).count()
    if answered == 0:
        return 'not_started'
    return 'in_progress'


# --- Dimension Metadata ---
# Maps each dimension to its archetype name, strength text, challenge text,
# and per-dimension recommendation.

DIMENSION_META = {
    'Analytical Thinking': {
        'archetype': 'The Analytical Thinker',
        'strength': 'Strong ability to break down complex problems and think logically',
        'challenge': 'May overthink simple tasks or struggle with ambiguity',
        'recommendation': 'Practice working through problems step-by-step, and try timed exercises to build speed',
    },
    'Creative Learning': {
        'archetype': 'The Creative Explorer',
        'strength': 'Naturally finds innovative approaches and thinks outside the box',
        'challenge': 'May struggle with structured, rule-based tasks',
        'recommendation': 'Use mind maps and visual aids to organize your creative thinking',
    },
    'Practical Learning': {
        'archetype': 'The Hands-On Builder',
        'strength': 'Learns best by doing — excels with hands-on projects and real-world application',
        'challenge': 'May lose focus during purely theoretical or lecture-based learning',
        'recommendation': 'Seek out projects, labs, and practical exercises to reinforce concepts',
    },
    'Social Learning': {
        'archetype': 'The Collaborative Learner',
        'strength': 'Thrives in group settings and learns well through discussion and collaboration',
        'challenge': 'May find it difficult to study effectively alone',
        'recommendation': 'Form study groups and use discussion-based learning techniques',
    },
    'Self-Discipline': {
        'archetype': 'The Focused Achiever',
        'strength': 'Excellent at managing time, staying organized, and following through on plans',
        'challenge': 'May need help with flexibility when plans change unexpectedly',
        'recommendation': 'Build consistent study routines with scheduled breaks for balance',
    },
}

# --- Archetype base recommendations ---
ARCHETYPE_RECOMMENDATIONS = {
    'The Analytical Thinker': [
        'Use structured note-taking methods like Cornell Notes or outlines',
        'Break large topics into smaller logical components before studying',
    ],
    'The Creative Explorer': [
        'Use color-coded notes, diagrams, and concept maps',
        'Try explaining topics to others in your own creative way',
    ],
    'The Hands-On Builder': [
        'Look for interactive tutorials, simulations, and real-world projects',
        'Build something small with each new concept you learn',
    ],
    'The Collaborative Learner': [
        'Join or create study groups for your toughest subjects',
        'Teach concepts to a peer — explaining helps you learn deeply',
    ],
    'The Focused Achiever': [
        'Use a planner or digital calendar to schedule every study session',
        'Set clear daily goals and track your streaks',
    ],
}


def calculate_dimension_scores(student):
    """
    Calculate 0–100 scores for each dimension from a student's responses.

    Formula: ((average_likert_value - 1) / 4) * 100

    Returns:
        dict: { 'Analytical Thinking': 75, 'Creative Learning': 60, ... }
    """
    responses = AssessmentResponse.objects.filter(
        student=student
    ).select_related('question')

    # Group answers by dimension
    dimension_totals = {}  # { dimension: [answer_values] }
    for response in responses:
        dim = response.question.dimension
        value = response.answer_value

        # For likert, answer_value is an integer 1–5
        # For multiple_choice, we map the selected option to its index + 1
        if response.question.question_type == 'likert':
            numeric_value = int(value)
        else:
            # Multiple choice: option index (1-based) maps to score
            options = response.question.options or []
            if value in options:
                # Last option is highest alignment, first is lowest
                numeric_value = options.index(value) + 1
            else:
                numeric_value = 3  # default middle if somehow invalid

        if dim not in dimension_totals:
            dimension_totals[dim] = []
        dimension_totals[dim].append(numeric_value)

    # Calculate normalized scores
    scores = {}
    for dim, values in dimension_totals.items():
        raw_avg = sum(values) / len(values)
        # Normalize from 1-5 scale to 0-100
        normalized = round(((raw_avg - 1) / 4) * 100)
        scores[dim] = max(0, min(100, normalized))  # clamp to 0-100

    return scores


def determine_archetype(dimension_scores):
    """
    Determine the student's archetype from their dimension scores.

    Rule: highest-scoring dimension wins.
    Tie-break: alphabetical dimension name (deterministic).

    Returns:
        str: archetype name, e.g. "The Analytical Thinker"
    """
    if not dimension_scores:
        return 'Unknown'

    # Sort by score descending, then by dimension name ascending (tie-break)
    sorted_dims = sorted(
        dimension_scores.items(),
        key=lambda x: (-x[1], x[0]),
    )

    top_dimension = sorted_dims[0][0]
    meta = DIMENSION_META.get(top_dimension)
    if meta:
        return meta['archetype']

    return 'The Balanced Learner'


def derive_strengths_challenges(dimension_scores):
    """
    Identify strengths (score >= 70) and challenges (score <= 40).

    Returns:
        tuple: (strengths: list[str], challenges: list[str])
    """
    strengths = []
    challenges = []

    for dim, score in sorted(dimension_scores.items()):
        meta = DIMENSION_META.get(dim, {})
        if score >= 70 and meta.get('strength'):
            strengths.append(meta['strength'])
        if score <= 40 and meta.get('challenge'):
            challenges.append(meta['challenge'])

    # If no strengths found (all scores moderate), pick the highest
    if not strengths and dimension_scores:
        top_dim = max(dimension_scores, key=dimension_scores.get)
        meta = DIMENSION_META.get(top_dim, {})
        if meta.get('strength'):
            strengths.append(meta['strength'])

    # If no challenges found, that's fine — student has no weak areas
    return strengths, challenges


def generate_recommendations(archetype, dimension_scores):
    """
    Generate personalized recommendations based on archetype + challenges.

    Returns:
        list[str]: Recommendation strings
    """
    recommendations = []

    # Base recommendations from archetype
    base_recs = ARCHETYPE_RECOMMENDATIONS.get(archetype, [])
    recommendations.extend(base_recs)

    # Additional recommendations from challenge dimensions (score <= 40)
    for dim, score in sorted(dimension_scores.items()):
        if score <= 40:
            meta = DIMENSION_META.get(dim, {})
            rec = meta.get('recommendation')
            if rec and rec not in recommendations:
                recommendations.append(rec)

    return recommendations


def score_assessment(student):
    """
    Main entry point: score a student's completed assessment.

    1. Calculate dimension scores
    2. Determine archetype
    3. Derive strengths and challenges
    4. Generate recommendations
    5. Create or update the LearningProfile

    Returns:
        LearningProfile: the created/updated profile
    """
    dimension_scores = calculate_dimension_scores(student)
    archetype = determine_archetype(dimension_scores)
    strengths, challenges = derive_strengths_challenges(dimension_scores)
    recommendations = generate_recommendations(archetype, dimension_scores)

    # Upsert: create or update the learning profile
    profile, created = LearningProfile.objects.update_or_create(
        student=student,
        defaults={
            'archetype': archetype,
            'dimension_scores': dimension_scores,
            'strengths': strengths,
            'challenges': challenges,
            'recommendations': recommendations,
        },
    )

    return profile
