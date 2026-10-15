from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.db import IntegrityError
from django.test import SimpleTestCase, TestCase

from core.models import Author, Book, Genre
from core.services import books as book_service
from core.services.external import ExternalBook
from core.services.maintenance import normalize_catalog
from core.services.normalize import (
    clean_cover_url,
    clean_description,
    clean_isbn,
    clean_person_name,
    clean_text,
    clean_title,
    clean_year,
)
from core.text import name_key, search_form
from tests.conftest_helpers import make_user


class CleanerTests(SimpleTestCase):
    def test_text_loses_invisible_and_control_characters_and_extra_spaces(self):
        self.assertEqual(clean_text("  Ко\u200bбзар \x00  \u00a0Шевченка\n"), "Кобзар Шевченка")

    def test_apostrophes_inside_words_are_unified_but_quotes_are_untouched(self):
        for variant in ("п'ята", "пʼята", "п‘ята", "п`ята", "п’ята"):
            with self.subTest(variant=variant):
                self.assertEqual(clean_text(variant), "п’ята")
        self.assertEqual(clean_text("'Привіт' сказав він"), "'Привіт' сказав він")

    def test_title_is_truncated_to_column_size(self):
        self.assertEqual(len(clean_title("а" * 400)), 255)

    def test_person_name_case_and_punctuation(self):
        self.assertEqual(clean_person_name("тарас  шевченко"), "Тарас Шевченко")
        self.assertEqual(clean_person_name("ТАРАС ШЕВЧЕНКО"), "Тарас Шевченко")
        self.assertEqual(clean_person_name("дж. р. р. толкін"), "Дж. Р. Р. Толкін")
        self.assertEqual(clean_person_name("о'генрі"), "О’Генрі")
        self.assertEqual(clean_person_name("ван Гог"), "ван Гог")
        self.assertEqual(clean_person_name("Автор А ;Автор Б,"), "Автор А, Автор Б")
        self.assertEqual(clean_person_name(" , "), "")

    def test_description_strips_html_and_limits_length_at_word_boundary(self):
        self.assertEqual(clean_description("<p>Команда <b>злодіїв</b></p>"), "Команда злодіїв")
        long = clean_description("слово " * 2000)
        self.assertLessEqual(len(long), 5000)
        self.assertTrue(long.endswith("слово"))

    def test_description_keeps_paragraphs(self):
        self.assertEqual(clean_description("Перший.\n\n\n\nДругий.\r\n  Третій  "), "Перший.\n\nДругий.\nТретій")

    def test_year_must_be_realistic(self):
        self.assertEqual(clean_year("1840"), 1840)
        for bad in (0, -5, 99999, "abc", None):
            with self.subTest(bad=bad):
                self.assertIsNone(clean_year(bad))

    def test_cover_url_must_be_https_and_short(self):
        self.assertEqual(clean_cover_url("http://books.google.com/x.jpg"), "https://books.google.com/x.jpg")
        self.assertEqual(clean_cover_url("javascript:alert(1)"), "")
        self.assertEqual(clean_cover_url("не посилання"), "")
        self.assertEqual(clean_cover_url("https://x.test/" + "a" * 600), "")

    def test_isbn_is_cleaned_and_validated_by_shape(self):
        self.assertEqual(clean_isbn("978-966-917-170-6"), "9789669171706")
        self.assertEqual(clean_isbn("0-8044-2957-x"), "080442957X")
        for bad in ("123", "abcdefghijklm", "97896691717X6"):
            with self.subTest(bad=bad):
                self.assertEqual(clean_isbn(bad), "")

    def test_g_with_upturn_matches_plain_g_in_search_and_author_keys(self):
        self.assertEqual(search_form("Бардуґо"), search_form("Бардуго"))
        self.assertEqual(name_key("Шевченко Тарас"), name_key("тарас ШЕВЧЕНКО"))


class SavePipelineTests(TestCase):
    def test_model_normalizes_whatever_is_passed_in(self):
        book = Book.objects.create(
            title="  п'ята   пора\x00 ",
            description="<p>Опис</p>",
            cover_url="http://x.test/c.jpg",
            isbn="978-966-917-170-6",
            year=99999,
            is_approved=True,
        )
        book.refresh_from_db()
        self.assertEqual(
            (book.title, book.description, book.cover_url, book.isbn, book.year),
            ("п’ята пора", "Опис", "https://x.test/c.jpg", "9789669171706", None),
        )

    def test_author_is_normalized_and_keyed_on_save(self):
        author = Author.objects.create(name="тарас  шевченко")
        self.assertEqual((author.name, author.name_key), ("Тарас Шевченко", "тарас шевченко"))

    def test_same_author_in_different_spelling_is_reused(self):
        first = book_service.get_or_create_author("Лі Бардуґо")
        for variant in ("лі бардуго", "Бардуго Лі", "  ЛІ   БАРДУГО "):
            with self.subTest(variant=variant):
                self.assertEqual(book_service.get_or_create_author(variant), first)
        self.assertEqual(Author.objects.count(), 1)

    def test_genre_matching_ignores_case_even_for_cyrillic(self):
        first = book_service.get_or_create_genre("фентезі")
        self.assertEqual(first.name, "Фентезі")
        self.assertEqual(book_service.get_or_create_genre("ФЕНТЕЗІ"), first)
        self.assertEqual(Genre.objects.count(), 1)

    def test_empty_author_and_genre_give_none(self):
        self.assertIsNone(book_service.get_or_create_author(" , "))
        self.assertIsNone(book_service.get_or_create_genre("   "))


class DuplicateDetectionTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.book = book_service.create_book(user=self.user, title="Шістка воронів", author_name="Лі Бардуґо", isbn="9789669171706")

    def test_found_despite_case_apostrophe_g_and_name_order(self):
        for title, author in (("ШІСТКА ВОРОНІВ", "бардуго лі"), ("шістка  воронів", "Лі Бардуго")):
            with self.subTest(title=title):
                self.assertEqual(book_service.find_duplicate(title, author), self.book)

    def test_found_by_isbn_even_if_title_differs(self):
        self.assertEqual(book_service.find_duplicate("Six of Crows", "Leigh Bardugo", "978-966-917-170-6"), self.book)

    def test_same_title_by_another_author_is_not_a_duplicate(self):
        self.assertIsNone(book_service.find_duplicate("Шістка воронів", "Хтось Інший"))

    def test_book_without_author_does_not_match_book_with_author(self):
        self.assertIsNone(book_service.find_duplicate("Шістка воронів", ""))


class ImportRobustnessTests(TestCase):
    def test_import_survives_hostile_external_data(self):
        user = make_user()
        external = ExternalBook("g" * 80, "т" * 400, "ПЕТРО  КОЦЮБИНСЬКИЙ", 99999, "ftp://x/y", "<b>Опис</b>\x00", "bad")
        book, created = book_service.import_external_book(external, user)
        self.assertTrue(created)
        self.assertEqual(len(book.title), 255)
        self.assertEqual((book.author.name, book.year, book.cover_url, book.isbn, book.description), ("Петро Коцюбинський", None, "", "", "Опис"))
        self.assertIsNone(book.google_books_id)

    def test_parallel_import_of_same_book_returns_existing_instead_of_failing(self):
        user = make_user()
        external = ExternalBook("gX", "Кобзар", "Тарас Шевченко", 1840, "", "", "")
        winner = Book.objects.create(title="Інша назва", google_books_id="gX", is_approved=True)
        real_create = Book.objects.create

        def create_after_race(**kwargs):
            raise IntegrityError("duplicate google_books_id")

        with mock.patch("core.services.books.find_duplicate", return_value=None), \
                mock.patch.object(Book.objects, "create", side_effect=create_after_race):
            with mock.patch("core.services.books.Book.objects.filter") as lookup:
                lookup.return_value.first.side_effect = [None, winner]
                book, created = book_service.import_external_book(external, user)
        self.assertEqual((book, created), (winner, False))
        self.assertIsNotNone(real_create)


class NormalizeCatalogTests(TestCase):
    def setUp(self):
        # bulk_create обходить save(), тож це імітація «брудних» даних, що були в базі до нормалізації.
        Author.objects.bulk_create(
            [
                Author(name="тарас  шевченко", slug="a1"),
                Author(name="Шевченко Тарас", slug="a2"),
                Author(name="Леся Українка", slug="a3"),
            ]
        )
        first, second, third = Author.objects.order_by("pk")
        Book.objects.bulk_create(
            [
                Book(title=" Кобзар ", slug="kobzar", author=first, is_approved=True),
                Book(title="Кобзар", slug="kobzar-2", author=second, is_approved=True),
                Book(title="Лісова  пісня", slug="lisova", author=third, description="<p>Драма</p>", is_approved=True),
            ]
        )

    def test_duplicate_authors_are_merged_and_books_follow(self):
        report = normalize_catalog()
        self.assertEqual(report.authors_merged, 1)
        self.assertEqual(Author.objects.count(), 2)
        shevchenko = Author.objects.get(name="Тарас Шевченко")
        self.assertEqual(Book.objects.filter(author=shevchenko).count(), 2)
        self.assertEqual(shevchenko.name_key, "тарас шевченко")

    def test_books_are_cleaned_and_keys_rebuilt(self):
        report = normalize_catalog()
        book = Book.objects.get(slug="lisova")
        self.assertEqual((book.title, book.description), ("Лісова пісня", "Драма"))
        self.assertEqual(book.search_key, "лісова пісня леся українка")
        self.assertEqual(report.books_updated, 3)

    def test_duplicate_books_are_reported_not_deleted(self):
        report = normalize_catalog()
        self.assertEqual(report.duplicate_books, [("кобзар", "тарас шевченко")])
        self.assertEqual(Book.objects.count(), 3)

    def test_dry_run_changes_nothing(self):
        report = normalize_catalog(dry_run=True)
        self.assertEqual(report.authors_merged, 1)
        self.assertEqual(Author.objects.count(), 3)
        self.assertEqual(Book.objects.get(slug="lisova").description, "<p>Драма</p>")

    def test_command_prints_summary(self):
        out = StringIO()
        call_command("normalize_catalog", "--dry-run", stdout=out)
        self.assertIn("Авторів злито: 1", out.getvalue())
        self.assertIn("нічого не збережено", out.getvalue())
