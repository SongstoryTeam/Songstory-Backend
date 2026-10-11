from django.test import TestCase, override_settings
from django.urls import reverse

from core.services.preferences import THEME_OPTIONS
from tests.conftest_helpers import make_user

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=CACHES)
class SettingsPageTests(TestCase):
    def test_page_is_public_and_lists_every_theme_option(self):
        response = self.client.get(reverse("core:settings"))
        self.assertEqual(response.status_code, 200)
        for option in THEME_OPTIONS:
            with self.subTest(option=option.value):
                self.assertContains(response, f'value="{option.value}"')
        self.assertContains(response, 'name="robots"')

    def test_anonymous_sees_login_links_authenticated_sees_logout(self):
        anonymous = self.client.get(reverse("core:settings"))
        self.assertContains(anonymous, reverse("login"))
        self.assertNotContains(anonymous, reverse("logout"))

        self.client.force_login(make_user())
        authenticated = self.client.get(reverse("core:settings"))
        self.assertContains(authenticated, reverse("core:profile"))
        self.assertContains(authenticated, reverse("logout"))

    def test_theme_toggle_is_removed_from_topbar_and_linked_in_sidebar(self):
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "data-theme-toggle")
        self.assertContains(response, reverse("core:settings"))
