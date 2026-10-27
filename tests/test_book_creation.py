from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Book, Genre
from core.services import books as book_service
from tests.conftest_helpers import make_book, make_user

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PAYLOAD = {"title": "Нова книга", "author_name": "Новий Автор", "year": 2020}


@override_settings(CACHES=CACHES)
class CreateBookPageTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.client.force_login(self.user)
        self.url = reverse("core:create_book")

    def test_page_renders_all_steps_in_order(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([step["id"] for step in response.context["form"].STEPS], ["book", "details", "cover"])
        for marker in ("data-book-wizard", 'data-wizard-step="0"', 'data-wizard-step="2"', "data-preview", "data-lookup"):
            self.assertContains(response, marker)

    def test_wizard_root_activates_wizard_styles(self):
        self.assertContains(self.client.get(self.url), 'class="form-box wizard book-form"')

    def test_preview_receives_cover_check_delay_from_settings(self):
        with override_settings(COVER_CHECK_DEBOUNCE_MS=777):
            self.assertContains(self.client.get(self.url), 'data-cover-delay="777"')

    def test_creation_form_has_no_reset_controls(self):
        self.assertNotContains(self.client.get(self.url), "data-field-reset")

    def test_title_is_prefilled_from_search_query(self):
        response = self.client.get(self.url, {"title": "  Тіні   забутих "})
        self.assertEqual(response.context["form"].initial["title"], "Тіні забутих")

    def test_existing_genres_are_offered_for_reuse(self):
        Genre.objects.create(name="Фентезі")
        self.assertContains(self.client.get(self.url), '<option value="Фентезі">')

    def test_manual_book_waits_for_moderation(self):
        response = self.client.post(self.url, PAYLOAD)
        book = Book.objects.get()
        self.assertRedirects(response, book.get_absolute_url())
        self.assertFalse(book.is_approved)

    def test_staff_book_is_published_immediately(self):
        self.client.force_login(make_user("editor", is_staff=True))
        self.client.post(self.url, PAYLOAD)
        self.assertTrue(Book.objects.get().is_approved)

    def test_notice_depends_on_moderation_rules(self):
        self.assertContains(self.client.get(self.url), "після перевірки модератором")
        self.client.force_login(make_user("editor", is_staff=True))
        self.assertContains(self.client.get(self.url), "одразу після додавання")


@override_settings(CACHES=CACHES)
class DuplicateGuardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.client.force_login(self.user)
        self.url = reverse("core:create_book")
        self.existing = book_service.create_book(
            user=make_user("owner"), title="Шістка воронів", author_name="Лі Бардуґо", isbn="9789669171706"
        )
        self.existing.is_approved = True
        self.existing.save(update_fields=["is_approved"])

    def test_same_isbn_is_rejected_even_with_different_title(self):
        payload = {**PAYLOAD, "isbn": "978-966-917-170-6"}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Book.objects.count(), 1)
        self.assertContains(response, self.existing.get_absolute_url())

    def test_same_title_and_author_in_other_spelling_is_rejected(self):
        response = self.client.post(self.url, {"title": "ШІСТКА  ВОРОНІВ", "author_name": "бардуго лі"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Book.objects.count(), 1)

    def test_hidden_duplicate_is_reported_without_leaking_a_link(self):
        hidden = make_book(make_user("other"), title="Приховане", author="Автор Прихованого", approved=False)
        response = self.client.post(self.url, {"title": "Приховане", "author_name": "Автор Прихованого"})
        self.assertContains(response, "вже надіслана на перевірку")
        self.assertNotContains(response, hidden.get_absolute_url())
        self.assertEqual(Book.objects.filter(title="Приховане").count(), 1)

    def test_invalid_isbn_is_reported(self):
        response = self.client.post(self.url, {**PAYLOAD, "isbn": "12345"})
        self.assertEqual(Book.objects.count(), 1)
        self.assertContains(response, "ISBN має містити 10 або 13 цифр")


@override_settings(CACHES=CACHES)
class CheckBookEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.book = make_book(self.user)
        self.client.force_login(self.user)
        self.url = reverse("core:check_book")

    def check(self, **params):
        return self.client.get(self.url, params).json()["duplicate"]

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url, {"title": "Кобзар", "author": "Тарас Шевченко"}).status_code, 302)

    def test_unknown_book_is_not_a_duplicate(self):
        self.assertIsNone(self.check(title="Зовсім інша", author="Тарас Шевченко"))

    def test_incomplete_input_is_ignored(self):
        self.assertIsNone(self.check(title="Кобзар"))
        self.assertIsNone(self.check(author="Тарас Шевченко"))

    def test_visible_duplicate_comes_with_link(self):
        self.assertEqual(
            self.check(title="кобзар", author="Шевченко Тарас"),
            {"title": "Кобзар", "url": self.book.get_absolute_url()},
        )

    def test_book_hidden_from_user_is_reported_as_pending_only(self):
        make_book(make_user("other"), title="Приховане", author="Інший Автор", approved=False)
        self.assertEqual(self.check(title="Приховане", author="Інший Автор"), {"pending": True})

    def test_requests_are_rate_limited(self):
        with override_settings(RATE_LIMITS={"book_check": "1/m"}):
            self.client.get(self.url, {"title": "а", "author": "б"})
            response = self.client.get(self.url, {"title": "а", "author": "б"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {"error": "rate_limited"})


@override_settings(CACHES=CACHES)
class SpamProtectionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.client.force_login(self.user)
        self.url = reverse("core:create_book")

    @override_settings(PENDING_BOOKS_LIMIT=2)
    def test_pending_books_are_capped_per_user(self):
        for number in range(2):
            self.client.post(self.url, {"title": f"Книга {number}", "author_name": "Автор"})
        response = self.client.post(self.url, {"title": "Зайва", "author_name": "Автор"})
        self.assertEqual(Book.objects.count(), 2)
        self.assertNotContains(response, "data-book-wizard")
        self.assertContains(response, "чекають на перевірку")

    @override_settings(PENDING_BOOKS_LIMIT=1)
    def test_approved_books_do_not_count_towards_cap(self):
        make_book(self.user, approved=True)
        self.client.post(self.url, PAYLOAD)
        self.assertEqual(Book.objects.count(), 2)

    @override_settings(PENDING_BOOKS_LIMIT=1)
    def test_staff_is_not_capped(self):
        self.client.force_login(make_user("editor", is_staff=True))
        for number in range(3):
            self.client.post(self.url, {"title": f"Книга {number}", "author_name": "Автор"})
        self.assertEqual(Book.objects.count(), 3)

    def test_pending_books_left_reports_remaining_quota(self):
        with override_settings(PENDING_BOOKS_LIMIT=3):
            self.client.post(self.url, PAYLOAD)
            self.assertEqual(book_service.pending_books_left(self.user), 2)
            self.assertIsNone(book_service.pending_books_left(make_user("editor", is_staff=True)))

    def test_creation_is_rate_limited(self):
        with override_settings(RATE_LIMITS={"create_book": "1/m"}):
            self.client.post(self.url, PAYLOAD)
            response = self.client.post(self.url, {"title": "Інша", "author_name": "Автор"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(Book.objects.count(), 1)
