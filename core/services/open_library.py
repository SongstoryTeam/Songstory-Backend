import re

from django.conf import settings

from .external import ExternalBook, ExternalSearch, cached_search
from .http import get_json

LANGUAGE_FILTER = "language:ukr"
SOLR_SPECIAL = re.compile(r'[:"()\[\]{}^~*?\\/!+\-]')
COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
FIELDS = "key,title,author_name,first_publish_year,cover_i,isbn,language,editions"
MAX_AUTHORS = 3


def _query(text: str) -> str:
    cleaned = " ".join(SOLR_SPECIAL.sub(" ", text).split())
    return f"{cleaned} {LANGUAGE_FILTER}"


def _first(values) -> str:
    if isinstance(values, list):
        return str(values[0]) if values else ""
    return str(values or "")


def _year(edition: dict, doc: dict) -> int | None:
    years = edition.get("publish_year") or []
    candidates = [year for year in years if isinstance(year, int)]
    if candidates:
        return min(candidates)
    year = doc.get("first_publish_year")
    return year if isinstance(year, int) else None


def parse_doc(doc: dict) -> ExternalBook | None:
    """Open Library шукає по «роботах» (works). Завдяки `language:ukr` у запиті в `editions` лежить саме українське видання,
    тож назва береться з нього: «Шістка воронів», а не оригінальна «Six of Crows»."""
    work_key = (doc.get("key") or "").rsplit("/", 1)[-1]
    editions = (doc.get("editions") or {}).get("docs") or []
    edition = editions[0] if editions else {}
    work_title = (doc.get("title") or "").strip()
    title = (edition.get("title") or work_title).strip()
    if not work_key or not title:
        return None
    cover_id = edition.get("cover_i") or doc.get("cover_i")
    return ExternalBook(
        external_id=f"ol:{work_key}",
        title=title,
        author=", ".join((doc.get("author_name") or [])[:MAX_AUTHORS]),
        year=_year(edition, doc),
        cover_url=COVER_URL.format(cover_id=cover_id) if cover_id else "",
        description="",
        isbn=_first(edition.get("isbn")) or _first(doc.get("isbn")),
        original_title=work_title if work_title != title else "",
    )


def search_open_library(query: str, limit: int | None = None) -> ExternalSearch:
    limit = limit or settings.EXTERNAL_SEARCH_LIMIT

    def fetch() -> list[ExternalBook]:
        params = {"q": _query(query), "fields": FIELDS, "limit": settings.EXTERNAL_SEARCH_LIMIT, "lang": "uk"}
        payload = get_json(settings.OPEN_LIBRARY_API_URL, params)
        return [book for book in map(parse_doc, payload.get("docs", [])) if book]

    return cached_search("open_library:uk", query, fetch, limit=limit)
