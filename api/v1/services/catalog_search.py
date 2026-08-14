from __future__ import annotations

import re
from dataclasses import dataclass, replace

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db.models import Q
from django.urls import reverse

from core.models import Book

from .google_books import GoogleBook, google_books_client
from .open_library import OpenLibraryBook, open_library_client
from .translation import needs_translation, translate_to_english

# The catalog itself is Ukrainian-first (every Book has translated title
# fields), so a same-language *edition* is always preferred when one
# exists in the external catalogs too. It rarely does — see _search_external
# for how a query that only matches an English edition is still surfaced,
# instead of silently returning nothing.
SEARCH_LANGUAGE = "uk"

CATALOG_SOURCE = "catalog"
GOOGLE_BOOKS_SOURCE = "google_books"
OPEN_LIBRARY_SOURCE = "open_library"

# Google Books volume ids and Open Library work ids share the same
# namespace on Book.open_library_id, so Google ids are prefixed to keep
# them unambiguous. Shared with the legacy /api/search/books/ endpoint.
GOOGLE_BOOKS_ID_PREFIX = "gbooks:"

QUICK_SEARCH_LIMIT = 6
RESULTS_PAGE_LIMIT = 24
MIN_QUERY_LENGTH = 2

_TITLE_NOISE_RE = re.compile(r"[^\w\s]", re.UNICODE)


@dataclass(frozen=True)
class SearchResult:
    source: str
    title: str
    author: str
    year: int | None
    cover_url: str
    description: str
    isbn: str
    in_catalog: bool
    url: str | None
    external_id: str | None = None
    # True when this result was only found by translating the user's
    # (Ukrainian) query to English before querying the external catalog —
    # i.e. it's very likely an English edition, not a Ukrainian one, even
    # though it's a genuine match for what the person typed. The template
    # uses this to label the result honestly instead of implying it's a
    # Ukrainian-language match.
    matched_via_translation: bool = False


def search_books(
    query: str,
    limit: int = QUICK_SEARCH_LIMIT,
    user: AbstractBaseUser | AnonymousUser | None = None,
) -> list[SearchResult]:
    """Search the local catalog first, then fill remaining slots with
    results from external book catalogs, skipping anything that clearly
    duplicates a catalog match by title."""
    query = query.strip()
    if len(query) < MIN_QUERY_LENGTH:
        return []

    catalog_results = _search_catalog(query, limit, user)
    remaining = limit - len(catalog_results)
    if remaining <= 0:
        return catalog_results[:limit]

    seen_titles = {_normalize_title(result.title) for result in catalog_results}
    external_results = _search_external(query, remaining, seen_titles)

    return [*catalog_results, *external_results][:limit]


def _search_catalog(query: str, limit: int, user: AbstractBaseUser | AnonymousUser | None) -> list[SearchResult]:
    books_qs = Book.published.all()
    if user is not None and user.is_authenticated and user.is_staff:
        books_qs = Book.objects.all()

    books_qs = (
        books_qs.filter(_catalog_query_filter(query))
        .select_related("author")
        .distinct()[:limit]
    )

    return [
        SearchResult(
            source=CATALOG_SOURCE,
            title=book.get_title(),
            author=book.get_author_name(),
            year=book.year,
            cover_url=book.get_cover() or "",
            description=book.get_description(),
            isbn=book.isbn,
            in_catalog=True,
            url=book.get_absolute_url(),
            external_id=book.open_library_id or None,
        )
        for book in books_qs
    ]


def _search_external(query: str, limit: int, exclude_titles: set[str]) -> list[SearchResult]:
    """External lookup against Google Books / Open Library, in two passes.

    Pass 1 searches the query exactly as typed, restricted to
    confirmed-or-unconfirmed Ukrainian editions (existing behaviour) — this
    catches the rare case where a Ukrainian edition is indexed under its
    Ukrainian title.

    Pass 2 only runs if pass 1 didn't fill the slots *and* the query looks
    Ukrainian (contains Cyrillic): the query is translated to English and
    searched again, this time without a language restriction. This is what
    actually finds a book when someone searches "Переслідування аделіни"
    for a work that's only indexed as "Hunting Adeline" — previously that
    query matched nothing at all, because Google Books/Open Library metadata
    is overwhelmingly English and a literal Cyrillic query has nothing to
    match against.

    Pass-2 results are flagged with matched_via_translation so the template
    can be upfront that they're a translated match, not a Ukrainian edition.
    """
    seen_titles = set(exclude_titles)

    results = _run_external_pass(query, limit, seen_titles, language=SEARCH_LANGUAGE)
    seen_titles.update(_normalize_title(result.title) for result in results)

    remaining = limit - len(results)
    if remaining > 0 and needs_translation(query):
        translated = translate_to_english(query)
        if translated and _normalize_title(translated) != _normalize_title(query):
            translated_results = _run_external_pass(
                translated, remaining, seen_titles, language=None, via_translation=True
            )
            results += translated_results

    return results[:limit]


def _run_external_pass(
    query: str,
    limit: int,
    exclude_titles: set[str],
    language: str | None,
    via_translation: bool = False,
) -> list[SearchResult]:
    google_books = google_books_client.search(query, limit=limit, language=language)
    open_library_books = open_library_client.search(query, limit=limit, language=language)
    candidates = [
        _to_search_result(book, via_translation) for book in (*google_books, *open_library_books)
    ]

    catalogued_by_id = _lookup_catalogued(
        [result.external_id for result in candidates if result.external_id]
    )

    results: list[SearchResult] = []
    seen_titles = set(exclude_titles)

    for result in candidates:
        title_key = _normalize_title(result.title)
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        slug = catalogued_by_id.get(result.external_id)
        if slug:
            result = replace(
                result,
                in_catalog=True,
                url=reverse("core:book_detail_slug", kwargs={"slug": slug}),
            )

        results.append(result)

    return results[:limit]


def _lookup_catalogued(external_ids: list[str]) -> dict[str, str]:
    if not external_ids:
        return {}
    return dict(
        Book.objects.filter(open_library_id__in=external_ids).values_list("open_library_id", "slug")
    )


def _to_search_result(book: GoogleBook | OpenLibraryBook, via_translation: bool = False) -> SearchResult:
    if isinstance(book, GoogleBook):
        return SearchResult(
            source=GOOGLE_BOOKS_SOURCE,
            external_id=f"{GOOGLE_BOOKS_ID_PREFIX}{book.external_id}",
            title=book.title,
            author=book.author,
            year=book.year,
            cover_url=book.cover_url,
            description=book.description,
            isbn=book.isbn,
            in_catalog=False,
            url=None,
            matched_via_translation=via_translation,
        )

    return SearchResult(
        source=OPEN_LIBRARY_SOURCE,
        external_id=book.open_library_id,
        title=book.title,
        author=book.author,
        year=book.year,
        cover_url=book.cover_url,
        description=book.description,
        isbn=book.isbn,
        in_catalog=False,
        url=None,
        matched_via_translation=via_translation,
    )


def _catalog_query_filter(query: str) -> Q:
    """Match if every word in the query shows up somewhere in the title or
    the author's name — not necessarily in the same order or the same
    field. A strict whole-phrase substring match previously failed on
    anything typed in a different word order than the title itself."""
    words = [word for word in query.split() if word]
    if not words:
        return Q(pk__in=[])

    combined = Q()
    for word in words:
        combined &= Q(translations__title__icontains=word) | Q(author__translations__name__icontains=word)
    return combined


def _normalize_title(title: str) -> str:
    return _TITLE_NOISE_RE.sub("", title).strip().lower()
