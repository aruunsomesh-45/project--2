import json

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from .models import AssessmentQuestion, AssessmentResponse, LearningProfile
from .scoring import score_assessment


@login_required
@role_required(['student'])
def assessment_take_view(request):
    """
    Main assessment view — shows one question at a time.

    GET params:
        ?q=<display_order> — which question to show (default: 1)

    The view:
        1. Loads all questions in order.
        2. Loads any existing responses (for resume/pre-fill).
        3. Shows the question at position `q`.
        4. Passes progress data for the progress bar.
    """
    # If already completed, redirect to profile
    if LearningProfile.objects.filter(student=request.user).exists():
        return redirect('assessment:profile')

    questions = AssessmentQuestion.objects.all()
    total = questions.count()

    if total == 0:
        return render(request, 'assessment/no_questions.html')

    # Load existing responses for pre-fill
    existing_responses = {
        r.question_id: r.answer_value
        for r in AssessmentResponse.objects.filter(student=request.user)
    }

    # Count answered questions for progress
    answered_count = len(existing_responses)

    # Root cause of the "loop back to the start" bug: this view used to
    # default `current_q` to 1 whenever `?q=` was absent, so every re-entry
    # point (the nav bar link, the onboarding "Start Assessment" button, a
    # page reload) reset an in-progress student straight back to question 1
    # instead of resuming where they left off. Only trust `?q=` when the
    # caller explicitly navigated (Previous/Next); otherwise resume at the
    # first unanswered question.
    if 'q' in request.GET:
        current_q = int(request.GET.get('q', 1))
        current_q = max(1, min(current_q, total))
    else:
        answered_question_ids = set(existing_responses.keys())
        current_q = total  # fall back to the last question if all answered
        for question_obj in questions:
            if question_obj.id not in answered_question_ids:
                current_q = question_obj.display_order
                break

    question = questions[current_q - 1]

    # Get current answer if exists
    current_answer = existing_responses.get(question.id)

    context = {
        'question': question,
        'current_q': current_q,
        'total': total,
        'progress_pct': round((answered_count / total) * 100),
        'answered_count': answered_count,
        'current_answer': current_answer,
        'is_first': current_q == 1,
        'is_last': current_q == total,
        'can_submit': answered_count == total,
    }

    return render(request, 'assessment/take.html', context)


@login_required
@role_required(['student'])
@require_POST
def assessment_save_view(request):
    """
    AJAX endpoint — auto-saves a single answer.

    POST body (JSON):
        { "question_id": 5, "answer_value": 4 }

    Upserts on (student, question) — overwrites previous answer.
    Returns JSON: { "status": "saved", "answered_count": 12 }
    """
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        answer_value = data.get('answer_value')

        if question_id is None or answer_value is None:
            return JsonResponse({'error': 'Missing question_id or answer_value'}, status=400)

        question = get_object_or_404(AssessmentQuestion, id=question_id)

        # Upsert: create or update
        AssessmentResponse.objects.update_or_create(
            student=request.user,
            question=question,
            defaults={'answer_value': answer_value},
        )

        # Return updated count
        answered_count = AssessmentResponse.objects.filter(student=request.user).count()
        total = AssessmentQuestion.objects.count()

        return JsonResponse({
            'status': 'saved',
            'answered_count': answered_count,
            'total': total,
            'progress_pct': round((answered_count / total) * 100) if total > 0 else 0,
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@login_required
@role_required(['student'])
@require_POST
def assessment_submit_view(request):
    """
    Submit the completed assessment — triggers the scoring engine.

    Only processes if all questions have been answered.
    Creates/updates the LearningProfile and redirects to the results.
    """
    total = AssessmentQuestion.objects.count()
    answered = AssessmentResponse.objects.filter(student=request.user).count()

    if answered < total:
        from django.contrib import messages
        messages.warning(request, f'Please answer all questions before submitting. ({answered}/{total} answered)')
        return redirect(f'/assessment/?q={answered + 1}')

    # Run the scoring engine
    profile = score_assessment(request.user)

    from django.contrib import messages
    messages.success(request, 'Assessment complete! Here is your Learning Profile.')

    return redirect('assessment:profile')


@login_required
@role_required(['student'])
def learning_profile_view(request):
    """
    Display the student's Learning Profile results.

    Shows: archetype, dimension score bars, strengths, challenges, recommendations.
    """
    try:
        profile = LearningProfile.objects.get(student=request.user)
    except LearningProfile.DoesNotExist:
        return redirect('accounts:onboarding')

    # Sort dimension scores for display (highest first)
    sorted_dimensions = sorted(
        profile.dimension_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    context = {
        'profile': profile,
        'sorted_dimensions': sorted_dimensions,
    }

    return render(request, 'assessment/profile.html', context)
