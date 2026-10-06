from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse

from core.text import normalize, search_terms

from .book import Book, Chapter


class Platform(models.TextChoices):
    YOUTUBE = "youtube", "YouTube"
    SPOTIFY = "spotify", "Spotify"


class TrackQuerySet(models.QuerySet):
    def search(self, query: str) -> "TrackQuerySet":
        queryset = self
        for term in search_terms(query):
            queryset = queryset.filter(search_key__contains=term)
        return queryset


class Track(models.Model):
    platform = models.CharField("Платформа", max_length=20, choices=Platform.choices)
    external_id = models.CharField(max_length=100)
    title = models.CharField("Назва", max_length=255)
    artist = models.CharField("Виконавець", max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    search_key = models.CharField(max_length=520, editable=False, default="")

    objects = TrackQuerySet.as_manager()

    class Meta:
        ordering = ["title"]
        constraints = [models.UniqueConstraint(fields=["platform", "external_id"], name="unique_track_per_platform")]
        verbose_name = "Трек"
        verbose_name_plural = "Треки"

    def __str__(self) -> str:
        return f"{self.artist} — {self.title}" if self.artist else self.title

    def save(self, *args, **kwargs) -> None:
        self.search_key = normalize(f"{self.title} {self.artist}")[:520]
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = {*update_fields, "search_key"}
        super().save(*args, **kwargs)

    @property
    def url(self) -> str:
        from core.services.music_links import canonical_url

        return canonical_url(self.platform, self.external_id)

    @property
    def embed_url(self) -> str:
        from core.services.music_links import embed_url

        return embed_url(self.platform, self.external_id)


class Recommendation(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="recommendations")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="recommendations")
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, null=True, blank=True, related_name="recommendations"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recommendations")
    comment = models.CharField("Коментар", max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "track", "book", "chapter"], name="unique_recommendation_per_chapter"
            ),
            models.UniqueConstraint(
                fields=["user", "track", "book"],
                condition=Q(chapter__isnull=True),
                name="unique_recommendation_per_book",
            ),
        ]
        verbose_name = "Рекомендація"
        verbose_name_plural = "Рекомендації"

    def __str__(self) -> str:
        return f"{self.user} → {self.track} ({self.book})"

    def clean(self) -> None:
        if self.chapter_id and self.chapter.book_id != self.book_id:
            raise ValidationError("Розділ не належить до цієї книги.")


class Playlist(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="playlists")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="playlists")
    title = models.CharField("Назва", max_length=255)
    description = models.TextField("Опис", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tracks = models.ManyToManyField(Track, through="PlaylistItem", related_name="playlists")

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Плейлист"
        verbose_name_plural = "Плейлисти"

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("core:playlist_detail", kwargs={"pk": self.pk})

    def can_manage(self, user) -> bool:
        return user.is_authenticated and (user.is_staff or user == self.user)


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="items")
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="playlist_items")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [models.UniqueConstraint(fields=["playlist", "track"], name="unique_track_per_playlist")]
        verbose_name = "Трек у плейлисті"
        verbose_name_plural = "Треки у плейлисті"

    def __str__(self) -> str:
        return f"{self.playlist}: {self.track}"
