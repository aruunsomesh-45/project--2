import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from ai_insights.services.base import AIProvider, AIProviderError
from classroom.models import Class, ClassStudent

from .models import PlanAdaptationDraft, StudyPlan, StudyTask
from .services.plan_generation import apply_adaptation_draft, generate_plan_with_ai, request_adaptation
from .services.progress import calculate_progress
from .services.validators import validate_and_clean_tasks, validate_plan_structure


def make_user(username, role):
    user = User.objects.create_user(username=username, email=username, password='pass12345')
    Profile.objects.create(user=user, role=role, full_name=username.split('@')[0])
    return user


def make_plan(student, teacher, **overrides):
    today = timezone.localdate()
    defaults = {
        'student': student, 'teacher': teacher, 'subject': 'Mathematics', 'title': '',
        'goal': 'Pass the final exam', 'start_date': today, 'end_date': today + timedelta(days=13),
        'exam_date': today + timedelta(days=14), 'daily_minutes': 60,
        'available_days': [0, 1, 2, 3, 4], 'difficulty': 'intermediate',
    }
    defaults.update(overrides)
    return StudyPlan.objects.create(**defaults)


VALID_PLAN_RESPONSE = {
    "title": "Mathematics Final Exam Plan",
    "overview": "A focused two-week plan covering algebra fundamentals and practice.",
    "weeks": [
        {
            "week_number": 1,
            "focus": "Algebra Fundamentals",
            "tasks": [
                {
                    "date": "2026-11-01", "title": "Review algebra", "description": "Cover core identities.",
                    "estimated_minutes": 30, "task_type": "learning",
                },
            ],
        }
    ],
}


class MockAIProvider(AIProvider):
    def __init__(self, response_text=None, raise_error=False):
        self._response_text = response_text
        self._raise_error = raise_error
        self.call_count = 0

    @property
    def model_name(self):
        return 'mock-model'

    def generate(self, system_prompt, user_prompt):
        self.call_count += 1
        if self._raise_error:
            raise AIProviderError("mock failure")
        return self._response_text


def _valid_response_for(plan, minutes=30, count=2):
    """Build a valid AI response scheduling `count` tasks on the plan's
    first available day, well within the daily budget."""
    first_day = plan.start_date
    while first_day.weekday() not in (plan.available_days or [0, 1, 2, 3, 4]):
        first_day += timedelta(days=1)
    tasks = [
        {
            "date": first_day.isoformat(), "title": f"Task {i+1}",
            "description": "Practice problems.", "estimated_minutes": minutes, "task_type": "practice",
        }
        for i in range(count)
    ]
    return json.dumps({
        "title": "Mathematics Final Exam Plan",
        "overview": "A focused plan covering algebra fundamentals and practice.",
        "weeks": [{"week_number": 1, "focus": "Algebra", "tasks": tasks}],
    })


class ValidatorStructureTests(TestCase):
    def test_valid_structure_passes(self):
        is_valid, result = validate_plan_structure(VALID_PLAN_RESPONSE)
        self.assertTrue(is_valid)
        self.assertEqual(result['title'], VALID_PLAN_RESPONSE['title'])

    def test_missing_field_fails(self):
        bad = dict(VALID_PLAN_RESPONSE)
        del bad['weeks']
        is_valid, _ = validate_plan_structure(bad)
        self.assertFalse(is_valid)

    def test_not_a_dict_fails(self):
        is_valid, _ = validate_plan_structure(["a", "list"])
        self.assertFalse(is_valid)

    def test_empty_weeks_fails(self):
        bad = dict(VALID_PLAN_RESPONSE)
        bad['weeks'] = []
        is_valid, _ = validate_plan_structure(bad)
        self.assertFalse(is_valid)

    def test_no_usable_tasks_fails(self):
        bad = {"title": "X", "overview": "Y", "weeks": [{"week_number": 1, "focus": "Z", "tasks": []}]}
        is_valid, _ = validate_plan_structure(bad)
        self.assertFalse(is_valid)


class ValidatorBusinessRuleTests(TestCase):
    def setUp(self):
        self.teacher = make_user('vteacher@example.com', 'teacher')
        self.student = make_user('vstudent@example.com', 'student')
        self.plan = make_plan(self.student, self.teacher, daily_minutes=60, available_days=[0, 1, 2, 3, 4])

    def test_task_outside_date_range_dropped(self):
        raw = [{
            'date': (self.plan.end_date + timedelta(days=5)).isoformat(), 'title': 'Too late',
            'estimated_minutes': 30, 'task_type': 'practice',
        }]
        clean, warnings = validate_and_clean_tasks(self.plan, raw)
        self.assertEqual(clean, [])
        self.assertTrue(warnings)

    def test_task_after_exam_date_dropped(self):
        exam_plus_one = self.plan.exam_date + timedelta(days=1)
        end_date_extended = exam_plus_one
        self.plan.end_date = end_date_extended
        self.plan.save()
        raw = [{'date': exam_plus_one.isoformat(), 'title': 'After exam', 'estimated_minutes': 30, 'task_type': 'practice'}]
        clean, warnings = validate_and_clean_tasks(self.plan, raw)
        self.assertEqual(clean, [])

    def test_task_on_unavailable_day_dropped(self):
        # Find a day within range that's NOT in available_days [0-4] (i.e. a weekend)
        d = self.plan.start_date
        while d.weekday() in self.plan.available_days:
            d += timedelta(days=1)
            if d > self.plan.end_date:
                self.skipTest("No unavailable day within range for this fixture")
        raw = [{'date': d.isoformat(), 'title': 'Weekend task', 'estimated_minutes': 30, 'task_type': 'practice'}]
        clean, warnings = validate_and_clean_tasks(self.plan, raw)
        self.assertEqual(clean, [])

    def test_zero_duration_task_dropped(self):
        d = self.plan.start_date
        raw = [{'date': d.isoformat(), 'title': 'Bad duration', 'estimated_minutes': 0, 'task_type': 'practice'}]
        clean, _ = validate_and_clean_tasks(self.plan, raw)
        self.assertEqual(clean, [])

    def test_invalid_task_type_dropped(self):
        d = self.plan.start_date
        raw = [{'date': d.isoformat(), 'title': 'Bad type', 'estimated_minutes': 30, 'task_type': 'not_a_type'}]
        clean, _ = validate_and_clean_tasks(self.plan, raw)
        self.assertEqual(clean, [])

    def test_daily_minutes_limit_enforced(self):
        d = self.plan.start_date
        while d.weekday() not in self.plan.available_days:
            d += timedelta(days=1)
        raw = [
            {'date': d.isoformat(), 'title': 'Task A', 'estimated_minutes': 40, 'task_type': 'practice'},
            {'date': d.isoformat(), 'title': 'Task B', 'estimated_minutes': 40, 'task_type': 'practice'},  # 80 > 60 limit
        ]
        clean, warnings = validate_and_clean_tasks(self.plan, raw)
        self.assertEqual(len(clean), 1)
        self.assertTrue(any('daily' in w.lower() for w in warnings))

    def test_valid_task_within_all_constraints_kept(self):
        d = self.plan.start_date
        while d.weekday() not in self.plan.available_days:
            d += timedelta(days=1)
        raw = [{'date': d.isoformat(), 'title': 'Good task', 'estimated_minutes': 30, 'task_type': 'practice'}]
        clean, warnings = validate_and_clean_tasks(self.plan, raw)
        self.assertEqual(len(clean), 1)
        self.assertEqual(warnings, [])


class PlanGenerationTests(TestCase):
    def setUp(self):
        self.teacher = make_user('genteacher@example.com', 'teacher')
        self.student = make_user('genstudent@example.com', 'student')
        self.plan = make_plan(self.student, self.teacher)

    @patch('study_plans.services.plan_generation.get_provider')
    def test_successful_generation_creates_tasks_and_sets_provenance(self, mock_get_provider):
        mock_get_provider.return_value = MockAIProvider(response_text=_valid_response_for(self.plan))
        success, message, warnings = generate_plan_with_ai(self.plan)
        self.assertTrue(success)
        self.plan.refresh_from_db()
        self.assertTrue(self.plan.ai_generated)
        self.assertTrue(self.plan.title)
        self.assertEqual(self.plan.tasks.count(), 2)

    @patch('study_plans.services.plan_generation.get_provider')
    def test_provider_failure_does_not_create_tasks(self, mock_get_provider):
        mock_get_provider.return_value = MockAIProvider(raise_error=True)
        success, message, warnings = generate_plan_with_ai(self.plan)
        self.assertFalse(success)
        self.assertEqual(self.plan.tasks.count(), 0)

    @patch('study_plans.services.plan_generation.get_provider')
    def test_malformed_json_does_not_crash_and_creates_no_tasks(self, mock_get_provider):
        mock_get_provider.return_value = MockAIProvider(response_text="not json at all")
        success, message, warnings = generate_plan_with_ai(self.plan)
        self.assertFalse(success)
        self.assertEqual(self.plan.tasks.count(), 0)

    @patch('study_plans.services.plan_generation.get_provider')
    def test_daily_limit_violation_is_trimmed_not_trusted(self, mock_get_provider):
        # AI proposes way more than the daily budget allows on one day.
        response = _valid_response_for(self.plan, minutes=50, count=3)  # 150 min > 60 min budget
        mock_get_provider.return_value = MockAIProvider(response_text=response)
        success, message, warnings = generate_plan_with_ai(self.plan)
        self.assertTrue(success)
        total_minutes_that_day = sum(t.estimated_minutes for t in self.plan.tasks.all())
        self.assertLessEqual(total_minutes_that_day, self.plan.daily_minutes)
        self.assertTrue(warnings)


class ProgressCalculationTests(TestCase):
    def setUp(self):
        self.teacher = make_user('progteacher@example.com', 'teacher')
        self.student = make_user('progstudent@example.com', 'student')
        self.plan = make_plan(self.student, self.teacher, status='active')

    def test_progress_with_no_tasks(self):
        progress = calculate_progress(self.plan)
        self.assertEqual(progress['total_tasks'], 0)
        self.assertEqual(progress['completion_pct'], 0)

    def test_progress_counts_by_status(self):
        today = timezone.localdate()
        StudyTask.objects.create(study_plan=self.plan, title='A', date=today, estimated_minutes=30, task_type='practice', status='completed', completed_at=timezone.now())
        StudyTask.objects.create(study_plan=self.plan, title='B', date=today, estimated_minutes=20, task_type='practice', status='pending')
        StudyTask.objects.create(study_plan=self.plan, title='C', date=today, estimated_minutes=10, task_type='practice', status='skipped')

        progress = calculate_progress(self.plan)
        self.assertEqual(progress['total_tasks'], 3)
        self.assertEqual(progress['completed_tasks'], 1)
        self.assertEqual(progress['pending_tasks'], 1)
        self.assertEqual(progress['skipped_tasks'], 1)
        self.assertEqual(progress['completion_pct'], 33)  # 1/3 rounded
        self.assertEqual(progress['completed_minutes'], 30)

    def test_overdue_tasks_detected(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        StudyTask.objects.create(study_plan=self.plan, title='Late', date=yesterday, estimated_minutes=30, task_type='practice', status='pending')
        progress = calculate_progress(self.plan)
        self.assertEqual(progress['overdue_tasks'], 1)

    def test_completed_task_not_counted_as_overdue(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        StudyTask.objects.create(study_plan=self.plan, title='Done', date=yesterday, estimated_minutes=30, task_type='practice', status='completed', completed_at=timezone.now())
        progress = calculate_progress(self.plan)
        self.assertEqual(progress['overdue_tasks'], 0)


class TaskCompletionPermissionTests(TestCase):
    def setUp(self):
        self.teacher = make_user('tcteacher@example.com', 'teacher')
        self.student = make_user('tcstudent@example.com', 'student')
        self.other_student = make_user('tcother@example.com', 'student')
        self.plan = make_plan(self.student, self.teacher, status='active')
        self.task = StudyTask.objects.create(
            study_plan=self.plan, title='Task', date=timezone.localdate(), estimated_minutes=30,
            task_type='practice', status='pending',
        )

    def test_student_can_complete_own_task(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse('study_plans:task_complete', args=[self.task.pk]))
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'completed')
        self.assertIsNotNone(self.task.completed_at)

    def test_student_cannot_complete_others_task(self):
        self.client.force_login(self.other_student)
        response = self.client.post(reverse('study_plans:task_complete', args=[self.task.pk]))
        self.assertEqual(response.status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'pending')

    def test_student_can_skip_own_task(self):
        self.client.force_login(self.student)
        self.client.post(reverse('study_plans:task_skip', args=[self.task.pk]))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'skipped')


class TeacherPermissionTests(TestCase):
    def setUp(self):
        self.teacher_a = make_user('tpteacherA@example.com', 'teacher')
        self.teacher_b = make_user('tpteacherB@example.com', 'teacher')
        self.student = make_user('tpstudent@example.com', 'student')
        self.class_a = Class.objects.create(teacher=self.teacher_a, name='Class A')
        ClassStudent.objects.create(classroom=self.class_a, student=self.student)
        self.plan = make_plan(self.student, self.teacher_a)

    def test_owning_teacher_can_view_plan(self):
        self.client.force_login(self.teacher_a)
        response = self.client.get(reverse('study_plans_teacher:detail', args=[self.plan.pk]))
        self.assertEqual(response.status_code, 200)

    def test_other_teacher_cannot_view_plan(self):
        self.client.force_login(self.teacher_b)
        response = self.client.get(reverse('study_plans_teacher:detail', args=[self.plan.pk]))
        self.assertEqual(response.status_code, 403)

    def test_other_teacher_cannot_create_plan_for_unowned_student(self):
        self.client.force_login(self.teacher_b)
        response = self.client.get(reverse('study_plans_teacher:create', args=[self.student.pk]))
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_access_teacher_plan_list(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('study_plans_teacher:list'))
        self.assertEqual(response.status_code, 403)

    def test_approve_requires_at_least_one_task(self):
        self.client.force_login(self.teacher_a)
        response = self.client.post(reverse('study_plans_teacher:approve', args=[self.plan.pk]))
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, 'draft')

    def test_completed_task_cannot_be_deleted(self):
        task = StudyTask.objects.create(
            study_plan=self.plan, title='Done', date=timezone.localdate(), estimated_minutes=30,
            task_type='practice', status='completed', completed_at=timezone.now(),
        )
        self.client.force_login(self.teacher_a)
        self.client.post(reverse('study_plans_teacher:task_delete', args=[self.plan.pk, task.pk]))
        self.assertTrue(StudyTask.objects.filter(pk=task.pk).exists())


class AdaptationTests(TestCase):
    def setUp(self):
        self.teacher = make_user('adteacher@example.com', 'teacher')
        self.student = make_user('adstudent@example.com', 'student')
        self.plan = make_plan(self.student, self.teacher, status='active',
                               start_date=timezone.localdate() - timedelta(days=3),
                               end_date=timezone.localdate() + timedelta(days=10),
                               exam_date=timezone.localdate() + timedelta(days=11),
                               available_days=[0, 1, 2, 3, 4, 5, 6])
        today = timezone.localdate()
        # Historical: one completed (past), one skipped (past)
        self.completed_task = StudyTask.objects.create(
            study_plan=self.plan, title='Past done', date=today - timedelta(days=2),
            estimated_minutes=30, task_type='practice', status='completed', completed_at=timezone.now(),
        )
        self.skipped_task = StudyTask.objects.create(
            study_plan=self.plan, title='Past skipped', date=today - timedelta(days=1),
            estimated_minutes=30, task_type='practice', status='skipped',
        )
        # Future pending task that adaptation SHOULD be allowed to replace
        self.future_task = StudyTask.objects.create(
            study_plan=self.plan, title='Future pending', date=today + timedelta(days=2),
            estimated_minutes=30, task_type='practice', status='pending',
        )

    @patch('study_plans.services.plan_generation.get_provider')
    def test_adaptation_creates_draft_without_touching_db_tasks(self, mock_get_provider):
        today = timezone.localdate()
        future_date = today + timedelta(days=3)
        response_json = json.dumps({
            "title": "Updated", "overview": "Adjusted plan.",
            "weeks": [{"week_number": 1, "focus": "X", "tasks": [
                {"date": future_date.isoformat(), "title": "New future task", "description": "",
                 "estimated_minutes": 30, "task_type": "revision"},
            ]}],
        })
        mock_get_provider.return_value = MockAIProvider(response_text=response_json)
        draft, message = request_adaptation(self.plan, teacher_instructions='Focus more on revision')
        self.assertIsNotNone(draft)
        self.assertEqual(draft.status, 'pending_review')
        # Nothing in the DB changed yet
        self.assertEqual(self.plan.tasks.count(), 3)

    @patch('study_plans.services.plan_generation.get_provider')
    def test_applying_adaptation_preserves_completed_and_skipped_history(self, mock_get_provider):
        today = timezone.localdate()
        future_date = today + timedelta(days=3)
        response_json = json.dumps({
            "title": "Updated", "overview": "Adjusted plan.",
            "weeks": [{"week_number": 1, "focus": "X", "tasks": [
                {"date": future_date.isoformat(), "title": "New future task", "description": "",
                 "estimated_minutes": 30, "task_type": "revision"},
            ]}],
        })
        mock_get_provider.return_value = MockAIProvider(response_text=response_json)
        draft, _ = request_adaptation(self.plan)
        apply_adaptation_draft(draft)

        self.assertTrue(StudyTask.objects.filter(pk=self.completed_task.pk).exists())
        self.assertTrue(StudyTask.objects.filter(pk=self.skipped_task.pk).exists())
        self.assertFalse(StudyTask.objects.filter(pk=self.future_task.pk).exists())
        self.assertTrue(StudyTask.objects.filter(title='New future task').exists())

        draft.refresh_from_db()
        self.assertEqual(draft.status, 'applied')

    def test_apply_adaptation_never_touches_past_dates(self):
        today = timezone.localdate()
        draft = PlanAdaptationDraft.objects.create(
            study_plan=self.plan,
            proposed_tasks=[{
                'title': 'Should not appear', 'description': '', 'date': (today - timedelta(days=1)).isoformat(),
                'estimated_minutes': 20, 'task_type': 'practice', 'order': 1,
            }],
        )
        apply_adaptation_draft(draft)
        # validate_and_clean_tasks would have dropped this before draft
        # creation in the real flow; this test directly exercises apply()
        # to confirm it doesn't touch the historical skipped task either.
        self.assertTrue(StudyTask.objects.filter(pk=self.skipped_task.pk, status='skipped').exists())
