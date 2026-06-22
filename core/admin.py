from django.contrib import admin

from .models import (
    Author,
    AuthorTranslation,
    AuthorVerification,
    Book,
    BookRating,
    BookTranslation,
    Chapter,
    ChapterTranslation,
    Comment,
    Follow,
    Genre,
    GenreTranslation,
    Language,
    Like,
    MusicRecommendation,
    Notification,
    Playlist,
    PlaylistTrack,
    SavedBook,
    UserProfile,
)


class AuthorTranslationInline(admin.TabularInline):
    model = AuthorTranslation
    extra = 1


class GenreTranslationInline(admin.TabularInline):
    model = GenreTranslation
    extra = 1


class BookTranslationInline(admin.TabularInline):
    model = BookTranslation
    extra = 1


class ChapterTranslationInline(admin.TabularInline):
    model = ChapterTranslation
    extra = 1


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ["number", "is_approved"]
    show_change_link = True


class MusicRecommendationInline(admin.TabularInline):
    model = MusicRecommendation
    extra = 0
    fields = ["track_title", "artist", "link_url", "mood", "likes_count"]
    readonly_fields = ["likes_count"]


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_editable = ["is_active"]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["slug"]
    prepopulated_fields = {"slug": ("slug",)}
    inlines = [GenreTranslationInline]


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["slug", "birth_year", "open_library_id"]
    search_fields = ["slug", "translations__name"]
    prepopulated_fields = {"slug": ("slug",)}
    inlines = [AuthorTranslationInline]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["get_title_uk", "author", "genre", "year", "is_approved", "verified_author", "views_count", "created_at"]
    list_filter = ["is_approved", "genre", "year"]
    search_fields = ["translations__title", "author_legacy", "author__translations__name"]
    raw_id_fields = ["creator", "verified_author", "author", "genre", "canonical_book"]
    actions = ["approve_books", "reject_books"]
    inlines = [BookTranslationInline, ChapterInline]

    @admin.display(description="Title (uk)")
    def get_title_uk(self, obj):
        return obj.get_title("uk")

    @admin.action(description="Approve selected books")
    def approve_books(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} book(s) approved.")

    @admin.action(description="Reject selected books")
    def reject_books(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} book(s) rejected.")


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["book", "number", "get_title_uk", "is_approved"]
    list_filter = ["book", "is_approved"]
    search_fields = ["translations__title", "book__translations__title"]
    inlines = [ChapterTranslationInline, MusicRecommendationInline]

    @admin.display(description="Title (uk)")
    def get_title_uk(self, obj):
        return obj.get_title("uk")


@admin.register(MusicRecommendation)
class MusicRecommendationAdmin(admin.ModelAdmin):
    list_display = ["track_title", "artist", "mood", "chapter", "user", "likes_count", "created_at"]
    list_filter = ["link_type", "mood", "created_at"]
    search_fields = ["track_title", "artist"]


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ["title", "book", "creator", "likes_count", "is_public", "created_at"]
    list_filter = ["is_public", "created_at"]


@admin.register(PlaylistTrack)
class PlaylistTrackAdmin(admin.ModelAdmin):
    list_display = ["playlist", "track_title", "artist", "order"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["user", "text_preview", "created_at"]

    @admin.display(description="Text")
    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ["user", "music_recommendation", "playlist", "created_at"]


@admin.register(SavedBook)
class SavedBookAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "created_at"]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone", "is_verified_author"]
    list_filter = ["is_verified_author"]
    search_fields = ["user__username", "user__email"]


@admin.register(AuthorVerification)
class AuthorVerificationAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "status", "submitted_at", "reviewed_at", "reviewed_by"]
    list_filter = ["status"]
    readonly_fields = ["submitted_at", "reviewed_at", "reviewed_by"]
    search_fields = ["user__username", "book__translations__title"]
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description="Approve selected")
    def approve_selected(self, request, queryset):
        count = sum(
            1 for v in queryset.filter(status=AuthorVerification.STATUS_PENDING)
            if not v.approve(admin_user=request.user) or True
        )
        self.message_user(request, f"{count} application(s) approved.")

    @admin.action(description="Reject selected")
    def reject_selected(self, request, queryset):
        count = sum(
            1 for v in queryset.filter(status=AuthorVerification.STATUS_PENDING)
            if not v.reject(admin_user=request.user, note="Rejected via bulk action.") or True
        )
        self.message_user(request, f"{count} application(s) rejected.")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ["follower", "following", "created_at"]
    search_fields = ["follower__username", "following__username"]


@admin.register(BookRating)
class BookRatingAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "score"]
    list_filter = ["score"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "type", "is_read", "created_at"]
    list_filter = ["type", "is_read"]
    search_fields = ["recipient__username"]
    actions = ["mark_read"]

    @admin.action(description="Mark selected as read")
    def mark_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notification(s) marked as read.")
