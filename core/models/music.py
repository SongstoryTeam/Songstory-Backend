from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from .book import Book, Chapter


class MusicRecommendation(models.Model):
    LINK_TYPES = [
        ("youtube", "YouTube"),
        ("spotify", "Spotify"),
        ("soundcloud", "SoundCloud"),
        ("other", "Other"),
    ]

    MOOD_CHOICES = [
        ("epic", "Epic"),
        ("sad", "Melancholic"),
        ("calm", "Calm"),
        ("tense", "Tense"),
        ("romantic", "Romantic"),
        ("dark", "Dark"),
        ("uplifting", "Uplifting"),
        ("mysterious", "Mysterious"),
    ]

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="music_recommendations")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track_title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    link_type = models.CharField(max_length=20, choices=LINK_TYPES, default="youtube")
    link_url = models.URLField()
    embed_code = models.CharField(max_length=100, blank=True)
    comment = models.TextField(blank=True)
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, blank=True)
    likes_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Music recommendation"
        verbose_name_plural = "Music recommendations"
        ordering = ["-likes_count", "-created_at"]

    def __str__(self) -> str:
        return f"{self.track_title} — {self.artist}"


class Playlist(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="playlists")
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, null=True, blank=True, related_name="playlists"
    )
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    mood = models.CharField(max_length=200, blank=True)
    external_link = models.URLField(blank=True)
    likes_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Playlist"
        verbose_name_plural = "Playlists"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        if self.slug:
            return reverse("core:playlist_detail_slug", kwargs={"slug": self.slug})
        return reverse("core:playlist_detail", kwargs={"pk": self.pk})


class PlaylistTrack(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="tracks")
    track_title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    link_url = models.URLField()
    embed_code = models.CharField(max_length=100, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.track_title} — {self.artist}"
