from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.models import Accent, Comment, UserProfile
from tests.conftest_helpers import make_book, make_user

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
JSON_ACCEPT = {"HTTP_ACCEPT": "application/json"}


def set_accent(user, accent: str) -> None:
    UserProfile.objects.filter(user=user).update(accent=accent)


@override_settings(CACHES=CACHES)
class AccentUpdateTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.url = reverse("core:accent_update")
        self.client.force_login(self.user)

    def accent(self) -> str:
        return UserProfile.objects.get(user=self.user).accent

    def test_new_profile_starts_with_brand_accent(self):
        self.assertEqual(self.accent(), Accent.TERRACOTTA)

    def test_form_post_saves_and_redirects_back_to_settings(self):
        response = self.client.post(self.url, {"accent": Accent.OCEAN}, follow=True)
        self.assertRedirects(response, reverse("core:settings"))
        self.assertEqual(self.accent(), Accent.OCEAN)
        self.assertContains(response, "Колір оновлено.")

    def test_json_post_saves_and_returns_accent(self):
        response = self.client.post(self.url, {"accent": Accent.VIOLET}, **JSON_ACCEPT)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"accent": Accent.VIOLET})
        self.assertEqual(self.accent(), Accent.VIOLET)

    def test_unknown_accent_is_rejected_for_json_clients(self):
        response = self.client.post(self.url, {"accent": "neon"}, **JSON_ACCEPT)
        self.assertEqual(response.status_code, 400)
        self.assertIn("accent", response.json()["errors"])
        self.assertEqual(self.accent(), Accent.TERRACOTTA)

    def test_unknown_accent_is_rejected_for_form_clients(self):
        response = self.client.post(self.url, {"accent": "neon"}, follow=True)
        self.assertContains(response, "Оберіть колір зі списку.")
        self.assertEqual(self.accent(), Accent.TERRACOTTA)

    def test_missing_accent_is_rejected(self):
        response = self.client.post(self.url, {}, **JSON_ACCEPT)
        self.assertEqual(response.status_code, 400)

    def test_only_post_is_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.post(self.url, {"accent": Accent.ROSE})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_updates_are_rate_limited(self):
        with override_settings(RATE_LIMITS={"accent": "1/m"}):
            self.client.post(self.url, {"accent": Accent.ROSE})
            response = self.client.post(self.url, {"accent": Accent.TEAL})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(self.accent(), Accent.ROSE)


@override_settings(CACHES=CACHES)
class AccentRenderingTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_anonymous_pages_carry_no_accent(self):
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "data-accent")

    def test_root_element_reflects_saved_accent(self):
        set_accent(self.user, Accent.FOREST)
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, f'<html lang="uk" data-accent="{Accent.FOREST}"')

    def test_settings_offers_every_accent_and_marks_current(self):
        set_accent(self.user, Accent.INDIGO)
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:settings"))
        for accent in Accent:
            with self.subTest(accent=accent.value):
                self.assertContains(response, f'value="{accent.value}"')
        self.assertEqual(response.context["accent_form"]["accent"].value(), Accent.INDIGO)

    def test_settings_asks_anonymous_to_log_in_instead_of_showing_picker(self):
        response = self.client.get(reverse("core:settings"))
        self.assertNotContains(response, "data-accent-form")
        self.assertContains(response, "Власний колір")

    def test_profile_page_shows_bio_and_avatar_in_accent(self):
        UserProfile.objects.filter(user=self.user).update(accent=Accent.ROSE, bio="Люблю читати під дощ")
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:profile"))
        self.assertContains(response, "Люблю читати під дощ")
        self.assertContains(response, f'class="user-avatar user-avatar--lg" data-accent="{Accent.ROSE}"')


@override_settings(CACHES=CACHES)
class CommentAvatarTests(TestCase):
    def setUp(self):
        self.book = make_book()

    def add_comment(self, username: str, accent: str) -> None:
        author = make_user(username)
        set_accent(author, accent)
        Comment.objects.create(user=author, book=self.book, text=f"Від {username}")

    def test_comment_avatars_use_their_authors_accent(self):
        self.add_comment("anna", Accent.ROSE)
        self.add_comment("oleh", Accent.OCEAN)
        response = self.client.get(self.book.get_absolute_url())
        self.assertContains(response, f'user-avatar user-avatar--sm" data-accent="{Accent.ROSE}"')
        self.assertContains(response, f'user-avatar user-avatar--sm" data-accent="{Accent.OCEAN}"')

    def test_query_count_does_not_grow_with_comments(self):
        self.add_comment("anna", Accent.ROSE)
        with CaptureQueriesContext(connection) as single:
            self.client.get(self.book.get_absolute_url())
        for index in range(5):
            self.add_comment(f"reader{index}", Accent.TEAL)
        with CaptureQueriesContext(connection) as many:
            self.client.get(self.book.get_absolute_url())
        self.assertEqual(len(many), len(single))
