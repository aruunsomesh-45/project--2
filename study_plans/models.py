from django.db import models
from django.contrib.auth.models import User


DIFFICULTY_CHOICES = [
    ('beginner', 'Beginner'),
    ('intermediate', 'Intermediate'),
    ('advanced', 'Advanced'),
]

PLAN_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('active', 'Active'),
    ('completed', 'Completed'),
    ('archived', 'Archived'),
]

TASK_TYPE_CHOICES = [
    ('learning', 'Learning'),
    ('practice', 'Practice'),
    ('revision', 'Revision'),
    ('quiz', 'Quiz'),
    ('reflection', 'Reflection'),
    ('review', 'Review'),
    ('assessment', 'Assessment'),
]

TASK_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('skipped', 'Skipped'),
]

RESOURCE_TYPE_CHOICES = [
    ('video', 'Video'),
    ('article', 'Article'),
    ('document', 'Document'),
    ('link', 'Link'),
    ('exercise', 'Exercise'),
]

# 0=Monday .. 6=Sunday, matching date.weekday()
WEEKDAY_CHOICES = [
    (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'),
    (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
]


class StudyPlan(models.Model):
    """
    A personalized study plan a teacher creates for one student — either
    AI-generated (via study_plans/services/plan_generation.py, reusing the
    Phase 3 AI provider) or built manually. Never active/visible to the
    student until a teacher explicitly approves it (see `status`).
    """
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_plans')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_study_plans')

    subject = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    goal = models.CharField(max_length=300)
    description = models.TextField(blank=True)

    start_date = models.DateField()
    end_date = models.DateField()
    exam_date = models.DateField(null=True, blank=True)

    daily_minutes = models.PositiveIntegerField(help_text='Maximum study minutes per day.')
    available_days = models.JSONField(default=list, help_text='List of weekday ints (0=Monday..6=Sunday) the student can study.')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='intermediate')
    teacher_instructions = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=PLAN_STATUS_CHOICES, default='draft')

    # AI provenance — mirrors ai_insights.StudentAIInsight's pattern.
    ai_generated = models.BooleanField(default=False)
    prompt_version = models.CharField(max_length=50, blank=True)
    model_name = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['student']), models.Index(fields=['teacher'])]

    def __str__(self):
        return f"{self.title} — {self.student.profile.full_name} ({self.get_status_display()})"


class StudyTask(models.Model):
    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField()
    estimated_minutes = models.PositiveIntegerField()
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, blank=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='pending')
    order = models.PositiveIntegerField(default=1)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'order']
        indexes = [models.Index(fields=['study_plan', 'date'])]

    def __str__(self):
        return f"{self.title} ({self.date}) — {self.get_status_display()}"


class StudyResource(models.Model):
    study_task = models.ForeignKey(StudyTask, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.title


class PlanAdaptationDraft(models.Model):
    """
    A proposed adaptation of a plan's *future* tasks, held for teacher
    review before anything in the database actually changes. Applying a
    draft only ever touches tasks with date >= today and status in
    (pending, in_progress) — completed/skipped tasks and past history are
    never modified or deleted (Phase 4 spec's most important rule).
    """
    STATUS_CHOICES = [('pending_review', 'Pending Review'), ('applied', 'Applied'), ('discarded', 'Discarded')]

    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='adaptation_drafts')
    teacher_instructions = models.TextField(blank=True)
    # Validated, ready-to-apply task list: [{title, description, date, estimated_minutes, task_type}, ...]
    proposed_tasks = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_review')
    prompt_version = models.CharField(max_length=50, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Adaptation draft for {self.study_plan.title} ({self.status})"
