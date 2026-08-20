from django.db import models
from django.contrib.auth.models import User


class AssessmentQuestion(models.Model):
    """
    A single question in the learning assessment.

    Each question belongs to a `dimension` (e.g., 'Analytical Thinking')
    and is either a Likert-scale or multiple-choice question.
    Questions are displayed in `display_order`.
    """

    QUESTION_TYPE_CHOICES = [
        ('likert', 'Likert Scale'),
        ('multiple_choice', 'Multiple Choice'),
    ]

    dimension = models.CharField(
        max_length=100,
        help_text='Learning dimension this question measures, e.g. "Analytical Thinking"',
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
    )
    options = models.JSONField(
        null=True,
        blank=True,
        help_text='For multiple_choice: list of option strings. Null for likert.',
    )
    display_order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.dimension}] Q{self.display_order}: {self.question_text[:60]}"

    class Meta:
        ordering = ['display_order']


class AssessmentResponse(models.Model):
    """
    A student's answer to a single assessment question.

    Auto-saved as the student progresses — upserts on (student, question).
    The answer_value stores:
        - An integer (1-5) for Likert questions
        - A string (selected option) for multiple choice
    """

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assessment_responses',
    )
    question = models.ForeignKey(
        AssessmentQuestion,
        on_delete=models.CASCADE,
        related_name='responses',
    )
    answer_value = models.JSONField(
        help_text='Numeric (1-5) for likert, or selected option string for multiple_choice.',
    )
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'question'],
                name='unique_student_question',
            )
        ]
        ordering = ['question__display_order']

    def __str__(self):
        return f"{self.student.profile.full_name} → Q{self.question.display_order}: {self.answer_value}"


class LearningProfile(models.Model):
    """
    The result of scoring a student's completed assessment.

    One per student (upserted if retaken). Contains:
        - archetype: e.g. "The Problem Solver"
        - dimension_scores: { "Analytical Thinking": 88, ... }
        - strengths: ["Strong analytical skills", ...]
        - challenges: ["May overthink simple problems", ...]
        - recommendations: ["Try hands-on practice exercises", ...]
    """

    student = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='learning_profile',
    )
    archetype = models.CharField(max_length=100)
    dimension_scores = models.JSONField()
    strengths = models.JSONField()
    challenges = models.JSONField()
    recommendations = models.JSONField()
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.profile.full_name} — {self.archetype}"
