from django.core.exceptions import PermissionDenied

from classroom.models import ClassStudent


def check_teacher_owns_student(teacher, student_id):
    """Same rule as classroom/ai_insights: a teacher may only act on
    students enrolled in one of their own classes (or be a superuser)."""
    if teacher.is_superuser:
        return
    if not ClassStudent.objects.filter(classroom__teacher=teacher, student_id=student_id).exists():
        raise PermissionDenied("You can only manage study plans for students enrolled in your classes.")


def check_teacher_owns_plan(teacher, plan):
    check_teacher_owns_student(teacher, plan.student_id)


def check_student_owns_task(student, task):
    if task.study_plan.student_id != student.pk:
        raise PermissionDenied("You can only manage your own study tasks.")
