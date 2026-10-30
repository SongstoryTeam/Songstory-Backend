from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from core import emails
from core.models import Author, Book, BookEditSuggestion, Genre
from core.text import name_key

from .books import find_author, find_duplicate, find_genre, get_or_create_author, get_or_create_genre
from .normalize import clean_genre_name, clean_person_name

Field = BookEditSuggestion.Field
Status = BookEditSuggestion.Status

IDENTITY_FIELDS = frozenset({Field.TITLE, Field.AUTHOR_NAME, Field.ISBN})


class SuggestionError(Exception):
    default_message = ""

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class PendingSuggestionExists(SuggestionError):
    default_message = "Ваші попередні зміни до цієї книги ще розглядаються."


class SuggestionConflict(SuggestionError):
    default_message = "Після цих змін книга дублювала б іншу книгу в каталозі."


class SuggestionAlreadyReviewed(SuggestionError):
    default_message = "Цю пропозицію вже розглянуто."


class SuggestionRevised(SuggestionError):
    default_message = "Автор змінив пропозицію, поки ви її переглядали. Перегляньте нову редакцію."


def _equivalence_key(field: str, value: Any) -> Any:
    if field == Field.AUTHOR_NAME:
        return name_key(value or "")
    if field == Field.GENRE_NAME:
        return (value or "").casefold()
    return value


def _set_author(book: Book, value: str) -> None:
    book.author = get_or_create_author(value)


def _set_genre(book: Book, value: str) -> None:
    book.genre = get_or_create_genre(value)


def _preview_author(book: Book, value: str) -> None:
    cleaned = clean_person_name(value)
    book.author = (find_author(cleaned) or Author(name=cleaned)) if cleaned else None


def _preview_genre(book: Book, value: str) -> None:
    cleaned = clean_genre_name(value)
    book.genre = (find_genre(cleaned) or Genre(name=cleaned)) if cleaned else None


Setters = dict[str, Callable[[Book, Any], None]]

PERSISTING_SETTERS: Setters = {
    Field.AUTHOR_NAME: _set_author,
    Field.GENRE_NAME: _set_genre,
}

DETACHED_SETTERS: Setters = {
    Field.AUTHOR_NAME: _preview_author,
    Field.GENRE_NAME: _preview_genre,
}


def apply_value(book: Book, field: str, value: Any, setters: Setters = PERSISTING_SETTERS) -> None:
    setter = setters.get(field)
    if setter:
        setter(book, value)
    else:
        setattr(book, field, value)


def book_snapshot(book: Book) -> dict[str, Any]:
    return {
        Field.TITLE: book.title,
        Field.AUTHOR_NAME: book.author.name if book.author_id else "",
        Field.YEAR: book.year,
        Field.GENRE_NAME: book.genre.name if book.genre_id else "",
        Field.ISBN: book.isbn,
        Field.DESCRIPTION: book.description,
        Field.COVER_URL: book.cover_url,
    }


def proposed_values(book: Book, suggestion: BookEditSuggestion) -> dict[str, Any]:
    return {**book_snapshot(book), **suggestion.new_values}


def preview(book: Book, suggestion: BookEditSuggestion) -> Book:
    for field, value in suggestion.new_values.items():
        apply_value(book, field, value, DETACHED_SETTERS)
    return book


def outdated_fields(suggestion: BookEditSuggestion | None, book: Book) -> list[str]:
    if suggestion is None:
        return []
    current = book_snapshot(book)
    labels = []
    for name, change in suggestion.changes.items():
        field = Field(name)
        present = _equivalence_key(field, current[field])
        if present not in (_equivalence_key(field, change["old"]), _equivalence_key(field, change["new"])):
            labels.append(field.label)
    return labels


def compute_changes(book: Book, values: dict[str, Any]) -> dict[str, dict[str, Any]]:
    current = book_snapshot(book)
    return {
        field.value: {"old": current[field], "new": values[field]}
        for field in Field
        if _equivalence_key(field, values[field]) != _equivalence_key(field, current[field])
    }


def touches_identity(changes: dict[str, Any]) -> bool:
    return not IDENTITY_FIELDS.isdisjoint(changes)


def find_conflicting_book(book: Book, values: dict[str, Any]) -> Book | None:
    return find_duplicate(
        values[Field.TITLE],
        values[Field.AUTHOR_NAME],
        values[Field.ISBN],
        exclude_pk=book.pk,
    )


def pending_for(user: User, book: Book) -> BookEditSuggestion | None:
    if not user.is_authenticated:
        return None
    return BookEditSuggestion.objects.select_related("book").filter(user=user, book=book, status=Status.PENDING).first()


def pending_suggestions_left(user: User) -> int | None:
    if user.is_staff:
        return None
    pending = BookEditSuggestion.objects.filter(user=user, status=Status.PENDING).count()
    return max(settings.PENDING_SUGGESTIONS_LIMIT - pending, 0)


def submit_suggestion(*, user: User, book: Book, changes: dict, reason: str = "") -> BookEditSuggestion:
    try:
        with transaction.atomic():
            suggestion = BookEditSuggestion.objects.create(book=book, user=user, changes=changes, reason=reason)
    except IntegrityError as error:
        raise PendingSuggestionExists from error
    if user.is_staff:
        return approve_suggestion(suggestion, reviewer=user, notify=False)
    emails.notify_admin_new_suggestion(suggestion)
    return suggestion


def revise_suggestion(suggestion: BookEditSuggestion, *, changes: dict, reason: str = "") -> BookEditSuggestion:
    with transaction.atomic():
        locked = _lock_pending(suggestion)
        locked.revise(changes, reason)
    return locked


def withdraw_suggestion(suggestion: BookEditSuggestion) -> BookEditSuggestion:
    with transaction.atomic():
        locked = _lock_pending(suggestion)
        locked.withdraw()
    return locked


def approve_suggestion(
        suggestion: BookEditSuggestion,
        reviewer: User,
        note: str = "",
        *,
        notify: bool = True,
        expected_revision: int | None = None,
) -> BookEditSuggestion:
    with transaction.atomic():
        locked = _lock_pending(suggestion, expected_revision)
        book = Book.objects.select_for_update(of=("self",)).select_related("author", "genre").get(pk=locked.book_id)
        merged = {**book_snapshot(book), **locked.new_values}
        if touches_identity(locked.changes) and find_conflicting_book(book, merged):
            raise SuggestionConflict
        for field, value in locked.new_values.items():
            apply_value(book, field, value)
        book.save()
        locked.book = book
        locked.close(Status.APPROVED, reviewer, note)
    if notify:
        emails.send_suggestion_approved(locked)
    return locked


def reject_suggestion(
        suggestion: BookEditSuggestion,
        reviewer: User,
        note: str = "",
        *,
        notify: bool = True,
        expected_revision: int | None = None,
) -> BookEditSuggestion:
    with transaction.atomic():
        locked = _lock_pending(suggestion, expected_revision)
        locked.close(Status.REJECTED, reviewer, note)
    if notify:
        emails.send_suggestion_rejected(locked)
    return locked


def _lock_pending(suggestion: BookEditSuggestion, expected_revision: int | None = None) -> BookEditSuggestion:
    locked = BookEditSuggestion.objects.select_for_update(of=("self",)).select_related("user", "book").get(
        pk=suggestion.pk)
    if not locked.is_pending:
        raise SuggestionAlreadyReviewed
    if expected_revision is not None and locked.revision != expected_revision:
        raise SuggestionRevised
    return locked
