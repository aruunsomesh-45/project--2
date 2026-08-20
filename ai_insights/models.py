from django.db import models
from django.contrib.auth.models import User


class StudentAIInsight(models.Model):
    """
    AI-generated teacher-facing interpretation of a student's Phase 2
    Learning Profile.

    This is NOT the source of truth for the student's scores — Phase 2's
    deterministic scoring engine (assessment/scoring.py) remains that.
    This model only stores the AI layer's *interpretation* of that data,
    so it can be regenerated, versioned, or removed without touching the
    underlying assessment/scoring system at all.

    One row per student (upserted on regeneration); `status` distinguishes
    a usable result from a pending/failed generation attempt so the UI can
    fall back to the Phase 2 profile without crashing.
    """

    STATUS_CHOICES = [
        ('ready', 'Ready'),
        ('generating', 'Generating'),
        ('failed', 'Failed'),
    ]

    student = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='ai_insight',
    )

    # --- Structured AI output (see ai_insights/services/prompts.py for the
    # exact JSON contract this is validated against) ---
    overview = models.TextField(blank=True)
    learning_preferences = models.JSONField(default=list, blank=True)
    strength_insights = models.JSONField(default=list, blank=True)
    development_insights = models.JSONField(default=list, blank=True)
    teaching_strategies = models.JSONField(default=list, blank=True)
    communication = models.JSONField(default=list, blank=True)
    classroom_recommendations = models.JSONField(default=list, blank=True)
    potential_challenges = models.JSONField(default=list, blank=True)
    teacher_actions = models.JSONField(default=list, blank=True)

    # --- Versioning / provenance (Phase 3 spec §24) ---
    # profile_version: bumped whenever the underlying LearningProfile this
    # insight was generated from changes (we use its dimension_scores hash
    # as a cheap invalidation signal — see services/student_insights.py).
    source_profile_snapshot = models.CharField(max_length=64, blank=True)
    prompt_version = models.CharField(max_length=50, blank=True)
    model_name = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AI Insight for {self.student.profile.full_name} ({self.status})"


class StudentAIInsightHistory(models.Model):
    """
    A snapshot of a previous StudentAIInsight, taken right before a
    regeneration overwrites it. Regeneration should never silently destroy
    the prior interpretation (Phase 3 spec §25) — this is the lightweight
    version of that without building a full attempt-comparison system.
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_insight_history',
    )
    overview = models.TextField(blank=True)
    learning_preferences = models.JSONField(default=list, blank=True)
    strength_insights = models.JSONField(default=list, blank=True)
    development_insights = models.JSONField(default=list, blank=True)
    teaching_strategies = models.JSONField(default=list, blank=True)
    communication = models.JSONField(default=list, blank=True)
    classroom_recommendations = models.JSONField(default=list, blank=True)
    potential_challenges = models.JSONField(default=list, blank=True)
    teacher_actions = models.JSONField(default=list, blank=True)
    prompt_version = models.CharField(max_length=50, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Student AI insight history'
        ordering = ['-archived_at']

    def __str__(self):
        return f"Archived insight for {self.student.profile.full_name} ({self.archived_at:%Y-%m-%d})"
