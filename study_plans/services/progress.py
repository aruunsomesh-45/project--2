"""
Progress calculation — always derived live from StudyTask rows, never
stored/cached, so it can never drift out of sync or show fabricated
numbers.
"""

from django.utils import timezone


def calculate_progress(plan):
    """Returns a dict of real, derived progress stats for one StudyPlan."""
    today = timezone.localdate()
    tasks = list(plan.tasks.all())

    total = len(tasks)
    completed = [t for t in tasks if t.status == 'completed']
    pending = [t for t in tasks if t.status == 'pending']
    in_progress = [t for t in tasks if t.status == 'in_progress']
    skipped = [t for t in tasks if t.status == 'skipped']
    overdue = [t for t in tasks if t.date < today and t.status in ('pending', 'in_progress')]

    completed_minutes = sum(t.estimated_minutes for t in completed)
    total_minutes = sum(t.estimated_minutes for t in tasks)

    completion_pct = round(len(completed) / total * 100) if total else 0

    return {
        'total_tasks': total,
        'completed_tasks': len(completed),
        'pending_tasks': len(pending),
        'in_progress_tasks': len(in_progress),
        'skipped_tasks': len(skipped),
        'overdue_tasks': len(overdue),
        'completion_pct': completion_pct,
        'completed_minutes': completed_minutes,
        'total_minutes': total_minutes,
    }


def todays_tasks(plan):
    today = timezone.localdate()
    return plan.tasks.filter(date=today).order_by('order')


def upcoming_tasks(plan, limit=10):
    today = timezone.localdate()
    return plan.tasks.filter(date__gt=today).exclude(status='skipped').order_by('date', 'order')[:limit]


def completed_tasks(plan, limit=20):
    return plan.tasks.filter(status='completed').order_by('-completed_at')[:limit]
