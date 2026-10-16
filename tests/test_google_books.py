import io
import logging
from unittest import mock

import requests
from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from core.services.google_books import _cache_key, parse_volume, search_google_books
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
        self.assertEqual(fetch.call_count, 4)  # два пошуки, у кожному два проходи: з мовою і без

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
        self.assertIsNone(cache.get(_cache_key("кобзар")))


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


@override_settings(CACHES=CACHES, GOOGLE_BOOKS_API_KEY=SECRET)
class RetryTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        patcher = mock.patch("core.services.google_books.time.sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_transient_503_is_retried_and_last_attempt_drops_language_params(self):
        outage = ExternalServiceError("HTTP 503", status=503)
        good = {"items": [volume("g1", "Тюремна цілителька", "Автор")]}
        # Четвертий виклик — другий прохід без мови: знайшлася лише одна книга, тож пошук розширюється.
        with mock.patch("core.services.google_books.get_json", side_effect=[outage, outage, good, {}]) as fetch:
            result = search_google_books("тюремна цілителька")
        self.assertFalse(result.unavailable)
        self.assertEqual([book.external_id for book in result.books], ["g1"])
        self.assertEqual(fetch.call_count, 4)
        self.assertIn("langRestrict", fetch.call_args_list[0].args[1])
        self.assertNotIn("langRestrict", fetch.call_args_list[2].args[1])
        self.assertIn("key", fetch.call_args_list[2].args[1])

    def test_persistent_503_gives_up_after_three_attempts(self):
        outage = ExternalServiceError("HTTP 503", status=503)
        with mock.patch("core.services.google_books.get_json", side_effect=outage) as fetch:
            result = search_google_books("кобзар")
        self.assertTrue(result.unavailable)
        self.assertEqual(fetch.call_count, 3)

    def test_client_errors_are_not_retried(self):
        for status in (400, 403, 429):
            with self.subTest(status=status):
                with mock.patch("core.services.google_books.get_json", side_effect=ExternalServiceError("x", status=status)) as fetch:
                    result = search_google_books(f"кобзар {status}")
                self.assertTrue(result.unavailable)
                self.assertEqual(fetch.call_count, 1)


def raw_volume(identifier, title, subtitle="", language="uk", authors=("Дженніфер Л. Арментраут",)):
    info = {"title": title, "authors": list(authors), "language": language}
    if subtitle:
        info["subtitle"] = subtitle
    return {"id": identifier, "volumeInfo": info}


class VolumeParsingTests(SimpleTestCase):
    def test_subtitle_becomes_part_of_title_for_series_editions(self):
        parsed = parse_volume(raw_volume("g1", "Кров і попіл", "Книга 1. Із крові й попелу"))
        self.assertEqual(parsed.title, "Кров і попіл. Книга 1. Із крові й попелу")

    def test_generic_or_repeated_subtitles_are_ignored(self):
        self.assertEqual(parse_volume(raw_volume("g1", "Тигролови", "Роман")).title, "Тигролови")
        self.assertEqual(parse_volume(raw_volume("g2", "Кобзар. Вибране", "Вибране")).title, "Кобзар. Вибране")

    def test_missing_language_is_accepted_for_ukrainian_looking_titles_only(self):
        self.assertIsNotNone(parse_volume(raw_volume("g1", "Із крові й попелу", language="")))
        self.assertIsNone(parse_volume(raw_volume("g2", "Мастер и Маргарита", language="")))
        self.assertIsNone(parse_volume(raw_volume("g3", "From Blood and Ash", language="")))

    def test_wrong_language_label_is_tolerated_only_with_ukrainian_letters(self):
        self.assertIsNotNone(parse_volume(raw_volume("g1", "Із крові й попелу", language="ru")))
        self.assertIsNone(parse_volume(raw_volume("g2", "Кобзар", language="ru")))
        self.assertIsNone(parse_volume(raw_volume("g3", "Six of Crows", language="en")))


@override_settings(CACHES=CACHES, GOOGLE_BOOKS_API_KEY=SECRET)
class SecondPassTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_sparse_results_trigger_search_without_language_restriction(self):
        strict = {"items": []}
        loose = {"items": [raw_volume("g1", "Кров і попіл", "Книга 1. Із крові й попелу", language="")]}
        with mock.patch("core.services.google_books.get_json", side_effect=[strict, loose]) as fetch:
            result = search_google_books("із крові й попелу")
        self.assertEqual([book.external_id for book in result.books], ["g1"])
        self.assertIn("langRestrict", fetch.call_args_list[0].args[1])
        self.assertNotIn("langRestrict", fetch.call_args_list[1].args[1])

    def test_enough_results_skip_second_pass(self):
        items = [raw_volume(f"g{n}", f"Книга {n}") for n in range(4)]
        with mock.patch("core.services.google_books.get_json", return_value={"items": items}) as fetch:
            search_google_books("книга")
        self.assertEqual(fetch.call_count, 1)

    def test_failed_second_pass_keeps_first_results(self):
        first = {"items": [raw_volume("g1", "Кобзар", authors=("Тарас Шевченко",))]}
        with mock.patch(
            "core.services.google_books.get_json",
            side_effect=[first, ExternalServiceError("x", status=403)],
        ):
            result = search_google_books("кобзар")
        self.assertFalse(result.unavailable)
        self.assertEqual(len(result.books), 1)
