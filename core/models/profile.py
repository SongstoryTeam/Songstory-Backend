from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
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


AVATAR_FIELDS = ("avatar_url", "avatar_x", "avatar_y", "avatar_zoom")


def position_validators() -> list:
    return [MinValueValidator(limits.AVATAR_POSITION_MIN), MaxValueValidator(limits.AVATAR_POSITION_MAX)]


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

    avatar_url = models.URLField("Фото профілю", max_length=limits.URL_MAX_LENGTH, blank=True)
    avatar_x = models.PositiveSmallIntegerField(
        "Кадр фото: горизонталь", default=limits.AVATAR_POSITION_DEFAULT, validators=position_validators()
    )
    avatar_y = models.PositiveSmallIntegerField(
        "Кадр фото: вертикаль", default=limits.AVATAR_POSITION_DEFAULT, validators=position_validators()
    )
    avatar_zoom = models.PositiveSmallIntegerField(
        "Кадр фото: масштаб",
        default=limits.AVATAR_ZOOM_DEFAULT,
        validators=[MinValueValidator(limits.AVATAR_ZOOM_MIN), MaxValueValidator(limits.AVATAR_ZOOM_MAX)],
    )

    objects = UserProfileManager()

    class Meta:
        verbose_name = "Профіль"
        verbose_name_plural = "Профілі"

    def __str__(self) -> str:
        return f"Профіль {self.user.username}"

    @property
    def has_avatar(self) -> bool:
        return bool(self.avatar_url)

    def reset_avatar(self) -> None:
        for name in AVATAR_FIELDS:
            setattr(self, name, self._meta.get_field(name).get_default())
        self.save(update_fields=AVATAR_FIELDS)
