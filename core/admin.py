from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from core import limits
from core.services import suggestions as suggestion_service

from .models import (
    Author,
    AuthorVerification,
    Book,
    BookEditSuggestion,
    Chapter,
    Comment,
    Genre,
    Playlist,
    PlaylistItem,
    Recommendation,
    Track,
    UserProfile,
)

admin.site.site_header = "Songstery"
admin.site.site_title = "Songstery"
admin.site.index_title = "Керування сайтом"


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ("number", "title")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "year", "genre", "is_approved", "creator", "created_at")
    list_filter = ("is_approved", "genre")
    list_select_related = ("author", "genre", "creator")
    search_fields = ("title", "author__name", "isbn")
    autocomplete_fields = ("author", "genre")
    raw_id_fields = ("creator", "verified_author")
    readonly_fields = ("slug", "google_books_id", "created_at")
    inlines = [ChapterInline]
    actions = ["approve_selected"]

    @admin.action(description="Схвалити вибрані книги")
    def approve_selected(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"Схвалено книг: {updated}.", messages.SUCCESS)


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("book", "number", "title")
    list_select_related = ("book",)
    search_fields = ("book__title", "title")
    raw_id_fields = ("book",)


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "platform", "created_at")
    list_filter = ("platform",)
    search_fields = ("title", "artist", "external_id")
    raw_id_fields = ("created_by",)


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("track", "book", "chapter", "user", "created_at")
    list_select_related = ("track", "book", "chapter", "user")
    search_fields = ("track__title", "book__title", "user__username")
    raw_id_fields = ("track", "book", "chapter", "user")


class PlaylistItemInline(admin.TabularInline):
    model = PlaylistItem
    extra = 0
    raw_id_fields = ("track",)


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ("title", "book", "user", "created_at")
    list_select_related = ("book", "user")
    search_fields = ("title", "book__title", "user__username")
    raw_id_fields = ("book", "user")
    inlines = [PlaylistItemInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "short_text", "book", "chapter", "playlist", "created_at")
    search_fields = ("text", "user__username")
    raw_id_fields = ("user", "book", "chapter", "playlist", "parent")

    @admin.display(description="Текст")
    def short_text(self, obj):
        return obj.text[: limits.ADMIN_PREVIEW_LENGTH]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "accent", "is_verified_author")
    list_filter = ("is_verified_author", "accent")
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user",)


@admin.register(AuthorVerification)
class AuthorVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "status", "submitted_at", "reviewed_by")
    list_filter = ("status",)
    list_select_related = ("user", "book", "reviewed_by")
    search_fields = ("user__username", "book__title")
    raw_id_fields = ("user", "book", "reviewed_by")
    readonly_fields = ("proof_document_link", "proof_authorship_link", "submitted_at", "reviewed_at", "reviewed_by")
    fields = (
        "user",
        "book",
        "proof_document_link",
        "proof_authorship_link",
        "publisher_url",
        "additional_notes",
        "status",
        "admin_note",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
    )
    actions = ["approve_selected", "reject_selected"]

    @admin.display(description="Документ, що посвідчує особу")
    def proof_document_link(self, obj):
        return self._link(obj, "proof_document")

    @admin.display(description="Підтвердження авторства")
    def proof_authorship_link(self, obj):
        return self._link(obj, "proof_authorship")

    @staticmethod
    def _link(obj, field: str):
        if not obj.pk or not getattr(obj, field):
            return "—"
        url = reverse("core:proof_download", kwargs={"pk": obj.pk, "field": field})
        return format_html('<a href="{}">Завантажити</a>', url)

    def save_model(self, request, obj, form, change):
        decision = obj.status if change and "status" in form.changed_data else None
        if decision in (AuthorVerification.Status.APPROVED, AuthorVerification.Status.REJECTED):
            obj.status = AuthorVerification.Status.PENDING
        super().save_model(request, obj, form, change)
        if decision == AuthorVerification.Status.APPROVED:
            obj.approve(request.user, obj.admin_note)
        elif decision == AuthorVerification.Status.REJECTED:
            obj.reject(request.user, obj.admin_note)

    @admin.action(description="Схвалити вибрані заявки")
    def approve_selected(self, request, queryset):
        pending = list(queryset.filter(status=AuthorVerification.Status.PENDING))
        for verification in pending:
            verification.approve(request.user)
        self.message_user(request, f"Схвалено заявок: {len(pending)}.", messages.SUCCESS)

    @admin.action(description="Відхилити вибрані заявки")
    def reject_selected(self, request, queryset):
        pending = list(queryset.filter(status=AuthorVerification.Status.PENDING))
        for verification in pending:
            verification.reject(request.user)
        self.message_user(request, f"Відхилено заявок: {len(pending)}.", messages.SUCCESS)


@admin.register(BookEditSuggestion)
class BookEditSuggestionAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "changed_fields", "status", "submitted_at", "reviewed_by")
    list_filter = ("status",)
    list_select_related = ("book", "user", "reviewed_by")
    search_fields = ("book__title", "user__username")
    fields = (
        "book",
        "user",
        "changes_table",
        "reason",
        "status",
        "admin_note",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
    )
    actions = ["approve_selected", "reject_selected"]

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly = ["book", "user", "changes_table", "reason", "submitted_at", "reviewed_at", "reviewed_by"]
        if obj is not None and not obj.is_pending:
            readonly += ["status", "admin_note"]
        return readonly

    @admin.display(description="Що змінено")
    def changed_fields(self, obj):
        return ", ".join(obj.field_labels)

    @admin.display(description="Зміни")
    def changes_table(self, obj):
        if not obj.pk:
            return "—"
        rows = format_html_join(
            "",
            "<tr><th>{}</th><td>{}</td><td>{}</td></tr>",
            ((row.label, row.old, row.new) for row in obj.change_rows()),
        )
        return format_html(
            "<table><thead><tr><th></th><th>Було</th><th>Стане</th></tr></thead><tbody>{}</tbody></table>",
            rows,
        )

    def save_model(self, request, obj, form, change):
        decision = obj.status if change and "status" in form.changed_data else None
        reviewers = {
            BookEditSuggestion.Status.APPROVED: suggestion_service.approve_suggestion,
            BookEditSuggestion.Status.REJECTED: suggestion_service.reject_suggestion,
        }
        if decision in reviewers:
            obj.status = BookEditSuggestion.Status.PENDING
        super().save_model(request, obj, form, change)
        if decision in reviewers:
            self._review(request, obj, reviewers[decision])

    @admin.action(description="Прийняти вибрані пропозиції")
    def approve_selected(self, request, queryset):
        reviewed = self._review_pending(request, queryset, suggestion_service.approve_suggestion)
        self.message_user(request, f"Прийнято пропозицій: {reviewed}.", messages.SUCCESS)

    @admin.action(description="Відхилити вибрані пропозиції")
    def reject_selected(self, request, queryset):
        reviewed = self._review_pending(request, queryset, suggestion_service.reject_suggestion)
        self.message_user(request, f"Відхилено пропозицій: {reviewed}.", messages.SUCCESS)

    def _review_pending(self, request, queryset, review) -> int:
        pending = queryset.filter(status=BookEditSuggestion.Status.PENDING).select_related("user", "book")
        return sum(self._review(request, suggestion, review) for suggestion in pending)

    def _review(self, request, suggestion, review) -> bool:
        try:
            review(suggestion, request.user, suggestion.admin_note)
        except suggestion_service.SuggestionError as error:
            self.message_user(request, f"{suggestion.book}: {error}", messages.ERROR)
            return False
        return True
