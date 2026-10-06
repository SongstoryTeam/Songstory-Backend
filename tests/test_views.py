import tempfile
from unittest import mock

from django.conf import settings as django_settings
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import AuthorVerification, Book, Comment, Playlist, Recommendation, Track
from core.services.google_books import ExternalBook, ExternalSearch
from core.services.music_links import TrackMetadata
from tests.conftest_helpers import make_book, make_chapter, make_track, make_user

YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=CACHES)
class PublicPageTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book(self.user)
        self.chapter = make_chapter(self.book)

    def test_public_pages_render(self):
        urls = [
            reverse("core:home"),
            reverse("core:book_list"),
            reverse("core:book_list") + "?sort=popular&genre=none",
            self.book.get_absolute_url(),
            self.chapter.get_absolute_url(),
            reverse("login"),
            reverse("signup"),
            reverse("robots_txt"),
            reverse("sitemap"),
            reverse("offline"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_unknown_pages_return_404(self):
        self.assertEqual(self.client.get("/book/no-such-book/").status_code, 404)
        self.assertEqual(self.client.get(f"/book/{self.book.slug}/chapter/99/").status_code, 404)

    def test_unapproved_book_hidden_from_strangers(self):
        hidden = make_book(self.user, title="Прихована", approved=False)
        self.assertEqual(self.client.get(hidden.get_absolute_url()).status_code, 404)
        self.client.force_login(make_user("stranger"))
        self.assertEqual(self.client.get(hidden.get_absolute_url()).status_code, 404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(hidden.get_absolute_url()).status_code, 200)

    def test_home_shelves_include_books_without_music(self):
        response = self.client.get(reverse("core:home"))
        titles = [book.title for shelf in response.context["shelves"] for book in shelf["books"]]
        self.assertIn(self.book.title, titles)

    def test_suggest_returns_local_matches_only(self):
        response = self.client.get(reverse("core:search_suggest"), {"q": "кобзар"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["title"], self.book.title)

    def test_protected_pages_redirect_anonymous(self):
        for url in (
            reverse("core:create_book"),
            reverse("core:profile"),
            reverse("core:recommend", args=[self.book.slug]),
            reverse("core:playlist_create", args=[self.book.slug]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)


@override_settings(CACHES=CACHES)
class SearchAndImportTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.external = ExternalBook("gb1", "Тіні забутих предків", "Михайло Коцюбинський", 1911, "", "Опис", "123")

    def test_search_page_lists_external_results(self):
        with mock.patch("core.views.catalog.search_google_books", return_value=ExternalSearch([self.external])):
            response = self.client.get(reverse("core:search"), {"q": "тіні забутих"})
        self.assertContains(response, "Тіні забутих предків")

    def test_search_hides_external_books_already_in_catalog(self):
        make_book(title="Тіні забутих предків", author="Михайло Коцюбинський")
        with mock.patch("core.views.catalog.search_google_books", return_value=ExternalSearch([self.external])):
            response = self.client.get(reverse("core:search"), {"q": "тіні"})
        self.assertEqual(response.context["external_books"], [])

    def test_search_reports_unavailable_service(self):
        with mock.patch("core.views.catalog.search_google_books", return_value=ExternalSearch([], unavailable=True)):
            response = self.client.get(reverse("core:search"), {"q": "тіні"})
        self.assertContains(response, "тимчасово недоступний")

    def test_import_creates_approved_book_once(self):
        self.client.force_login(self.user)
        with mock.patch("core.views.books.get_google_book", return_value=self.external):
            first = self.client.post(reverse("core:import_book"), {"external_id": "gb1"})
            second = self.client.post(reverse("core:import_book"), {"external_id": "gb1"})
        self.assertEqual(Book.objects.count(), 1)
        book = Book.objects.get()
        self.assertTrue(book.is_approved)
        self.assertEqual(book.author.name, "Михайло Коцюбинський")
        self.assertRedirects(first, book.get_absolute_url())
        self.assertRedirects(second, book.get_absolute_url())

    def test_import_requires_login_and_post(self):
        self.assertEqual(self.client.post(reverse("core:import_book"), {"external_id": "gb1"}).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("core:import_book")).status_code, 405)

    def test_manual_book_creation_and_duplicate_guard(self):
        self.client.force_login(self.user)
        payload = {"title": "Нова", "author_name": "Автор", "year": 2020}
        self.client.post(reverse("core:create_book"), payload)
        book = Book.objects.get()
        self.assertFalse(book.is_approved)
        response = self.client.post(reverse("core:create_book"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Book.objects.count(), 1)

    def test_chapters_added_with_next_numbers(self):
        book = make_book(self.user)
        make_chapter(book, 1)
        self.client.force_login(self.user)
        self.client.post(reverse("core:add_chapters", args=[book.slug]), {"count": 3})
        self.assertEqual(list(book.chapters.values_list("number", flat=True)), [1, 2, 3, 4])

    def test_only_manager_can_add_chapters(self):
        book = make_book(self.user)
        self.client.force_login(make_user("other"))
        self.assertEqual(self.client.get(reverse("core:add_chapters", args=[book.slug])).status_code, 404)


@override_settings(CACHES=CACHES)
class RecommendFlowTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book(self.user)
        self.chapter = make_chapter(self.book)
        self.url = reverse("core:recommend", args=[self.book.slug])
        self.client.force_login(self.user)

    def test_pasting_link_creates_track_and_recommendation(self):
        metadata = TrackMetadata(title="Пісня", artist="Гурт")
        with mock.patch("core.views.music.fetch_metadata", return_value=metadata):
            response = self.client.post(self.url, {"action": "link", "url": YOUTUBE_URL, "comment": "Підходить"})
        self.assertRedirects(response, self.book.get_absolute_url())
        track = Track.objects.get()
        self.assertEqual((track.title, track.external_id), ("Пісня", "dQw4w9WgXcQ"))
        self.assertEqual(Recommendation.objects.get().comment, "Підходить")

    def test_existing_track_is_reused_without_calling_oembed(self):
        make_track("dQw4w9WgXcQ")
        with mock.patch("core.views.music.fetch_metadata") as fetch:
            self.client.post(self.url, {"action": "link", "url": YOUTUBE_URL, "chapter": self.chapter.number})
        fetch.assert_not_called()
        self.assertEqual(Track.objects.count(), 1)
        self.assertEqual(Recommendation.objects.get().chapter, self.chapter)

    def test_manual_title_fallback_when_oembed_fails(self):
        with mock.patch("core.views.music.fetch_metadata", return_value=None):
            response = self.client.post(self.url, {"action": "link", "url": YOUTUBE_URL})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["draft_form"])
        self.client.post(
            self.url,
            {"action": "draft", "platform": "youtube", "external_id": "dQw4w9WgXcQ", "title": "Вручну", "artist": ""},
        )
        self.assertEqual(Track.objects.get().title, "Вручну")

    def test_rejects_unsupported_link(self):
        response = self.client.post(self.url, {"action": "link", "url": "https://example.com/song"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Track.objects.count(), 0)

    def test_pick_existing_track_and_search_existing(self):
        track = make_track(title="Місячна соната")
        found = self.client.get(self.url, {"q": "МІСЯЧНА"})
        self.assertEqual(list(found.context["found"]), [track])
        self.client.post(self.url, {"action": "pick", "track": track.pk})
        self.assertEqual(Recommendation.objects.count(), 1)

    def test_cannot_use_chapter_of_another_book(self):
        other = make_chapter(make_book(self.user, title="Інша", author="Інший"))
        response = self.client.post(self.url, {"action": "pick", "track": make_track().pk, "chapter": other.number + 40})
        self.assertEqual(response.status_code, 404)

    def test_delete_only_own_recommendation(self):
        recommendation = Recommendation.objects.create(user=self.user, track=make_track(), book=self.book)
        self.client.force_login(make_user("intruder"))
        self.client.post(reverse("core:recommendation_delete", args=[recommendation.pk]))
        self.assertTrue(Recommendation.objects.filter(pk=recommendation.pk).exists())
        self.client.force_login(self.user)
        self.client.post(reverse("core:recommendation_delete", args=[recommendation.pk]))
        self.assertFalse(Recommendation.objects.filter(pk=recommendation.pk).exists())

    def test_rate_limit_returns_429(self):
        with override_settings(RATE_LIMITS={**django_settings.RATE_LIMITS, "recommend": "1/h"}):
            self.client.post(self.url, {"action": "pick", "track": make_track().pk})
            response = self.client.post(self.url, {"action": "pick", "track": make_track("zzzzzzzzzzz").pk})
        self.assertEqual(response.status_code, 429)


@override_settings(CACHES=CACHES)
class PlaylistAndCommentTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book(self.user)
        self.track = make_track()
        Recommendation.objects.create(user=self.user, track=self.track, book=self.book)
        self.client.force_login(self.user)

    def test_playlist_is_built_from_book_tracks_only(self):
        foreign = make_track("foreignfore", title="Чужий")
        self.client.post(
            reverse("core:playlist_create", args=[self.book.slug]),
            {"title": "Мій", "tracks": [self.track.pk, foreign.pk]},
        )
        self.assertEqual(Playlist.objects.count(), 0)
        self.client.post(reverse("core:playlist_create", args=[self.book.slug]), {"title": "Мій", "tracks": [self.track.pk]})
        playlist = Playlist.objects.get()
        self.assertEqual(list(playlist.tracks.all()), [self.track])
        self.assertEqual(self.client.get(playlist.get_absolute_url()).status_code, 200)

    def test_only_owner_manages_playlist(self):
        playlist = Playlist.objects.create(book=self.book, user=self.user, title="P")
        self.client.force_login(make_user("other"))
        self.assertEqual(self.client.post(reverse("core:playlist_delete", args=[playlist.pk])).status_code, 404)
        self.assertTrue(Playlist.objects.exists())

    def test_add_and_remove_playlist_track(self):
        playlist = Playlist.objects.create(book=self.book, user=self.user, title="P")
        self.client.post(reverse("core:playlist_add_track", args=[playlist.pk]), {"track": self.track.pk})
        item = playlist.items.get()
        self.client.post(reverse("core:playlist_remove_item", args=[playlist.pk, item.pk]))
        self.assertEqual(playlist.items.count(), 0)

    def test_comment_and_single_level_reply(self):
        self.client.post(reverse("core:add_comment"), {"book": self.book.pk, "text": "Чудова книга"})
        parent = Comment.objects.get()
        self.client.post(reverse("core:add_comment"), {"book": self.book.pk, "text": "Згоден", "parent": parent.pk})
        reply = Comment.objects.exclude(pk=parent.pk).get()
        self.assertEqual(reply.parent, parent)
        response = self.client.post(
            reverse("core:add_comment"), {"book": self.book.pk, "text": "Глибше", "parent": reply.pk}
        )
        self.assertEqual(response.status_code, 404)

    def test_empty_comment_rejected_and_delete_permissions(self):
        self.client.post(reverse("core:add_comment"), {"book": self.book.pk, "text": "   "})
        self.assertEqual(Comment.objects.count(), 0)
        comment = Comment.objects.create(user=self.user, book=self.book, text="x")
        self.client.force_login(make_user("other"))
        self.client.post(reverse("core:delete_comment", args=[comment.pk]))
        self.assertTrue(Comment.objects.exists())


@override_settings(CACHES=CACHES)
class AccountTests(TestCase):
    def test_signup_creates_profile_and_logs_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "newreader",
                "email": "new@example.com",
                "phone": "+380501112233",
                "password1": "very-strong-pass-1",
                "password2": "very-strong-pass-1",
            },
        )
        self.assertRedirects(response, reverse("core:home"))
        user = self.client.get(reverse("core:profile")).context["user"]
        self.assertEqual(user.profile.phone, "+380501112233")

    def test_signup_check_endpoint(self):
        make_user("taken")
        self.assertFalse(self.client.get(reverse("signup_check"), {"field": "username", "value": "TAKEN"}).json()["available"])
        self.assertTrue(self.client.get(reverse("signup_check"), {"field": "username", "value": "free"}).json()["available"])
        self.assertIsNone(self.client.get(reverse("signup_check"), {"field": "bogus", "value": "x"}).json()["available"])

    def test_profile_update(self):
        user = make_user()
        self.client.force_login(user)
        self.client.post(reverse("core:profile"), {"first_name": "Іван", "last_name": "", "email": "i@example.com", "bio": "Читач"})
        user.refresh_from_db()
        self.assertEqual((user.first_name, user.profile.bio), ("Іван", "Читач"))


@override_settings(CACHES=CACHES, ADMIN_EMAIL="admin@example.com", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AuthorVerificationTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book()
        self.url = reverse("core:apply_author", args=[self.book.slug])
        self.client.force_login(self.user)

    def private_root(self) -> str:
        return self.enterContext(tempfile.TemporaryDirectory())

    def payload(self):
        return {
            "proof_document": SimpleUploadedFile("id.pdf", b"%PDF-1"),
            "proof_authorship": SimpleUploadedFile("book.pdf", b"%PDF-1"),
        }

    def test_application_notifies_admin_and_blocks_duplicates(self):
        with self.settings(PRIVATE_MEDIA_ROOT=self.private_root()):
            self.client.post(self.url, self.payload())
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(AuthorVerification.objects.count(), 1)
            response = self.client.get(self.url)
            self.assertRedirects(response, self.book.get_absolute_url())

    def test_rejects_disallowed_extension(self):
        files = {"proof_document": SimpleUploadedFile("id.exe", b"x"), "proof_authorship": SimpleUploadedFile("b.pdf", b"x")}
        response = self.client.post(self.url, files)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AuthorVerification.objects.count(), 0)

    def test_approval_marks_book_and_profile_and_emails_user(self):
        with self.settings(PRIVATE_MEDIA_ROOT=self.private_root()):
            self.client.post(self.url, self.payload())
            verification = AuthorVerification.objects.get()
            verification.approve(make_user("moderator", is_staff=True))
        self.book.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.book.verified_author, self.user)
        self.assertTrue(self.user.profile.is_verified_author)
        self.assertEqual(mail.outbox[-1].to, [self.user.email])

    def test_proof_download_is_staff_only(self):
        with self.settings(PRIVATE_MEDIA_ROOT=self.private_root()):
            self.client.post(self.url, self.payload())
            verification = AuthorVerification.objects.get()
            url = reverse("core:proof_download", args=[verification.pk, "proof_document"])
            self.assertEqual(self.client.get(url).status_code, 302)
            self.client.force_login(make_user("moderator", is_staff=True))
            self.assertEqual(self.client.get(url).status_code, 200)
