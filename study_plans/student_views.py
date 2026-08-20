from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required

from .models import StudyPlan, StudyTask
from .permissions import check_student_owns_task
from .services.progress import calculate_progress, completed_tasks, todays_tasks, upcoming_tasks


@login_required
@role_required(['student'])
def my_plans_view(request):
    """/study-plans/ — the student's own active plan(s). Draft plans are
    teacher-only and never appear here."""
    plans = StudyPlan.objects.filter(student=request.user, status__in=['active', 'completed']).order_by('-created_at')

    plans_with_data = []
    for plan in plans:
        plans_with_data.append({
            'plan': plan,
            'progress': calculate_progress(plan),
            'today': todays_tasks(plan),
            'upcoming': upcoming_tasks(plan),
            'completed': completed_tasks(plan),
        })

    return render(request, 'study_plans/student_plans.html', {'plans_with_data': plans_with_data})


@login_required
@role_required(['student'])
@require_POST
def task_start_view(request, task_id):
    task = get_object_or_404(StudyTask, pk=task_id)
    check_student_owns_task(request.user, task)
    if task.status == 'pending':
        task.status = 'in_progress'
        task.save(update_fields=['status', 'updated_at'])
    return redirect('study_plans:my_plans')


@login_required
@role_required(['student'])
@require_POST
def task_complete_view(request, task_id):
    task = get_object_or_404(StudyTask, pk=task_id)
    check_student_owns_task(request.user, task)
    if task.status in ('pending', 'in_progress'):
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'completed_at', 'updated_at'])
        messages.success(request, f'"{task.title}" marked complete.')
    return redirect('study_plans:my_plans')


@login_required
@role_required(['student'])
@require_POST
def task_skip_view(request, task_id):
    task = get_object_or_404(StudyTask, pk=task_id)
    check_student_owns_task(request.user, task)
    if task.status in ('pending', 'in_progress'):
        task.status = 'skipped'
        task.save(update_fields=['status', 'updated_at'])
        messages.info(request, f'"{task.title}" skipped.')
    return redirect('study_plans:my_plans')
