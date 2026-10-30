from django.db import models
from django.db.models import QuerySet

from core import audit
from core.models import Book, Recommendation
from staffpanel.access import Permission
from staffpanel.actions import Action, registry
from staffpanel.services.common import pks, related_count


class BookState(models.TextChoices):
    PENDING = "pending", "На перевірці"
    APPROVED = "approved", "Опубліковані"
    ALL = "all", "Усі"


DEFAULT_STATE = BookState.PENDING

_STATE_FILTERS = {
    BookState.PENDING: {"is_approved": False},
    BookState.APPROVED: {"is_approved": True},
    BookState.ALL: {},
}


def book_queryset(*, state: str, query: str) -> QuerySet[Book]:
    state = BookState(state) if state in BookState.values else DEFAULT_STATE
    queryset = Book.objects.search(query) if query else Book.objects.all()
    queryset = (
        queryset.filter(**_STATE_FILTERS[state])
        .select_related("author", "genre", "creator")
        .annotate(recommendations_total=related_count(Recommendation, "book"))
    )
    if query:
        return queryset
    ordering = ("created_at", "pk") if state is BookState.PENDING else ("-created_at", "-pk")
    return queryset.order_by(*ordering)


def _is_pending(book: Book, actor) -> bool:
    return not book.is_approved


def _is_published(book: Book, actor) -> bool:
    return book.is_approved


def _set_approved(value: bool):
    def apply(books: list[Book]) -> None:
        Book.objects.filter(pk__in=pks(books)).update(is_approved=value)

    return apply


def _delete(books: list[Book]) -> None:
    Book.objects.filter(pk__in=pks(books)).delete()


BOOK_ACTIONS = registry(
    Action(
        key="approve",
        label="Схвалити",
        icon="check",
        permission=Permission.BOOKS_CHANGE,
        flag=audit.CHANGE,
        log_message="Книгу схвалено",
        done_message="Схвалено книг: {count}.",
        apply=_set_approved(True),
        eligible=_is_pending,
    ),
    Action(
        key="hide",
        label="Приховати",
        icon="eye-off",
        permission=Permission.BOOKS_CHANGE,
        flag=audit.CHANGE,
        log_message="Книгу приховано з каталогу",
        done_message="Приховано книг: {count}.",
        apply=_set_approved(False),
        eligible=_is_published,
    ),
    Action(
        key="delete",
        label="Видалити",
        icon="trash-2",
        permission=Permission.BOOKS_DELETE,
        flag=audit.DELETION,
        log_message="Книгу видалено",
        done_message="Видалено книг: {count}.",
        apply=_delete,
        danger=True,
        confirm_title="Видалити книги?",
        confirm_message="Разом із книгою назавжди зникнуть її розділи, рекомендації, плейлисти та коментарі.",
    ),
)
