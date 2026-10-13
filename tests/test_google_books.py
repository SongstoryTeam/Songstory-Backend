import io
import logging
from unittest import mock

import requests
from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from core.services.google_books import search_google_books
from core.services.http import ExternalServiceError, get_json, redact

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
SECRET = "AIzaSyFAKEKEY1234567890"


def fake_response(status=200, payload=None, text=""):
    response = mock.Mock(spec=requests.Response)
    response.ok = status < 400
    response.status_code = status
    response.text = text
    response.json.return_value = payload if payload is not None else {}
    return response


def volume(identifier, title, author="Автор"):
    return {"id": identifier, "volumeInfo": {"title": title, "authors": [author], "language": "uk"}}


class RedactTests(SimpleTestCase):
    def test_key_is_masked_in_urls(self):
        text = f"403 Client Error for url: https://x.test/volumes?q=a&key={SECRET}&maxResults=5"
        cleaned = redact(text)
        self.assertNotIn(SECRET, cleaned)
        self.assertIn("key=***&maxResults=5", cleaned)


class GetJsonTests(SimpleTestCase):
    def test_http_error_exposes_status_and_google_message(self):
        payload = {"error": {"message": "API key not valid. Please pass a valid API key."}}
        with mock.patch("core.services.http.requests.get", return_value=fake_response(400, payload)):
            with self.assertRaises(ExternalServiceError) as context:
                get_json("https://x.test", {"key": SECRET})
        self.assertEqual(context.exception.status, 400)
        self.assertIn("API key not valid", context.exception.detail)

    def test_network_error_never_leaks_key_to_logs_or_exception(self):
        error = requests.ConnectionError(f"Max retries exceeded with url: /v1?q=a&key={SECRET}")
        with mock.patch("core.services.http.requests.get", side_effect=error):
            with self.assertLogs("core.services.http", level=logging.WARNING) as logs:
                with self.assertRaises(ExternalServiceError) as context:
                    get_json("https://x.test", {"key": SECRET})
        self.assertNotIn(SECRET, "\n".join(logs.output))
        self.assertNotIn(SECRET, str(context.exception))
        self.assertIsNone(context.exception.__cause__)

    def test_invalid_json_is_reported(self):
        response = fake_response(200)
        response.json.side_effect = ValueError("bad")
        with mock.patch("core.services.http.requests.get", return_value=response):
            with self.assertRaises(ExternalServiceError):
                get_json("https://x.test")


@override_settings(CACHES=CACHES)
class SearchCacheTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_empty_results_are_not_cached(self):
        with mock.patch("core.services.google_books.get_json", return_value={"items": []}) as fetch:
            search_google_books("кобзар")
            search_google_books("кобзар")
        self.assertEqual(fetch.call_count, 2)

    def test_small_limit_does_not_truncate_cache_for_larger_limit(self):
        items = [volume(f"g{number}", f"Книга {number}") for number in range(8)]
        with mock.patch("core.services.google_books.get_json", return_value={"items": items}) as fetch:
            short = search_google_books("книга", limit=5)
            full = search_google_books("книга", limit=10)
        self.assertEqual((len(short.books), len(full.books)), (5, 8))
        self.assertEqual(fetch.call_count, 1)

    def test_failure_is_reported_and_not_cached(self):
        with mock.patch("core.services.google_books.get_json", side_effect=ExternalServiceError("x", status=403)):
            result = search_google_books("кобзар")
        self.assertTrue(result.unavailable)
        self.assertIsNone(cache.get("google_books:uk:кобзар"))


@override_settings(GOOGLE_BOOKS_API_KEY=SECRET)
class CheckCommandTests(SimpleTestCase):
    def run_command(self, side_effect):
        out = io.StringIO()
        with mock.patch("core.management.commands.check_google_books.get_json", side_effect=side_effect):
            call_command("check_google_books", "кобзар", stdout=out)
        return out.getvalue()

    def test_reports_masked_key_and_results(self):
        output = self.run_command([{"items": [volume("1", "Кобзар", "Шевченко")]}] * 2)
        self.assertNotIn(SECRET, output)
        self.assertIn("AIza", output)
        self.assertIn("[без ключа] OK", output)
        self.assertIn("[з ключем] OK: від Google 1, після фільтра мови 1", output)

    def test_reports_google_error_reason(self):
        error = ExternalServiceError("HTTP 403", status=403, detail="Books API has not been used in project 123")
        output = self.run_command([{"items": []}, error])
        self.assertIn("HTTP 403", output)
        self.assertIn("Books API has not been used", output)

    @override_settings(GOOGLE_BOOKS_API_KEY="")
    def test_warns_when_key_missing(self):
        output = self.run_command([{"items": []}])
        self.assertIn("НЕ ЗАДАНО", output)
        self.assertNotIn("[з ключем]", output)
