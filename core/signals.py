from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import UserProfile


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance: User, created: bool, raw: bool = False, **kwargs) -> None:
    if created and not raw:
        UserProfile.objects.for_user(instance)


@receiver(user_logged_in)
def ensure_profile_on_login(sender, user: User, **kwargs) -> None:
    UserProfile.objects.for_user(user)
