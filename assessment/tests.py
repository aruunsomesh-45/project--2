from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import Profile
from .models import AssessmentQuestion, AssessmentResponse, LearningProfile
from .scoring import (
    calculate_dimension_scores,
    derive_strengths_challenges,
    determine_archetype,
    get_assessment_status,
    get_score_level,
    get_dimension_interpretation,
    score_assessment,
)


def make_student(username='student@example.com'):
    user = User.objects.create_user(username=username, email=username, password='pass12345')
    Profile.objects.create(user=user, role='student', full_name='Test Student')
    return user


class ScoreLevelTests(TestCase):
    def test_boundary_values(self):
        self.assertEqual(get_score_level(0), 'Low')
        self.assertEqual(get_score_level(39), 'Low')
        self.assertEqual(get_score_level(40), 'Developing')
        self.assertEqual(get_score_level(59), 'Developing')
        self.assertEqual(get_score_level(60), 'Strong')
        self.assertEqual(get_score_level(79), 'Strong')
        self.assertEqual(get_score_level(80), 'Very Strong')
        self.assertEqual(get_score_level(100), 'Very Strong')

    def test_interpretation_uses_neutral_language(self):
        text = get_dimension_interpretation('Analytical Thinking', 85)
        self.assertIn('indicate', text)
        # Must not make absolute identity claims
        self.assertNotIn('The student is', text)
        self.assertNotIn('will always', text)


class DimensionScoringTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.q1 = AssessmentQuestion.objects.create(
            dimension='Analytical Thinking', question_text='Q1', question_type='likert', display_order=1,
        )
        self.q2 = AssessmentQuestion.objects.create(
            dimension='Analytical Thinking', question_text='Q2', question_type='likert', display_order=2,
        )

    def test_dimension_score_normalizes_1to5_to_0to100(self):
        AssessmentResponse.objects.create(student=self.student, question=self.q1, answer_value=5)
        AssessmentResponse.objects.create(student=self.student, question=self.q2, answer_value=5)
        scores = calculate_dimension_scores(self.student)
        self.assertEqual(scores['Analytical Thinking'], 100)

    def test_missing_answers_excluded_from_dimension(self):
        # Only q1 answered — dimension score should reflect just that answer.
        AssessmentResponse.objects.create(student=self.student, question=self.q1, answer_value=3)
        scores = calculate_dimension_scores(self.student)
        self.assertEqual(scores['Analytical Thinking'], 50)


class ArchetypeAndDetectionTests(TestCase):
    def test_archetype_picks_highest_dimension_with_alphabetical_tiebreak(self):
        scores = {'Analytical Thinking': 90, 'Creative Learning': 90}
        archetype = determine_archetype(scores)
        # Alphabetically 'Analytical Thinking' < 'Creative Learning'
        self.assertEqual(archetype, 'The Analytical Thinker')

    def test_strength_included_when_score_at_least_70(self):
        strengths, _ = derive_strengths_challenges({'Analytical Thinking': 70, 'Creative Learning': 50})
        self.assertEqual(len(strengths), 1)

    def test_below_threshold_falls_back_to_top_dimension(self):
        # derive_strengths_challenges guarantees at least one strength shown
        # (the highest-scoring dimension) even when nothing clears the >=70
        # bar, so a profile is never "no strengths at all".
        strengths, _ = derive_strengths_challenges({'Analytical Thinking': 69})
        self.assertEqual(len(strengths), 1)

    def test_challenge_requires_score_at_most_40(self):
        _, challenges = derive_strengths_challenges({'Self-Discipline': 40})
        self.assertTrue(challenges)
        _, challenges = derive_strengths_challenges({'Self-Discipline': 41})
        self.assertFalse(challenges)


class AssessmentStatusTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.q1 = AssessmentQuestion.objects.create(
            dimension='Analytical Thinking', question_text='Q1', question_type='likert', display_order=1,
        )
        self.q2 = AssessmentQuestion.objects.create(
            dimension='Analytical Thinking', question_text='Q2', question_type='likert', display_order=2,
        )

    def test_not_started(self):
        self.assertEqual(get_assessment_status(self.student), 'not_started')

    def test_in_progress(self):
        AssessmentResponse.objects.create(student=self.student, question=self.q1, answer_value=3)
        self.assertEqual(get_assessment_status(self.student), 'in_progress')

    def test_completed_once_profile_generated(self):
        AssessmentResponse.objects.create(student=self.student, question=self.q1, answer_value=3)
        AssessmentResponse.objects.create(student=self.student, question=self.q2, answer_value=4)
        score_assessment(self.student)
        self.assertEqual(get_assessment_status(self.student), 'completed')
        self.assertTrue(LearningProfile.objects.filter(student=self.student).exists())
