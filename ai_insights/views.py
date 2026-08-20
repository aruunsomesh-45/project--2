from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from classroom.models import ClassStudent
from .models import StudentAIInsight
from .services.student_insights import InsightGenerationError, generate_student_insights

# Minimum time between regeneration requests for the same student, so a
# teacher clicking "Regenerate" repeatedly can't burn through API calls.
REGENERATION_COOLDOWN_SECONDS = 30


def _check_teacher_owns_student(request, student_id):
    """Same ownership rule as classroom.views.teacher_student_profile_view:
    a teacher may only act on students enrolled in one of their own
    classes (superusers exempted, matching the rest of the app)."""
    is_enrolled_in_teacher_class = ClassStudent.objects.filter(
        classroom__teacher=request.user,
        student_id=student_id,
    ).exists()
    if not is_enrolled_in_teacher_class and not request.user.is_superuser:
        raise PermissionDenied("You can only view AI insights for students enrolled in your classes.")


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def generate_insights_view(request, student_id):
    """
    Generate AI insights for a student if none exist yet (or reuse an
    existing up-to-date result — no unnecessary API calls). Teachers use
    the separate regenerate endpoint to force a fresh generation.
    """
    _check_teacher_owns_student(request, student_id)
    student = get_object_or_404(User, pk=student_id)

    try:
        insight, generated = generate_student_insights(student, force=False)
    except InsightGenerationError:
        messages.error(request, "This student hasn't completed the assessment yet, so no insights can be generated.")
        return redirect('classroom:student_profile', student_id=student_id)

    if insight.status == 'ready':
        if generated:
            messages.success(request, "AI insights generated.")
    else:
        messages.warning(request, "AI insights are temporarily unavailable. The student's learning profile is still available below.")

    return redirect('classroom:student_profile', student_id=student_id)


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def regenerate_insights_view(request, student_id):
    """Force a fresh AI generation, replacing (and archiving) any existing
    result. Rate-limited per student to prevent repeated-click API cost."""
    _check_teacher_owns_student(request, student_id)
    student = get_object_or_404(User, pk=student_id)

    existing = StudentAIInsight.objects.filter(student=student).first()
    if existing:
        seconds_since_update = (timezone.now() - existing.updated_at).total_seconds()
        if seconds_since_update < REGENERATION_COOLDOWN_SECONDS:
            wait = int(REGENERATION_COOLDOWN_SECONDS - seconds_since_update)
            messages.warning(request, f"Please wait {wait}s before regenerating insights again.")
            return redirect('classroom:student_profile', student_id=student_id)

    try:
        insight, generated = generate_student_insights(student, force=True)
    except InsightGenerationError:
        messages.error(request, "This student hasn't completed the assessment yet, so no insights can be generated.")
        return redirect('classroom:student_profile', student_id=student_id)

    if generated:
        messages.success(request, "AI insights regenerated.")
    elif insight.status == 'ready':
        messages.warning(request, "Regeneration failed — your previous AI insights have been kept.")
    else:
        messages.warning(request, "AI insights are temporarily unavailable.")

    return redirect('classroom:student_profile', student_id=student_id)
