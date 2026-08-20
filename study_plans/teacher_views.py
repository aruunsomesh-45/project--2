from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from classroom.models import ClassStudent

from .models import DIFFICULTY_CHOICES, PlanAdaptationDraft, RESOURCE_TYPE_CHOICES, StudyPlan, StudyResource, StudyTask, TASK_TYPE_CHOICES, WEEKDAY_CHOICES
from .permissions import check_teacher_owns_plan, check_teacher_owns_student
from .services.plan_generation import apply_adaptation_draft, generate_plan_with_ai, request_adaptation
from .services.progress import calculate_progress


@login_required
@role_required(['teacher', 'admin'])
def plan_list_view(request):
    """/classroom/study-plans/ — all plans across the teacher's own students."""
    if request.user.is_superuser:
        plans = StudyPlan.objects.select_related('student__profile').all()
    else:
        student_ids = ClassStudent.objects.filter(classroom__teacher=request.user).values_list('student_id', flat=True)
        plans = StudyPlan.objects.select_related('student__profile').filter(student_id__in=student_ids)

    plans_with_progress = [{'plan': p, 'progress': calculate_progress(p)} for p in plans]
    return render(request, 'study_plans/teacher_plan_list.html', {'plans_with_progress': plans_with_progress})


@login_required
@role_required(['teacher', 'admin'])
def plan_create_view(request, student_id):
    """/classroom/student/<id>/study-plans/create/ — teacher fills out the request form."""
    check_teacher_owns_student(request.user, student_id)
    student = get_object_or_404(User, pk=student_id)

    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        goal = request.POST.get('goal', '').strip()
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        exam_date = request.POST.get('exam_date') or None
        daily_minutes = request.POST.get('daily_minutes')
        available_days = [int(d) for d in request.POST.getlist('available_days')]
        difficulty = request.POST.get('difficulty', 'intermediate')
        teacher_instructions = request.POST.get('teacher_instructions', '').strip()

        errors = []
        if not subject:
            errors.append('Subject is required.')
        if not goal:
            errors.append('Goal is required.')
        if not start_date or not end_date:
            errors.append('Start and end dates are required.')
        if not available_days:
            errors.append('Select at least one available day.')
        try:
            daily_minutes = int(daily_minutes)
            if daily_minutes <= 0:
                errors.append('Daily study time must be greater than zero.')
        except (TypeError, ValueError):
            errors.append('Daily study time must be a number.')

        if not errors:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                exam_date_obj = datetime.strptime(exam_date, '%Y-%m-%d').date() if exam_date else None
                if end_date_obj < start_date_obj:
                    errors.append('End date must be after the start date.')
            except ValueError:
                errors.append('Invalid date format.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            plan = StudyPlan.objects.create(
                student=student, teacher=request.user, subject=subject,
                title='', goal=goal, start_date=start_date_obj, end_date=end_date_obj,
                exam_date=exam_date_obj, daily_minutes=daily_minutes, available_days=available_days,
                difficulty=difficulty, teacher_instructions=teacher_instructions, status='draft',
            )
            messages.success(request, 'Study plan draft created. Generate with AI or add tasks manually.')
            return redirect('study_plans_teacher:detail', plan_id=plan.pk)

    return render(request, 'study_plans/plan_create.html', {
        'student': student, 'difficulty_choices': DIFFICULTY_CHOICES, 'weekday_choices': WEEKDAY_CHOICES,
    })


@login_required
@role_required(['teacher', 'admin'])
def plan_detail_view(request, plan_id):
    """Teacher review/edit page — the plan stays a draft until explicitly approved."""
    plan = get_object_or_404(StudyPlan, pk=plan_id)
    check_teacher_owns_plan(request.user, plan)

    weeks = {}
    for task in plan.tasks.all().order_by('date', 'order'):
        weeks.setdefault(task.date, []).append(task)

    pending_draft = plan.adaptation_drafts.filter(status='pending_review').first()

    return render(request, 'study_plans/plan_detail.html', {
        'plan': plan,
        'tasks_by_date': weeks,
        'progress': calculate_progress(plan),
        'task_type_choices': TASK_TYPE_CHOICES,
        'resource_type_choices': RESOURCE_TYPE_CHOICES,
        'pending_draft': pending_draft,
    })


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def plan_generate_view(request, plan_id):
    plan = get_object_or_404(StudyPlan, pk=plan_id)
    check_teacher_owns_plan(request.user, plan)

    if plan.status != 'draft':
        messages.error(request, 'Only draft plans can be (re)generated with AI.')
        return redirect('study_plans_teacher:detail', plan_id=plan.pk)

    success, message, warnings = generate_plan_with_ai(plan)
    if success:
        messages.success(request, message)
        for w in warnings:
            messages.warning(request, w)
    else:
        messages.error(request, message)
    return redirect('study_plans_teacher:detail', plan_id=plan.pk)


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def plan_approve_view(request, plan_id):
    plan = get_object_or_404(StudyPlan, pk=plan_id)
    check_teacher_owns_plan(request.user, plan)

    if plan.status != 'draft':
        messages.error(request, 'Only draft plans can be approved.')
    elif not plan.tasks.exists():
        messages.error(request, 'Add at least one task before approving this plan.')
    else:
        plan.status = 'active'
        plan.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Plan approved and assigned to {plan.student.profile.full_name}.')
    return redirect('study_plans_teacher:detail', plan_id=plan.pk)


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def plan_archive_view(request, plan_id):
    plan = get_object_or_404(StudyPlan, pk=plan_id)
    check_teacher_owns_plan(request.user, plan)
    plan.status = 'archived'
    plan.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Plan archived.')
    return redirect('study_plans_teacher:list')


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def task_add_view(request, plan_id):
    plan = get_object_or_404(StudyPlan, pk=plan_id)
    check_teacher_owns_plan(request.user, plan)

    title = request.POST.get('title', '').strip()
    date_str = request.POST.get('date')
    minutes = request.POST.get('estimated_minutes')
    task_type = request.POST.get('task_type')
    description = request.POST.get('description', '').strip()

    errors = []
    if not title:
        errors.append('Task title is required.')
    task_date = None
    try:
        task_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if task_date < plan.start_date or task_date > plan.end_date:
            errors.append('Task date must be within the plan\'s date range.')
        if plan.exam_date and task_date > plan.exam_date:
            errors.append('Task date cannot be after the exam date.')
    except (TypeError, ValueError):
        errors.append('Invalid date.')
    try:
        minutes = int(minutes)
        if minutes <= 0:
            errors.append('Duration must be greater than zero.')
    except (TypeError, ValueError):
        errors.append('Duration must be a number.')
    if task_type not in dict(TASK_TYPE_CHOICES):
        errors.append('Invalid task type.')

    if task_date and minutes and not errors:
        existing_minutes = sum(t.estimated_minutes for t in plan.tasks.filter(date=task_date))
        if existing_minutes + minutes > plan.daily_minutes:
            errors.append(f'Adding this task would exceed the {plan.daily_minutes}-minute daily limit for {task_date}.')

    if errors:
        for e in errors:
            messages.error(request, e)
    else:
        next_order = (plan.tasks.filter(date=task_date).count() or 0) + 1
        StudyTask.objects.create(
            study_plan=plan, title=title, description=description, date=task_date,
            estimated_minutes=minutes, task_type=task_type, order=next_order,
        )
        messages.success(request, 'Task added.')

    return redirect('study_plans_teacher:detail', plan_id=plan.pk)


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def task_delete_view(request, plan_id, task_id):
    plan = get_object_or_404(StudyPlan, pk=plan_id)
    check_teacher_owns_plan(request.user, plan)
    task = get_object_or_404(StudyTask, pk=task_id, study_plan=plan)
    if task.status == 'completed':
        messages.error(request, 'Completed tasks cannot be deleted — historical progress is preserved.')
    else:
        task.delete()
        messages.success(request, 'Task removed.')
    return redirect('study_plans_teacher:detail', plan_id=plan.pk)


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def resource_add_view(request, plan_id, task_id):
    plan = get_object_or_404(StudyPlan, pk=plan_id)
    check_teacher_owns_plan(request.user, plan)
    task = get_object_or_404(StudyTask, pk=task_id, study_plan=plan)

    title = request.POST.get('title', '').strip()
    resource_type = request.POST.get('resource_type')
    url = request.POST.get('url', '').strip()

    if not title or resource_type not in dict(RESOURCE_TYPE_CHOICES):
        messages.error(request, 'Resource title and a valid type are required.')
    else:
        StudyResource.objects.create(
            study_task=task, title=title, resource_type=resource_type, url=url,
            description=request.POST.get('description', '').strip(),
        )
        messages.success(request, 'Resource added.')
    return redirect('study_plans_teacher:detail', plan_id=plan.pk)


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def adaptation_request_view(request, plan_id):
    plan = get_object_or_404(StudyPlan, pk=plan_id)
    check_teacher_owns_plan(request.user, plan)

    if plan.status != 'active':
        messages.error(request, 'Only active plans can be adapted.')
        return redirect('study_plans_teacher:detail', plan_id=plan.pk)

    instructions = request.POST.get('teacher_instructions', '').strip()
    draft, message = request_adaptation(plan, teacher_instructions=instructions)
    if draft:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('study_plans_teacher:detail', plan_id=plan.pk)


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def adaptation_apply_view(request, plan_id, draft_id):
    plan = get_object_or_404(StudyPlan, pk=plan_id)
    check_teacher_owns_plan(request.user, plan)
    draft = get_object_or_404(PlanAdaptationDraft, pk=draft_id, study_plan=plan, status='pending_review')
    apply_adaptation_draft(draft)
    messages.success(request, 'Future tasks updated. Completed tasks and past history were not changed.')
    return redirect('study_plans_teacher:detail', plan_id=plan.pk)


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def adaptation_discard_view(request, plan_id, draft_id):
    plan = get_object_or_404(StudyPlan, pk=plan_id)
    check_teacher_owns_plan(request.user, plan)
    draft = get_object_or_404(PlanAdaptationDraft, pk=draft_id, study_plan=plan, status='pending_review')
    draft.status = 'discarded'
    draft.save(update_fields=['status'])
    messages.info(request, 'Adaptation discarded.')
    return redirect('study_plans_teacher:detail', plan_id=plan.pk)


@login_required
@role_required(['teacher', 'admin'])
def student_progress_view(request, student_id):
    """/classroom/student/<id>/progress/"""
    check_teacher_owns_student(request.user, student_id)
    student = get_object_or_404(User, pk=student_id)

    plans = StudyPlan.objects.filter(student=student).exclude(status='draft')
    plans_with_progress = [{'plan': p, 'progress': calculate_progress(p)} for p in plans]

    return render(request, 'study_plans/student_progress.html', {
        'student_user': student, 'plans_with_progress': plans_with_progress,
    })
