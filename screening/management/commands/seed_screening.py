from django.core.management.base import BaseCommand
from django.db import transaction

from screening.models import ScreeningQuestion, SelfReportQuestion
from screening.services.seed_data import (
    ADAPTIVE_QUESTIONS_BY_TIER,
    INTERESTS_QUESTIONS_SHARED,
    INTERESTS_Q3_SCHOOL,
    INTERESTS_Q3_UGPG,
    LEARNING_STYLE_PROBES_BY_TIER,
    OPEN_MESSAGE_QUESTION,
    PERSONALITY_QUESTIONS,
    SOFT_SKILLS_QUESTIONS,
    WELLBEING_QUESTIONS,
)


class Command(BaseCommand):
    help = 'Seeds the Adaptive Screening Test question bank (idempotent — safe to re-run).'

    @transaction.atomic
    def handle(self, *args, **options):
        q_count = 0

        # --- Part 1: adaptive Subject Knowledge / Cognitive Aptitude ---
        for tier, questions in ADAPTIVE_QUESTIONS_BY_TIER.items():
            for order, (topic, difficulty, passage, text, options, correct) in enumerate(questions, start=1):
                section = 'subject_knowledge' if topic in ('Reading Comprehension', 'General Awareness') else 'cognitive_aptitude'
                _, created = ScreeningQuestion.objects.update_or_create(
                    tier=tier, section=section, topic=topic, difficulty=difficulty,
                    defaults={
                        'passage': passage,
                        'question_text': text,
                        'options': [{'label': label, 'text': opt_text} for label, opt_text in options],
                        'correct_option': correct,
                        'display_order': order,
                    },
                )
                q_count += 1 if created else 0

        # --- Part 1: Learning Style Probes ---
        tag_map = {'A': 'Visual', 'B': 'Reading/Verbal', 'C': 'Practical/Kinesthetic', 'D': 'Reasoning/Theoretical'}
        for tier, probes in LEARNING_STYLE_PROBES_BY_TIER.items():
            for order, (text, option_texts) in enumerate(probes, start=1):
                labels = ['A', 'B', 'C', 'D']
                _, created = ScreeningQuestion.objects.update_or_create(
                    tier=tier, section='learning_style', topic='', difficulty='', display_order=order,
                    defaults={
                        'question_text': text,
                        'options': [
                            {'label': label, 'text': opt_text, 'tag': tag_map[label]}
                            for label, opt_text in zip(labels, option_texts)
                        ],
                        'correct_option': '',
                        'passage': '',
                    },
                )
                q_count += 1 if created else 0

        sr_count = 0

        def make_options(entries):
            return [{'label': label, 'text': text, 'tag': tag} for label, text, tag in entries]

        # --- Part 2: Personality ---
        for order, (text, entries) in enumerate(PERSONALITY_QUESTIONS, start=1):
            _, created = SelfReportQuestion.objects.update_or_create(
                category='personality', display_order=order,
                defaults={'question_text': text, 'options': make_options(entries), 'tiers': [], 'sub_key': ''},
            )
            sr_count += 1 if created else 0

        # --- Part 2: Interests (2 shared + 1 tier-variant pair) ---
        for order, (text, entries) in enumerate(INTERESTS_QUESTIONS_SHARED, start=1):
            _, created = SelfReportQuestion.objects.update_or_create(
                category='interests', display_order=order,
                defaults={'question_text': text, 'options': make_options(entries), 'tiers': [], 'sub_key': ''},
            )
            sr_count += 1 if created else 0

        for text, entries, tiers in (INTERESTS_Q3_SCHOOL, INTERESTS_Q3_UGPG):
            _, created = SelfReportQuestion.objects.update_or_create(
                category='interests', question_text=text,
                defaults={'options': make_options(entries), 'tiers': tiers, 'sub_key': '', 'display_order': 3},
            )
            sr_count += 1 if created else 0

        # --- Part 2: Wellbeing (teacher-facing only) ---
        for order, (sub_key, text, option_texts) in enumerate(WELLBEING_QUESTIONS, start=1):
            labels = ['A', 'B', 'C', 'D']
            _, created = SelfReportQuestion.objects.update_or_create(
                category='wellbeing', display_order=order,
                defaults={
                    'question_text': text,
                    'options': [{'label': label, 'text': t, 'tag': ''} for label, t in zip(labels, option_texts)],
                    'tiers': [], 'sub_key': sub_key, 'teacher_facing_only': True,
                },
            )
            sr_count += 1 if created else 0

        # --- Part 2: Soft Skills ---
        for order, (sub_key, text, entries) in enumerate(SOFT_SKILLS_QUESTIONS, start=1):
            _, created = SelfReportQuestion.objects.update_or_create(
                category='soft_skills', display_order=order,
                defaults={'question_text': text, 'options': make_options(entries), 'tiers': [], 'sub_key': sub_key},
            )
            sr_count += 1 if created else 0

        # --- Part 2: Open Message ---
        _, created = SelfReportQuestion.objects.update_or_create(
            category='open_message', display_order=1,
            defaults={'question_text': OPEN_MESSAGE_QUESTION, 'options': [], 'tiers': [], 'is_open_text': True, 'sub_key': ''},
        )
        sr_count += 1 if created else 0

        self.stdout.write(self.style.SUCCESS(
            f"Screening bank seeded: {ScreeningQuestion.objects.count()} Part 1 questions, "
            f"{SelfReportQuestion.objects.count()} Part 2 questions."
        ))
