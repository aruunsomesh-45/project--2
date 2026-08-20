from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Profile
from .models import Class, ClassStudent


def make_user(username, role, password='pass12345'):
    user = User.objects.create_user(username=username, email=username, password=password)
    Profile.objects.create(user=user, role=role, full_name=username.split('@')[0])
    return user


class ClassCodeTests(TestCase):
    def test_class_code_is_unique_and_generated(self):
        teacher = make_user('teacher1@example.com', 'teacher')
        c1 = Class.objects.create(teacher=teacher, name='Class 1')
        c2 = Class.objects.create(teacher=teacher, name='Class 2')
        self.assertNotEqual(c1.class_code, c2.class_code)
        self.assertTrue(c1.class_code)


class ClassMembershipTests(TestCase):
    def setUp(self):
        self.teacher = make_user('teacher2@example.com', 'teacher')
        self.student = make_user('student1@example.com', 'student')
        self.class_obj = Class.objects.create(teacher=self.teacher, name='Math 101')

    def test_student_can_join_with_valid_active_code(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse('classroom:join_class'), {'class_code': self.class_obj.class_code})
        self.assertRedirects(response, reverse('classroom:join_class'))
        self.assertTrue(ClassStudent.objects.filter(classroom=self.class_obj, student=self.student).exists())

    def test_join_code_is_case_insensitive(self):
        self.client.force_login(self.student)
        self.client.post(reverse('classroom:join_class'), {'class_code': self.class_obj.class_code.lower()})
        self.assertTrue(ClassStudent.objects.filter(classroom=self.class_obj, student=self.student).exists())

    def test_cannot_join_with_invalid_code(self):
        self.client.force_login(self.student)
        self.client.post(reverse('classroom:join_class'), {'class_code': 'NOPE99'})
        self.assertFalse(ClassStudent.objects.filter(classroom=self.class_obj, student=self.student).exists())

    def test_cannot_join_inactive_class(self):
        self.class_obj.is_active = False
        self.class_obj.save()
        self.client.force_login(self.student)
        self.client.post(reverse('classroom:join_class'), {'class_code': self.class_obj.class_code})
        self.assertFalse(ClassStudent.objects.filter(classroom=self.class_obj, student=self.student).exists())

    def test_duplicate_membership_prevented(self):
        ClassStudent.objects.create(classroom=self.class_obj, student=self.student)
        self.client.force_login(self.student)
        self.client.post(reverse('classroom:join_class'), {'class_code': self.class_obj.class_code})
        self.assertEqual(
            ClassStudent.objects.filter(classroom=self.class_obj, student=self.student).count(), 1
        )


class TeacherPermissionTests(TestCase):
    def setUp(self):
        self.teacher_a = make_user('teacherA@example.com', 'teacher')
        self.teacher_b = make_user('teacherB@example.com', 'teacher')
        self.student = make_user('student2@example.com', 'student')

        self.class_a = Class.objects.create(teacher=self.teacher_a, name='A Class')
        ClassStudent.objects.create(classroom=self.class_a, student=self.student)

    def test_teacher_can_view_own_class(self):
        self.client.force_login(self.teacher_a)
        response = self.client.get(reverse('classroom:class_detail', args=[self.class_a.pk]))
        self.assertEqual(response.status_code, 200)

    def test_teacher_cannot_view_another_teachers_class(self):
        self.client.force_login(self.teacher_b)
        response = self.client.get(reverse('classroom:class_detail', args=[self.class_a.pk]))
        self.assertEqual(response.status_code, 403)

    def test_teacher_cannot_edit_another_teachers_class(self):
        self.client.force_login(self.teacher_b)
        response = self.client.post(
            reverse('classroom:class_edit', args=[self.class_a.pk]), {'name': 'Hijacked'}
        )
        self.assertEqual(response.status_code, 403)
        self.class_a.refresh_from_db()
        self.assertEqual(self.class_a.name, 'A Class')

    def test_teacher_cannot_view_another_teachers_student(self):
        self.client.force_login(self.teacher_b)
        response = self.client.get(reverse('classroom:student_profile', args=[self.student.pk]))
        self.assertEqual(response.status_code, 403)

    def test_teacher_can_view_own_student(self):
        self.client.force_login(self.teacher_a)
        response = self.client.get(reverse('classroom:student_profile', args=[self.student.pk]))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_teacher_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('classroom:dashboard'))
        self.assertEqual(response.status_code, 403)


class StudentSearchFilterTests(TestCase):
    def setUp(self):
        self.teacher = make_user('teacher3@example.com', 'teacher')
        self.class_obj = Class.objects.create(teacher=self.teacher, name='Search Class')

        self.arun = make_user('arun@example.com', 'student')
        self.arun.profile.full_name = 'Arun Kumar'
        self.arun.profile.save()
        ClassStudent.objects.create(classroom=self.class_obj, student=self.arun)

        self.rahul = make_user('rahul@example.com', 'student')
        self.rahul.profile.full_name = 'Rahul Singh'
        self.rahul.profile.save()
        ClassStudent.objects.create(classroom=self.class_obj, student=self.rahul)

    def test_search_by_name(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('classroom:class_detail', args=[self.class_obj.pk]), {'q': 'arun'})
        self.assertContains(response, 'Arun Kumar')
        self.assertNotContains(response, 'Rahul Singh')

    def test_search_by_email_case_insensitive(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('classroom:class_detail', args=[self.class_obj.pk]), {'q': 'RAHUL@EXAMPLE'})
        self.assertContains(response, 'Rahul Singh')
        self.assertNotContains(response, 'Arun Kumar')


class StudentProfilePageTests(TestCase):
    """Phase 2: assessment status distinction on the teacher-facing student page."""

    def setUp(self):
        self.teacher = make_user('teacher4@example.com', 'teacher')
        self.class_obj = Class.objects.create(teacher=self.teacher, name='Status Class')
        self.student = make_user('statusstudent@example.com', 'student')
        ClassStudent.objects.create(classroom=self.class_obj, student=self.student)
        self.client.force_login(self.teacher)

    def test_shows_not_started_when_no_answers(self):
        response = self.client.get(reverse('classroom:student_profile', args=[self.student.pk]))
        self.assertContains(response, 'Assessment Not Started')

    def test_roster_reflects_not_started_status(self):
        response = self.client.get(reverse('classroom:class_detail', args=[self.class_obj.pk]))
        self.assertContains(response, 'Not Started')

    def test_status_filter_excludes_non_matching_students(self):
        response = self.client.get(
            reverse('classroom:class_detail', args=[self.class_obj.pk]), {'status': 'completed'}
        )
        self.assertNotContains(response, self.student.profile.full_name)
