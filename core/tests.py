"""
Focused regression tests for the behaviours that were broken or fixed
during the senior-level review (July 2026):

- moderation visibility (unapproved books/chapters)
- Like.clean() validation
- AuthorVerification resubmission after rejection
- translated title/description actually rendering (core_extras filters)
- API: private playlists are not readable by anonymous/non-owner users
- API: unapproved chapter music is not leaked via AllowAny GET
- API: search / profile / author-verification / authors endpoints are wired (not 404)
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from core.models import (
    Author,
    AuthorTranslation,
    AuthorVerification,
    Book,
    BookTranslation,
    Chapter,
    ChapterTranslation,
    Genre,
    GenreTranslation,
    Language,
    Like,
    MusicRecommendation,
    Playlist,
)


def _make_book(creator, is_approved=True, title="Тестова книга"):
    uk, _ = Language.objects.get_or_create(code="uk", defaults={"name": "Українська"})
    genre, _ = Genre.objects.get_or_create(slug="fantasy")
    GenreTranslation.objects.get_or_create(genre=genre, language=uk, defaults={"name": "Фентезі"})
    book = Book.objects.create(
        slug=f"book-{Book.objects.count() + 1}",
        genre=genre,
        creator=creator,
        is_approved=is_approved,
        year=2024,
    )
    BookTranslation.objects.create(book=book, language=uk, title=title, description="Опис")
    return book


def _make_chapter(book, is_approved=True, number=1):
    uk = Language.objects.get(code="uk")
    chapter = Chapter.objects.create(book=book, number=number, is_approved=is_approved)
    ChapterTranslation.objects.create(chapter=chapter, language=uk, title=f"Розділ {number}", mood_tags="спокійно")
    return chapter


class ModerationVisibilityTests(TestCase):
    """Etap 0.1 -- books/chapters must be hidden until approved."""

    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pass12345")
        self.stranger = User.objects.create_user("stranger", password="pass12345")
        self.staff = User.objects.create_user("staffer", password="pass12345", is_staff=True)

    def test_unapproved_book_hidden_from_home(self):
        _make_book(self.owner, is_approved=False, title="Прихована книга")
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "Прихована книга")

    def test_unapproved_book_visible_to_creator(self):
        book = _make_book(self.owner, is_approved=False, title="Прихована книга")
        self.client.force_login(self.owner)
        response = self.client.get(f"/book/{book.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_unapproved_book_404_for_stranger(self):
        book = _make_book(self.owner, is_approved=False)
        self.client.force_login(self.stranger)
        response = self.client.get(f"/book/{book.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_unapproved_chapter_404_for_stranger_even_by_direct_url(self):
        book = _make_book(self.owner, is_approved=True)
        chapter = _make_chapter(book, is_approved=False)
        self.client.force_login(self.stranger)
        response = self.client.get(f"/book/{book.pk}/chapter/{chapter.number}/")
        self.assertEqual(response.status_code, 404)

    def test_unapproved_chapter_visible_to_staff(self):
        book = _make_book(self.owner, is_approved=True)
        chapter = _make_chapter(book, is_approved=False)
        self.client.force_login(self.staff)
        response = self.client.get(f"/book/{book.pk}/chapter/{chapter.number}/")
        self.assertEqual(response.status_code, 200)


class LikeValidationTests(TestCase):
    """Etap 0.1 -- a Like must point at exactly one target."""

    def setUp(self):
        self.user = User.objects.create_user("liker", password="pass12345")
        book = _make_book(self.user)
        chapter = _make_chapter(book)
        self.music = MusicRecommendation.objects.create(
            chapter=chapter, user=self.user, track_title="Song",
            artist="Artist", link_type="spotify", link_url="https://open.spotify.com/track/1",
        )
        self.playlist = Playlist.objects.create(
            book=book, creator=self.user, slug="mix", title="Mix", is_public=True,
        )

    def test_like_with_no_target_is_invalid(self):
        like = Like(user=self.user)
        with self.assertRaises(ValidationError):
            like.full_clean()

    def test_like_with_both_targets_is_invalid(self):
        like = Like(user=self.user, music_recommendation=self.music, playlist=self.playlist)
        with self.assertRaises(ValidationError):
            like.full_clean()

    def test_like_with_single_target_is_valid(self):
        like = Like(user=self.user, music_recommendation=self.music)
        like.full_clean()  # should not raise


class AuthorVerificationResubmissionTests(TestCase):
    """Etap 0.1 -- rejected applicants must be able to re-apply."""

    def setUp(self):
        self.user = User.objects.create_user("writer", password="pass12345")
        self.book = _make_book(self.user)

    def test_can_reapply_after_rejection(self):
        first = AuthorVerification.objects.create(user=self.user, book=self.book)
        first.status = AuthorVerification.STATUS_REJECTED
        first.save()

        second = AuthorVerification.objects.create(user=self.user, book=self.book)
        self.assertEqual(
            AuthorVerification.objects.filter(user=self.user).count(), 2
        )
        self.assertEqual(second.status, AuthorVerification.STATUS_PENDING)


class TranslatedTitleTemplateTests(TestCase):
    """
    Regression test for the critical bug found in this review: templates
    referencing book.title/chapter.title/book.description/chapter.mood_tags
    directly rendered empty, because those fields no longer exist on the
    model (they moved to BookTranslation/ChapterTranslation). This must be
    accessed through the core_extras filters instead.
    """

    def setUp(self):
        self.user = User.objects.create_user("author1", password="pass12345")
        self.book = _make_book(self.user, title="Райкер")
        self.chapter = _make_chapter(self.book, number=1)

    def test_raw_attribute_access_is_empty(self):
        # This documents *why* the bug happened: Book has no .title field.
        self.assertFalse(hasattr(self.book, "title"))
        self.assertFalse(hasattr(self.chapter, "title"))

    def test_localized_title_filter_renders_correctly(self):
        tpl = Template("{% load core_extras %}{{ book|localized_title }}")
        rendered = tpl.render(Context({"book": self.book}))
        self.assertEqual(rendered, "Райкер")

    def test_book_detail_page_shows_title(self):
        response = self.client.get(f"/book/{self.book.pk}/")
        self.assertContains(response, "Райкер")

    def test_home_page_shows_book_title_in_card(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Райкер")


class ApiAccessControlTests(TestCase):
    """
    Regression tests for the two access-control gaps found during this
    review: private playlists and unapproved-chapter music were readable
    by anyone through the API despite being hidden in the Django templates.
    """

    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pass12345")
        self.stranger = User.objects.create_user("stranger", password="pass12345")
        self.book = _make_book(self.owner)
        self.playlist = Playlist.objects.create(
            book=self.book, creator=self.owner, slug="private-mix",
            title="Private", is_public=False,
        )

    def _auth_header(self, username, password="pass12345"):
        token_response = self.client.post(
            "/api/auth/token/", {"username": username, "password": password},
            content_type="application/json",
        )
        access = token_response.json()["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {access}"}

    def test_private_playlist_hidden_from_anonymous(self):
        response = self.client.get(f"/api/playlists/{self.playlist.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_private_playlist_hidden_from_non_owner(self):
        response = self.client.get(
            f"/api/playlists/{self.playlist.slug}/", **self._auth_header("stranger")
        )
        self.assertEqual(response.status_code, 404)

    def test_private_playlist_visible_to_owner(self):
        response = self.client.get(
            f"/api/playlists/{self.playlist.slug}/", **self._auth_header("owner")
        )
        self.assertEqual(response.status_code, 200)

    def test_unapproved_chapter_music_hidden_from_anonymous(self):
        chapter = _make_chapter(self.book, is_approved=False)
        response = self.client.get(f"/api/chapters/{chapter.pk}/music/")
        self.assertEqual(response.status_code, 404)

    def test_unapproved_chapter_music_visible_to_owner(self):
        chapter = _make_chapter(self.book, is_approved=False)
        response = self.client.get(
            f"/api/chapters/{chapter.pk}/music/", **self._auth_header("owner")
        )
        self.assertEqual(response.status_code, 200)


class ApiRoutingTests(TestCase):
    """
    Regression tests for the endpoints that used to 404 because their
    views existed but were never wired into api/urls.py.
    """

    def setUp(self):
        self.user = User.objects.create_user("reader", password="pass12345")
        self.author = Author.objects.create(slug="test-author")
        uk, _ = Language.objects.get_or_create(code="uk", defaults={"name": "Українська"})
        AuthorTranslation.objects.create(author=self.author, language=uk, name="Тест Автор")

    def _auth_header(self):
        token_response = self.client.post(
            "/api/auth/token/",
            {"username": "reader", "password": "pass12345"},
            content_type="application/json",
        )
        access = token_response.json()["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {access}"}

    def test_search_music_route_exists(self):
        response = self.client.get("/api/search/music/?q=test")
        self.assertNotEqual(response.status_code, 404)

    def test_search_books_route_exists(self):
        response = self.client.get("/api/search/books/?q=test")
        self.assertNotEqual(response.status_code, 404)

    def test_author_verification_route_exists(self):
        response = self.client.post("/api/author-verification/", {}, **self._auth_header())
        self.assertNotEqual(response.status_code, 404)

    def test_author_detail_route_uses_canonical_author_model(self):
        response = self.client.get(f"/api/authors/{self.author.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Тест Автор")

    def test_profile_me_route_exists(self):
        response = self.client.get("/api/profile/me/", **self._auth_header())
        self.assertEqual(response.status_code, 200)

    def test_logout_blacklists_refresh_token(self):
        token_response = self.client.post(
            "/api/auth/token/",
            {"username": "reader", "password": "pass12345"},
            content_type="application/json",
        )
        tokens = token_response.json()
        auth_header = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access']}"}

        logout_response = self.client.post(
            "/api/auth/logout/", {"refresh": tokens["refresh"]},
            content_type="application/json", **auth_header,
        )
        self.assertEqual(logout_response.status_code, 205)

        retry = self.client.post(
            "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, content_type="application/json",
        )
        self.assertEqual(retry.status_code, 401)
