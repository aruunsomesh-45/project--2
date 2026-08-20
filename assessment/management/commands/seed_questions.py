"""
Management command to seed the assessment question bank.

Usage:
    python manage.py seed_questions

This populates the database with the initial set of learning assessment
questions across 5 dimensions (5 questions each = 25 total).

All questions are Likert scale (1-5):
    1 = Strongly Disagree
    2 = Disagree
    3 = Neutral
    4 = Agree
    5 = Strongly Agree
"""

from django.core.management.base import BaseCommand
from assessment.models import AssessmentQuestion


QUESTIONS = [
    # === Analytical Thinking (5 questions) ===
    {
        'dimension': 'Analytical Thinking',
        'question_text': 'I enjoy breaking down complex problems into smaller, manageable parts.',
        'question_type': 'likert',
        'options': None,
        'display_order': 1,
    },
    {
        'dimension': 'Analytical Thinking',
        'question_text': 'When I read something new, I naturally look for patterns and logical connections.',
        'question_type': 'likert',
        'options': None,
        'display_order': 2,
    },
    {
        'dimension': 'Analytical Thinking',
        'question_text': 'I prefer to understand the "why" behind a concept before memorizing the "what."',
        'question_type': 'likert',
        'options': None,
        'display_order': 3,
    },
    {
        'dimension': 'Analytical Thinking',
        'question_text': 'I feel confident when a task requires careful reasoning and step-by-step thinking.',
        'question_type': 'likert',
        'options': None,
        'display_order': 4,
    },
    {
        'dimension': 'Analytical Thinking',
        'question_text': 'I like organizing information into charts, tables, or outlines to understand it better.',
        'question_type': 'likert',
        'options': None,
        'display_order': 5,
    },

    # === Creative Learning (5 questions) ===
    {
        'dimension': 'Creative Learning',
        'question_text': 'I often come up with unusual or original ideas when solving problems.',
        'question_type': 'likert',
        'options': None,
        'display_order': 6,
    },
    {
        'dimension': 'Creative Learning',
        'question_text': 'I prefer open-ended tasks where I can explore different solutions.',
        'question_type': 'likert',
        'options': None,
        'display_order': 7,
    },
    {
        'dimension': 'Creative Learning',
        'question_text': 'I enjoy using imagination and creativity when studying or working on assignments.',
        'question_type': 'likert',
        'options': None,
        'display_order': 8,
    },
    {
        'dimension': 'Creative Learning',
        'question_text': 'I learn better when I can connect a topic to something visual, like a drawing or diagram.',
        'question_type': 'likert',
        'options': None,
        'display_order': 9,
    },
    {
        'dimension': 'Creative Learning',
        'question_text': 'I sometimes find creative shortcuts or alternative methods that work well for me.',
        'question_type': 'likert',
        'options': None,
        'display_order': 10,
    },

    # === Practical Learning (5 questions) ===
    {
        'dimension': 'Practical Learning',
        'question_text': 'I learn best when I can apply what I am studying to a real-world situation.',
        'question_type': 'likert',
        'options': None,
        'display_order': 11,
    },
    {
        'dimension': 'Practical Learning',
        'question_text': 'I prefer hands-on activities like experiments, projects, or building things.',
        'question_type': 'likert',
        'options': None,
        'display_order': 12,
    },
    {
        'dimension': 'Practical Learning',
        'question_text': 'When learning a new skill, I would rather practice it immediately than read about it first.',
        'question_type': 'likert',
        'options': None,
        'display_order': 13,
    },
    {
        'dimension': 'Practical Learning',
        'question_text': 'I remember things better when I have physically done them, not just read or heard about them.',
        'question_type': 'likert',
        'options': None,
        'display_order': 14,
    },
    {
        'dimension': 'Practical Learning',
        'question_text': 'I get restless or lose focus during long lectures without interactive elements.',
        'question_type': 'likert',
        'options': None,
        'display_order': 15,
    },

    # === Social Learning (5 questions) ===
    {
        'dimension': 'Social Learning',
        'question_text': 'I understand topics better when I discuss them with others.',
        'question_type': 'likert',
        'options': None,
        'display_order': 16,
    },
    {
        'dimension': 'Social Learning',
        'question_text': 'I enjoy working in groups and learning from my peers.',
        'question_type': 'likert',
        'options': None,
        'display_order': 17,
    },
    {
        'dimension': 'Social Learning',
        'question_text': 'I feel more motivated to study when I have a study partner or group.',
        'question_type': 'likert',
        'options': None,
        'display_order': 18,
    },
    {
        'dimension': 'Social Learning',
        'question_text': 'Teaching or explaining a concept to someone else helps me understand it better.',
        'question_type': 'likert',
        'options': None,
        'display_order': 19,
    },
    {
        'dimension': 'Social Learning',
        'question_text': 'I actively seek feedback from classmates or teachers when I am uncertain.',
        'question_type': 'likert',
        'options': None,
        'display_order': 20,
    },

    # === Self-Discipline (5 questions) ===
    {
        'dimension': 'Self-Discipline',
        'question_text': 'I can stick to a study schedule even when I do not feel motivated.',
        'question_type': 'likert',
        'options': None,
        'display_order': 21,
    },
    {
        'dimension': 'Self-Discipline',
        'question_text': 'I set specific goals before starting a study session.',
        'question_type': 'likert',
        'options': None,
        'display_order': 22,
    },
    {
        'dimension': 'Self-Discipline',
        'question_text': 'I am good at managing my time and avoiding procrastination.',
        'question_type': 'likert',
        'options': None,
        'display_order': 23,
    },
    {
        'dimension': 'Self-Discipline',
        'question_text': 'I usually finish assignments well before the deadline.',
        'question_type': 'likert',
        'options': None,
        'display_order': 24,
    },
    {
        'dimension': 'Self-Discipline',
        'question_text': 'I can resist distractions like my phone or social media when I need to focus.',
        'question_type': 'likert',
        'options': None,
        'display_order': 25,
    },
]


class Command(BaseCommand):
    help = 'Seed the database with initial assessment questions (25 questions, 5 dimensions)'

    def handle(self, *args, **options):
        if AssessmentQuestion.objects.exists():
            self.stdout.write(self.style.WARNING(
                f'Questions already exist ({AssessmentQuestion.objects.count()} found). '
                f'Use --force to clear and re-seed.'
            ))
            if '--force' not in args:
                return

        if '--force' in args:
            AssessmentQuestion.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing questions.'))

        created_count = 0
        for q_data in QUESTIONS:
            _, created = AssessmentQuestion.objects.get_or_create(
                display_order=q_data['display_order'],
                defaults=q_data,
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {created_count} assessment questions across 5 dimensions.'
        ))
