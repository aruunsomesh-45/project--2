import string
import random
from django.db import models
from django.contrib.auth.models import User


def generate_unique_class_code():
    """Generates a random 6-character uppercase alphanumeric class code."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        if not Class.objects.filter(class_code=code).exists():
            return code


class Class(models.Model):
    """
    A classroom created by a teacher.

    Students join using the shareable `class_code`.
    """
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_classes',
    )
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=100, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    section = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    class_code = models.CharField(
        max_length=10,
        unique=True,
        default=generate_unique_class_code,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Classes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['teacher']),
        ]

    def __str__(self):
        return f"{self.name} ({self.class_code})"


class ClassStudent(models.Model):
    """
    Junction table representing a student enrolled in a class.
    """
    classroom = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='enrolments',
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrolled_classes',
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-joined_at']
        constraints = [
            models.UniqueConstraint(
                fields=['classroom', 'student'],
                name='unique_class_student',
            )
        ]

    def __str__(self):
        return f"{self.student.profile.full_name} in {self.classroom.name}"
