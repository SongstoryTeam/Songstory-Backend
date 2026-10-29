from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Author, Book, BookEditSuggestion, Genre
from core.services import suggestions as suggestion_service
from tests.conftest_helpers import make_book, make_user
from tests.test_book_suggestions import CACHES, EMAIL, form_payload

Status = BookEditSuggestion.Status


@override_settings(CACHES=CACHES, **EMAIL)
class LifecycleTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = make_user("owner")
        self.user = make_user("reader")
        self.book = make_book(self.owner)
        self.edit_url = reverse("core:suggest_edit", args=[self.book.slug])
        self.client.force_login(self.user)

    def propose(self, **overrides):
        return self.client.post(self.edit_url, form_payload(self.book, **overrides))

    def pending(self) -> BookEditSuggestion:
        return BookEditSuggestion.objects.get(status=Status.PENDING)

    def withdraw_url(self, suggestion) -> str:
        return reverse("core:withdraw_suggestion", args=[suggestion.pk])


class RevisionServiceTests(LifecycleTestCase):
    def setUp(self):
        super().setUp()
        self.propose(year=1841, reason="Перша версія")
        self.suggestion = self.pending()

    def test_revision_replaces_changes_and_counts_edits(self):
        before = self.suggestion.updated_at
        mail.outbox.clear()
        suggestion_service.revise_suggestion(
            self.suggestion, changes={"title": {"old": "Кобзар", "new": "Кобзар. Том 1"}}, reason="Друга версія"
        )
        self.suggestion.refresh_from_db()
        self.assertEqual(list(self.suggestion.changes), ["title"])
        self.assertEqual((self.suggestion.revision, self.suggestion.reason), (2, "Друга версія"))
        self.assertGreater(self.suggestion.updated_at, before)
        self.assertEqual(self.suggestion.status, Status.PENDING)
        self.assertEqual(mail.outbox, [])

    def test_closed_suggestion_cannot_be_revised(self):
        suggestion_service.reject_suggestion(self.suggestion, make_user("moderator", is_staff=True))
        with self.assertRaises(suggestion_service.SuggestionAlreadyReviewed):
            suggestion_service.revise_suggestion(self.suggestion, changes={"year": {"old": 1840, "new": 1850}})

    def test_withdrawal_closes_the_suggestion_and_frees_the_slot(self):
        left = suggestion_service.pending_suggestions_left(self.user)
        suggestion_service.withdraw_suggestion(self.suggestion)
        self.suggestion.refresh_from_db()
        self.assertEqual(self.suggestion.status, Status.WITHDRAWN)
        self.assertEqual(suggestion_service.pending_suggestions_left(self.user), left + 1)
        self.assertIsNone(suggestion_service.pending_for(self.user, self.book))

    def test_new_suggestion_is_possible_after_withdrawal(self):
        suggestion_service.withdraw_suggestion(self.suggestion)
        self.propose(year=1850)
        self.assertEqual(BookEditSuggestion.objects.count(), 2)
        self.assertEqual(self.pending().changes["year"]["new"], 1850)

    def test_withdrawn_suggestion_cannot_be_approved(self):
        suggestion_service.withdraw_suggestion(self.suggestion)
        with self.assertRaises(suggestion_service.SuggestionAlreadyReviewed):
            suggestion_service.approve_suggestion(self.suggestion, make_user("moderator", is_staff=True))

    def test_review_of_a_revision_the_moderator_did_not_see_is_refused(self):
        suggestion_service.revise_suggestion(self.suggestion, changes={"year": {"old": 1840, "new": 1855}})
        moderator = make_user("moderator", is_staff=True)
        with self.assertRaises(suggestion_service.SuggestionRevised):
            suggestion_service.approve_suggestion(self.suggestion, moderator, expected_revision=1)
        self.assertEqual(self.pending().revision, 2)
        suggestion_service.approve_suggestion(self.suggestion, moderator, expected_revision=2)
        self.book.refresh_from_db()
        self.assertEqual(self.book.year, 1855)

    def test_pending_for_ignores_anonymous_and_other_users(self):
        self.client.logout()
        self.assertIsNone(suggestion_service.pending_for(make_user("stranger"), self.book))
        self.assertEqual(suggestion_service.pending_for(self.user, self.book), self.suggestion)


class OutdatedFieldsTests(LifecycleTestCase):
    def setUp(self):
        super().setUp()
        self.propose(year=1841, genre_name="Поезія")
        self.suggestion = self.pending()

    def change_book(self, **values):
        Book.objects.filter(pk=self.book.pk).update(**values)
        self.book.refresh_from_db()

    def test_untouched_book_has_nothing_outdated(self):
        self.assertEqual(suggestion_service.outdated_fields(self.suggestion, self.book), [])

    def test_field_edited_after_submission_is_reported(self):
        self.change_book(year=1850)
        self.assertEqual(suggestion_service.outdated_fields(self.suggestion, self.book), ["Рік видання"])

    def test_field_that_already_matches_the_proposal_is_not_reported(self):
        self.change_book(year=1841)
        self.assertEqual(suggestion_service.outdated_fields(self.suggestion, self.book), [])

    def test_no_suggestion_means_nothing_is_outdated(self):
        self.assertEqual(suggestion_service.outdated_fields(None, self.book), [])


class PreviewTests(LifecycleTestCase):
    def test_preview_applies_values_without_touching_the_database(self):
        authors, genres = Author.objects.count(), Genre.objects.count()
        suggestion = BookEditSuggestion(
            book=self.book,
            user=self.user,
            changes={
                "title": {"old": "Кобзар", "new": "Новий заголовок"},
                "author_name": {"old": "Тарас Шевченко", "new": "Зовсім Новий Автор"},
                "genre_name": {"old": "", "new": "Нова категорія"},
                "year": {"old": 1840, "new": 1999},
            },
        )
        book = suggestion_service.preview(self.book, suggestion)
        self.assertEqual((book.title, book.year), ("Новий заголовок", 1999))
        self.assertEqual((book.author.name, book.genre.name), ("Зовсім Новий Автор", "Нова категорія"))
        self.assertEqual((Author.objects.count(), Genre.objects.count()), (authors, genres))
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, "Кобзар")

    def test_preview_reuses_existing_author_and_clears_empty_values(self):
        existing = Author.objects.create(name="Іван Франко")
        suggestion = BookEditSuggestion(
            book=self.book,
            user=self.user,
            changes={
                "author_name": {"old": "Тарас Шевченко", "new": "  франко   іван "},
                "genre_name": {"old": "Поезія", "new": ""},
            },
        )
        book = suggestion_service.preview(self.book, suggestion)
        self.assertEqual(book.author, existing)
        self.assertIsNone(book.genre)

    def test_proposed_values_overlay_the_current_book(self):
        suggestion = BookEditSuggestion(book=self.book, user=self.user, changes={"year": {"old": 1840, "new": 1999}})
        values = suggestion_service.proposed_values(self.book, suggestion)
        self.assertEqual((values["year"], values["title"]), (1999, "Кобзар"))


class RevisionPageTests(LifecycleTestCase):
    def setUp(self):
        super().setUp()
        self.propose(year=1841, reason="Помилка")
        self.suggestion = self.pending()

    def test_page_is_prefilled_with_the_proposal_and_keeps_the_original_for_comparison(self):
        response = self.client.get(self.edit_url)
        form = response.context["form"]
        self.assertEqual(form.initial["year"], 1841)
        self.assertEqual(form.initial["reason"], "Помилка")
        self.assertContains(response, 'data-initial="1840"')
        self.assertContains(response, 'data-saved="1841"')
        self.assertContains(response, "Змінити пропозицію")
        self.assertContains(response, self.withdraw_url(self.suggestion))

    def test_first_time_page_has_no_saved_baseline_or_withdraw_form(self):
        self.client.force_login(make_user("newcomer"))
        response = self.client.get(self.edit_url)
        self.assertNotContains(response, "data-saved")
        self.assertNotContains(response, "/withdraw/")

    def test_saving_updates_the_same_suggestion(self):
        response = self.client.post(
            self.edit_url, form_payload(self.book, year=1842, description="Новий опис"), follow=True
        )
        self.assertRedirects(response, self.book.get_absolute_url(), fetch_redirect_response=False)
        self.assertContains(response, "Пропозицію оновлено.")
        suggestion = self.pending()
        self.assertEqual(suggestion.pk, self.suggestion.pk)
        self.assertEqual(sorted(suggestion.changes), ["description", "year"])
        self.assertEqual(suggestion.revision, 2)

    def test_revision_is_computed_against_the_current_book(self):
        Book.objects.filter(pk=self.book.pk).update(description="Додано іншим")
        self.book.refresh_from_db()
        self.propose(year=1842, description="Додано іншим")
        self.assertEqual(list(self.pending().changes), ["year"])

    def test_reverting_every_field_points_to_withdrawal(self):
        response = self.propose()
        self.assertContains(response, "відкличте")
        self.assertEqual(self.pending().revision, 1)

    @override_settings(PENDING_SUGGESTIONS_LIMIT=1)
    def test_revising_does_not_need_a_free_slot(self):
        self.propose(year=1843)
        self.assertEqual(self.pending().changes["year"]["new"], 1843)

    def test_outdated_fields_are_flagged_on_the_edit_page(self):
        Book.objects.filter(pk=self.book.pk).update(year=1900)
        self.assertContains(self.client.get(self.edit_url), "Після подання пропозиції в книзі змінилося: Рік видання")

    def test_after_a_decision_the_next_submission_starts_a_new_suggestion(self):
        suggestion_service.reject_suggestion(self.suggestion, make_user("moderator", is_staff=True))
        self.propose(year=1844)
        self.suggestion.refresh_from_db()
        self.assertEqual(self.suggestion.status, Status.REJECTED)
        self.assertEqual(self.pending().changes["year"]["new"], 1844)
        self.assertEqual(self.pending().revision, 1)


class WithdrawViewTests(LifecycleTestCase):
    def setUp(self):
        super().setUp()
        self.propose(year=1841)
        self.suggestion = self.pending()

    def test_owner_withdraws_and_returns_to_the_book(self):
        response = self.client.post(self.withdraw_url(self.suggestion), follow=True)
        self.assertRedirects(response, self.book.get_absolute_url(), fetch_redirect_response=False)
        self.assertContains(response, "Пропозицію відкликано.")
        self.suggestion.refresh_from_db()
        self.assertEqual(self.suggestion.status, Status.WITHDRAWN)

    def test_someone_elses_suggestion_is_not_found(self):
        self.client.force_login(make_user("stranger"))
        self.assertEqual(self.client.post(self.withdraw_url(self.suggestion)).status_code, 404)
        self.suggestion.refresh_from_db()
        self.assertEqual(self.suggestion.status, Status.PENDING)

    def test_withdrawal_requires_post_and_login(self):
        self.assertEqual(self.client.get(self.withdraw_url(self.suggestion)).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(self.withdraw_url(self.suggestion)).status_code, 302)
        self.suggestion.refresh_from_db()
        self.assertEqual(self.suggestion.status, Status.PENDING)

    def test_reviewed_suggestion_cannot_be_withdrawn(self):
        suggestion_service.approve_suggestion(self.suggestion, make_user("moderator", is_staff=True))
        response = self.client.post(self.withdraw_url(self.suggestion), follow=True)
        self.assertContains(response, "вже розглянуто")
        self.suggestion.refresh_from_db()
        self.assertEqual(self.suggestion.status, Status.APPROVED)

    def test_next_target_is_honoured_only_for_local_urls(self):
        local = reverse("core:my_suggestions")
        response = self.client.post(self.withdraw_url(self.suggestion), {"next": local})
        self.assertRedirects(response, local)

    def test_external_next_target_is_ignored(self):
        response = self.client.post(self.withdraw_url(self.suggestion), {"next": "https://evil.example/"})
        self.assertRedirects(response, self.book.get_absolute_url())

    def test_withdrawal_is_rate_limited(self):
        with override_settings(RATE_LIMITS={"suggestion_withdraw": "1/m"}):
            self.client.post(self.withdraw_url(self.suggestion))
            response = self.client.post(self.withdraw_url(self.suggestion))
        self.assertEqual(response.status_code, 429)


class OwnerOverlayTests(LifecycleTestCase):
    def setUp(self):
        super().setUp()
        self.propose(title="Кобзар. Том 1", year=1841, author_name="Нова Авторка")
        self.url = self.book.get_absolute_url()

    def test_proposer_sees_the_book_with_their_changes_and_a_banner(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Кобзар. Том 1")
        self.assertContains(response, "1841")
        self.assertContains(response, "Нова Авторка")
        self.assertContains(response, "Ви бачите книгу з вашими змінами")
        self.assertEqual(response.context["suggestion"], self.pending())

    def test_original_view_is_one_click_away(self):
        response = self.client.get(self.url, {"view": "original"})
        self.assertContains(response, "Ви дивитесь опубліковану версію книги")
        self.assertContains(response, "Тарас Шевченко")
        self.assertNotContains(response, "Нова Авторка")
        self.assertContains(response, "Показати зі змінами")
        self.assertContains(self.client.get(self.url), "?view=original")

    def test_viewing_never_writes_to_the_database(self):
        authors = Author.objects.count()
        self.client.get(self.url)
        self.assertEqual(Author.objects.count(), authors)
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, "Кобзар")

    def test_other_users_and_guests_see_the_published_book(self):
        for viewer in (make_user("stranger"), None):
            self.client.logout()
            if viewer:
                self.client.force_login(viewer)
            response = self.client.get(self.url)
            self.assertNotContains(response, "Нова Авторка")
            self.assertNotContains(response, "Ви бачите книгу з вашими змінами")

    def test_banner_warns_about_newer_edits_and_offers_actions(self):
        Book.objects.filter(pk=self.book.pk).update(year=1900)
        response = self.client.get(self.url)
        self.assertContains(response, "Після подання пропозиції в книзі змінилося: Рік видання")
        self.assertContains(response, self.edit_url)
        self.assertContains(response, self.withdraw_url(self.pending()))

    def test_menu_reflects_the_pending_suggestion(self):
        self.assertContains(self.client.get(self.url), "Змінити мою пропозицію")
        self.client.post(self.withdraw_url(self.pending()))
        self.assertContains(self.client.get(self.url), "Запропонувати зміни")

    def test_no_banner_without_a_suggestion(self):
        self.client.post(self.withdraw_url(self.pending()))
        self.assertNotContains(self.client.get(self.url), "suggestion-banner")


class MySuggestionsPageTests(LifecycleTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("core:my_suggestions")

    def test_login_is_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_empty_state_points_to_the_catalog(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Немає пропозицій на розгляді")
        self.assertNotContains(response, "Історія")

    def test_pending_suggestion_offers_edit_and_withdraw(self):
        self.propose(year=1841, reason="Помилка у році")
        response = self.client.get(self.url)
        self.assertContains(response, "Кобзар")
        self.assertContains(response, "1841")
        self.assertContains(response, "Помилка у році")
        self.assertContains(response, self.edit_url)
        self.assertContains(response, self.withdraw_url(self.pending()))
        self.assertContains(response, "Вільно: 9")

    def test_history_shows_decisions_and_moderator_notes(self):
        self.propose(year=1841)
        moderator = make_user("moderator", is_staff=True)
        suggestion_service.reject_suggestion(self.pending(), moderator, "Джерело не підтверджує")
        self.propose(year=1842)
        suggestion_service.withdraw_suggestion(self.pending())
        response = self.client.get(self.url)
        self.assertContains(response, "Історія")
        self.assertContains(response, "Відхилено")
        self.assertContains(response, "Відкликано")
        self.assertContains(response, "Джерело не підтверджує")
        self.assertNotContains(response, "Змінити</a>")

    def test_only_own_suggestions_are_listed(self):
        other = make_user("other")
        BookEditSuggestion.objects.create(book=self.book, user=other, changes={"year": {"old": 1840, "new": 1999}})
        self.assertNotContains(self.client.get(self.url), "1999")

    @override_settings(SUGGESTION_HISTORY_PAGE_SIZE=1)
    def test_history_is_paginated(self):
        for year in (1841, 1842, 1843):
            self.propose(year=year)
            suggestion_service.withdraw_suggestion(self.pending())
        first = self.client.get(self.url)
        self.assertEqual(len(first.context["page"].object_list), 1)
        self.assertEqual(first.context["page"].paginator.num_pages, 3)
        self.assertContains(first, "pagination")

    def test_navigation_links_to_the_page(self):
        self.assertContains(self.client.get(self.url), f'href="{self.url}"')

    def test_staff_has_no_slot_counter(self):
        self.client.force_login(make_user("editor", is_staff=True))
        self.assertNotContains(self.client.get(self.url), "Вільно")


class AdminReviewGuardTests(LifecycleTestCase):
    def setUp(self):
        super().setUp()
        self.propose(year=1841)
        self.suggestion = self.pending()
        self.admin = make_user("moderator", is_staff=True, is_superuser=True)
        self.url = reverse("admin:core_bookeditsuggestion_change", args=[self.suggestion.pk])

    def decide(self, seen_revision):
        self.client.force_login(self.admin)
        return self.client.post(
            self.url, {"status": Status.APPROVED, "admin_note": "", "seen_revision": seen_revision}, follow=True
        )

    def test_form_carries_the_revision_the_moderator_is_looking_at(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.url), 'name="seen_revision" value="1"')

    def test_approval_of_an_unseen_revision_is_refused(self):
        suggestion_service.revise_suggestion(self.suggestion, changes={"year": {"old": 1840, "new": 1855}})
        response = self.decide(seen_revision=1)
        self.assertContains(response, "Автор змінив пропозицію")
        self.assertEqual(self.pending().revision, 2)
        self.book.refresh_from_db()
        self.assertEqual(self.book.year, 1840)

    def test_approval_of_the_seen_revision_goes_through(self):
        self.decide(seen_revision=1)
        self.book.refresh_from_db()
        self.assertEqual(self.book.year, 1841)

    def test_detail_page_warns_when_the_book_moved_on(self):
        Book.objects.filter(pk=self.book.pk).update(year=1900)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.url), "Після подання в книзі змінилося: Рік видання")
