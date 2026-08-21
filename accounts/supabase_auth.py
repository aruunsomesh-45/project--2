"""
Supabase-hosted Google OAuth.

Django's own User/Profile system remains the source of truth for identity
in this app — Supabase here is only the *OAuth broker* that talks to
Google on our behalf. Flow:

    1. User clicks "Sign in with Google"
    2. We redirect to Supabase's /auth/v1/authorize?provider=google
    3. Supabase handles the Google OAuth dance itself (using the Google
       client ID/secret configured in the Supabase dashboard, NOT ours)
    4. Supabase redirects back to our callback page with the session
       tokens in the URL fragment (#access_token=...) — fragments never
       reach the server, so a small JS snippet on the callback page reads
       it and POSTs it to our API endpoint
    5. We verify the access_token by asking Supabase's own /auth/v1/user
       endpoint who it belongs to (never trust the token content itself
       without asking Supabase) and get back a verified email
    6. We create-or-find a Django User for that email (same logic as the
       old django-social-auth pipeline) and log them in normally

No Supabase service-role key or JWT secret needed — verifying via the
/auth/v1/user endpoint is enough, and only requires the anon key.
"""

import requests
from django.conf import settings


class SupabaseAuthError(Exception):
    pass


def build_authorize_url(redirect_to):
    """URL to send the browser to, to kick off Supabase's Google OAuth flow."""
    base = settings.SUPABASE_URL.rstrip('/')
    return f"{base}/auth/v1/authorize?provider=google&redirect_to={redirect_to}"


def verify_access_token(access_token):
    """
    Ask Supabase who this access token belongs to. Never trust a token
    handed to us by the browser without checking with Supabase itself.

    Returns the verified user dict (containing at least 'email') on
    success. Raises SupabaseAuthError on any failure.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise SupabaseAuthError("Supabase is not configured (SUPABASE_URL/SUPABASE_ANON_KEY missing).")

    base = settings.SUPABASE_URL.rstrip('/')
    try:
        response = requests.get(
            f"{base}/auth/v1/user",
            headers={
                'Authorization': f'Bearer {access_token}',
                'apikey': settings.SUPABASE_ANON_KEY,
            },
            timeout=10,
        )
    except requests.RequestException as e:
        raise SupabaseAuthError(f"Could not reach Supabase: {e.__class__.__name__}") from e

    if response.status_code != 200:
        raise SupabaseAuthError(f"Supabase rejected the access token (status {response.status_code}).")

    data = response.json()
    if not data.get('email'):
        raise SupabaseAuthError("Supabase did not return a verified email for this user.")

    return data


def get_or_create_django_user(supabase_user):
    """
    Find-or-create the local Django User + Profile for a verified Supabase
    user. Mirrors the old django-social-auth pipeline's behavior exactly:
    new accounts default to role='student', display name comes from
    Google's profile data or is derived from the email as a fallback.
    """
    from django.contrib.auth.models import User
    from .models import Profile
    from .utils import derive_name_from_email

    email = supabase_user['email']
    user_metadata = supabase_user.get('user_metadata', {}) or {}
    full_name = user_metadata.get('full_name') or user_metadata.get('name')

    user, created = User.objects.get_or_create(
        username=email,
        defaults={'email': email},
    )
    if created:
        user.set_unusable_password()
        user.save()

    if not hasattr(user, 'profile'):
        Profile.objects.create(
            user=user,
            role='student',
            full_name=full_name or derive_name_from_email(email),
        )

    return user
