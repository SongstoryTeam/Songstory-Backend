from django.db import models

from .language import Language
from .mixins import TranslatableMixin


class Genre(TranslatableMixin, models.Model):
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = "Genre"
        verbose_name_plural = "Genres"
        ordering = ["slug"]

    def __str__(self) -> str:
        return self.slug

    def get_name(self, lang: str | None = None) -> str:
        return self.get_translated_field("name", lang) or self.slug


class GenreTranslation(models.Model):
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ["genre", "language"]
        verbose_name = "Genre translation"
        verbose_name_plural = "Genre translations"

    def __str__(self) -> str:
        return f"{self.genre.slug} [{self.language.code}] → {self.name}"