import json
import re

from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Genre, Playlist, PlaylistItem, Recommendation
from tests.conftest_helpers import make_book, make_chapter, make_track, make_user

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def robots_of(response) -> str:
    return re.search(r'<meta name="robots" content="([^"]*)"', response.content.decode()).group(1)


def canonical_of(response) -> str:
    return re.search(r'<link rel="canonical" href="([^"]*)"', response.content.decode()).group(1)


def json_ld_of(response) -> dict:
    raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', response.content.decode(), re.S).group(1)
    return json.loads(raw)


def graph_types(response) -> list[str]:
    return [node["@type"] for node in json_ld_of(response)["@graph"]]


@override_settings(CACHES=CACHES, SITE_URL="https://songstory.test", SITE_DOMAIN="songstory.test")
class SeoTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.genre = Genre.objects.create(name="Фентезі")
        self.book = make_book(self.user)
        self.book.genre = self.genre
        self.book.save()
        self.chapter = make_chapter(self.book)
        self.track = make_track(title="Епічна тема")

    def recommend(self, chapter=None):
        return Recommendation.objects.create(user=self.user, track=self.track, book=self.book, chapter=chapter)

    def test_home_targets_head_queries(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "<title>Музика для книг і читання")
        self.assertContains(response, "<h1")
        self.assertContains(response, "Музика для книг і читання</h1>")
        self.assertIn("WebSite", graph_types(response))
        self.assertEqual(robots_of(response).split(",")[0], "index")

    def test_book_without_music_is_noindex(self):
        response = self.client.get(self.book.get_absolute_url())
        self.assertTrue(robots_of(response).startswith("noindex"))

    def test_book_with_music_is_indexable_with_rich_metadata(self):
        self.recommend()
        response = self.client.get(self.book.get_absolute_url())
        self.assertTrue(robots_of(response).startswith("index"))
        self.assertContains(response, "<title>Музика до книги «Кобзар» — Тарас Шевченко")
        self.assertContains(response, "Епічна тема")
        description = re.search(r'<meta name="description" content="([^"]*)"', response.content.decode()).group(1)
        self.assertIn("Яку музику слухати під час читання «Кобзар»", description)
        self.assertIn("Виконавець — Епічна тема", description)
        self.assertLessEqual(len(description), 160)
        self.assertEqual(canonical_of(response), f"http://songstory.test{self.book.get_absolute_url()}")
        types = graph_types(response)
        self.assertIn("Book", types)
        self.assertIn("BreadcrumbList", types)
        self.assertIn("ItemList", types)

    def test_description_declines_track_count(self):
        self.recommend()
        description = re.search(
            r'<meta name="description" content="([^"]*)"', self.client.get(self.book.get_absolute_url()).content.decode()
        ).group(1)
        self.assertIn("Читачі радять 1 трек:", description)

    def test_book_page_survives_unsaved_genre_in_suggestion_preview(self):
        from core.models import Book

        book = Book.objects.get(pk=self.book.pk)
        book.genre = Genre(name="Новий жанр")
        from core.seo import book_json_ld

        self.assertIn("BreadcrumbList", book_json_ld(book))

    def test_book_json_ld_is_valid_json_with_genre(self):
        self.recommend()
        nodes = json_ld_of(self.client.get(self.book.get_absolute_url()))["@graph"]
        book = next(node for node in nodes if node["@type"] == "Book")
        self.assertEqual(book["genre"], "Фентезі")
        self.assertEqual(book["inLanguage"], "uk")

    def test_chapter_indexable_only_with_music(self):
        url = self.chapter.get_absolute_url()
        self.assertTrue(robots_of(self.client.get(url)).startswith("noindex"))
        self.recommend(chapter=self.chapter)
        response = self.client.get(url)
        self.assertTrue(robots_of(response).startswith("index"))
        self.assertContains(response, "Музика до розділу «Розділ 1» — «Кобзар»")
        self.assertIn("BreadcrumbList", graph_types(response))

    def test_playlist_metadata(self):
        playlist = Playlist.objects.create(book=self.book, user=self.user, title="Для вечора")
        url = playlist.get_absolute_url()
        self.assertTrue(robots_of(self.client.get(url)).startswith("noindex"))
        PlaylistItem.objects.create(playlist=playlist, track=self.track, position=1)
        response = self.client.get(url)
        self.assertTrue(robots_of(response).startswith("index"))
        node = next(n for n in json_ld_of(response)["@graph"] if n["@type"] == "MusicPlaylist")
        self.assertEqual(node["numTracks"], 1)
        self.assertEqual(node["track"][0]["name"], "Епічна тема")

    def test_genre_page(self):
        url = reverse("core:genre_detail", kwargs={"slug": self.genre.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(robots_of(response).startswith("noindex"))
        self.recommend()
        response = self.client.get(url)
        self.assertTrue(robots_of(response).startswith("index"))
        self.assertContains(response, "Музика для читання фентезі")
        self.assertContains(response, self.book.title)
        self.genre.seo_title = "Фентезі під музику"
        self.genre.save()
        self.assertContains(self.client.get(url), "<title>Фентезі під музику")

    def test_known_genre_has_prepared_copy_without_admin(self):
        self.assertEqual(self.genre.page_title, "Музика для читання фентезі")
        self.assertIn("епічні саундтреки", self.genre.intro_text)
        self.recommend()
        response = self.client.get(self.genre.get_absolute_url())
        self.assertContains(response, "<title>Музика для читання фентезі")
        self.assertContains(response, "епічні саундтреки")

    def test_unknown_genre_gets_generic_copy_and_admin_overrides(self):
        genre = Genre.objects.create(name="Дивний жанр")
        self.assertEqual(genre.page_title, "Музика до книг жанру «Дивний жанр»")
        self.assertIn("«Дивний жанр»", genre.intro_text)
        genre.intro = "Свій текст"
        self.assertEqual(genre.intro_text, "Свій текст")

    def test_empty_genre_is_404(self):
        empty = Genre.objects.create(name="Порожній")
        self.assertEqual(self.client.get(empty.get_absolute_url()).status_code, 404)

    def test_reading_guide(self):
        self.recommend()
        response = self.client.get(reverse("core:reading_music"))
        self.assertContains(response, "<title>Музика для читання: що слухати")
        self.assertContains(response, self.genre.get_absolute_url())
        self.assertContains(response, self.book.title)
        self.assertIn("BreadcrumbList", graph_types(response))

    def test_catalog_pagination_has_own_canonical(self):
        with override_settings(CATALOG_PAGE_SIZE=1):
            make_book(self.user, title="Друга", author="Інший")
            first = self.client.get(reverse("core:book_list"))
            second = self.client.get(reverse("core:book_list") + "?page=2")
        self.assertFalse(canonical_of(first).endswith("?page=2"))
        self.assertTrue(canonical_of(second).endswith("/books/?page=2"))

    def test_filtered_catalog_is_noindex(self):
        response = self.client.get(reverse("core:book_list") + "?music=1")
        self.assertTrue(robots_of(response).startswith("noindex"))

    def test_sitemap_lists_only_pages_with_music(self):
        silent = make_book(self.user, title="Без музики", author="Тихий")
        self.recommend(chapter=self.chapter)
        body = self.client.get(reverse("sitemap")).content.decode()
        self.assertIn(self.book.get_absolute_url(), body)
        self.assertNotIn(silent.get_absolute_url(), body)
        self.assertIn(self.genre.get_absolute_url(), body)
        self.assertIn(self.chapter.get_absolute_url(), body)
        self.assertIn(reverse("core:reading_music"), body)

    def test_robots_blocks_action_pages_and_lists_sitemap(self):
        body = self.client.get(reverse("robots_txt")).content.decode()
        self.assertIn("Disallow: /signup/", body)
        self.assertIn("Disallow: /book/*/recommend/", body)
        self.assertIn("Sitemap:", body)
