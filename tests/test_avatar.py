import socket
from io import StringIO
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import translation

from core import limits
from core.models import Comment, UserProfile
from core.services import remote_image
from core.services.avatars import AvatarRejected, Rejection, validate_avatar_url
from core.services.remote_image import Failure, FetchPolicy, RemoteImageError, fetch_image_type
from core.templatetags.core_extras import avatar_style
from tests.conftest_helpers import make_book, make_user

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PHOTO = "https://images.example.com/me.jpg"
PUBLIC_ADDRESS = "93.184.216.34"
PNG_BODY = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG_BODY = b"\xff\xd8\xff\xe0" + b"\x00" * 64
GIF_BODY = b"GIF89a" + b"\x00" * 64
WEBP_BODY = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64
HTML_BODY = b"<!doctype html><html></html>"
FETCH = "core.services.avatars.fetch_image_type"
POLICY = FetchPolicy(
    allowed_types=frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"}),
    max_bytes=1024,
    timeout=1,
    deadline=5,
    user_agent="tests",
)


def records(*addresses: str):
    return [(socket.AF_INET6 if ":" in item else socket.AF_INET, socket.SOCK_STREAM, 6, "", (item, 443)) for item in addresses]


class FakeResponse:
    def __init__(self, body: bytes = PNG_BODY, status: int = 200, headers: dict | None = None):
        self.body = body
        self.status_code = status
        self.headers = headers or {}
        self.closed = False

    def iter_content(self, size):
        for start in range(0, len(self.body), size):
            yield self.body[start : start + size]

    def close(self):
        self.closed = True


def profile_of(user) -> UserProfile:
    return UserProfile.objects.get(user=user)


def set_avatar(user, url: str = PHOTO, x: int = 50, y: int = 50, zoom: int = 100) -> None:
    UserProfile.objects.filter(user=user).update(avatar_url=url, avatar_x=x, avatar_y=y, avatar_zoom=zoom)


class SniffTests(SimpleTestCase):
    def test_recognises_supported_formats(self):
        expected = {
            PNG_BODY: "image/png",
            JPEG_BODY: "image/jpeg",
            GIF_BODY: "image/gif",
            WEBP_BODY: "image/webp",
        }
        for body, content_type in expected.items():
            with self.subTest(content_type=content_type):
                self.assertEqual(remote_image.sniff_content_type(body[: remote_image.SIGNATURE_BYTES]), content_type)

    def test_rejects_markup_and_svg(self):
        for body in (HTML_BODY, b"<svg xmlns='http://www.w3.org/2000/svg'/>", b"", b"RIFF\x00\x00\x00\x00WAVE"):
            with self.subTest(body=body[:12]):
                self.assertIsNone(remote_image.sniff_content_type(body))


class ResolveAddressTests(SimpleTestCase):
    def resolve(self, *addresses: str):
        with patch.object(remote_image.socket, "getaddrinfo", return_value=records(*addresses)):
            return remote_image.resolve_public_address("images.example.com", 443)

    def test_public_address_is_returned(self):
        self.assertEqual(str(self.resolve(PUBLIC_ADDRESS)), PUBLIC_ADDRESS)

    def test_ipv4_is_preferred_over_ipv6(self):
        self.assertEqual(str(self.resolve("2606:2800:220:1:248:1893:25c8:1946", PUBLIC_ADDRESS)), PUBLIC_ADDRESS)

    def test_non_public_addresses_are_forbidden(self):
        for address in ("127.0.0.1", "10.0.0.5", "192.168.1.10", "169.254.169.254", "::1", "fc00::1", "::ffff:127.0.0.1"):
            with self.subTest(address=address), self.assertRaises(RemoteImageError) as caught:
                self.resolve(address)
            self.assertEqual(caught.exception.failure, Failure.FORBIDDEN_ADDRESS)

    def test_a_single_private_record_poisons_the_host(self):
        with self.assertRaises(RemoteImageError) as caught:
            self.resolve(PUBLIC_ADDRESS, "10.0.0.5")
        self.assertEqual(caught.exception.failure, Failure.FORBIDDEN_ADDRESS)

    def test_unresolvable_host_is_unreachable(self):
        with patch.object(remote_image.socket, "getaddrinfo", side_effect=socket.gaierror), self.assertRaises(
            RemoteImageError
        ) as caught:
            remote_image.resolve_public_address("nope.example.com", 443)
        self.assertEqual(caught.exception.failure, Failure.UNREACHABLE)

    def test_ipv6_address_is_bracketed_in_pinned_url(self):
        parts = remote_image.urlsplit("https://images.example.com/a.png?v=1")
        address = remote_image.ipaddress.ip_address("2606:2800:220:1::1")
        self.assertEqual(remote_image.pinned_url(parts, address), "https://[2606:2800:220:1::1]/a.png?v=1")

    def test_custom_port_is_kept_in_pinned_url(self):
        parts = remote_image.urlsplit("https://images.example.com:8443/a.png")
        address = remote_image.ipaddress.ip_address(PUBLIC_ADDRESS)
        self.assertEqual(remote_image.pinned_url(parts, address), f"https://{PUBLIC_ADDRESS}:8443/a.png")


class FetchImageTypeTests(SimpleTestCase):
    def fetch(self, response=None, **kwargs):
        response = response or FakeResponse()
        with patch.object(remote_image.socket, "getaddrinfo", return_value=records(PUBLIC_ADDRESS)), patch.object(
            requests.Session, "get", return_value=response, **kwargs
        ) as get:
            return fetch_image_type(PHOTO, POLICY), get, response

    def failure_of(self, response=None, **kwargs) -> Failure:
        with self.assertRaises(RemoteImageError) as caught:
            self.fetch(response, **kwargs)
        return caught.exception.failure

    def test_returns_sniffed_type_and_releases_connection(self):
        content_type, _, response = self.fetch(FakeResponse(JPEG_BODY))
        self.assertEqual(content_type, "image/jpeg")
        self.assertTrue(response.closed)

    def test_connects_to_the_validated_address_without_following_redirects(self):
        _, get, _ = self.fetch()
        args, kwargs = get.call_args
        self.assertEqual(args[0], f"https://{PUBLIC_ADDRESS}/me.jpg")
        self.assertEqual(kwargs["headers"]["Host"], "images.example.com")
        self.assertFalse(kwargs["allow_redirects"])
        self.assertTrue(kwargs["stream"])

    def test_html_masquerading_as_image_is_rejected(self):
        self.assertEqual(self.failure_of(FakeResponse(HTML_BODY, headers={"Content-Type": "image/png"})), Failure.NOT_AN_IMAGE)

    def test_unsupported_but_valid_type_is_rejected(self):
        with patch.object(remote_image, "SIGNATURES", (remote_image.Signature("image/bmp", ((0, b"BM"),)),)):
            self.assertEqual(self.failure_of(FakeResponse(b"BM" + b"\x00" * 32)), Failure.NOT_AN_IMAGE)

    def test_redirects_and_errors_are_unreachable(self):
        for status in (301, 302, 403, 404, 500):
            with self.subTest(status=status):
                self.assertEqual(self.failure_of(FakeResponse(status=status)), Failure.UNREACHABLE)

    def test_declared_size_over_limit_is_rejected(self):
        response = FakeResponse(headers={"Content-Length": str(POLICY.max_bytes + 1)})
        self.assertEqual(self.failure_of(response), Failure.TOO_LARGE)

    def test_undeclared_size_over_limit_is_rejected_while_streaming(self):
        self.assertEqual(self.failure_of(FakeResponse(PNG_BODY + b"\x00" * POLICY.max_bytes)), Failure.TOO_LARGE)

    def test_declared_size_stops_reading_after_signature(self):
        response = FakeResponse(PNG_BODY, headers={"Content-Length": str(len(PNG_BODY))})
        chunks = []
        original = response.iter_content

        def spy(size):
            for chunk in original(size):
                chunks.append(chunk)
                yield chunk

        response.iter_content = spy
        self.fetch(response)
        self.assertEqual(len(chunks), 1)

    def test_network_errors_are_unreachable(self):
        for error in (requests.ConnectionError, requests.Timeout, requests.exceptions.SSLError):
            with self.subTest(error=error.__name__):
                with patch.object(remote_image.socket, "getaddrinfo", return_value=records(PUBLIC_ADDRESS)), patch.object(
                    requests.Session, "get", side_effect=error
                ), self.assertRaises(RemoteImageError) as caught:
                    fetch_image_type(PHOTO, POLICY)
                self.assertEqual(caught.exception.failure, Failure.UNREACHABLE)

    def test_slow_stream_hits_the_deadline(self):
        with patch.object(remote_image.time, "monotonic", side_effect=[0, POLICY.deadline + 1]):
            self.assertEqual(self.failure_of(FakeResponse(PNG_BODY * 4)), Failure.UNREACHABLE)

    def test_private_target_is_never_requested(self):
        with patch.object(remote_image.socket, "getaddrinfo", return_value=records("127.0.0.1")), patch.object(
            requests.Session, "get"
        ) as get, self.assertRaises(RemoteImageError):
            fetch_image_type(PHOTO, POLICY)
        get.assert_not_called()


class ValidateAvatarUrlTests(SimpleTestCase):
    def rejection_of(self, url: str) -> Rejection:
        with patch(FETCH, return_value="image/png") as fetch, self.assertRaises(AvatarRejected) as caught:
            validate_avatar_url(url)
        fetch.assert_not_called()
        return caught.exception.rejection

    def test_valid_url_passes_and_is_returned_cleaned(self):
        with patch(FETCH, return_value="image/png") as fetch:
            self.assertEqual(validate_avatar_url(f"  {PHOTO}  "), PHOTO)
        self.assertEqual(fetch.call_args.args[0], PHOTO)

    def test_insecure_scheme_is_upgraded_before_checking(self):
        with patch(FETCH, return_value="image/png") as fetch:
            self.assertEqual(validate_avatar_url("http://images.example.com/me.jpg"), PHOTO)
        self.assertEqual(fetch.call_args.args[0], PHOTO)

    def test_malformed_and_dangerous_schemes_are_rejected_without_network(self):
        for url in ("", "not a url", "javascript:alert(1)", "data:image/png;base64,AAAA", "ftp://example.com/a.png"):
            with self.subTest(url=url):
                self.assertEqual(self.rejection_of(url), Rejection.INVALID_URL)

    def test_credentials_ports_and_odd_hosts_are_rejected_without_network(self):
        for url in (
            "https://user:pass@images.example.com/me.jpg",
            "https://images.example.com:8443/me.jpg",
            "https://intranet/me.jpg",
            "https://bücher.example.com/me.jpg",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.rejection_of(url), Rejection.INVALID_URL)

    def test_ip_literals_are_forbidden_without_network(self):
        for url in ("https://93.184.216.34/me.jpg", "https://127.0.0.1/me.jpg", "https://[2606:2800:220:1::1]/me.jpg"):
            with self.subTest(url=url):
                self.assertIn(self.rejection_of(url), {Rejection.FORBIDDEN_HOST, Rejection.INVALID_URL})

    def test_blocked_hosts_and_their_subdomains_are_forbidden(self):
        with override_settings(AVATAR_BLOCKED_HOSTS=frozenset({"bad.example"})):
            for url in ("https://bad.example/a.jpg", "https://cdn.bad.example/a.jpg"):
                with self.subTest(url=url):
                    self.assertEqual(self.rejection_of(url), Rejection.FORBIDDEN_HOST)
            with patch(FETCH, return_value="image/png"):
                self.assertEqual(validate_avatar_url("https://notbad.example/a.jpg"), "https://notbad.example/a.jpg")

    def test_default_blocklist_is_configured(self):
        self.assertIn("pornhub.com", __import__("django.conf").conf.settings.AVATAR_BLOCKED_HOSTS)

    def test_network_failures_become_user_facing_rejections(self):
        expected = {
            Failure.UNREACHABLE: Rejection.UNREACHABLE,
            Failure.FORBIDDEN_ADDRESS: Rejection.FORBIDDEN_HOST,
            Failure.NOT_AN_IMAGE: Rejection.NOT_AN_IMAGE,
            Failure.TOO_LARGE: Rejection.TOO_LARGE,
        }
        for failure, rejection in expected.items():
            with self.subTest(failure=failure.value), patch(FETCH, side_effect=RemoteImageError(failure)):
                with self.assertRaises(AvatarRejected) as caught:
                    validate_avatar_url(PHOTO)
                self.assertEqual(caught.exception.rejection, rejection)

    def test_only_network_trouble_is_transient(self):
        self.assertTrue(AvatarRejected(Rejection.UNREACHABLE).is_transient)
        for rejection in Rejection:
            if rejection is not Rejection.UNREACHABLE:
                with self.subTest(rejection=rejection.name):
                    self.assertFalse(AvatarRejected(rejection).is_transient)

    @override_settings(AVATAR_MAX_BYTES=3 * 1024 * 1024, AVATAR_CONTENT_TYPES=frozenset({"image/png", "image/webp"}))
    def test_messages_reflect_configuration(self):
        self.assertIn("3 МБ", str(AvatarRejected(Rejection.TOO_LARGE)))
        self.assertIn("PNG, WEBP", str(AvatarRejected(Rejection.NOT_AN_IMAGE)))


class ProfileAvatarModelTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_new_profile_has_no_avatar_and_centered_frame(self):
        profile = profile_of(self.user)
        self.assertFalse(profile.has_avatar)
        self.assertEqual(
            (profile.avatar_x, profile.avatar_y, profile.avatar_zoom),
            (limits.AVATAR_POSITION_DEFAULT, limits.AVATAR_POSITION_DEFAULT, limits.AVATAR_ZOOM_DEFAULT),
        )

    def test_reset_restores_defaults_and_persists(self):
        set_avatar(self.user, x=10, y=90, zoom=250)
        profile = profile_of(self.user)
        profile.reset_avatar()
        stored = profile_of(self.user)
        self.assertEqual((stored.avatar_url, stored.avatar_x, stored.avatar_y, stored.avatar_zoom), ("", 50, 50, 100))

    def test_style_uses_dot_decimal_separator_in_any_locale(self):
        set_avatar(self.user, x=20, y=80, zoom=150)
        with translation.override("uk"):
            style = avatar_style(profile_of(self.user))
        self.assertEqual(style, "--avatar-x: 20%; --avatar-y: 80%; --avatar-zoom: 1.5")


@override_settings(CACHES=CACHES)
class UpdateAvatarTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.url = reverse("core:avatar_update")
        self.client.force_login(self.user)

    def post(self, url: str = PHOTO, **crop):
        data = {"avatar_url": url, "avatar_x": 50, "avatar_y": 50, "avatar_zoom": 100, **crop}
        with patch(FETCH, return_value="image/png") as fetch:
            response = self.client.post(self.url, data)
        return response, fetch

    def test_saves_url_and_crop_then_returns_to_the_avatar_section(self):
        response, fetch = self.post(avatar_x=12, avatar_y=88, avatar_zoom=175)
        self.assertRedirects(response, f"{reverse('core:settings')}#avatar", fetch_redirect_response=False)
        fetch.assert_called_once()
        profile = profile_of(self.user)
        self.assertEqual((profile.avatar_url, profile.avatar_x, profile.avatar_y, profile.avatar_zoom), (PHOTO, 12, 88, 175))

    def test_success_message_is_shown(self):
        response, _ = self.post()
        self.assertContains(self.client.get(response["Location"].split("#")[0]), "Фото профілю оновлено.")

    def test_insecure_url_is_stored_as_https(self):
        self.post("http://images.example.com/me.jpg")
        self.assertEqual(profile_of(self.user).avatar_url, PHOTO)

    def test_crop_values_outside_bounds_are_rejected(self):
        cases = {
            "avatar_zoom": (limits.AVATAR_ZOOM_MIN - 1, limits.AVATAR_ZOOM_MAX + 1),
            "avatar_x": (limits.AVATAR_POSITION_MIN - 1, limits.AVATAR_POSITION_MAX + 1),
            "avatar_y": (limits.AVATAR_POSITION_MIN - 1, limits.AVATAR_POSITION_MAX + 1),
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    response, _ = self.post(**{field: value})
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(field, response.context["avatar_form"].errors)
                    self.assertFalse(profile_of(self.user).has_avatar)

    def test_non_numeric_crop_is_rejected(self):
        response, _ = self.post(avatar_zoom="big")
        self.assertIn("avatar_zoom", response.context["avatar_form"].errors)

    def test_empty_url_clears_avatar_and_resets_crop(self):
        set_avatar(self.user, x=5, y=95, zoom=280)
        response, fetch = self.post("", avatar_x=5, avatar_y=95, avatar_zoom=280)
        self.assertEqual(response.status_code, 302)
        fetch.assert_not_called()
        profile = profile_of(self.user)
        self.assertEqual((profile.avatar_url, profile.avatar_x, profile.avatar_y, profile.avatar_zoom), ("", 50, 50, 100))

    def test_rejected_url_keeps_previous_avatar_and_explains_why(self):
        set_avatar(self.user, url="https://old.example.com/a.png")
        with patch(FETCH, side_effect=RemoteImageError(Failure.NOT_AN_IMAGE)):
            response = self.client.post(
                self.url, {"avatar_url": PHOTO, "avatar_x": 50, "avatar_y": 50, "avatar_zoom": 100}
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Посилання має вести на фото у форматі")
        self.assertContains(response, f'value="{PHOTO}"')
        self.assertEqual(profile_of(self.user).avatar_url, "https://old.example.com/a.png")

    def test_dangerous_schemes_never_reach_the_network(self):
        response, fetch = self.post("javascript:alert(1)")
        self.assertEqual(response.status_code, 200)
        fetch.assert_not_called()
        self.assertFalse(profile_of(self.user).has_avatar)

    def test_blocked_host_is_refused(self):
        with override_settings(AVATAR_BLOCKED_HOSTS=frozenset({"images.example.com"})):
            response, fetch = self.post()
        self.assertContains(response, "Це джерело не підтримується")
        fetch.assert_not_called()

    def test_failed_submission_does_not_change_the_page_avatar(self):
        response, _ = self.post("javascript:alert(1)", avatar_zoom=250)
        self.assertNotContains(response, "--avatar-zoom: 2.5")

    def test_only_post_is_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.client.post(self.url, {"avatar_url": PHOTO})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_updates_are_rate_limited(self):
        with override_settings(RATE_LIMITS={"avatar": "1/m"}):
            self.post()
            response, _ = self.post("https://images.example.com/other.jpg")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(profile_of(self.user).avatar_url, PHOTO)


@override_settings(CACHES=CACHES)
class RemoveAvatarTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.url = reverse("core:avatar_remove")
        self.client.force_login(self.user)
        set_avatar(self.user, x=10, y=20, zoom=200)

    def test_removes_photo_and_resets_frame(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, f"{reverse('core:settings')}#avatar", fetch_redirect_response=False)
        profile = profile_of(self.user)
        self.assertEqual((profile.avatar_url, profile.avatar_x, profile.avatar_y, profile.avatar_zoom), ("", 50, 50, 100))

    def test_only_post_is_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertTrue(profile_of(self.user).has_avatar)

    def test_anonymous_user_cannot_remove(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertTrue(profile_of(self.user).has_avatar)


@override_settings(CACHES=CACHES)
class AvatarEditorPageTests(TestCase):
    def test_authenticated_user_gets_editor_with_bounds_for_the_script(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.get(reverse("core:settings"))
        self.assertContains(response, "data-avatar-editor")
        self.assertContains(response, f'min="{limits.AVATAR_ZOOM_MIN}"')
        self.assertContains(response, f'max="{limits.AVATAR_ZOOM_MAX}"')
        self.assertContains(response, f'step="{limits.AVATAR_ZOOM_STEP}"')
        self.assertContains(response, f'data-default="{limits.AVATAR_POSITION_DEFAULT}"')
        self.assertContains(response, "core/js/modules/avatar-editor.js")
        self.assertNotContains(response, reverse("core:avatar_remove"))

    def test_remove_button_appears_only_with_a_photo(self):
        user = make_user()
        self.client.force_login(user)
        set_avatar(user)
        self.assertContains(self.client.get(reverse("core:settings")), reverse("core:avatar_remove"))

    def test_anonymous_user_gets_no_editor_and_no_scripts(self):
        response = self.client.get(reverse("core:settings"))
        self.assertNotContains(response, "data-avatar-editor")
        self.assertNotContains(response, "avatar-editor.js")

    def test_profile_page_links_to_the_editor(self):
        self.client.force_login(make_user())
        self.assertContains(self.client.get(reverse("core:profile")), f"{reverse('core:settings')}#avatar")


@override_settings(CACHES=CACHES)
class AvatarRenderingTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_photo_is_rendered_with_frame_privacy_and_letter_fallback(self):
        set_avatar(self.user, x=30, y=70, zoom=200)
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:profile"))
        self.assertContains(response, f'<img class="user-avatar__image" src="{PHOTO}"')
        self.assertContains(response, 'referrerpolicy="no-referrer"')
        self.assertContains(response, "--avatar-x: 30%; --avatar-y: 70%; --avatar-zoom: 2")
        self.assertContains(response, '<span class="user-avatar__letter">R</span>')

    def test_users_without_photo_render_only_the_letter(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:profile"))
        self.assertNotContains(response, "user-avatar__image")
        self.assertContains(response, '<span class="user-avatar__letter">R</span>')

    def test_photo_is_shown_in_comments_without_extra_queries(self):
        book = make_book()
        author = make_user("anna")
        set_avatar(author)
        Comment.objects.create(user=author, book=book, text="Чудова книга")
        with CaptureQueriesContext(connection) as single:
            response = self.client.get(book.get_absolute_url())
        self.assertContains(response, f'src="{PHOTO}"')
        for index in range(5):
            reader = make_user(f"reader{index}")
            set_avatar(reader, url=f"https://images.example.com/{index}.jpg")
            Comment.objects.create(user=reader, book=book, text=f"Відгук {index}")
        with CaptureQueriesContext(connection) as many:
            self.client.get(book.get_absolute_url())
        self.assertEqual(len(many), len(single))

    def test_sidebar_shows_the_photo_on_every_page(self):
        set_avatar(self.user)
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, f'<span class="sidebar__user-name">{self.user.username}</span>')
        self.assertContains(response, 'class="user-avatar__image"')


@override_settings(CACHES=CACHES)
class RecheckAvatarsCommandTests(TestCase):
    def setUp(self):
        self.good = make_user("good")
        self.bad = make_user("bad")
        self.flaky = make_user("flaky")
        set_avatar(self.good, "https://ok.example.com/a.png")
        set_avatar(self.bad, "https://bad.example.com/a.png", x=1, y=2, zoom=300)
        set_avatar(self.flaky, "https://flaky.example.com/a.png")

    def run_command(self, *args) -> str:
        outcomes = {
            "https://ok.example.com/a.png": "image/png",
            "https://bad.example.com/a.png": RemoteImageError(Failure.NOT_AN_IMAGE),
            "https://flaky.example.com/a.png": RemoteImageError(Failure.UNREACHABLE),
        }

        def fake(url, policy):
            outcome = outcomes[url]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        output = StringIO()
        with patch(FETCH, side_effect=fake):
            call_command("recheck_avatars", *args, stdout=output)
        return output.getvalue()

    def test_removes_only_permanently_invalid_photos(self):
        output = self.run_command()
        self.assertTrue(profile_of(self.good).has_avatar)
        self.assertTrue(profile_of(self.flaky).has_avatar)
        bad = profile_of(self.bad)
        self.assertEqual((bad.avatar_url, bad.avatar_x, bad.avatar_y, bad.avatar_zoom), ("", 50, 50, 100))
        self.assertIn("Фото прибрано: 1, пропущено через збій мережі: 1", output)

    def test_dry_run_changes_nothing(self):
        output = self.run_command("--dry-run")
        self.assertTrue(profile_of(self.bad).has_avatar)
        self.assertIn("[пробний запуск", output)
        self.assertIn("Фото прибрано: 1", output)


class AvatarAdminTests(TestCase):
    def setUp(self):
        self.admin = make_user("boss", is_staff=True, is_superuser=True)
        self.client.force_login(self.admin)
        self.target = make_user("target")
        set_avatar(self.target)

    def test_change_page_previews_the_photo(self):
        profile = profile_of(self.target)
        response = self.client.get(reverse("admin:core_userprofile_change", args=[profile.pk]))
        self.assertContains(response, f'src="{PHOTO}"')
        self.assertContains(response, 'referrerpolicy="no-referrer"')

    def test_changelist_can_be_searched_by_photo_host(self):
        response = self.client.get(reverse("admin:core_userprofile_changelist"), {"q": "images.example.com"})
        self.assertContains(response, "target")

    def test_bulk_action_removes_photos(self):
        response = self.client.post(
            reverse("admin:core_userprofile_changelist"),
            {"action": "reset_avatars", "_selected_action": [profile_of(self.target).pk]},
            follow=True,
        )
        self.assertContains(response, "Фото прибрано: 1.")
        self.assertFalse(profile_of(self.target).has_avatar)
