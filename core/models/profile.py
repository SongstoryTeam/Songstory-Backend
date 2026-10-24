from django.contrib.auth.models import User
from django.db import models

from core import limits


class UserProfileManager(models.Manager):
    def for_user(self, user: User) -> "UserProfile":
        profile, _ = self.get_or_create(user=user)
        return profile


class Accent(models.TextChoices):
    TERRACOTTA = "terracotta", "Теракота"
    ROSE = "rose", "Троянда"
    AMBER = "amber", "Бурштин"
    FOREST = "forest", "Хвоя"
    TEAL = "teal", "Бірюза"
    OCEAN = "ocean", "Океан"
    INDIGO = "indigo", "Індиго"
    VIOLET = "violet", "Фіалка"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField("Телефон", max_length=limits.PHONE_MAX_LENGTH, blank=True)
    bio = models.TextField("Про себе", blank=True)
    is_verified_author = models.BooleanField("Підтверджений автор", default=False)
    accent = models.CharField(
        "Акцентний колір",
        max_length=limits.ACCENT_MAX_LENGTH,
        choices=Accent.choices,
        default=Accent.TERRACOTTA,
    )

    objects = UserProfileManager()

    class Meta:
        verbose_name = "Профіль"
        verbose_name_plural = "Профілі"

    def __str__(self) -> str:
        return f"Профіль {self.user.username}"
