from django.db import models
from django.contrib.auth.models import User


TIER_CHOICES = [
    ('grade_8_10', 'Grade 8-10'),
    ('grade_10_12', 'Grade 10-12'),
    ('undergraduate', 'Undergraduate'),
    ('postgraduate', 'Postgraduate'),
]
TIER_CODES = [code for code, _ in TIER_CHOICES]

SECTION_CHOICES = [
    ('subject_knowledge', 'Subject Knowledge'),
    ('cognitive_aptitude', 'Cognitive Aptitude'),
    ('learning_style', 'Learning Style'),
]

DIFFICULTY_CHOICES = [
    ('easy', 'Easy'),
    ('medium', 'Medium'),
    ('hard', 'Hard'),
]

# The four adaptive topics, in the fixed order they're presented.
ADAPTIVE_TOPICS = [
    ('subject_knowledge', 'Reading Comprehension'),
    ('subject_knowledge', 'General Awareness'),
    ('cognitive_aptitude', 'Pattern & Code Reasoning'),
    ('cognitive_aptitude', 'Verbal / Logical Reasoning'),
]

# Learning Style Probe answer options map to the same style tag on every
# question, consistently across all tiers (per the source question bank).
LEARNING_STYLE_TAGS = {
    'A': 'Visual',
    'B': 'Reading/Verbal',
    'C': 'Practical/Kinesthetic',
    'D': 'Reasoning/Theoretical',
}

CATEGORY_CHOICES = [
    ('personality', 'Personality'),
    ('interests', 'Interests & Career Inclination'),
    ('wellbeing', 'Wellbeing & Motivation'),
    ('soft_skills', 'Soft Skills & Behavior'),
    ('open_message', 'Open Message to Teacher'),
]


class ScreeningQuestion(models.Model):
    """
    Part 1 content: adaptive Subject Knowledge / Cognitive Aptitude
    questions (right-or-wrong, difficulty-tiered) and the non-adaptive
    Learning Style probes. One tier-specific bank per grade tier.
    """
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    section = models.CharField(max_length=20, choices=SECTION_CHOICES)
    topic = models.CharField(max_length=100, blank=True, help_text='e.g. "Reading Comprehension". Blank for learning_style.')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, blank=True, help_text='Blank for learning_style probes (non-adaptive).')
    passage = models.TextField(blank=True, help_text='Optional reading passage shown above the question.')
    question_text = models.TextField()
    # Each option: {"label": "A", "text": "...", "tag": "Visual"}  (tag only used for learning_style)
    options = models.JSONField()
    correct_option = models.CharField(max_length=1, blank=True, help_text='A/B/C/D. Blank for learning_style probes (not scored).')
    display_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['tier', 'section', 'topic', 'display_order']

    def __str__(self):
        label = self.topic or 'Learning Style Probe'
        diff = f" ({self.get_difficulty_display()})" if self.difficulty else ''
        return f"[{self.get_tier_display()}] {label}{diff}: {self.question_text[:50]}"


class SelfReportQuestion(models.Model):
    """
    Part 2 content: personality, interests, wellbeing, soft skills, and the
    open-ended message to the teacher. Shared across tiers by default;
    `tiers` restricts a question to specific tiers for wording variants
    (e.g. the Interests Q3 elective/career-field wording).
    """
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    sub_key = models.CharField(max_length=50, blank=True, help_text='Stable key for this sub-question, e.g. "confidence", "deadlines" — used to key tags in the report.')
    tiers = models.JSONField(default=list, blank=True, help_text='Tier codes this question applies to. Empty = all tiers.')
    question_text = models.TextField()
    options = models.JSONField(default=list, blank=True, help_text='[{"label": "A", "text": "...", "tag": "Achiever"}, ...]. Empty for open-text questions.')
    is_open_text = models.BooleanField(default=False)
    teacher_facing_only = models.BooleanField(default=False, help_text='If true, this response/derived flag is shown only to teachers, never to the student or any aggregate view.')
    display_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['category', 'display_order']

    def applies_to_tier(self, tier):
        return not self.tiers or tier in self.tiers

    def __str__(self):
        return f"[{self.get_category_display()}] {self.question_text[:50]}"


class ScreeningAttempt(models.Model):
    """
    One screening test-taking session for a student. Adaptive state for
    Part 1 is derived from ScreeningResponse rows (no separate state to
    keep in sync) — see screening/services/engine.py.
    """
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='screening_attempts')
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    part1_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    part2_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    @property
    def is_completed(self):
        return self.part1_status == 'completed' and self.part2_status == 'completed'

    def __str__(self):
        return f"{self.student.profile.full_name} — {self.get_tier_display()} ({self.started_at:%Y-%m-%d})"


class ScreeningResponse(models.Model):
    """A student's answer to one Part 1 question within an attempt."""
    attempt = models.ForeignKey(ScreeningAttempt, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(ScreeningQuestion, on_delete=models.CASCADE, related_name='responses')
    selected_option = models.CharField(max_length=1)
    is_correct = models.BooleanField(null=True, blank=True, help_text='Null for non-scored learning_style probes.')
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['attempt', 'question'], name='unique_attempt_question_response'),
        ]
        ordering = ['answered_at']


class SelfReportResponse(models.Model):
    """A student's answer to one Part 2 question within an attempt."""
    attempt = models.ForeignKey(ScreeningAttempt, on_delete=models.CASCADE, related_name='self_report_responses')
    question = models.ForeignKey(SelfReportQuestion, on_delete=models.CASCADE, related_name='responses')
    selected_option = models.CharField(max_length=1, blank=True)
    free_text = models.TextField(blank=True)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['attempt', 'question'], name='unique_attempt_self_report_question'),
        ]
        ordering = ['answered_at']


class ScreeningReport(models.Model):
    """
    Generated once both parts of an attempt are complete. Deterministic —
    no AI involved. `wellbeing_flag` and `open_message` are teacher-facing
    only per the source material; views must never surface them to the
    student or to any cross-student aggregate.
    """
    attempt = models.OneToOneField(ScreeningAttempt, on_delete=models.CASCADE, related_name='report')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='screening_reports')

    subject_knowledge_score = models.PositiveIntegerField(default=0)
    cognitive_aptitude_score = models.PositiveIntegerField(default=0)

    personality_tag = models.CharField(max_length=50, blank=True)
    interest_tag = models.CharField(max_length=50, blank=True)
    learning_style_tag = models.CharField(max_length=50, blank=True)

    # Teacher-facing only (spec: "never shown to the institution's aggregate dashboard")
    wellbeing_flag = models.CharField(max_length=10, blank=True)  # Green / Amber / Red
    soft_skills_tags = models.JSONField(default=dict, blank=True)
    open_message = models.TextField(blank=True)

    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Screening Report — {self.student.profile.full_name}"
