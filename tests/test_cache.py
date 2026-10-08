import time

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

UNREACHABLE_REDIS = {
    "default": {
        "BACKEND": "core.cache.ResilientRedisCache",
        "LOCATION": "redis://127.0.0.1:1",
        "OPTIONS": {"socket_connect_timeout": 0.2, "socket_timeout": 0.2, "cooldown": 30},
    }
}


@override_settings(CACHES=UNREACHABLE_REDIS)
class ResilientRedisCacheTests(SimpleTestCase):
    def test_reads_behave_like_a_miss(self):
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", "fallback"), "fallback")
        self.assertEqual(cache.get_many(["a", "b"]), {})
        self.assertFalse(cache.has_key("missing"))

    def test_writes_do_not_raise(self):
        cache.set("key", "value", 10)
        cache.set_many({"a": 1}, 10)
        cache.delete("key")
        cache.delete_many(["a"])
        cache.clear()

    def test_add_reports_success_so_rate_limits_fail_open(self):
        self.assertTrue(cache.add("limit", 1, 60))
        self.assertEqual(cache.incr("limit"), 1)

    def test_backend_is_bypassed_during_cooldown(self):
        cache.get("first")
        started = time.monotonic()
        for _ in range(50):
            cache.get("again")
        self.assertLess(time.monotonic() - started, 0.1)


@override_settings(CACHES=UNREACHABLE_REDIS)
class RateLimitedViewsWithoutRedisTests(TestCase):
    def test_rate_limited_view_still_responds(self):
        response = self.client.get(reverse("core:search"))
        self.assertEqual(response.status_code, 200)

    def test_home_still_renders(self):
        self.assertEqual(self.client.get(reverse("core:home")).status_code, 200)
