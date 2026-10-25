from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Author, Book, BookEditSuggestion, Genre
from core.services import suggestions as suggestion_service
from tests.conftest_helpers import make_book, make_user

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
EMAIL = {"ADMIN_EMAIL": "admin@example.com", "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
Status = BookEditSuggestion.Status


def form_payload(book: Book, **overrides) -> dict:
    payload = {
        "title": book.title,
        "author_name": book.author.name if book.author_id else "",
        "year": book.year or "",
        "genre_name": book.genre.name if book.genre_id else "",
        "isbn": book.isbn,
        "description": book.description,
        "cover_url": book.cover_url,
        "reason": "",
    }
    return {**payload, **overrides}


@override_settings(CACHES=CACHES, **EMAIL)
class SuggestionTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = make_user("owner")
        self.user = make_user("reader")
        self.book = make_book(self.owner)
        self.url = reverse("core:suggest_edit", args=[self.book.slug])
        self.client.force_login(self.user)

    def suggest(self, **overrides):
        return self.client.post(self.url, form_payload(self.book, **overrides))


class MenuTests(SuggestionTestCase):
    def test_menu_with_suggestion_link_is_shown_to_authenticated_users(self):
        response = self.client.get(self.book.get_absolute_url())
        self.assertContains(response, "data-menu-toggle")
        self.assertContains(response, self.url)

    def test_menu_is_hidden_from_anonymous_users(self):
        self.client.logout()
        response = self.client.get(self.book.get_absolute_url())
        self.assertNotContains(response, "data-menu-toggle")

    def test_management_actions_live_in_the_menu_for_owner_only(self):
        add_chapters = reverse("core:add_chapters", args=[self.book.slug])
        self.assertNotContains(self.client.get(self.book.get_absolute_url()), add_chapters)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.book.get_absolute_url()), add_chapters)


class SuggestionFormTests(SuggestionTestCase):
    def test_login_is_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_form_is_prefilled_with_current_values(self):
        form = self.client.get(self.url).context["form"]
        self.assertEqual(form.initial["title"], self.book.title)
        self.assertEqual(form.initial["author_name"], "Тарас Шевченко")
        self.assertEqual(form.initial["year"], 1840)

    def test_unapproved_book_of_someone_else_is_not_found(self):
        hidden = make_book(self.owner, title="Приховане", author="Інший Автор", approved=False)
        self.assertEqual(self.client.get(reverse("core:suggest_edit", args=[hidden.slug])).status_code, 404)

    def test_unchanged_form_is_rejected(self):
        response = self.suggest()
        self.assertContains(response, "Ви нічого не змінили")
        self.assertEqual(BookEditSuggestion.objects.count(), 0)

    def test_equivalent_spelling_is_not_a_change(self):
        response = self.suggest(author_name="  шевченко   тарас ")
        self.assertContains(response, "Ви нічого не змінили")

    def test_invalid_values_are_reported(self):
        response = self.suggest(isbn="123", cover_url="http://insecure.example/c.jpg")
        self.assertContains(response, "ISBN має містити 10 або 13 цифр")
        self.assertEqual(BookEditSuggestion.objects.count(), 0)

    def test_collision_with_another_book_is_rejected(self):
        make_book(self.owner, title="Зів'яле листя", author="Іван Франко")
        response = self.suggest(title="Зів'яле листя", author_name="Іван Франко")
        self.assertContains(response, "Така книга вже є в каталозі")
        self.assertEqual(BookEditSuggestion.objects.count(), 0)

    def test_book_without_author_can_be_edited_without_one(self):
        orphan = Book.objects.create(title="Без автора", creator=self.owner, is_approved=True)
        response = self.client.post(
            reverse("core:suggest_edit", args=[orphan.slug]), form_payload(orphan, description="Опис")
        )
        self.assertRedirects(response, orphan.get_absolute_url())
        self.assertEqual(BookEditSuggestion.objects.get().changes, {"description": {"old": "", "new": "Опис"}})


class SubmissionTests(SuggestionTestCase):
    def test_only_changed_fields_are_stored_and_admin_is_notified(self):
        response = self.suggest(year=1841, genre_name="поезія", reason="Помилка у році")
        self.assertRedirects(response, self.book.get_absolute_url())
        suggestion = BookEditSuggestion.objects.get()
        self.assertEqual(suggestion.status, Status.PENDING)
        self.assertEqual(
            suggestion.changes,
            {"year": {"old": 1840, "new": 1841}, "genre_name": {"old": "", "new": "Поезія"}},
        )
        self.assertEqual(suggestion.reason, "Помилка у році")
        self.assertEqual(mail.outbox[0].to, ["admin@example.com"])
        self.book.refresh_from_db()
        self.assertEqual(self.book.year, 1840)

    def test_second_pending_suggestion_for_same_book_is_blocked(self):
        self.suggest(year=1841)
        response = self.client.get(self.url)
        self.assertRedirects(response, self.book.get_absolute_url())
        self.suggest(year=1842)
        self.assertEqual(BookEditSuggestion.objects.count(), 1)

    def test_race_on_pending_constraint_is_reported(self):
        suggestion_service.submit_suggestion(
            user=self.user, book=self.book, changes={"year": {"old": 1840, "new": 1841}}
        )
        with self.assertRaises(suggestion_service.PendingSuggestionExists):
            suggestion_service.submit_suggestion(
                user=self.user, book=self.book, changes={"year": {"old": 1840, "new": 1842}}
            )

    @override_settings(PENDING_SUGGESTIONS_LIMIT=1)
    def test_pending_suggestions_are_capped_per_user(self):
        other = make_book(self.owner, title="Інша", author="Автор Інший")
        self.suggest(year=1841)
        response = self.client.post(reverse("core:suggest_edit", args=[other.slug]), form_payload(other, year=1999))
        self.assertContains(response, "На розгляді вже 1 ваших пропозицій")
        self.assertEqual(BookEditSuggestion.objects.count(), 1)

    @override_settings(PENDING_SUGGESTIONS_LIMIT=1)
    def test_staff_is_not_capped(self):
        self.assertIsNone(suggestion_service.pending_suggestions_left(make_user("editor", is_staff=True)))

    def test_staff_changes_are_applied_immediately_without_emails(self):
        self.client.force_login(make_user("editor", is_staff=True))
        response = self.suggest(title="Кобзар (повне видання)", year=1860)
        self.assertRedirects(response, self.book.get_absolute_url())
        self.book.refresh_from_db()
        self.assertEqual((self.book.title, self.book.year), ("Кобзар (повне видання)", 1860))
        self.assertEqual(BookEditSuggestion.objects.get().status, Status.APPROVED)
        self.assertEqual(mail.outbox, [])

    def test_submission_is_rate_limited(self):
        with override_settings(RATE_LIMITS={"suggest_edit": "1/m"}):
            self.suggest(year=1841)
            response = self.suggest(year=1842)
        self.assertEqual(response.status_code, 429)


class ReviewTests(SuggestionTestCase):
    def setUp(self):
        super().setUp()
        self.moderator = make_user("moderator", is_staff=True)
        self.suggest(
            title="Кобзар. Поезії",
            author_name="Леся Українка",
            genre_name="Поезія",
            year=1860,
            isbn="978-966-917-170-6",
            description="Новий опис",
            cover_url="https://example.com/cover.jpg",
        )
        self.suggestion = BookEditSuggestion.objects.get()
        mail.outbox.clear()

    def test_approval_applies_every_change_and_keeps_the_slug(self):
        slug = self.book.slug
        suggestion_service.approve_suggestion(self.suggestion, self.moderator, "Дякуємо")
        book = Book.objects.select_related("author", "genre").get(pk=self.book.pk)
        self.assertEqual(book.slug, slug)
        self.assertEqual(book.title, "Кобзар. Поезії")
        self.assertEqual(book.author.name, "Леся Українка")
        self.assertEqual(book.genre.name, "Поезія")
        self.assertEqual((book.year, book.isbn), (1860, "9789669171706"))
        self.assertEqual(book.description, "Новий опис")
        self.assertEqual(book.cover_url, "https://example.com/cover.jpg")
        self.assertIn("леся", book.search_key)
        self.assertEqual(Book.objects.search("Леся Українка").get(), book)

    def test_approval_reuses_existing_author_and_genre(self):
        genre = Genre.objects.create(name="Поезія")
        author = Author.objects.create(name="Леся Українка")
        suggestion_service.approve_suggestion(self.suggestion, self.moderator)
        book = Book.objects.get(pk=self.book.pk)
        self.assertEqual((book.genre, book.author), (genre, author))
        self.assertEqual(Author.objects.filter(name="Леся Українка").count(), 1)

    def test_approval_closes_suggestion_and_emails_the_author(self):
        suggestion_service.approve_suggestion(self.suggestion, self.moderator, "Дякуємо")
        self.suggestion.refresh_from_db()
        self.assertEqual(self.suggestion.status, Status.APPROVED)
        self.assertEqual(self.suggestion.reviewed_by, self.moderator)
        self.assertIsNotNone(self.suggestion.reviewed_at)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn("Дякуємо", mail.outbox[0].body)

    def test_rejection_leaves_the_book_untouched_and_emails_the_author(self):
        suggestion_service.reject_suggestion(self.suggestion, self.moderator, "Неточне джерело")
        self.suggestion.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(self.suggestion.status, Status.REJECTED)
        self.assertEqual(self.book.title, "Кобзар")
        self.assertIn("Неточне джерело", mail.outbox[0].body)

    def test_reviewed_suggestion_cannot_be_reviewed_again(self):
        suggestion_service.reject_suggestion(self.suggestion, self.moderator)
        with self.assertRaises(suggestion_service.SuggestionAlreadyReviewed):
            suggestion_service.approve_suggestion(self.suggestion, self.moderator)

    def test_approval_is_refused_when_book_would_become_a_duplicate(self):
        make_book(self.owner, title="Кобзар. Поезії", author="Леся Українка")
        with self.assertRaises(suggestion_service.SuggestionConflict):
            suggestion_service.approve_suggestion(self.suggestion, self.moderator)
        self.suggestion.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(self.suggestion.status, Status.PENDING)
        self.assertEqual(self.book.title, "Кобзар")

    def test_user_can_suggest_again_after_review(self):
        suggestion_service.reject_suggestion(self.suggestion, self.moderator)
        response = self.suggest(year=1900)
        self.assertRedirects(response, self.book.get_absolute_url())
        self.assertEqual(BookEditSuggestion.objects.filter(status=Status.PENDING).count(), 1)


class SuggestionAdminTests(SuggestionTestCase):
    def setUp(self):
        super().setUp()
        self.suggest(year=1841)
        self.suggestion = BookEditSuggestion.objects.get()
        self.admin = make_user("moderator", is_staff=True, is_superuser=True)
        self.client.force_login(self.admin)

    def test_changelist_and_detail_render_the_diff(self):
        self.assertContains(self.client.get(reverse("admin:core_bookeditsuggestion_changelist")), "Рік видання")
        detail = self.client.get(reverse("admin:core_bookeditsuggestion_change", args=[self.suggestion.pk]))
        self.assertContains(detail, "1840")
        self.assertContains(detail, "1841")

    def test_bulk_approve_action(self):
        self.client.post(
            reverse("admin:core_bookeditsuggestion_changelist"),
            {"action": "approve_selected", "_selected_action": [self.suggestion.pk]},
        )
        self.book.refresh_from_db()
        self.assertEqual(self.book.year, 1841)

    def test_status_change_in_detail_form_triggers_review(self):
        url = reverse("admin:core_bookeditsuggestion_change", args=[self.suggestion.pk])
        self.client.post(url, {"status": Status.REJECTED, "admin_note": "Ні"})
        self.suggestion.refresh_from_db()
        self.assertEqual(self.suggestion.status, Status.REJECTED)
        self.assertEqual(self.suggestion.reviewed_by, self.admin)
