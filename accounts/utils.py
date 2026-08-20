import re


def derive_name_from_email(email):
    """
    Derive a display name from an email address, e.g.:
        john.doe@example.com   -> "John Doe"
        j_smith99@example.com  -> "J Smith99"
        info@example.com       -> "Info"

    Used only as a fallback when no name is already stored on the profile.
    """
    local_part = (email or '').split('@')[0]
    pieces = [p for p in re.split(r'[._+-]+', local_part) if p]
    if not pieces:
        return local_part
    return ' '.join(p.capitalize() for p in pieces)
