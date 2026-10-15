"""Одноразове приведення вже наявних даних до єдиного формату (див. команду normalize_catalog)."""

from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Count

from core.models import Author, Book
from core.services.normalize import clean_person_name
from core.text import name_key, search_form


@dataclass
class CatalogReport:
    authors_merged: int = 0
    authors_renamed: int = 0
    books_updated: int = 0
    duplicate_books: list[tuple[str, str]] = field(default_factory=list)


def _merge_authors(report: CatalogReport) -> None:
    groups: dict[str, list[Author]] = {}
    for author in Author.objects.order_by("pk"):
        groups.setdefault(name_key(clean_person_name(author.name)), []).append(author)

    for authors in groups.values():
        keeper, *duplicates = authors
        for duplicate in duplicates:
            Book.objects.filter(author=duplicate).update(author=keeper)
            duplicate.delete()
            report.authors_merged += 1
        cleaned = clean_person_name(keeper.name)
        if duplicates or keeper.name != cleaned or keeper.name_key != name_key(cleaned):
            if keeper.name != cleaned:
                report.authors_renamed += 1
            keeper.name = cleaned
            keeper.save()  # перебудовує name_key і search_key усіх книг автора


def _normalize_books(report: CatalogReport) -> None:
    tracked = ("title", "description", "cover_url", "isbn", "year")
    for book in Book.objects.select_related("author").iterator():
        before = {name: getattr(book, name) for name in tracked}
        book.normalize_fields()
        stale_keys = book.search_key != book.build_search_key() or book.title_key != search_form(book.title)[:255]
        if stale_keys or any(getattr(book, name) != before[name] for name in tracked):
            book.save()
            report.books_updated += 1


def _find_duplicate_books(report: CatalogReport) -> None:
    groups = (
        Book.objects.values("title_key", "author__name_key")
        .annotate(total=Count("pk"))
        .filter(total__gt=1)
        .order_by("title_key")
    )
    report.duplicate_books = [(row["title_key"], row["author__name_key"] or "") for row in groups]


@transaction.atomic
def normalize_catalog(*, dry_run: bool = False) -> CatalogReport:
    """Зливає авторів-дублікати, чистить назви й описи. Дублікати книг лише повідомляє: до них прив'язані рекомендації."""
    report = CatalogReport()
    _merge_authors(report)
    _normalize_books(report)
    _find_duplicate_books(report)
    if dry_run:
        transaction.set_rollback(True)
    return report
