from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Max

from core.models import Author, Book, Chapter, Genre
from core.text import normalize

from .google_books import ExternalBook


def get_or_create_author(name: str) -> Author | None:
    cleaned = " ".join(name.split())
    if not cleaned:
        return None
    existing = Author.objects.filter(name__iexact=cleaned).first()
    return existing or Author.objects.create(name=cleaned)


def get_or_create_genre(name: str) -> Genre | None:
    cleaned = " ".join(name.split())
    if not cleaned:
        return None
    existing = Genre.objects.filter(name__iexact=cleaned).first()
    return existing or Genre.objects.create(name=cleaned)


def create_book(
    *,
    user: User,
    title: str,
    author_name: str,
    year: int | None = None,
    description: str = "",
    cover_url: str = "",
    genre_name: str = "",
) -> Book:
    return Book.objects.create(
        title=title.strip(),
        description=description.strip(),
        author=get_or_create_author(author_name),
        genre=get_or_create_genre(genre_name),
        year=year,
        cover_url=cover_url,
        creator=user,
        is_approved=user.is_staff,
    )


@transaction.atomic
def import_external_book(external: ExternalBook, user: User) -> tuple[Book, bool]:
    existing = Book.objects.filter(google_books_id=external.external_id).first()
    if existing:
        return existing, False
    book = Book.objects.create(
        title=external.title,
        description=external.description,
        author=get_or_create_author(external.author),
        year=external.year,
        cover_url=external.cover_url,
        isbn=external.isbn,
        google_books_id=external.external_id,
        creator=user,
        is_approved=True,
    )
    return book, True


def find_duplicate(title: str, author_name: str) -> Book | None:
    key = normalize(f"{title} {author_name}")
    return Book.objects.filter(search_key=key).first()


@transaction.atomic
def add_chapters(book: Book, count: int) -> list[Chapter]:
    count = min(count, settings.BULK_CHAPTERS_MAX)
    last = book.chapters.aggregate(last=Max("number"))["last"] or 0
    chapters = [Chapter(book=book, number=last + offset) for offset in range(1, count + 1)]
    return Chapter.objects.bulk_create(chapters)
