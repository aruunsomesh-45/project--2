import json
import urllib.parse

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages

from .forms import RegistrationForm, LoginForm
from .models import Profile
from .decorators import role_required
from .utils import derive_name_from_email
from . import supabase_auth


def register_view(request):
    """
    Handles user registration for students and teachers.

    GET: Displays the registration form.
    POST: Validates the form, creates User + Profile, logs in, and redirects.

    Redirect logic (per code-standards.md):
        - Student → onboarding page
        - Teacher → placeholder dashboard (Stage 2)
    """
    if request.user.is_authenticated:
        return redirect('accounts:redirect_after_login')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            full_name = form.cleaned_data['full_name']
            role = form.cleaned_data['role']

            # Create the Django User (email used as username)
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=full_name.split()[0] if full_name else '',
                last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
            )

            # Create the Profile
            Profile.objects.create(
                user=user,
                role=role,
                full_name=full_name,
            )

            # Log the user in immediately
            login(request, user)
            messages.success(request, f'Welcome, {full_name}! Your account has been created.')

            return redirect('accounts:redirect_after_login')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    Handles user login.

    GET: Displays the login form.
    POST: Authenticates and redirects based on role.
    """
    if request.user.is_authenticated:
        return redirect('accounts:redirect_after_login')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Backfill display name from email if the profile has none yet
            # (e.g. a profile created via a path that didn't collect a name).
            profile = getattr(user, 'profile', None)
            if profile is not None and not profile.full_name:
                profile.full_name = derive_name_from_email(user.email)
                profile.save(update_fields=['full_name'])

            messages.success(request, f'Welcome back, {user.profile.full_name}!')
            return redirect('accounts:redirect_after_login')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Logs the user out and redirects to the landing page."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('landing')


@login_required
def redirect_after_login(request):
    """
    Central redirect logic after login/registration.

    Routes based on the user's role:
        - Student: to onboarding (if assessment not completed) or their profile
        - Teacher: placeholder page (full dashboard in Stage 2)
        - Admin: Django admin
    """
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={
                'role': 'admin' if request.user.is_superuser else 'student',
                'full_name': request.user.get_full_name() or request.user.username,
            }
        )

    if profile.role == 'student':
        # Check if student has completed the assessment
        from assessment.models import LearningProfile
        if LearningProfile.objects.filter(student=request.user).exists():
            return redirect('assessment:profile')
        return redirect('accounts:onboarding')

    elif profile.role in ('teacher', 'admin'):
        return redirect('classroom:dashboard')

    return redirect('landing')


@login_required
@role_required(['student'])
def onboarding_view(request):
    """
    Student onboarding — a simple intro screen before the assessment.

    Explains what the assessment is, how long it takes, and what to expect.
    Shows a "Start Assessment" button.
    """
    # If student already completed assessment, skip to profile
    from assessment.models import LearningProfile
    if LearningProfile.objects.filter(student=request.user).exists():
        return redirect('assessment:profile')

    return render(request, 'accounts/onboarding.html')


@login_required
@role_required(['teacher'])
def teacher_placeholder_view(request):
    """
    Placeholder teacher dashboard — replaced with full dashboard in Stage 2.
    """
    return render(request, 'accounts/teacher_placeholder.html')


def supabase_login_view(request):
    """
    "Sign in with Google" entry point — redirects to Supabase's hosted
    Google OAuth flow rather than Django talking to Google directly.
    """
    if request.user.is_authenticated:
        return redirect('accounts:redirect_after_login')

    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        messages.error(request, 'Google sign-in is not configured right now. Please use email/password instead.')
        return redirect('accounts:login')

    callback_url = request.build_absolute_uri(reverse('accounts:supabase_callback'))
    authorize_url = supabase_auth.build_authorize_url(urllib.parse.quote(callback_url, safe=''))
    return redirect(authorize_url)


def supabase_callback_view(request):
    """
    Landing page Supabase redirects back to. The session comes back in the
    URL fragment (#access_token=...), which never reaches the server — so
    this just renders a small page whose JS reads the fragment and POSTs
    it to supabase_callback_api_view to actually finish the login.
    """
    return render(request, 'accounts/supabase_callback.html')


@require_POST
def supabase_callback_api_view(request):
    """
    Receives the access_token from the callback page's JS, verifies it
    with Supabase, and logs the (created-if-needed) Django user in.
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    access_token = payload.get('access_token')
    if not access_token:
        return JsonResponse({'error': 'Missing access token.'}, status=400)

    try:
        supabase_user = supabase_auth.verify_access_token(access_token)
        user = supabase_auth.get_or_create_django_user(supabase_user)
    except supabase_auth.SupabaseAuthError as e:
        return JsonResponse({'error': str(e)}, status=400)

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    profile = getattr(user, 'profile', None)
    if profile is not None and not profile.full_name:
        profile.full_name = derive_name_from_email(user.email)
        profile.save(update_fields=['full_name'])

    messages.success(request, f'Welcome, {user.profile.full_name}!')
    return JsonResponse({'redirect_url': reverse('accounts:redirect_after_login')})
