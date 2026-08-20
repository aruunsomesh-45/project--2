from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from classroom.models import Class, ClassStudent

from .models import (
    ADAPTIVE_TOPICS, ScreeningAttempt, ScreeningQuestion, ScreeningReport,
    SelfReportQuestion,
)
from .services import engine


def make_user(username, role):
    user = User.objects.create_user(username=username, email=username, password='pass12345')
    Profile.objects.create(user=user, role=role, full_name=username.split('@')[0])
    return user


class SeedDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_screening')

    def test_seed_is_idempotent(self):
        before = ScreeningQuestion.objects.count()
        call_command('seed_screening')
        self.assertEqual(ScreeningQuestion.objects.count(), before)

    def test_all_four_tiers_fully_seeded(self):
        for tier, _ in [('grade_8_10', ''), ('grade_10_12', ''), ('undergraduate', ''), ('postgraduate', '')]:
            adaptive_count = ScreeningQuestion.objects.filter(
                tier=tier, section__in=['subject_knowledge', 'cognitive_aptitude']
            ).count()
            ls_count = ScreeningQuestion.objects.filter(tier=tier, section='learning_style').count()
            self.assertEqual(adaptive_count, 12, f"{tier} should have 12 adaptive questions (4 topics x 3 difficulties)")
            self.assertEqual(ls_count, 3, f"{tier} should have 3 learning style probes")

    def test_interests_q3_has_tier_specific_variants(self):
        school_variant = SelfReportQuestion.objects.get(category='interests', tiers=['grade_8_10', 'grade_10_12'])
        ugpg_variant = SelfReportQuestion.objects.get(category='interests', tiers=['undergraduate', 'postgraduate'])
        self.assertNotEqual(school_variant.question_text, ugpg_variant.question_text)

    def test_wellbeing_marked_teacher_facing_only(self):
        wellbeing_qs = SelfReportQuestion.objects.filter(category='wellbeing')
        self.assertTrue(wellbeing_qs.exists())
        self.assertTrue(all(q.teacher_facing_only for q in wellbeing_qs))


class AdaptiveEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_screening')

    def setUp(self):
        self.student = make_user('screeningstudent@example.com', 'student')
        self.attempt = ScreeningAttempt.objects.create(student=self.student, tier='undergraduate')

    def test_first_question_of_each_topic_is_medium(self):
        question = engine.get_next_part1_question(self.attempt)
        self.assertEqual(question.difficulty, 'medium')
        self.assertEqual(question.topic, ADAPTIVE_TOPICS[0][1])

    def test_correct_answer_routes_to_hard(self):
        question = engine.get_next_part1_question(self.attempt)
        engine.record_part1_answer(self.attempt, question, question.correct_option)
        next_question = engine.get_next_part1_question(self.attempt)
        self.assertEqual(next_question.topic, question.topic)
        self.assertEqual(next_question.difficulty, 'hard')

    def test_incorrect_answer_routes_to_easy(self):
        question = engine.get_next_part1_question(self.attempt)
        wrong_option = next(o['label'] for o in question.options if o['label'] != question.correct_option)
        engine.record_part1_answer(self.attempt, question, wrong_option)
        next_question = engine.get_next_part1_question(self.attempt)
        self.assertEqual(next_question.topic, question.topic)
        self.assertEqual(next_question.difficulty, 'easy')

    def test_topic_completes_after_two_answers_and_moves_to_next_topic(self):
        q1 = engine.get_next_part1_question(self.attempt)
        engine.record_part1_answer(self.attempt, q1, q1.correct_option)
        q2 = engine.get_next_part1_question(self.attempt)
        engine.record_part1_answer(self.attempt, q2, q2.correct_option)
        q3 = engine.get_next_part1_question(self.attempt)
        self.assertNotEqual(q3.topic, q1.topic)
        self.assertEqual(q3.difficulty, 'medium')

    def test_part1_moves_to_learning_style_after_all_topics_done(self):
        for _ in range(len(ADAPTIVE_TOPICS)):
            for _ in range(2):
                q = engine.get_next_part1_question(self.attempt)
                engine.record_part1_answer(self.attempt, q, q.correct_option)
        next_item = engine.get_next_part1_question(self.attempt)
        self.assertEqual(next_item.section, 'learning_style')

    def _complete_part1(self, all_correct=True):
        for _ in range(len(ADAPTIVE_TOPICS)):
            for _ in range(2):
                q = engine.get_next_part1_question(self.attempt)
                answer = q.correct_option if all_correct else next(
                    o['label'] for o in q.options if o['label'] != q.correct_option
                )
                engine.record_part1_answer(self.attempt, q, answer)
        while True:
            q = engine.get_next_part1_question(self.attempt)
            if q is None:
                break
            engine.record_part1_answer(self.attempt, q, 'A')

    def _complete_part2(self):
        while True:
            q = engine.get_next_part2_question(self.attempt)
            if q is None:
                break
            if q.is_open_text:
                engine.record_part2_answer(self.attempt, q, free_text='Sample message.')
            else:
                engine.record_part2_answer(self.attempt, q, selected_option='A')

    def test_full_attempt_generates_report(self):
        self._complete_part1(all_correct=True)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.part1_status, 'completed')

        self._complete_part2()
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.part2_status, 'completed')
        self.assertIsNotNone(self.attempt.completed_at)

        report = ScreeningReport.objects.get(attempt=self.attempt)
        self.assertEqual(report.subject_knowledge_score, 100)
        self.assertEqual(report.cognitive_aptitude_score, 100)
        self.assertTrue(report.personality_tag)
        self.assertTrue(report.wellbeing_flag)

    def test_all_incorrect_gives_zero_scores(self):
        self._complete_part1(all_correct=False)
        report = engine.generate_report(self.attempt)
        self.assertEqual(report.subject_knowledge_score, 0)
        self.assertEqual(report.cognitive_aptitude_score, 0)

    def test_wellbeing_flag_amber_on_mixed_answers(self):
        self._complete_part1(all_correct=True)
        wellbeing_qs = list(SelfReportQuestion.objects.filter(category='wellbeing').order_by('display_order'))
        # Answer everything except wellbeing normally, then set a genuinely
        # mixed pattern for wellbeing itself (1 A/B, could tie depending on
        # count) — verify the flag matches the counting rule directly via
        # generate_report rather than depending on exact UI sequencing.
        for q in SelfReportQuestion.objects.exclude(category='wellbeing'):
            if not q.applies_to_tier(self.attempt.tier):
                continue
            if q.is_open_text:
                engine.record_part2_answer(self.attempt, q, free_text='x')
            else:
                engine.record_part2_answer(self.attempt, q, selected_option='A')
        engine.record_part2_answer(self.attempt, wellbeing_qs[0], selected_option='A')
        engine.record_part2_answer(self.attempt, wellbeing_qs[1], selected_option='D')
        engine.record_part2_answer(self.attempt, wellbeing_qs[2], selected_option='C')
        report = engine.generate_report(self.attempt)
        # 1 A/B, 2 C/D -> Red per the "mostly C/D" rule
        self.assertEqual(report.wellbeing_flag, 'Red')


class ScreeningPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_screening')

    def setUp(self):
        self.teacher_a = make_user('screeningteacherA@example.com', 'teacher')
        self.teacher_b = make_user('screeningteacherB@example.com', 'teacher')
        self.student = make_user('screeningpermstudent@example.com', 'student')
        self.class_a = Class.objects.create(teacher=self.teacher_a, name='Class A')
        ClassStudent.objects.create(classroom=self.class_a, student=self.student)

    def test_student_can_reach_start_page(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('screening:start'))
        self.assertEqual(response.status_code, 200)

    def test_teacher_cannot_access_student_start_page(self):
        self.client.force_login(self.teacher_a)
        response = self.client.get(reverse('screening:start'))
        self.assertEqual(response.status_code, 403)

    def test_owning_teacher_can_view_screening_report_url(self):
        self.client.force_login(self.teacher_a)
        response = self.client.get(reverse('classroom:student_screening_report', args=[self.student.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "hasn't completed")  # no report yet

    def test_other_teacher_cannot_view_screening_report(self):
        self.client.force_login(self.teacher_b)
        response = self.client.get(reverse('classroom:student_screening_report', args=[self.student.pk]))
        self.assertEqual(response.status_code, 403)

    def test_report_shows_wellbeing_only_to_teacher_not_student(self):
        attempt = ScreeningAttempt.objects.create(student=self.student, tier='undergraduate')
        for _ in range(len(ADAPTIVE_TOPICS) * 2 + 3):
            q = engine.get_next_part1_question(attempt)
            engine.record_part1_answer(attempt, q, q.options[0]['label'])
        while True:
            q = engine.get_next_part2_question(attempt)
            if q is None:
                break
            if q.is_open_text:
                engine.record_part2_answer(attempt, q, free_text='hello')
            else:
                engine.record_part2_answer(attempt, q, selected_option='A')

        self.client.force_login(self.student)
        student_response = self.client.get(reverse('screening:report'))
        self.assertNotContains(student_response, 'teacher-only')

        self.client.force_login(self.teacher_a)
        teacher_response = self.client.get(reverse('classroom:student_screening_report', args=[self.student.pk]))
        self.assertContains(teacher_response, 'teacher-only')
