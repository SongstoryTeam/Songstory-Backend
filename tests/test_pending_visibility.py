from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Book, Genre
from core.services import books as book_service
from core.services import catalog
from core.services.external import ExternalBook
from tests.conftest_helpers import make_book, make_user

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
OWN_NOTICE = "Поки що її бачите лише ви"
FOREIGN_NOTICE = "Її бачать лише той, хто її додав, і модератори"
PENDING_BADGE = "На перевірці"


@override_settings(CACHES=CACHES)
class PendingBookVisibilityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = make_user("owner")
        self.reader = make_user("reader")
        self.moderator = make_user("moderator", is_staff=True)
        self.pending = make_book(self.owner, title="Чернетка", author="Автор Чернетки", approved=False)
        self.published = make_book(self.owner, title="Опублікована", author="Автор Опублікованої", approved=True)

    def titles(self, user, query="") -> list[str]:
        return [book.title for book in catalog.search_local(user, query or "а", 20)]

    def listed(self, user) -> set[str]:
        return {book.title for book in catalog.visible_books(user)}

    def test_pending_book_is_listed_only_for_its_owner(self):
        self.assertIn(self.pending.title, self.listed(self.owner))
        self.assertNotIn(self.pending.title, self.listed(self.reader))

    def test_staff_catalog_does_not_include_foreign_pending_books(self):
        self.assertNotIn(self.pending.title, self.listed(self.moderator))
        self.assertIn(self.published.title, self.listed(self.moderator))

    def test_staff_can_still_open_foreign_pending_book_directly(self):
        self.client.force_login(self.moderator)
        self.assertEqual(self.client.get(self.pending.get_absolute_url()).status_code, 200)

    def test_anonymous_catalog_hides_pending_books(self):
        self.assertNotContains(self.client.get(reverse("core:book_list")), self.pending.title)
        self.assertNotContains(self.client.get(reverse("core:home")), self.pending.title)

    def test_reader_never_sees_pending_book_anywhere(self):
        self.client.force_login(self.reader)
        for url in (reverse("core:home"), reverse("core:book_list")):
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), self.pending.title)
        search = self.client.get(reverse("core:search"), {"q": "Чернетка"})
        self.assertEqual(search.context["local_books"], [])
        self.assertEqual(self.client.get(reverse("core:search_suggest"), {"q": "Чернетка"}).json()["results"], [])
        self.assertEqual(self.client.get(self.pending.get_absolute_url()).status_code, 404)

    def test_owner_sees_pending_book_marked_in_catalog(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("core:book_list"))
        self.assertContains(response, self.pending.title)
        self.assertContains(response, PENDING_BADGE, count=1)

    def test_detail_notice_differs_for_owner_and_moderator(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.pending.get_absolute_url())
        self.assertContains(response, OWN_NOTICE)
        self.assertNotContains(response, FOREIGN_NOTICE)
        self.client.force_login(self.moderator)
        response = self.client.get(self.pending.get_absolute_url())
        self.assertContains(response, FOREIGN_NOTICE)
        self.assertNotContains(response, OWN_NOTICE)

    def test_published_book_has_no_notice(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.published.get_absolute_url())
        self.assertNotContains(response, OWN_NOTICE)
        self.assertNotContains(response, FOREIGN_NOTICE)

    def test_catalog_total_matches_what_the_user_can_list(self):
        for user, expected in ((self.reader, 1), (self.owner, 2), (self.moderator, 1)):
            with self.subTest(user=user.username):
                self.assertEqual(catalog.listed_total(user), expected)
                self.assertEqual(len(self.listed(user)), expected)

    def test_genre_counts_follow_the_viewer(self):
        genre = Genre.objects.create(name="Чернетковий жанр")
        Book.objects.filter(pk=self.pending.pk).update(genre=genre)
        self.assertFalse(catalog.genres_in_use(self.reader).filter(pk=genre.pk).exists())
        self.assertFalse(catalog.genres_in_use(self.moderator).filter(pk=genre.pk).exists())
        self.assertEqual(catalog.genres_in_use(self.owner).get(pk=genre.pk).books_total, 1)

    def test_catalog_page_count_is_consistent_with_header(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("core:book_list"))
        self.assertEqual(response.context["catalog_total"], response.context["result"].total)


@override_settings(CACHES=CACHES)
class ImportOfHiddenBookTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = make_user("owner")
        self.reader = make_user("reader")
        self.client.force_login(self.reader)
        self.external = ExternalBook(
            external_id="ext-1",
            title="Чужа чернетка",
            author="Автор",
            isbn="9789669171706",
            year=2020,
            cover_url="",
            description="",
        )
        self.pending = book_service.create_book(
            user=self.owner, title="Чужа чернетка", author_name="Автор", isbn="9789669171706"
        )

    def post_import(self):
        with patch("core.views.books.get_external_book", return_value=self.external):
            return self.client.post(reverse("core:import_book"), {"external_id": "ext-1"})

    def test_import_of_hidden_duplicate_does_not_redirect_to_it(self):
        response = self.post_import()
        self.assertRedirects(response, reverse("core:book_list"), fetch_redirect_response=False)
        self.assertEqual(Book.objects.count(), 1)

    def test_import_of_hidden_duplicate_does_not_approve_it(self):
        self.post_import()
        self.pending.refresh_from_db()
        self.assertFalse(self.pending.is_approved)

    def test_import_of_visible_duplicate_redirects_to_it(self):
        Book.objects.filter(pk=self.pending.pk).update(is_approved=True)
        response = self.post_import()
        self.assertRedirects(response, self.pending.get_absolute_url(), fetch_redirect_response=False)
