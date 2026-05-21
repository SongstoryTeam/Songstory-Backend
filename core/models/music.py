import re
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from .book import Book, Chapter

_YOUTUBE_RE = re.compile(r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})')
_MUSIC_YT_RE = re.compile(r'music\.youtube\.com')
_SPOTIFY_RE = re.compile(r'spotify\.com/track/([A-Za-z0-9]+)')


class MusicRecommendation(models.Model):
    LINK_TYPES = [
        ('youtube', 'YouTube'),
        ('spotify', 'Spotify'),
        ('soundcloud', 'SoundCloud'),
        ('other', 'Інше'),
    ]

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='music_recommendations')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track_title = models.CharField(max_length=255, verbose_name="Назва треку")
    artist = models.CharField(max_length=255, verbose_name="Виконавець")
    link_type = models.CharField(max_length=20, choices=LINK_TYPES, default='youtube')
    link_url = models.URLField(verbose_name="Посилання")
    embed_code = models.CharField(max_length=100, blank=True)
    comment = models.TextField(blank=True, verbose_name="Коментар")
    likes_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Музична рекомендація"
        verbose_name_plural = "Музичні рекомендації"
        ordering = ['-likes_count', '-created_at']

    def save(self, *args, **kwargs):
        if self.link_type == 'youtube' and _MUSIC_YT_RE.search(self.link_url):
            self.link_url = self.link_url.replace('music.youtube.com', 'www.youtube.com')
        if not self.embed_code:
            if self.link_type == 'youtube':
                match = _YOUTUBE_RE.search(self.link_url)
                self.embed_code = match.group(1) if match else ''
            elif self.link_type == 'spotify':
                match = _SPOTIFY_RE.search(self.link_url)
                self.embed_code = match.group(1) if match else ''
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.track_title} — {self.artist}"


class Playlist(models.Model):
    title = models.CharField(max_length=255, verbose_name="Назва")
    description = models.TextField(blank=True, verbose_name="Опис")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='playlists')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True, blank=True, related_name='playlists')
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    mood = models.CharField(max_length=200, blank=True)
    external_link = models.URLField(blank=True, verbose_name="Посилання на плейлист (YouTube/Spotify)")
    likes_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Плейлист"
        verbose_name_plural = "Плейлисти"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('core:playlist_detail', kwargs={'pk': self.pk})


class PlaylistTrack(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='tracks')
    track_title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    link_url = models.URLField()
    embed_code = models.CharField(max_length=100, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.track_title} — {self.artist} (#{self.order})"