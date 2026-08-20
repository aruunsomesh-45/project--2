import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from assessment.models import AssessmentQuestion, AssessmentResponse
from assessment.scoring import score_assessment
from classroom.models import Class, ClassStudent

from .models import StudentAIInsight, StudentAIInsightHistory
from .services.base import AIProvider, AIProviderError
from .services.student_insights import (
    InsightGenerationError,
    build_structured_input,
    generate_student_insights,
)
from .services.validators import validate_ai_response
from .services.provider import GeminiProvider, get_provider, NullProvider


VALID_RESPONSE = {
    "overview": "The student's responses indicate a preference for analytical and practical learning approaches.",
    "learning_preferences": [
        {"title": "Analytical + Practical", "description": "Engages well with reasoning tasks.", "confidence": "high"}
    ],
    "strength_insights": [
        {"strength": "Strong ability to break down complex problems and think logically", "interpretation": "May enjoy structured problem-solving tasks."}
    ],
    "development_insights": [
        {"area": "May need help with flexibility when plans change unexpectedly", "interpretation": "Structured routines may help.", "suggestion": "Provide advance notice of changes."}
    ],
    "teaching_strategies": [
        {"strategy": "Use real-world examples", "reason": "Connects abstract concepts to practice.", "example": "Use a budgeting exercise for percentages."}
    ],
    "communication": ["Clear expectations", "Specific feedback"],
    "classroom_recommendations": ["Allow independent problem solving"],
    "potential_challenges": ["May benefit from structured deadlines"],
    "teacher_actions": ["Break large assignments into milestones"],
}


class MockAIProvider(AIProvider):
    """Predictable provider for tests — never calls a real API."""

    def __init__(self, response_text=None, raise_error=False):
        self._response_text = response_text if response_text is not None else json.dumps(VALID_RESPONSE)
        self._raise_error = raise_error
        self.call_count = 0

    @property
    def model_name(self):
        return 'mock-model'

    def generate(self, system_prompt, user_prompt):
        self.call_count += 1
        if self._raise_error:
            raise AIProviderError("mock provider failure")
        return self._response_text


def make_user(username, role, full_name=None):
    user = User.objects.create_user(username=username, email=username, password='pass12345')
    Profile.objects.create(user=user, role=role, full_name=full_name or username.split('@')[0])
    return user


def make_assessed_student(username='student@example.com'):
    student = make_user(username, 'student', full_name='Arun Kumar')
    q1 = AssessmentQuestion.objects.create(dimension='Analytical Thinking', question_text='Q1', question_type='likert', display_order=1)
    q2 = AssessmentQuestion.objects.create(dimension='Self-Discipline', question_text='Q2', question_type='likert', display_order=2)
    AssessmentResponse.objects.create(student=student, question=q1, answer_value=5)
    AssessmentResponse.objects.create(student=student, question=q2, answer_value=2)
    score_assessment(student)
    return student


class StructuredInputTests(TestCase):
    def test_excludes_pii(self):
        student = make_assessed_student()
        data = build_structured_input(student)
        serialized = json.dumps(data)
        self.assertNotIn(student.email, serialized)
        self.assertNotIn(student.username, serialized)
        self.assertNotIn(str(student.pk), serialized)
        self.assertIn('dimensions', data)
        self.assertIn('strengths', data)
        self.assertIn('development_areas', data)

    def test_includes_only_first_name(self):
        student = make_assessed_student()
        data = build_structured_input(student)
        self.assertEqual(data['student']['first_name'], 'Arun')


class ProviderFactoryTests(TestCase):
    def test_no_api_key_returns_null_provider(self):
        with self.settings(AI_API_KEY=''):
            self.assertIsInstance(get_provider(), NullProvider)

    def test_gemini_provider_selected_when_configured(self):
        with self.settings(AI_PROVIDER='gemini', AI_API_KEY='some-key'):
            self.assertIsInstance(get_provider(), GeminiProvider)

    def test_unknown_provider_falls_back_to_null_provider(self):
        with self.settings(AI_PROVIDER='some_unsupported_provider', AI_API_KEY='x'):
            self.assertIsInstance(get_provider(), NullProvider)


class ValidatorTests(TestCase):
    def test_valid_response_passes(self):
        is_valid, result = validate_ai_response(
            VALID_RESPONSE,
            allowed_strengths=['Strong ability to break down complex problems and think logically'],
            allowed_development_areas=['May need help with flexibility when plans change unexpectedly'],
        )
        self.assertTrue(is_valid)
        self.assertEqual(result['overview'], VALID_RESPONSE['overview'])

    def test_missing_field_fails(self):
        bad = dict(VALID_RESPONSE)
        del bad['overview']
        is_valid, _ = validate_ai_response(bad)
        self.assertFalse(is_valid)

    def test_wrong_type_fails(self):
        bad = dict(VALID_RESPONSE)
        bad['communication'] = "not a list"
        is_valid, _ = validate_ai_response(bad)
        self.assertFalse(is_valid)

    def test_not_a_dict_fails(self):
        is_valid, _ = validate_ai_response(["just", "a", "list"])
        self.assertFalse(is_valid)

    def test_invented_strength_is_filtered_out(self):
        response = dict(VALID_RESPONSE)
        response['strength_insights'] = [
            {"strength": "Something never mentioned in Phase 2 data", "interpretation": "x"}
        ]
        is_valid, result = validate_ai_response(response, allowed_strengths=['Real strength'])
        self.assertTrue(is_valid)
        self.assertEqual(result['strength_insights'], [])

    def test_excessive_array_items_truncated(self):
        response = dict(VALID_RESPONSE)
        response['communication'] = [f"item {i}" for i in range(20)]
        is_valid, result = validate_ai_response(response)
        self.assertTrue(is_valid)
        self.assertLessEqual(len(result['communication']), 6)

    def test_forbidden_language_rejected(self):
        response = dict(VALID_RESPONSE)
        response['overview'] = "This student has a diagnosed learning disability."
        is_valid, _ = validate_ai_response(response)
        self.assertFalse(is_valid)


class GenerationWorkflowTests(TestCase):
    def setUp(self):
        self.student = make_assessed_student()

    def test_raises_when_no_completed_assessment(self):
        student_without_assessment = make_user('nostudent@example.com', 'student')
        with self.assertRaises(InsightGenerationError):
            generate_student_insights(student_without_assessment)

    @patch('ai_insights.services.student_insights.get_provider')
    def test_successful_generation_stores_ready_insight(self, mock_get_provider):
        mock_get_provider.return_value = MockAIProvider()
        insight, generated = generate_student_insights(self.student)
        self.assertTrue(generated)
        self.assertEqual(insight.status, 'ready')
        self.assertTrue(insight.overview)
        self.assertEqual(StudentAIInsight.objects.filter(student=self.student).count(), 1)

    @patch('ai_insights.services.student_insights.get_provider')
    def test_reuses_existing_insight_when_profile_unchanged(self, mock_get_provider):
        provider = MockAIProvider()
        mock_get_provider.return_value = provider
        generate_student_insights(self.student)
        self.assertEqual(provider.call_count, 1)

        insight, generated = generate_student_insights(self.student, force=False)
        self.assertFalse(generated)
        self.assertEqual(provider.call_count, 1)  # no second API call

    @patch('ai_insights.services.student_insights.get_provider')
    def test_force_regeneration_calls_provider_again_and_archives_old(self, mock_get_provider):
        provider = MockAIProvider()
        mock_get_provider.return_value = provider
        generate_student_insights(self.student)
        insight, generated = generate_student_insights(self.student, force=True)
        self.assertTrue(generated)
        self.assertEqual(provider.call_count, 2)
        self.assertEqual(StudentAIInsightHistory.objects.filter(student=self.student).count(), 1)

    @patch('ai_insights.services.student_insights.get_provider')
    def test_provider_failure_marks_failed_when_no_prior_insight(self, mock_get_provider):
        mock_get_provider.return_value = MockAIProvider(raise_error=True)
        insight, generated = generate_student_insights(self.student)
        self.assertFalse(generated)
        self.assertEqual(insight.status, 'failed')

    @patch('ai_insights.services.student_insights.get_provider')
    def test_malformed_json_does_not_crash_and_marks_failed(self, mock_get_provider):
        mock_get_provider.return_value = MockAIProvider(response_text="not valid json at all")
        insight, generated = generate_student_insights(self.student)
        self.assertFalse(generated)
        self.assertEqual(insight.status, 'failed')

    def test_failed_regeneration_preserves_previous_good_insight(self):
        with patch('ai_insights.services.student_insights.get_provider') as mock_get_provider:
            mock_get_provider.return_value = MockAIProvider()
            insight, _ = generate_student_insights(self.student)
            original_overview = insight.overview

        with patch('ai_insights.services.student_insights.get_provider') as mock_get_provider:
            mock_get_provider.return_value = MockAIProvider(raise_error=True)
            insight, generated = generate_student_insights(self.student, force=True)

        self.assertFalse(generated)
        self.assertEqual(insight.status, 'ready')
        self.assertEqual(insight.overview, original_overview)


class AIInsightPermissionTests(TestCase):
    def setUp(self):
        self.teacher_a = make_user('teacherA@example.com', 'teacher')
        self.teacher_b = make_user('teacherB@example.com', 'teacher')
        self.student = make_assessed_student('aistudent@example.com')

        self.class_a = Class.objects.create(teacher=self.teacher_a, name='A Class')
        ClassStudent.objects.create(classroom=self.class_a, student=self.student)

    @patch('ai_insights.services.student_insights.get_provider')
    def test_owning_teacher_can_generate(self, mock_get_provider):
        mock_get_provider.return_value = MockAIProvider()
        self.client.force_login(self.teacher_a)
        response = self.client.post(reverse('ai_insights:generate', args=[self.student.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StudentAIInsight.objects.filter(student=self.student).exists())

    def test_other_teacher_cannot_generate(self):
        self.client.force_login(self.teacher_b)
        response = self.client.post(reverse('ai_insights:generate', args=[self.student.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(StudentAIInsight.objects.filter(student=self.student).exists())

    def test_student_cannot_access_generate_endpoint(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse('ai_insights:generate', args=[self.student.pk]))
        self.assertEqual(response.status_code, 403)

    @patch('ai_insights.services.student_insights.get_provider')
    def test_regeneration_cooldown_blocks_rapid_clicks(self, mock_get_provider):
        mock_get_provider.return_value = MockAIProvider()
        self.client.force_login(self.teacher_a)
        self.client.post(reverse('ai_insights:generate', args=[self.student.pk]))
        first_call_count = StudentAIInsight.objects.get(student=self.student).updated_at

        response = self.client.post(reverse('ai_insights:regenerate', args=[self.student.pk]))
        self.assertEqual(response.status_code, 302)
        # Still only the original insight — cooldown blocked the regeneration.
        self.assertEqual(StudentAIInsight.objects.get(student=self.student).updated_at, first_call_count)
