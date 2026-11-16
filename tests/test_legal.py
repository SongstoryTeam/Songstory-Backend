from django.test import TestCase, override_settings
from django.urls import reverse

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=CACHES, SITE_CONTACT_EMAIL="hello@example.com")
class LegalPagesTests(TestCase):
    def test_pages_render_with_contact(self):
        for name in ("core:privacy", "core:terms", "core:about"):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "hello@example.com")

    def test_pages_without_contact_email_still_render(self):
        with override_settings(SITE_CONTACT_EMAIL=""):
            self.assertEqual(self.client.get(reverse("core:privacy")).status_code, 200)

    def test_footer_and_signup_link_to_legal_pages(self):
        self.assertContains(self.client.get(reverse("core:home")), reverse("core:privacy"))
        signup = self.client.get(reverse("signup"))
        self.assertContains(signup, reverse("core:terms"))
        self.assertContains(signup, reverse("core:privacy"))

    def test_sitemap_lists_legal_pages(self):
        body = self.client.get(reverse("sitemap")).content.decode()
        for name in ("core:privacy", "core:terms", "core:about"):
            self.assertIn(reverse(name), body)
