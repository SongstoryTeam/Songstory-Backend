from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from core.ratelimits import client_ip
from core.text import clean_query, normalize, search_terms
from tests.conftest_helpers import make_book

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


class NormalizeTests(TestCase):
    def test_apostrophe_variants_are_unified(self):
        for variant in ("п'ята", "п’ята", "пʼята", "п‘ята", "п`ята"):
            with self.subTest(variant=variant):
                self.assertEqual(normalize(variant), "п'ята")

    def test_search_terms_split_on_whitespace(self):
        self.assertEqual(search_terms("  Гаррі   ПОТТЕР "), ["гаррі", "поттер"])

    def test_clean_query_collapses_spaces_and_limits_length(self):
        self.assertEqual(clean_query("  а   б  "), "а б")
        self.assertEqual(len(clean_query("я" * 500)), 100)


@override_settings(CACHES=CACHES)
class SearchBehaviourTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_straight_apostrophe_finds_typographic_one(self):
        make_book(title="П’ята пора", author="Автор")
        self.assertEqual(self.client.get(reverse("core:search_suggest"), {"q": "п'ята"}).json()["results"][0]["title"], "П’ята пора")

    def test_suggest_ignores_too_short_queries(self):
        make_book()
        payload = self.client.get(reverse("core:search_suggest"), {"q": "к"}).json()
        self.assertEqual(payload["results"], [])
        self.assertIn("all_url", payload)

    def test_suggest_has_own_rate_limit_separate_from_search_page(self):
        make_book()
        with override_settings(RATE_LIMITS={"search": "1/m", "search_suggest": "5/m"}):
            for _ in range(5):
                self.assertEqual(self.client.get(reverse("core:search_suggest"), {"q": "кобзар"}).status_code, 200)
            self.assertEqual(self.client.get(reverse("core:search_suggest"), {"q": "кобзар"}).status_code, 429)

    def test_rate_limit_is_per_real_client_behind_proxy(self):
        make_book()
        url = reverse("core:search_suggest")
        with override_settings(RATE_LIMITS={"search_suggest": "2/m"}, TRUSTED_PROXY_COUNT=1):
            for _ in range(2):
                self.client.get(url, {"q": "кобзар"}, REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.5")
            blocked = self.client.get(url, {"q": "кобзар"}, REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.5")
            other_user = self.client.get(url, {"q": "кобзар"}, REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="198.51.100.7")
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(other_user.status_code, 200)


class ClientIpTests(TestCase):
    def request(self, **meta):
        return RequestFactory().get("/", **meta)

    @override_settings(TRUSTED_PROXY_COUNT=0)
    def test_without_proxy_uses_remote_addr_and_ignores_header(self):
        request = self.request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4")
        self.assertEqual(client_ip(request), "10.0.0.1")

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_takes_last_trusted_hop_so_spoofed_prefix_is_ignored(self):
        request = self.request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.5")
        self.assertEqual(client_ip(request), "203.0.113.5")

    @override_settings(TRUSTED_PROXY_COUNT=2)
    def test_two_proxies(self):
        request = self.request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.5, 172.16.0.2")
        self.assertEqual(client_ip(request), "203.0.113.5")

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_falls_back_to_remote_addr_without_header(self):
        self.assertEqual(client_ip(self.request(REMOTE_ADDR="10.0.0.1")), "10.0.0.1")


class RebuildSearchKeysMigrationTests(TestCase):
    def test_rebuilds_stale_keys_with_unified_apostrophes(self):
        import importlib

        from django.apps import apps

        from core.models import Book

        book = make_book(title="П’ята пора", author="Автор")
        Book.objects.filter(pk=book.pk).update(search_key="п’ята пора автор")
        migration = importlib.import_module("core.migrations.0003_rebuild_search_keys")

        migration.rebuild_search_keys(apps, None)

        book.refresh_from_db()
        self.assertEqual(book.search_key, "п'ята пора автор")
