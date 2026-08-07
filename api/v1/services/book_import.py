from __future__ import annotations

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from core.models import Book, BookTranslation, Chapter, ChapterTranslation, Language
from core.utils.catalog import get_or_create_author
from core.utils.slugs import generate_unique_slug

FIRST_CHAPTER_TITLE = "Розділ 1"
ISBN_MAX_LENGTH = 20


def import_book_from_open_library(
    *,
    open_library_id: str,
    title: str,
    author: str,
    year: int | str | None,
    isbn: str,
    cover_url: str,
    description: str,
    language_code: str,
    creator: User,
) -> tuple[Book, bool]:
    """Get or create a Book from an external catalog search result.

    `open_library_id` is a source-agnostic external identifier used for
    deduplication: it holds either an Open Library work id or a Google
    Books volume id prefixed with "gbooks:" by the search endpoint.

    `language_code` must match an active Language in the catalog. The
    caller is responsible for only offering one-click import once the
    result's actual content language has been confirmed — this function
    will not guess or default it.

    Returns (book, created). When created is False, the book already
    existed and the caller should redirect to it.
    """
    open_library_id = open_library_id.strip()
    title = title.strip()
    if not open_library_id or not title:
        raise ValueError("open_library_id and title are required")

    language = Language.objects.filter(code=language_code, is_active=True).first()
    if language is None:
        raise ValueError(f"unsupported language: {language_code!r}")

    existing = Book.objects.filter(open_library_id=open_library_id).first()
    if existing:
        return existing, False

    author = author.strip()

    try:
        with transaction.atomic():
            book = Book.objects.create(
                creator=creator,
                author=get_or_create_author(author, language) if author else None,
                year=_parse_year(year) or 0,
                cover_url=cover_url,
                isbn=isbn[:ISBN_MAX_LENGTH],
                open_library_id=open_library_id,
                is_approved=True,
                slug=generate_unique_slug(Book, title),
            )
            BookTranslation.objects.create(
                book=book,
                language=language,
                title=title,
                description=description.strip(),
            )
            chapter = Chapter.objects.create(book=book, number=1, is_approved=True)
            ChapterTranslation.objects.create(
                chapter=chapter,
                language=language,
                title=FIRST_CHAPTER_TITLE,
            )
    except IntegrityError:
        return Book.objects.get(open_library_id=open_library_id), False

    return book, True


def _parse_year(value: int | str | None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
