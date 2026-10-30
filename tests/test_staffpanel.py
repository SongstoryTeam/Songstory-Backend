from django.contrib.admin.models import CHANGE, DELETION, LogEntry
from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.models import AuthorVerification, Book, Comment, Recommendation
from staffpanel.access import Permission
from staffpanel.services import overview
from tests.conftest_helpers import make_book, make_chapter, make_staff, make_track, make_user

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
ALL_PERMISSIONS = [str(permission) for permission in Permission]
LIST_URL_NAMES = ["dashboard", "books", "verifications", "users", "comments", "activity"]
NEXT_EVIL = "https://evil.example/steal"


def admin_user(username: str = "root") -> User:
    return make_staff(username, superuser=True)


@override_settings(CACHES=CACHES, PASSWORD_HASHERS=FAST_HASHERS)
class PanelTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = make_user("owner")
        self.book = make_book(self.owner, approved=False)
        self.admin = admin_user()
        self.client.force_login(self.admin)

    def post(self, name, *args, **data):
        return self.client.post(reverse(f"staff:{name}", args=args), data)

    def last_log(self) -> LogEntry:
        return LogEntry.objects.order_by("-pk").first()


class AccessTests(PanelTestCase):
    def urls(self):
        return [reverse(f"staff:{name}") for name in LIST_URL_NAMES]

    def test_anonymous_is_redirected_to_login(self):
        self.client.logout()
        for url in self.urls():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn(reverse("login"), response["Location"])

    def test_regular_user_gets_404_everywhere(self):
        self.client.force_login(self.owner)
        for url in self.urls():
            self.assertEqual(self.client.get(url).status_code, 404, url)
        self.assertEqual(self.post("book_bulk", ids=[self.book.pk], action="approve").status_code, 404)

    def test_staff_without_permissions_gets_404(self):
        self.client.force_login(make_user("bare", is_staff=True))
        for url in self.urls():
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_inactive_staff_is_rejected(self):
        staff = make_staff("sleeper", *ALL_PERMISSIONS)
        User.objects.filter(pk=staff.pk).update(is_active=False)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("staff:books")).status_code, 302)

    def test_superuser_sees_every_section(self):
        for url in self.urls():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertContains(response, "noindex")

    def test_permissions_are_granular(self):
        self.client.force_login(make_staff("viewer", Permission.BOOKS_VIEW))
        self.assertEqual(self.client.get(reverse("staff:books")).status_code, 200)
        self.assertEqual(self.client.get(reverse("staff:users")).status_code, 404)
        response = self.post("book_action", self.book.pk, "approve")
        self.assertEqual(response.status_code, 404)
        self.book.refresh_from_db()
        self.assertFalse(self.book.is_approved)

    def test_mutations_reject_get(self):
        response = self.client.get(reverse("staff:book_action", args=[self.book.pk, "approve"]))
        self.assertEqual(response.status_code, 405)

    def test_csrf_is_enforced(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.admin)
        response = strict.post(reverse("staff:book_action", args=[self.book.pk, "approve"]))
        self.assertEqual(response.status_code, 403)
        self.book.refresh_from_db()
        self.assertFalse(self.book.is_approved)

    def test_unknown_action_is_404(self):
        self.assertEqual(self.post("book_action", self.book.pk, "explode").status_code, 404)

    @override_settings(RATE_LIMITS={"staff_action": "2/m"})
    def test_actions_are_rate_limited(self):
        statuses = [self.post("book_action", self.book.pk, "hide").status_code for _ in range(4)]
        self.assertIn(429, statuses)

    def test_unsafe_next_is_ignored(self):
        response = self.post("book_action", self.book.pk, "approve", next=NEXT_EVIL)
        self.assertRedirects(response, reverse("staff:books"))
        response = self.post("book_action", self.book.pk, "hide", next="/catalog/?q=a")
        self.assertEqual(response["Location"], "/catalog/?q=a")


class FootprintTests(PanelTestCase):
    def test_regular_user_pages_have_no_staff_chrome(self):
        self.client.force_login(self.owner)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("core:home"))
        self.assertNotIn("staff_nav", response.context)
        self.assertNotContains(response, "panel.css")
        self.assertNotContains(response, "Керування")
        self.assertFalse([q for q in queries if "logentry" in q["sql"] or "authorverification" in q["sql"]])

    def test_anonymous_pages_have_no_staff_chrome(self):
        self.client.logout()
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "panel.css")
        self.assertNotContains(response, "topbar__staff")

    def test_staff_sees_navigation_with_badges(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "panel.css")
        self.assertContains(response, reverse("staff:books"))
        self.assertContains(response, "topbar__staff")
        self.assertContains(response, 'class="sidebar__badge">1<')

    def test_navigation_respects_permissions(self):
        self.client.force_login(make_staff("viewer", Permission.COMMENTS_VIEW))
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, reverse("staff:comments"))
        self.assertNotContains(response, reverse("staff:books"))
        self.assertNotContains(response, reverse("staff:users"))

    def test_badges_are_cached(self):
        self.client.get(reverse("core:home"))
        with CaptureQueriesContext(connection) as queries:
            self.client.get(reverse("core:home"))
        self.assertFalse([q for q in queries if q["sql"].startswith("SELECT COUNT(*)")])

    def test_cache_is_invalidated_after_action(self):
        self.assertEqual(overview.pending_counts()["books"], 1)
        with self.captureOnCommitCallbacks(execute=True):
            self.post("book_action", self.book.pk, "approve")
        self.assertEqual(overview.pending_counts()["books"], 0)

    def test_book_page_toolbar_only_for_staff(self):
        url = self.book.get_absolute_url()
        response = self.client.get(url)
        self.assertContains(response, "staff-toolbar")
        self.assertContains(response, reverse("staff:book_action", args=[self.book.pk, "approve"]))
        self.assertContains(response, reverse("core:suggest_edit", args=[self.book.slug]))
        self.client.force_login(self.owner)
        self.assertNotContains(self.client.get(url), "staff-toolbar")
        self.client.logout()
        self.assertNotContains(self.client.get(make_book(title="Інша").get_absolute_url()), "staff-toolbar")

    def test_robots_hides_panel(self):
        self.client.logout()
        self.assertContains(self.client.get("/robots.txt"), f"Disallow: {reverse('staff:dashboard')}")


class BookModerationTests(PanelTestCase):
    def test_approve_and_hide_are_logged(self):
        self.post("book_action", self.book.pk, "approve")
        self.book.refresh_from_db()
        self.assertTrue(self.book.is_approved)
        self.assertEqual(self.last_log().action_flag, CHANGE)
        self.assertEqual(self.last_log().user, self.admin)
        self.post("book_action", self.book.pk, "hide")
        self.book.refresh_from_db()
        self.assertFalse(self.book.is_approved)

    def test_repeated_action_changes_nothing(self):
        self.post("book_action", self.book.pk, "hide")
        self.assertEqual(LogEntry.objects.count(), 0)

    def test_bulk_approve(self):
        second = make_book(self.owner, title="Друга", approved=False)
        response = self.post("book_bulk", ids=[self.book.pk, second.pk, "junk"], action="approve")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Book.objects.filter(is_approved=True).count(), 2)
        self.assertEqual(LogEntry.objects.count(), 2)

    def test_bulk_limit(self):
        with self.settings(STAFF_BULK_MAX=1):
            second = make_book(self.owner, title="Друга", approved=False)
            self.post("book_bulk", ids=[self.book.pk, second.pk], action="approve")
        self.assertEqual(Book.objects.filter(is_approved=True).count(), 1)

    def test_delete_requires_its_own_permission(self):
        mod = make_staff("mod", Permission.BOOKS_VIEW, Permission.BOOKS_CHANGE)
        self.client.force_login(mod)
        self.assertEqual(self.post("book_action", self.book.pk, "delete").status_code, 404)
        self.assertTrue(Book.objects.filter(pk=self.book.pk).exists())
        self.client.force_login(self.admin)
        self.post("book_action", self.book.pk, "delete")
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())
        self.assertEqual(self.last_log().action_flag, DELETION)

    def test_list_filters_and_search(self):
        make_book(self.owner, title="Опублікована", approved=True)
        pending = self.client.get(reverse("staff:books"))
        self.assertContains(pending, self.book.title)
        self.assertNotContains(pending, "Опублікована")
        everything = self.client.get(reverse("staff:books"), {"state": "all"})
        self.assertContains(everything, "Опублікована")
        found = self.client.get(reverse("staff:books"), {"state": "all", "q": "Опублік"})
        self.assertContains(found, "Опублікована")
        self.assertNotContains(found, self.book.title)

    def test_list_links_to_shared_edit_flow(self):
        response = self.client.get(reverse("staff:books"))
        self.assertContains(response, reverse("core:suggest_edit", args=[self.book.slug]))

    def test_invalid_filters_fall_back_to_default(self):
        self.assertEqual(self.client.get(reverse("staff:books"), {"state": "nope", "page": "zzz"}).status_code, 200)



class VerificationTests(PanelTestCase):
    def setUp(self):
        super().setUp()
        self.book.is_approved = True
        self.book.save()
        self.applicant = make_user("writer")
        self.verification = AuthorVerification.objects.create(
            user=self.applicant,
            book=self.book,
            proof_document=SimpleUploadedFile("passport.pdf", b"%PDF-1.4 doc", content_type="application/pdf"),
            proof_authorship=SimpleUploadedFile("contract.pdf", b"%PDF-1.4 contract", content_type="application/pdf"),
        )

    def review(self, decision, note=""):
        return self.post("verification_detail", self.verification.pk, decision=decision, note=note)

    def test_detail_renders_for_reviewer(self):
        response = self.client.get(reverse("staff:verification_detail", args=[self.verification.pk]))
        self.assertContains(response, "writer")
        self.assertContains(response, reverse("staff:proof_download", args=[self.verification.pk, "proof_document"]))

    def test_viewer_cannot_see_documents_or_review(self):
        self.client.force_login(make_staff("viewer", Permission.VERIFICATIONS_VIEW))
        url = reverse("staff:verification_detail", args=[self.verification.pk])
        response = self.client.get(url)
        self.assertNotContains(response, "/proof/")
        self.assertEqual(self.review("approve").status_code, 404)

    def test_approve_updates_profile_logs_and_emails(self):
        response = self.review("approve", "Дякуємо")
        self.assertRedirects(response, reverse("staff:verifications"))
        self.verification.refresh_from_db()
        self.book.refresh_from_db()
        self.applicant.profile.refresh_from_db()
        self.assertEqual(self.verification.status, AuthorVerification.Status.APPROVED)
        self.assertEqual(self.verification.reviewed_by, self.admin)
        self.assertEqual(self.book.verified_author, self.applicant)
        self.assertTrue(self.applicant.profile.is_verified_author)
        self.assertEqual(mail.outbox[-1].to, [self.applicant.email])
        self.assertTrue(LogEntry.objects.filter(object_id=self.verification.pk).exists())

    def test_reject_requires_a_note(self):
        response = self.review("reject")
        self.assertContains(response, "Вкажіть причину відмови")
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.status, AuthorVerification.Status.PENDING)
        self.assertEqual(self.review("reject", "Недостатньо доказів").status_code, 302)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.status, AuthorVerification.Status.REJECTED)
        self.assertEqual(self.verification.admin_note, "Недостатньо доказів")

    def test_second_review_is_refused(self):
        self.review("approve")
        mails = len(mail.outbox)
        response = self.review("reject", "пізно")
        self.assertEqual(response.status_code, 302)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.status, AuthorVerification.Status.APPROVED)
        self.assertEqual(len(mail.outbox), mails)

    def test_cannot_approve_when_authorship_is_taken(self):
        Book.objects.filter(pk=self.book.pk).update(verified_author=make_user("rival"))
        response = self.review("approve")
        self.assertRedirects(response, reverse("staff:verification_detail", args=[self.verification.pk]))
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.status, AuthorVerification.Status.PENDING)

    def test_invalid_decision_is_rejected(self):
        self.assertEqual(self.review("explode").status_code, 200)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.status, AuthorVerification.Status.PENDING)

    def test_proof_download_is_audited(self):
        url = reverse("staff:proof_download", args=[self.verification.pk, "proof_document"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 doc")
        self.assertIn("документ", self.last_log().change_message)
        self.assertEqual(self.client.get(reverse("staff:proof_download", args=[self.verification.pk, "id"])).status_code, 404)

    def test_list_filters_by_state(self):
        self.review("approve")
        self.assertNotContains(self.client.get(reverse("staff:verifications")), "writer")
        self.assertContains(self.client.get(reverse("staff:verifications"), {"state": "approved"}), "writer")


class UserManagementTests(PanelTestCase):
    def setUp(self):
        super().setUp()
        self.target = make_user("target")

    def test_deactivate_and_activate(self):
        self.post("user_action", self.target.pk, "deactivate")
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertEqual(self.last_log().action_flag, CHANGE)
        self.post("user_action", self.target.pk, "activate")
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)

    def test_protected_accounts_cannot_be_blocked(self):
        for protected in (self.admin, admin_user("other-root")):
            self.post("user_action", protected.pk, "deactivate")
            protected.refresh_from_db()
            self.assertTrue(protected.is_active)

    def test_non_superuser_cannot_touch_staff(self):
        manager = make_staff("manager", Permission.USERS_VIEW, Permission.USERS_CHANGE)
        colleague = make_staff("colleague")
        self.client.force_login(manager)
        self.post("user_action", colleague.pk, "deactivate")
        colleague.refresh_from_db()
        self.assertTrue(colleague.is_active)
        self.post("user_action", self.target.pk, "deactivate")
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)

    def test_revoke_author_status(self):
        profile = self.target.profile
        profile.is_verified_author = True
        profile.save()
        Book.objects.filter(pk=self.book.pk).update(verified_author=self.target)
        self.post("user_action", self.target.pk, "revoke-author")
        profile.refresh_from_db()
        self.book.refresh_from_db()
        self.assertFalse(profile.is_verified_author)
        self.assertIsNone(self.book.verified_author)

    def test_pages_render(self):
        self.assertContains(self.client.get(reverse("staff:users"), {"q": "targ"}), "target")
        self.assertContains(self.client.get(reverse("staff:users"), {"state": "staff"}), "root")
        detail = self.client.get(reverse("staff:user_detail", args=[self.target.pk]))
        self.assertContains(detail, "Заблокувати")
        own = self.client.get(reverse("staff:user_detail", args=[self.admin.pk]))
        self.assertNotContains(own, "Заблокувати")


class CommentModerationTests(PanelTestCase):
    def setUp(self):
        super().setUp()
        self.book.is_approved = True
        self.book.save()
        self.comment = Comment.objects.create(user=self.owner, book=self.book, text="Спірний коментар")

    def test_list_and_delete(self):
        self.assertContains(self.client.get(reverse("staff:comments")), "Спірний коментар")
        self.post("comment_action", self.comment.pk, "delete")
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())
        self.assertEqual(self.last_log().action_flag, DELETION)

    def test_bulk_delete_with_replies(self):
        reply = Comment.objects.create(user=self.admin, book=self.book, text="Відповідь", parent=self.comment)
        self.post("comment_bulk", ids=[self.comment.pk], action="delete")
        self.assertFalse(Comment.objects.filter(pk__in=[self.comment.pk, reply.pk]).exists())

    def test_chapter_comments_render(self):
        chapter = make_chapter(self.book)
        Comment.objects.create(user=self.owner, chapter=chapter, text="До розділу")
        self.assertContains(self.client.get(reverse("staff:comments")), "До розділу")

    def test_public_moderation_is_audited(self):
        self.client.post(reverse("core:delete_comment", args=[self.comment.pk]))
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())
        self.assertEqual(self.last_log().action_flag, DELETION)

    def test_author_deleting_own_comment_is_not_logged(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("core:delete_comment", args=[self.comment.pk]))
        self.assertEqual(LogEntry.objects.count(), 0)


class DashboardTests(PanelTestCase):
    def test_dashboard_shows_queues_and_metrics(self):
        make_track()
        response = self.client.get(reverse("staff:dashboard"))
        self.assertContains(response, "Потребує уваги")
        self.assertContains(response, "Сайт у цифрах")
        self.assertContains(response, self.book.title)

    def test_metrics_follow_permissions(self):
        self.client.force_login(make_staff("viewer", Permission.COMMENTS_VIEW))
        response = self.client.get(reverse("staff:dashboard"))
        self.assertContains(response, "Коментарі")
        self.assertNotContains(response, "Користувачі")
        self.assertNotContains(response, "Потребує уваги")

    def test_activity_log_lists_django_admin_and_panel_entries(self):
        self.post("book_action", self.book.pk, "approve")
        response = self.client.get(reverse("staff:activity"), {"state": "changed"})
        self.assertContains(response, self.book.title)
        self.assertNotContains(self.client.get(reverse("staff:activity"), {"state": "deleted"}), self.book.title)


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class RolesCommandTests(TestCase):
    def test_command_creates_groups_with_permissions(self):
        call_command("sync_staff_roles")
        moderators = Group.objects.get(name="Модератори")
        self.assertTrue(moderators.permissions.filter(codename="change_book").exists())
        self.assertFalse(moderators.permissions.filter(codename="change_user").exists())
        administrators = Group.objects.get(name="Адміністратори")
        self.assertTrue(administrators.permissions.filter(codename="view_logentry").exists())

    def test_command_is_idempotent_and_grants_access(self):
        call_command("sync_staff_roles")
        call_command("sync_staff_roles")
        staff = make_user("mod", is_staff=True)
        staff.groups.add(Group.objects.get(name="Модератори"))
        with override_settings(CACHES=CACHES):
            self.client.force_login(staff)
            self.assertEqual(self.client.get(reverse("staff:books")).status_code, 200)
            self.assertEqual(self.client.get(reverse("staff:users")).status_code, 404)

    def test_unknown_permission_fails_loudly(self):
        from django.core.management.base import CommandError

        with override_settings(STAFF_ROLES={"X": ["core.fly_to_moon"]}):
            with self.assertRaises(CommandError):
                call_command("sync_staff_roles")


class RecommendationAuditTests(PanelTestCase):
    def test_staff_removing_recommendation_is_audited(self):
        self.book.is_approved = True
        self.book.save()
        track = make_track()
        recommendation = Recommendation.objects.create(user=self.owner, book=self.book, track=track)
        self.client.post(reverse("core:recommendation_delete", args=[recommendation.pk]))
        self.assertFalse(Recommendation.objects.filter(pk=recommendation.pk).exists())
        self.assertEqual(self.last_log().action_flag, DELETION)
