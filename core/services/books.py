from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Max

from core import limits
from core.models import Author, Book, Chapter, Genre
from core.text import name_key, title_identity

from .external import ExternalBook
from .normalize import clean_external_id, clean_genre_name, clean_isbn, clean_person_name, clean_title


def get_or_create_author(name: str) -> Author | None:
    cleaned = clean_person_name(name)
    if not cleaned:
        return None
    key = name_key(cleaned)
    existing = Author.objects.filter(name_key=key).order_by("pk").first()
    if existing:
        return existing
    try:
        with transaction.atomic():
            return Author.objects.create(name=cleaned)
    except IntegrityError:
        return Author.objects.filter(name_key=key).order_by("pk").first() or Author.objects.filter(name=cleaned).first()


def get_or_create_genre(name: str) -> Genre | None:
    cleaned = clean_genre_name(name)
    if not cleaned:
        return None
    folded = cleaned.casefold()
    existing = next((genre for genre in Genre.objects.all() if genre.name.casefold() == folded), None)
    if existing:
        return existing
    try:
        with transaction.atomic():
            return Genre.objects.create(name=cleaned)
    except IntegrityError:
        return next((genre for genre in Genre.objects.all() if genre.name.casefold() == folded), None)


def pending_books_count(user: User) -> int:
    return Book.objects.filter(creator=user, is_approved=False).count()


def pending_books_left(user: User) -> int | None:
    if user.is_staff:
        return None
    return max(settings.PENDING_BOOKS_LIMIT - pending_books_count(user), 0)


def create_book(
    *,
    user: User,
    title: str,
    author_name: str,
    year: int | None = None,
    description: str = "",
    cover_url: str = "",
    genre_name: str = "",
    isbn: str = "",
) -> Book:
    return Book.objects.create(
        title=title,
        description=description,
        author=get_or_create_author(author_name),
        genre=get_or_create_genre(genre_name),
        year=year,
        cover_url=cover_url,
        isbn=isbn,
        creator=user,
        is_approved=user.is_staff,
    )


@transaction.atomic
def import_external_book(external: ExternalBook, user: User) -> tuple[Book, bool]:
    external_id = clean_external_id(external.external_id)
    existing = (external_id and Book.objects.filter(google_books_id=external_id).first()) or find_duplicate(
        external.title, external.author, external.isbn
    )
    if existing:
        return existing, False
    try:
        with transaction.atomic():
            book = Book.objects.create(
                title=external.title,
                description=external.description,
                author=get_or_create_author(external.author),
                year=external.year,
                cover_url=external.cover_url,
                isbn=external.isbn,
                google_books_id=external_id,
                creator=user,
                is_approved=True,
            )
    except IntegrityError:
        existing = external_id and Book.objects.filter(google_books_id=external_id).first()
        if existing:
            return existing, False
        raise
    return book, True


def find_duplicate(title: str, author_name: str, isbn: str = "") -> Book | None:
    code = clean_isbn(isbn)
    if code:
        by_isbn = Book.objects.filter(isbn=code).first()
        if by_isbn:
            return by_isbn
    identity = title_identity(clean_title(title))
    if not identity:
        return None
    author_key = name_key(clean_person_name(author_name))
    for candidate in Book.objects.filter(title_key__startswith=identity[: limits.TEXT_MAX_LENGTH]).select_related("author").order_by("pk"):
        candidate_key = candidate.author.name_key if candidate.author_id else ""
        if candidate_key == author_key and title_identity(candidate.title) == identity:
            return candidate
    return None


@transaction.atomic
def add_chapters(book: Book, count: int) -> list[Chapter]:
    count = min(count, settings.BULK_CHAPTERS_MAX)
    last = book.chapters.aggregate(last=Max("number"))["last"] or 0
    chapters = [Chapter(book=book, number=last + offset) for offset in range(1, count + 1)]
    return Chapter.objects.bulk_create(chapters)
