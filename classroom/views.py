from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count

from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from assessment.models import LearningProfile, AssessmentResponse, AssessmentQuestion
from assessment.scoring import get_score_level, get_dimension_interpretation, get_assessment_status
from .models import Class, ClassStudent, generate_unique_class_code


def _get_owned_class(request, pk):
    """
    Fetch a Class by pk and enforce that the requesting teacher owns it
    (or that the user is a superuser).
    """
    class_obj = get_object_or_404(Class, pk=pk)
    if class_obj.teacher != request.user and not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to manage this class.")
    return class_obj


@login_required
@role_required(['teacher', 'admin'])
def teacher_dashboard_view(request):
    """
    Teacher Dashboard: list created classes and handle new class creation.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Please provide a class name.')
        else:
            class_obj = Class.objects.create(
                teacher=request.user,
                name=name,
                subject=request.POST.get('subject', '').strip(),
                grade=request.POST.get('grade', '').strip(),
                section=request.POST.get('section', '').strip(),
                description=request.POST.get('description', '').strip(),
                class_code=generate_unique_class_code(),
            )
            messages.success(request, f'Class "{class_obj.name}" created! Code: {class_obj.class_code}')
            return redirect('classroom:class_detail', pk=class_obj.pk)

    if request.user.is_superuser:
        teacher_classes = Class.objects.all().prefetch_related('enrolments')
    else:
        teacher_classes = Class.objects.filter(teacher=request.user).prefetch_related('enrolments')

    student_ids = list(
        ClassStudent.objects.filter(classroom__in=teacher_classes)
        .values_list('student_id', flat=True).distinct()
    )
    total_students = len(student_ids)
    assessed_count = LearningProfile.objects.filter(student_id__in=student_ids).count()

    context = {
        'classes': teacher_classes,
        'stats': {
            'class_count': teacher_classes.count(),
            'active_class_count': teacher_classes.filter(is_active=True).count(),
            'student_count': total_students,
            'pending_assessments': total_students - assessed_count,
        },
    }
    return render(request, 'classroom/dashboard.html', context)


@login_required
@role_required(['teacher', 'admin'])
def class_detail_view(request, pk):
    """
    Teacher view of a single class: shows roster of enrolled students.
    Enforces server-side teacher ownership.
    """
    class_obj = _get_owned_class(request, pk)

    enrolments = (
        ClassStudent.objects.filter(classroom=class_obj)
        .select_related('student__profile')
        .order_by('student__profile__full_name')
    )

    # Attach learning profile + assessment status info to students
    student_ids = [e.student_id for e in enrolments]
    profiles_by_student = {
        lp.student_id: lp
        for lp in LearningProfile.objects.filter(student_id__in=student_ids)
    }
    answered_counts = dict(
        AssessmentResponse.objects.filter(student_id__in=student_ids)
        .values_list('student_id')
        .annotate(count=Count('id'))
    )
    from ai_insights.models import StudentAIInsight
    ai_status_by_student = dict(
        StudentAIInsight.objects.filter(student_id__in=student_ids).values_list('student_id', 'status')
    )

    student_roster = []
    for enrolment in enrolments:
        lp = profiles_by_student.get(enrolment.student_id)
        if lp is not None:
            status = 'completed'
        elif answered_counts.get(enrolment.student_id, 0) > 0:
            status = 'in_progress'
        else:
            status = 'not_started'

        # AI insight availability — only real generated state, never fake.
        if lp is None:
            ai_status = None
        else:
            ai_status = ai_status_by_student.get(enrolment.student_id, 'not_generated')

        student_roster.append({
            'enrolment': enrolment,
            'student': enrolment.student,
            'learning_profile': lp,
            'has_assessment': lp is not None,
            'assessment_status': status,
            'ai_status': ai_status,
        })

    # --- Search (name/email) ---
    query = request.GET.get('q', '').strip()
    if query:
        query_lower = query.lower()
        student_roster = [
            item for item in student_roster
            if query_lower in item['student'].profile.full_name.lower()
            or query_lower in item['student'].email.lower()
        ]

    # --- Filter ---
    status_filter = request.GET.get('status', 'all')
    if status_filter in ('completed', 'in_progress', 'not_started'):
        student_roster = [item for item in student_roster if item['assessment_status'] == status_filter]

    context = {
        'class_obj': class_obj,
        'student_roster': student_roster,
        'query': query,
        'status_filter': status_filter,
    }
    return render(request, 'classroom/class_detail.html', context)


@login_required
@role_required(['teacher', 'admin'])
def class_edit_view(request, pk):
    """Edit a class's details (name, subject, grade, section, description, active state)."""
    class_obj = _get_owned_class(request, pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Class name cannot be empty.')
        else:
            class_obj.name = name
            class_obj.subject = request.POST.get('subject', '').strip()
            class_obj.grade = request.POST.get('grade', '').strip()
            class_obj.section = request.POST.get('section', '').strip()
            class_obj.description = request.POST.get('description', '').strip()
            class_obj.is_active = request.POST.get('is_active') == 'on'
            class_obj.save()
            messages.success(request, f'"{class_obj.name}" updated.')
            return redirect('classroom:class_detail', pk=class_obj.pk)

    return render(request, 'classroom/class_edit.html', {'class_obj': class_obj})


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def class_delete_view(request, pk):
    """Delete a class (and its enrolments, via cascade). Teacher-owned or admin only."""
    class_obj = _get_owned_class(request, pk)

    name = class_obj.name
    class_obj.delete()
    messages.success(request, f'Class "{name}" has been deleted.')

    return redirect('classroom:dashboard')


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def class_regenerate_code_view(request, pk):
    """Issue a new shareable join code for a class. Teacher-owned or admin only."""
    class_obj = _get_owned_class(request, pk)

    class_obj.class_code = generate_unique_class_code()
    class_obj.save(update_fields=['class_code'])
    messages.success(request, f'New class code generated: {class_obj.class_code}')

    return redirect('classroom:class_detail', pk=class_obj.pk)


@login_required
@role_required(['teacher', 'admin'])
@require_POST
def remove_student_view(request, pk, student_id):
    """Remove a student's enrolment from a class. Teacher-owned or admin only."""
    class_obj = _get_owned_class(request, pk)

    enrolment = ClassStudent.objects.filter(classroom=class_obj, student_id=student_id).first()
    if enrolment is None:
        messages.error(request, 'That student is not enrolled in this class.')
    else:
        student_name = enrolment.student.profile.full_name
        enrolment.delete()
        messages.success(request, f'Removed {student_name} from "{class_obj.name}".')

    return redirect('classroom:class_detail', pk=class_obj.pk)


@login_required
@role_required(['teacher', 'admin'])
def teacher_student_profile_view(request, student_id):
    """
    Teacher-facing Student Learning Profile View.
    Enforces server-side access control: teacher must have the student enrolled in at least one of their classes (or user is superuser).
    """
    # Enforce access control
    is_enrolled_in_teacher_class = ClassStudent.objects.filter(
        classroom__teacher=request.user,
        student_id=student_id,
    ).exists()

    if not is_enrolled_in_teacher_class and not request.user.is_superuser:
        raise PermissionDenied("You can only view profiles of students enrolled in your classes.")

    student = get_object_or_404(User, pk=student_id)

    assessment_status = get_assessment_status(student)

    try:
        learning_profile = LearningProfile.objects.get(student=student)
        # Attach level + neutral-language interpretation to each dimension,
        # sorted highest-scoring first for display.
        sorted_dimensions = [
            {
                'name': dim,
                'score': score,
                'level': get_score_level(score),
                'interpretation': get_dimension_interpretation(dim, score),
            }
            for dim, score in sorted(
                learning_profile.dimension_scores.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ]
    except LearningProfile.DoesNotExist:
        learning_profile = None
        sorted_dimensions = []

    # Assessment progress, shown when the profile isn't ready yet
    total_questions = AssessmentQuestion.objects.count()
    answered_questions = AssessmentResponse.objects.filter(student=student).count()

    # Get student's enrolled classes taught by this teacher (or all if superuser)
    if request.user.is_superuser:
        shared_classes = Class.objects.filter(enrolments__student=student)
    else:
        shared_classes = Class.objects.filter(
            teacher=request.user,
            enrolments__student=student,
        )

    # Phase 3: AI interpretation layer — purely additive, never required for
    # the page to render. A missing/failed insight just means that section
    # is hidden; the Phase 2 deterministic profile above is unaffected.
    from ai_insights.models import StudentAIInsight
    ai_insight = StudentAIInsight.objects.filter(student=student).first()

    context = {
        'student_user': student,
        'learning_profile': learning_profile,
        'sorted_dimensions': sorted_dimensions,
        'shared_classes': shared_classes,
        'assessment_status': assessment_status,
        'total_questions': total_questions,
        'answered_questions': answered_questions,
        'ai_insight': ai_insight,
    }
    return render(request, 'classroom/student_detail.html', context)


@login_required
@role_required(['teacher', 'admin'])
def student_screening_report_view(request, student_id):
    """
    Teacher-facing Adaptive Screening Test report — separate from the
    Learning Profile assessment. Same ownership rule as the rest of this
    module: a teacher may only view students enrolled in one of their own
    classes. Includes the wellbeing flag and soft-skills tags, which are
    deliberately teacher-facing only (never shown to the student or any
    cross-student aggregate) per the source question bank.
    """
    is_enrolled_in_teacher_class = ClassStudent.objects.filter(
        classroom__teacher=request.user,
        student_id=student_id,
    ).exists()
    if not is_enrolled_in_teacher_class and not request.user.is_superuser:
        raise PermissionDenied("You can only view screening reports for students enrolled in your classes.")

    student = get_object_or_404(User, pk=student_id)

    from screening.models import ScreeningReport
    report = ScreeningReport.objects.filter(student=student).select_related('attempt').order_by('-generated_at').first()

    if report is None:
        return render(request, 'screening/no_report.html', {'student_user': student})

    return render(request, 'screening/report.html', {'report': report, 'is_teacher_view': True})


@login_required
@role_required(['student'])
def student_join_class_view(request):
    """
    Student View to join a class via shareable class code.
    """
    if request.method == 'POST':
        code = request.POST.get('class_code', '').strip().upper()
        if not code:
            messages.error(request, 'Please enter a class code.')
        else:
            try:
                class_obj = Class.objects.get(class_code=code, is_active=True)
                _, created = ClassStudent.objects.get_or_create(
                    classroom=class_obj,
                    student=request.user,
                )
                if created:
                    messages.success(request, f'Successfully joined "{class_obj.name}"!')
                else:
                    messages.info(request, f'You are already enrolled in "{class_obj.name}".')
                return redirect('classroom:join_class')
            except Class.DoesNotExist:
                messages.error(request, "We couldn't find an active class with that code. Please check and try again.")

    enrolled_classes = ClassStudent.objects.filter(student=request.user).select_related('classroom__teacher__profile')

    context = {
        'enrolled_classes': enrolled_classes,
    }
    return render(request, 'classroom/join_class.html', context)
