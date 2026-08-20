from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def role_required(allowed_roles):
    """
    Decorator that restricts a view to users with specific roles.

    Usage:
        @role_required(['student'])
        def my_student_view(request):
            ...

        @role_required(['teacher', 'admin'])
        def my_teacher_view(request):
            ...

    How it works:
        1. Checks if the user is authenticated — if not, redirects to login.
        2. Checks if the user has a Profile with a role in `allowed_roles`.
        3. If the role doesn't match, returns 403 Forbidden.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            if not hasattr(request.user, 'profile'):
                return HttpResponseForbidden('No profile found for this user.')

            if request.user.profile.role not in allowed_roles:
                return HttpResponseForbidden(
                    'You do not have permission to access this page.'
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
