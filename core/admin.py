from django.contrib import admin
from .models import (
    Book, Chapter, MusicRecommendation,
    Playlist, PlaylistTrack, Like, Comment, SavedBook, UserProfile,
)


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1
    fields = ['number', 'title', 'mood_tags', 'is_approved']


class MusicRecommendationInline(admin.TabularInline):
    model = MusicRecommendation
    extra = 0
    fields = ['track_title', 'artist', 'link_url', 'likes_count']
    readonly_fields = ['likes_count']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'year', 'genre', 'views_count', 'created_at']
    list_filter = ['genre', 'year']
    search_fields = ['title', 'author']
    inlines = [ChapterInline]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['book', 'number', 'title', 'is_approved', 'mood_tags']
    list_filter = ['book', 'is_approved']
    search_fields = ['title', 'book__title']
    inlines = [MusicRecommendationInline]


@admin.register(MusicRecommendation)
class MusicRecommendationAdmin(admin.ModelAdmin):
    list_display = ['track_title', 'artist', 'chapter', 'user', 'likes_count', 'created_at']
    list_filter = ['link_type', 'created_at']
    search_fields = ['track_title', 'artist']


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ['title', 'book', 'creator', 'likes_count', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at']


@admin.register(PlaylistTrack)
class PlaylistTrackAdmin(admin.ModelAdmin):
    list_display = ['playlist', 'track_title', 'artist', 'order']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'text_preview', 'created_at']

    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text

    text_preview.short_description = 'Text'


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'music_recommendation', 'playlist', 'created_at']


@admin.register(SavedBook)
class SavedBookAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'created_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'is_verified_author']
    list_filter = ['is_verified_author']
    search_fields = ['user__username', 'user__email']
