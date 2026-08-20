from .models import Profile
from .utils import derive_name_from_email

def save_profile_from_google(strategy, details, user=None, *args, **kwargs):
    """
    When a Google user logs in for the first time, create a Profile.
    We default the role to "student" and fill the full name from Google.
    If Google doesn't hand back a usable name, derive one from the email
    (e.g. "jane.doe@x.com" -> "Jane Doe") instead of storing the raw address.
    """
    if user is None:
        return
    if hasattr(user, "profile"):
        return  # already has a profile
    full_name = details.get("fullname") or details.get("username")
    if not full_name:
        full_name = derive_name_from_email(user.email)
    Profile.objects.create(
        user=user,
        role="student",
        full_name=full_name,
    )
