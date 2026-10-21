from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Book
from core.services import book_search
from core.services.external import ExternalBook, ExternalSearch
from tests.conftest_helpers import make_user

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
EXTERNAL_ID = "ol:OL1W"


def external_book():
    return ExternalBook(EXTERNAL_ID, "Шістка воронів", "Лі Бардуго", 2015, "", "Опис", "")


def repopulating_search(query, limit=None):
    book_search._remember([external_book()])
    return ExternalSearch([external_book()])


@override_settings(CACHES=CACHES)
class ImportRecoveryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_cache_miss_without_query_cannot_be_recovered(self):
        self.assertIsNone(book_search.get_external_book(EXTERNAL_ID))

    def test_cache_miss_is_recovered_by_repeating_the_search(self):
        with mock.patch.object(book_search, "search_books", side_effect=repopulating_search) as search:
            result = book_search.get_external_book(EXTERNAL_ID, "шістка воронів")
        search.assert_called_once_with("шістка воронів")
        self.assertEqual(result, external_book())

    def test_cache_hit_does_not_repeat_the_search(self):
        book_search._remember([external_book()])
        with mock.patch.object(book_search, "search_books") as search:
            result = book_search.get_external_book(EXTERNAL_ID, "шістка воронів")
        search.assert_not_called()
        self.assertEqual(result, external_book())

    def test_view_imports_book_after_cache_miss(self):
        self.client.force_login(make_user())
        with mock.patch.object(book_search, "search_books", side_effect=repopulating_search):
            response = self.client.post(
                reverse("core:import_book"), {"external_id": EXTERNAL_ID, "query": "шістка воронів"}
            )
        book = Book.objects.get()
        self.assertEqual(book.title, "Шістка воронів")
        self.assertRedirects(response, book.get_absolute_url())

    def test_view_reports_failure_when_book_cannot_be_recovered(self):
        self.client.force_login(make_user())
        with mock.patch.object(book_search, "search_books", return_value=ExternalSearch([])):
            response = self.client.post(
                reverse("core:import_book"),
                {"external_id": EXTERNAL_ID, "query": "щось інше"},
                headers={"accept": "application/json"},
            )
        self.assertEqual(response.status_code, 502)
        self.assertFalse(Book.objects.exists())
