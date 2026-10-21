from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, Q

from core.models import Book, Genre

from .books import find_duplicate
from .external import ExternalBook


SORT_OPTIONS = {
    "new": ("Нові", ("-created_at", "-pk")),
    "popular": ("За рекомендаціями", ("-recommendations_total", "-created_at")),
    "title": ("За назвою", ("title",)),
}
DEFAULT_SORT = "new"


def visible_books(user):
    return Book.objects.visible_to(user).select_related("author", "genre")


def home_shelves(user) -> list[dict]:
    size = settings.HOME_SHELF_SIZE
    base = visible_books(user).with_recommendation_count()
    return [
        {"key": "new", "title": "Нові в каталозі", "books": list(base.order_by("-created_at", "-pk")[:size])},
        {
            "key": "popular",
            "title": "Найбільше рекомендацій",
            "books": list(base.filter(recommendations_total__gt=0).order_by("-recommendations_total", "-created_at")[:size]),
        },
        {
            "key": "empty",
            "title": "Ще без музики — додайте першу",
            "books": list(base.filter(recommendations_total=0).order_by("-created_at", "-pk")[:size]),
        },
    ]


def catalog_page(user, *, genre_slug: str, sort: str, page_number: str | int):
    sort_key = sort if sort in SORT_OPTIONS else DEFAULT_SORT
    queryset = visible_books(user).with_recommendation_count()
    if genre_slug:
        queryset = queryset.filter(genre__slug=genre_slug)
    queryset = queryset.order_by(*SORT_OPTIONS[sort_key][1])
    page = Paginator(queryset, settings.CATALOG_PAGE_SIZE).get_page(page_number)
    return page, sort_key


def genres_in_use():
    return Genre.objects.annotate(books_total=Count("books", filter=Q(books__is_approved=True))).filter(books_total__gt=0)


def search_local(user, query: str, limit: int):
    return list(visible_books(user).search(query)[:limit])


def exclude_known(items: list[ExternalBook]) -> list[ExternalBook]:
    if not items:
        return []
    known_ids = set(
        Book.objects.filter(google_books_id__in=[item.external_id for item in items]).values_list(
            "google_books_id", flat=True
        )
    )
    return [
        item
        for item in items
        if item.external_id not in known_ids and find_duplicate(item.title, item.author, item.isbn) is None
    ]
