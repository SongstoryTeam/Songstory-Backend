from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from core.models import Book
from core.services import catalog
from core.services.books import import_external_book
from core.services.google_books import ExternalBook, ExternalSearch, book_key, search_google_books
from core.text import search_form, search_terms
from tests.conftest_helpers import make_book, make_user

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


class SearchFormTests(SimpleTestCase):
    def test_all_apostrophe_variants_collapse(self):
        variants = ["П'ять", "П’ять", "Пʼять", "П`ять", "Пять", "ПЯТЬ"]
        self.assertEqual({search_form(value) for value in variants}, {"пять"})

    def test_punctuation_and_whitespace_are_ignored(self):
        self.assertEqual(search_form("  Тигролови:  роман! "), "тигролови роман")
        self.assertEqual(search_terms("Дж. Р. Р. Толкін"), ["дж", "р", "р", "толкін"])

    def test_decomposed_unicode_matches_composed(self):
        composed, decomposed = "\u0419\u043e\u0441\u0438\u043f", "\u0418\u0306\u043e\u0441\u0438\u043f"
        self.assertNotEqual(composed, decomposed)
        self.assertEqual(search_form(composed), search_form(decomposed))

    def test_empty_after_normalization(self):
        self.assertEqual(search_terms(" ?! "), [])


class LocalSearchTests(TestCase):
    def setUp(self):
        self.user = make_user()
        for title, author in [
            ("П'ять пальців", "Автор"),
            ("Тигролови: роман", "Іван Багряний"),
            ("Тигролови", "Іван Багряний"),
            ("Володар перснів", "Толкін"),
            ("Історія перснів", "Інший"),
        ]:
            make_book(self.user, title=title, author=author)

    def titles(self, query):
        return [book.title for book in catalog.search_local(self.user, query, 10)]

    def test_apostrophe_and_case_insensitive_matching(self):
        for query in ("п'ять", "П’ять", "Пʼять", "ПЯТЬ", "пять пальців"):
            with self.subTest(query=query):
                self.assertEqual(self.titles(query), ["П’ять пальців"])

    def test_trailing_punctuation_does_not_break_match(self):
        self.assertIn("Тигролови", self.titles(" Тигролови: "))

    def test_exact_title_ranks_before_longer_titles(self):
        self.assertEqual(self.titles("тигролови")[0], "Тигролови")

    def test_prefix_beats_contains(self):
        self.assertEqual(self.titles("вол")[0], "Володар перснів")

    def test_author_search_and_empty_query(self):
        self.assertEqual(len(self.titles("багряний")), 2)
        self.assertEqual(self.titles("?!"), [])

    def test_renaming_book_updates_keys(self):
        book = Book.objects.get(title="Тигролови")
        book.title = "Дикі гуси"
        book.save()
        self.assertEqual(self.titles("дикі"), ["Дикі гуси"])
        self.assertNotIn("Тигролови", self.titles("тигролови"))


@override_settings(CACHES=CACHES)
class ExternalSearchTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def payload(self, *items):
        return {"items": [{"id": item[0], "volumeInfo": item[1]} for item in items]}

    def volume(self, title, author, cover=False, language="uk"):
        info = {"title": title, "authors": [author], "language": language, "publishedDate": "2010-01-01"}
        if cover:
            info["imageLinks"] = {"thumbnail": "http://books.google.com/x.jpg&edge=curl"}
        return info

    def test_editions_with_same_title_and_author_are_deduplicated_preferring_cover(self):
        payload = self.payload(
            ("a", self.volume("Кобзар", "Тарас Шевченко")),
            ("b", self.volume("Кобзар", "Тарас Шевченко", cover=True)),
            ("c", self.volume("Кобзар", "Тарас Шевченко", language="en")),
        )
        with mock.patch("core.services.google_books.get_json", return_value=payload):
            result = search_google_books("кобзар")
        self.assertEqual([book.external_id for book in result.books], ["b"])
        self.assertEqual(result.books[0].cover_url, "https://books.google.com/x.jpg")

    def test_requests_are_restricted_to_ukrainian(self):
        with mock.patch("core.services.google_books.get_json", return_value={}) as fetch:
            search_google_books("кобзар")
        self.assertEqual(fetch.call_args_list[0].args[1]["langRestrict"], "uk")

    def test_known_books_are_excluded_by_id_and_by_title_author(self):
        make_book(None, title="Кобзар", author="Тарас Шевченко")
        known = ExternalBook("x1", "Кобзар", "Тарас Шевченко", 2010, "", "", "")
        fresh = ExternalBook("x2", "Лісова пісня", "Леся Українка", 1911, "", "", "")
        self.assertEqual(catalog.exclude_known([known, fresh]), [fresh])

    def test_import_does_not_create_second_book_for_another_edition(self):
        user = make_user()
        first, created_first = import_external_book(ExternalBook("g1", "Кобзар", "Тарас Шевченко", 2010, "", "", ""), user)
        second, created_second = import_external_book(ExternalBook("g2", "Кобзар", "Тарас Шевченко", 2015, "", "", ""), user)
        self.assertEqual((created_first, created_second), (True, False))
        self.assertEqual(first, second)
        self.assertEqual(Book.objects.count(), 1)

    def test_book_key_ignores_apostrophe_style(self):
        a = ExternalBook("1", "П'ять", "Автор", None, "", "", "")
        b = ExternalBook("2", "П’ять", "Автор", None, "", "", "")
        self.assertEqual(book_key(a), book_key(b))


@override_settings(CACHES=CACHES)
class SuggestEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.url = reverse("core:search_suggest")
        self.external = ExternalBook("g9", "Тіні забутих предків", "Коцюбинський", 1911, "", "", "")

    def get(self, query, external=None):
        found = ExternalSearch([self.external] if external is None else external)
        with mock.patch("core.views.catalog.search_books", return_value=found) as fetch:
            response = self.client.get(self.url, {"q": query})
        return response.json(), fetch

    def test_returns_local_and_external_groups(self):
        make_book(None, title="Тіні в лісі", author="Хтось")
        payload, _ = self.get("тіні")
        self.assertEqual([item["title"] for item in payload["results"]], ["Тіні в лісі"])
        self.assertEqual(payload["external"][0]["external_id"], "g9")
        self.assertFalse(payload["can_import"])

    def test_external_not_requested_for_very_short_queries(self):
        payload, fetch = self.get("ті")
        fetch.assert_not_called()
        self.assertEqual(payload["external"], [])

    def test_external_skipped_when_catalog_already_has_enough_matches(self):
        for number in range(6):
            make_book(None, title=f"Тіні {number}", author=f"Автор {number}")
        payload, fetch = self.get("тіні")
        fetch.assert_not_called()
        self.assertEqual(len(payload["results"]), 6)

    def test_flags_unavailable_service(self):
        payload, _ = self.get("тіні", external=[])
        self.assertFalse(payload["external_unavailable"])
        with mock.patch("core.views.catalog.search_books", return_value=ExternalSearch([], unavailable=True)):
            payload = self.client.get(self.url, {"q": "тіні"}).json()
        self.assertTrue(payload["external_unavailable"])

    def test_import_flag_for_authenticated_user(self):
        self.client.force_login(make_user())
        payload, _ = self.get("тіні")
        self.assertTrue(payload["can_import"])
        self.assertEqual(payload["import_url"], reverse("core:import_book"))

    def test_blank_query_returns_empty_payload(self):
        payload, fetch = self.get("  ?! ")
        fetch.assert_not_called()
        self.assertEqual((payload["results"], payload["external"]), ([], []))
