from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from core.models import Book
from core.services import book_search
from core.services.apple_books import parse_result, search_apple_books
from core.services.external import ExternalBook, ExternalSearch, looks_ukrainian
from core.services.http import ExternalServiceError
from core.services.open_library import parse_doc, search_open_library
from tests.conftest_helpers import make_user

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def book(external_id, title, author="", cover="", original="", year=None):
    return ExternalBook(external_id, title, author, year, cover, "", "", original)


class LooksUkrainianTests(SimpleTestCase):
    def test_accepts_ukrainian_titles(self):
        for title in ("Шістка воронів", "Кобзар", "Тіні забутих предків", "Ґудзик"):
            with self.subTest(title=title):
                self.assertTrue(looks_ukrainian(title))

    def test_rejects_russian_and_latin_titles(self):
        for title in ("Мастер и Маргарита", "Что делать", "Six of Crows", "Эхо", ""):
            with self.subTest(title=title):
                self.assertFalse(looks_ukrainian(title))


class OpenLibraryParseTests(SimpleTestCase):
    doc = {
        "key": "/works/OL17930368W",
        "title": "Six of Crows",
        "author_name": ["Leigh Bardugo"],
        "first_publish_year": 2015,
        "cover_i": 111,
        "editions": {"docs": [{"title": "Шістка воронів", "cover_i": 222, "publish_year": [2019, 2021], "isbn": ["978"]}]},
    }

    def test_uses_ukrainian_edition_title_and_keeps_original(self):
        parsed = parse_doc(self.doc)
        self.assertEqual(parsed.title, "Шістка воронів")
        self.assertEqual(parsed.original_title, "Six of Crows")
        self.assertEqual((parsed.external_id, parsed.year, parsed.isbn), ("ol:OL17930368W", 2019, "978"))
        self.assertTrue(parsed.cover_url.endswith("/222-M.jpg"))

    def test_falls_back_to_work_data_without_editions(self):
        parsed = parse_doc({"key": "/works/OL1W", "title": "Кобзар", "first_publish_year": 1840, "cover_i": 5})
        self.assertEqual((parsed.title, parsed.year, parsed.original_title), ("Кобзар", 1840, ""))
        self.assertTrue(parsed.cover_url.endswith("/5-M.jpg"))

    def test_skips_docs_without_key_or_title(self):
        self.assertIsNone(parse_doc({"title": "Кобзар"}))
        self.assertIsNone(parse_doc({"key": "/works/OL1W"}))

    @override_settings(CACHES=CACHES)
    def test_request_asks_for_ukrainian_editions_and_strips_solr_syntax(self):
        cache.clear()
        with mock.patch("core.services.open_library.get_json", return_value={"docs": []}) as fetch:
            search_open_library('кобзар: "шевченко"')
        query = fetch.call_args.args[1]["q"]
        self.assertTrue(query.endswith("language:ukr"))
        self.assertNotIn('"', query.replace("language:ukr", ""))
        self.assertNotIn(":", query.replace("language:ukr", ""))


class AppleParseTests(SimpleTestCase):
    item = {
        "trackId": 42,
        "trackName": "Шістка воронів",
        "artistName": "Лі Бардуго",
        "releaseDate": "2019-05-01T07:00:00Z",
        "artworkUrl100": "https://is1.mzstatic.com/image/thumb/Publication/x/100x100bb.jpg",
        "description": "<b>Команда</b> злодіїв &amp; убивць",
    }

    def test_parses_fields_and_upgrades_cover(self):
        parsed = parse_result(self.item)
        self.assertEqual((parsed.external_id, parsed.year, parsed.author), ("apple:42", 2019, "Лі Бардуго"))
        self.assertIn("/400x400bb.jpg", parsed.cover_url)
        self.assertEqual(parsed.description, "Команда злодіїв & убивць")

    def test_drops_russian_and_latin_titles(self):
        self.assertIsNone(parse_result({**self.item, "trackName": "Мастер и Маргарита"}))
        self.assertIsNone(parse_result({**self.item, "trackName": "Six of Crows"}))

    @override_settings(CACHES=CACHES)
    def test_failure_enters_cooldown_and_does_not_hammer_the_service(self):
        cache.clear()
        with mock.patch("core.services.apple_books.get_json", side_effect=ExternalServiceError("x", status=429)) as fetch:
            first = search_apple_books("кобзар")
            second = search_apple_books("інша книга")
        self.assertTrue(first.unavailable and second.unavailable)
        self.assertEqual(fetch.call_count, 1)


@override_settings(CACHES=CACHES, BOOK_SOURCES=["google", "openlibrary", "apple"], GOOGLE_BOOKS_API_KEY="key")
class AggregatorTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def search(self, query="шістка воронів", google=(), library=(), apple=(), **flags):
        def result(books, name):
            return ExternalSearch(list(books), unavailable=flags.get(name, False))

        with mock.patch.object(book_search, "search_google_books", lambda q: result(google, "google_down")), \
                mock.patch.object(book_search, "search_open_library", lambda q: result(library, "library_down")), \
                mock.patch.object(book_search, "search_apple_books", lambda q: result(apple, "apple_down")):
            return book_search.search_books(query)

    def test_same_book_from_several_sources_is_merged_and_keeps_best_fields(self):
        result = self.search(
            google=[book("g1", "Шістка воронів", "Лі Бардуґо")],
            library=[book("ol:1", "Шістка воронів", "Leigh Bardugo", cover="https://c/ol.jpg", original="Six of Crows")],
            apple=[book("apple:1", "Шістка воронів", "Лі Бардуго", cover="https://c/apple.jpg")],
        )
        self.assertEqual(len(result.books), 1)
        merged = result.books[0]
        self.assertTrue(merged.cover_url)
        self.assertEqual(merged.original_title, "Six of Crows")
        self.assertTrue(merged.author.startswith("Лі"))

    def test_different_authors_with_same_title_are_not_merged(self):
        result = self.search(
            "мауглі",
            google=[book("g1", "Мауглі", "Редьярд Кіплінг"), book("g2", "Мауглі", "Іван Франко")],
        )
        self.assertEqual(len(result.books), 2)

    def test_one_source_down_does_not_break_search(self):
        result = self.search(library=[book("ol:1", "Шістка воронів", "Leigh Bardugo")], google_down=True, apple_down=True)
        self.assertEqual([item.external_id for item in result.books], ["ol:1"])
        self.assertFalse(result.unavailable)

    def test_all_sources_down_reports_unavailable(self):
        result = self.search(google_down=True, library_down=True, apple_down=True)
        self.assertTrue(result.unavailable)

    def test_all_sources_empty_is_not_unavailable(self):
        self.assertFalse(self.search().unavailable)

    def test_crashing_source_is_isolated(self):
        def boom(query):
            raise RuntimeError("boom")

        with mock.patch.object(book_search, "search_google_books", boom), \
                mock.patch.object(book_search, "search_open_library", lambda q: ExternalSearch([book("ol:1", "Шістка воронів")])), \
                mock.patch.object(book_search, "search_apple_books", lambda q: ExternalSearch([])):
            with self.assertLogs("core.services.book_search", level="ERROR"):
                result = book_search.search_books("шістка воронів")
        self.assertEqual(len(result.books), 1)

    def test_exact_title_with_cover_ranks_first_and_irrelevant_results_are_dropped(self):
        result = self.search(
            "кобзар",
            google=[
                book("g1", "Кобзар. Вибране", "Тарас Шевченко"),
                book("g2", "Лісова пісня", "Леся Українка"),
                book("g3", "Кобзар", "Тарас Шевченко", cover="https://c/k.jpg"),
            ],
        )
        self.assertEqual([item.external_id for item in result.books], ["g3", "g1"])

    def test_inflected_query_finds_title(self):
        result = self.search("воронів", google=[book("g1", "Ворони", "Автор")])
        self.assertEqual(len(result.books), 1)

    def test_english_query_matches_ukrainian_edition_via_original_title(self):
        result = self.search("six of crows", library=[book("ol:1", "Шістка воронів", "Leigh Bardugo", original="Six of Crows")])
        self.assertEqual([item.title for item in result.books], ["Шістка воронів"])

    def test_limit_is_applied(self):
        books = [book(f"g{n}", f"Кобзар {n}", "Автор") for n in range(8)]
        with mock.patch.object(book_search, "search_google_books", lambda q: ExternalSearch(books)), \
                mock.patch.object(book_search, "search_open_library", lambda q: ExternalSearch([])), \
                mock.patch.object(book_search, "search_apple_books", lambda q: ExternalSearch([])):
            self.assertEqual(len(book_search.search_books("кобзар", limit=3).books), 3)

    @override_settings(GOOGLE_BOOKS_API_KEY="")
    def test_google_is_skipped_without_key(self):
        google = mock.Mock(return_value=ExternalSearch([]))
        with mock.patch.object(book_search, "search_google_books", google), \
                mock.patch.object(book_search, "search_open_library", lambda q: ExternalSearch([])), \
                mock.patch.object(book_search, "search_apple_books", lambda q: ExternalSearch([])):
            book_search.search_books("кобзар")
        google.assert_not_called()

    @override_settings(BOOK_SOURCES=[])
    def test_no_sources_configured_reports_unavailable(self):
        self.assertTrue(book_search.search_books("кобзар").unavailable)

    def test_found_books_are_remembered_for_import(self):
        self.search(library=[book("ol:1", "Шістка воронів", "Leigh Bardugo")])
        self.assertEqual(book_search.get_external_book("ol:1").title, "Шістка воронів")

    def test_prefixed_id_missing_from_cache_is_not_sent_to_google(self):
        with mock.patch.object(book_search, "get_google_book") as google:
            self.assertIsNone(book_search.get_external_book("ol:unknown"))
        google.assert_not_called()

    def test_plain_id_falls_back_to_google(self):
        found = book("g1", "Кобзар")
        with mock.patch.object(book_search, "get_google_book", return_value=found):
            self.assertEqual(book_search.get_external_book("g1"), found)


@override_settings(CACHES=CACHES, BOOK_SOURCES=["openlibrary"])
class ImportFromOtherSourceTests(TestCase):
    def test_book_found_via_open_library_can_be_imported(self):
        cache.clear()
        self.addCleanup(cache.clear)
        user = make_user()
        self.client.force_login(user)
        found = book("ol:OL1W", "Шістка воронів", "Leigh Bardugo", year=2019)
        with mock.patch.object(book_search, "search_open_library", lambda q: ExternalSearch([found])):
            self.client.get(reverse("core:search_suggest"), {"q": "шістка воронів"})
        response = self.client.post(reverse("core:import_book"), {"external_id": "ol:OL1W"})
        self.assertEqual(response.status_code, 302)
        imported = Book.objects.get(google_books_id="ol:OL1W")
        self.assertEqual((imported.title, imported.author.name), ("Шістка воронів", "Leigh Bardugo"))
