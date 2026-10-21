import importlib
import json

from django.apps import apps
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from core.models import UserProfile
from tests.conftest_helpers import make_user


class ManifestTests(TestCase):
    def test_manifest_is_valid_json_built_from_settings(self):
        response = self.client.get(reverse("manifest"))
        self.assertEqual(response["Content-Type"], "application/manifest+json")
        data = json.loads(response.content)
        self.assertEqual(data["name"], settings.SITE_NAME)
        self.assertEqual(data["theme_color"], settings.PWA_THEME_COLOR)
        self.assertEqual(data["background_color"], settings.PWA_BACKGROUND_COLOR)
        self.assertEqual(data["start_url"], reverse("core:home"))
        self.assertEqual(
            [icon["sizes"] for icon in data["icons"]],
            [f"{size}x{size}" for size in settings.PWA_ICON_SIZES],
        )


class ServiceWorkerTests(TestCase):
    def test_headers_and_injected_urls(self):
        response = self.client.get(reverse("service_worker"))
        body = response.content.decode()
        self.assertEqual(response["Content-Type"], "text/javascript")
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertEqual(response["Cache-Control"], "no-cache")
        self.assertIn(f"'{reverse('offline')}'", body)
        self.assertIn(f"'/{settings.STATIC_URL.lstrip('/')}'", body)
        self.assertIn(settings.PWA_CACHE_VERSION, body)
        self.assertNotIn("{%", body)

    def test_cache_prefix_follows_site_name(self):
        with self.settings(SITE_NAME="Читацька Музика"):
            body = self.client.get(reverse("service_worker")).content.decode()
        self.assertNotIn("songstery-", body)

    def test_page_exposes_registration_attributes_in_production(self):
        with self.settings(DEBUG=False):
            html = self.client.get(reverse("core:home")).content.decode()
        self.assertIn(f'data-service-worker-url="{reverse("service_worker")}"', html)
        self.assertIn('data-cache-prefix="songstery-"', html)

    def test_registration_url_is_empty_in_debug(self):
        with self.settings(DEBUG=True):
            html = self.client.get(reverse("core:home")).content.decode()
        self.assertIn('data-service-worker-url=""', html)


class VerificationFileTests(TestCase):
    def test_google_verification_file_route_is_configured(self):
        response = self.client.get(f"/{settings.GOOGLE_SITE_VERIFICATION_FILE}")
        self.assertIn(response.status_code, (301, 302))


class ProfileResilienceTests(TestCase):
    def test_profile_page_works_for_user_without_profile_row(self):
        user = make_user()
        user.profile.delete()
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("core:profile")).status_code, 200)

    def test_profile_is_created_on_login(self):
        user = make_user()
        user.profile.delete()
        self.client.login(username=user.username, password="pass-12345")
        user.refresh_from_db()
        self.assertTrue(hasattr(user, "profile"))

    def test_backfill_migration_creates_missing_profiles(self):
        user = make_user()
        user.profile.delete()
        migration = importlib.import_module("core.migrations.0006_backfill_user_profiles")
        migration.backfill(apps, None)
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
