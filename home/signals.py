from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import UserProfile
from django.db.models import F

@receiver(user_logged_in)
def increment_activity_on_login(sender, user, request, **kwargs):
    """
    Signal handler that increments the activity count for a user upon login.
    """
    UserProfile.objects.filter(user=user).update(activities_count=F('activities_count') + 1)

@receiver(user_logged_out)
def increment_activity_on_logout(sender, user, request, **kwargs):
    """
    Signal handler that increments the activity count for a user upon logout.
    """
    UserProfile.objects.filter(user=user).update(activities_count=F('activities_count') + 1)