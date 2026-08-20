from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """
    Extends Django's built-in User model with role and platform-specific fields.
    
    Each user gets exactly one Profile, created during registration.
    The role field determines which views and features a user can access.
    """

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
    )
    full_name = models.CharField(max_length=200)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    class Meta:
        ordering = ['-created_at']


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_superuser_profile(sender, instance, created, **kwargs):
    if created and instance.is_superuser:
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                'role': 'admin',
                'full_name': instance.get_full_name() or instance.username,
            }
        )

