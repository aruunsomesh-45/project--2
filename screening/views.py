from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required

from .models import TIER_CHOICES, ScreeningAttempt, ScreeningQuestion, ScreeningReport, SelfReportQuestion
from .services import engine


@login_required
@role_required(['student'])
def start_view(request):
    """Tier selection screen — the entry point. Picking a tier loads only
    that tier's question bank, per the source material's grade-tier design."""
    # If the student has a completed attempt already, send them to the report.
    latest_completed = (
        ScreeningAttempt.objects.filter(student=request.user, part1_status='completed', part2_status='completed')
        .order_by('-completed_at')
        .first()
    )
    if latest_completed:
        return redirect('screening:report')

    if request.method == 'POST':
        tier = request.POST.get('tier')
        valid_tiers = dict(TIER_CHOICES)
        if tier not in valid_tiers:
            messages.error(request, 'Please select a valid level.')
        else:
            engine.get_or_create_attempt(request.user, tier)
            return redirect('screening:take')

    return render(request, 'screening/start.html', {'tier_choices': TIER_CHOICES})


@login_required
@role_required(['student'])
def take_view(request):
    """Serves the next unanswered item (Part 1 adaptive, then Part 1
    learning-style probes, then Part 2 self-report) and processes the POST
    for whichever item was just shown."""
    attempt = (
        ScreeningAttempt.objects.filter(student=request.user)
        .exclude(part1_status='completed', part2_status='completed')
        .order_by('-started_at')
        .first()
    )
    if attempt is None:
        return redirect('screening:start')

    if request.method == 'POST':
        stage = request.POST.get('stage')
        question_id = request.POST.get('question_id')

        if stage == 'part1':
            question = get_object_or_404(ScreeningQuestion, pk=question_id, tier=attempt.tier)
            selected = request.POST.get('answer')
            if selected not in ('A', 'B', 'C', 'D'):
                messages.error(request, 'Please select an answer to continue.')
                return redirect('screening:take')
            engine.record_part1_answer(attempt, question, selected)

        elif stage == 'part2':
            question = get_object_or_404(SelfReportQuestion, pk=question_id)
            if question.is_open_text:
                free_text = request.POST.get('free_text', '').strip()
                engine.record_part2_answer(attempt, question, free_text=free_text)
            else:
                selected = request.POST.get('answer')
                if selected not in ('A', 'B', 'C', 'D'):
                    messages.error(request, 'Please select an answer to continue.')
                    return redirect('screening:take')
                engine.record_part2_answer(attempt, question, selected_option=selected)

        if attempt.is_completed:
            messages.success(request, 'Screening complete! Here is your report.')
            return redirect('screening:report')
        return redirect('screening:take')

    # GET — figure out what to show next
    if attempt.part1_status != 'completed':
        item = engine.get_next_part1_question(attempt)
        answered, total = engine.total_part1_progress(attempt)
        return render(request, 'screening/take_part1.html', {
            'attempt': attempt, 'question': item, 'answered': answered, 'total': total,
        })
    else:
        item = engine.get_next_part2_question(attempt)
        answered, total = engine.total_part2_progress(attempt)
        return render(request, 'screening/take_part2.html', {
            'attempt': attempt, 'question': item, 'answered': answered, 'total': total,
        })


@login_required
@role_required(['student'])
def report_view(request):
    """Student's own report — wellbeing flag deliberately excluded per the
    source material ('teacher-facing only')."""
    report = ScreeningReport.objects.filter(student=request.user).order_by('-generated_at').first()
    if report is None:
        return redirect('screening:start')
    return render(request, 'screening/report.html', {'report': report, 'is_teacher_view': False})
