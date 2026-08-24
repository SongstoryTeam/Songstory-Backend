from django.conf import settings
from django.db import models


class Language(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Language"
        verbose_name_plural = "Languages"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    @classmethod
    def get_default(cls) -> "Language | None":
        """The catalog's default content language, driven by
        `settings.LANGUAGE_CODE` rather than a hardcoded value so the
        whole project only has one place that defines "default language"."""
        return cls.objects.filter(code=settings.LANGUAGE_CODE, is_active=True).first()