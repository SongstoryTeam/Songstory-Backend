from __future__ import annotations

from django.db import transaction

from core.models import Book, BookTranslation, Chapter, ChapterTranslation, Language

CHAPTER_TITLE_TEMPLATE = "Розділ {number}"


def bootstrap_book_translation(book: Book, *, title: str, description: str) -> None:
    """Attach the site's default-language translation and an opening
    chapter to a freshly created Book.

    Shared by the "add a book" HTML form and the equivalent API endpoint
    so both produce identical default content instead of drifting (the
    two previously hardcoded this in different languages).
    """
    language = Language.get_default()
    if language is None:
        return

    with transaction.atomic():
        BookTranslation.objects.create(
            book=book, language=language, title=title, description=description,
        )
        chapter = Chapter.objects.create(book=book, number=1, is_approved=True)
        ChapterTranslation.objects.create(
            chapter=chapter,
            language=language,
            title=CHAPTER_TITLE_TEMPLATE.format(number=1),
        )


def add_bulk_chapters(*, book: Book, count: int, is_owner: bool) -> list[Chapter]:
    """Append `count` new chapters to a book, numbered after its last
    existing chapter, and give each a default-language translation."""
    last_chapter = book.chapters.order_by("-number").first()
    start_num = (last_chapter.number + 1) if last_chapter else 1

    with transaction.atomic():
        chapters = Chapter.objects.bulk_create([
            Chapter(book=book, number=start_num + i, is_approved=is_owner)
            for i in range(count)
        ])

        language = Language.get_default()
        if language:
            ChapterTranslation.objects.bulk_create([
                ChapterTranslation(
                    chapter=chapter,
                    language=language,
                    title=CHAPTER_TITLE_TEMPLATE.format(number=start_num + i),
                )
                for i, chapter in enumerate(chapters)
            ])

    return chapters
