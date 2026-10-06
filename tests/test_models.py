from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Book, Recommendation
from core.services.recommendations import grouped_recommendations, recommend
from tests.conftest_helpers import make_book, make_chapter, make_track, make_user


class BookModelTests(TestCase):
    def test_slugs_are_generated_and_unique(self):
        first = make_book(title="Кобзар")
        second = make_book(title="Кобзар", author="Інший автор")
        self.assertTrue(first.slug)
        self.assertNotEqual(first.slug, second.slug)

    def test_search_is_case_insensitive_for_cyrillic(self):
        make_book(title="Гаррі Поттер і філософський камінь", author="Джоан Роулінг")
        for query in ("гаррі", "ГАРРІ", "Філософський", "роулінг", "поттер камінь"):
            with self.subTest(query=query):
                self.assertEqual(Book.objects.search(query).count(), 1)
        self.assertEqual(Book.objects.search("дюна").count(), 0)

    def test_unapproved_books_are_visible_only_to_creator_and_staff(self):
        creator, stranger, staff = make_user("creator"), make_user("stranger"), make_user("staff", is_staff=True)
        make_book(creator, approved=False)
        self.assertEqual(Book.objects.visible_to(creator).count(), 1)
        self.assertEqual(Book.objects.visible_to(staff).count(), 1)
        self.assertEqual(Book.objects.visible_to(stranger).count(), 0)


class RecommendationTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = make_book(self.user)
        self.chapter = make_chapter(self.book)
        self.track = make_track()

    def test_same_track_is_reused_and_counted(self):
        other = make_user("other")
        recommend(self.user, self.track, self.book)
        recommend(other, self.track, self.book)
        groups = grouped_recommendations(self.book, None, other)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].count, 2)
        self.assertIsNotNone(groups[0].mine)

    def test_recommending_twice_is_idempotent_for_book_and_chapter(self):
        for chapter in (None, self.chapter):
            _, created_first = recommend(self.user, self.track, self.book, chapter)
            _, created_second = recommend(self.user, self.track, self.book, chapter)
            self.assertTrue(created_first)
            self.assertFalse(created_second)

    def test_database_blocks_duplicate_book_level_recommendation(self):
        Recommendation.objects.create(user=self.user, track=self.track, book=self.book)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Recommendation.objects.create(user=self.user, track=self.track, book=self.book)

    def test_chapter_and_book_recommendations_are_separate(self):
        recommend(self.user, self.track, self.book)
        recommend(self.user, self.track, self.book, self.chapter)
        self.assertEqual(len(grouped_recommendations(self.book, None, self.user)), 1)
        self.assertEqual(len(grouped_recommendations(self.book, self.chapter, self.user)), 1)

    def test_verified_author_recommendations_come_first(self):
        author = make_user("author")
        self.book.verified_author = author
        self.book.save()
        popular, authors_pick = make_track("aaaaaaaaaaa", title="Популярний"), make_track("bbbbbbbbbbb", title="Вибір автора")
        recommend(self.user, popular, self.book)
        recommend(make_user("third"), popular, self.book)
        recommend(author, authors_pick, self.book)
        groups = grouped_recommendations(self.book, None, self.user)
        self.assertEqual(groups[0].track, authors_pick)
        self.assertTrue(groups[0].by_verified_author)
