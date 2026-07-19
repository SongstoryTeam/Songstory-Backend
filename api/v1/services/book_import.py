from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from core.models import Book, BookTranslation, Chapter, ChapterTranslation, Language
from core.utils.catalog import get_or_create_author
from core.utils.slugs import generate_unique_slug


def import_book_from_open_library(
        *, open_library_id: str, title: str, author: str, year, isbn: str,
        cover_url: str, description: str, creator: User,
) -> tuple[Book, bool]:
    """Get-or-create a Book by its Open Library id.
    Called from both core (session) and api/v1 (JWT) views — pure
    Python, no view logic, so nothing needs to duplicate it later.
    """
    open_library_id = open_library_id.strip()
    title = title.strip()
    if not open_library_id or not title:
        raise ValueError("open_library_id and title are required")

    existing = Book.objects.filter(open_library_id=open_library_id).first()
    if existing:
        return existing, False

    language = Language.objects.filter(code="uk").first()
    try:
        year_int = int(year)
    except (TypeError, ValueError):
        year_int = 0

    try:
        with transaction.atomic():
            book = Book.objects.create(
                creator=creator,
                author=get_or_create_author(author.strip(), language) if author.strip() else None,
                year=year_int,
                cover_url=cover_url,
                isbn=isbn[:20],
                open_library_id=open_library_id,
                is_approved=True,
                slug=generate_unique_slug(Book, title),
            )
            if language:
                BookTranslation.objects.create(
                    book=book, language=language, title=title, description=description.strip(),
                )
            chapter = Chapter.objects.create(book=book, number=1, is_approved=True)
            if language:
                ChapterTranslation.objects.create(chapter=chapter, language=language, title="Розділ 1")
    except IntegrityError:
        return Book.objects.get(open_library_id=open_library_id), False

    return book, True
