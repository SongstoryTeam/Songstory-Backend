from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField("Телефон", max_length=20, blank=True)
    bio = models.TextField("Про себе", blank=True)
    is_verified_author = models.BooleanField("Підтверджений автор", default=False)

    class Meta:
        verbose_name = "Профіль"
        verbose_name_plural = "Профілі"

    def __str__(self) -> str:
        return f"Профіль {self.user.username}"
