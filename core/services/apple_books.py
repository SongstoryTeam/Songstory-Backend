import re

from django.conf import settings

from .external import ExternalBook, ExternalSearch, cached_search, looks_ukrainian, strip_html
from .http import get_json

ARTWORK_SIZE = re.compile(r"/\d+x\d+bb")
MAX_DESCRIPTION = 2000


def _year(value: str) -> int | None:
    match = re.match(r"^\d{4}", value or "")
    return int(match.group()) if match else None


def _cover(url: str) -> str:
    return ARTWORK_SIZE.sub("/400x400bb", url or "")


def parse_result(item: dict) -> ExternalBook | None:
    """Apple не повертає мову книги, тому українськість визначаємо за назвою: кирилиця без російських літер."""
    title = (item.get("trackName") or "").strip()
    track_id = item.get("trackId")
    if not title or not track_id or not looks_ukrainian(title):
        return None
    return ExternalBook(
        external_id=f"apple:{track_id}",
        title=title,
        author=(item.get("artistName") or "").strip(),
        year=_year(item.get("releaseDate", "")),
        cover_url=_cover(item.get("artworkUrl100") or item.get("artworkUrl60") or ""),
        description=strip_html(item.get("description", ""))[:MAX_DESCRIPTION],
        isbn="",
    )


def search_apple_books(query: str, limit: int | None = None) -> ExternalSearch:
    limit = limit or settings.EXTERNAL_SEARCH_LIMIT

    def fetch() -> list[ExternalBook]:
        params = {
            "term": query,
            "media": "ebook",
            "entity": "ebook",
            "country": settings.APPLE_BOOKS_COUNTRY,
            "limit": settings.EXTERNAL_SEARCH_LIMIT * 2,
        }
        payload = get_json(settings.APPLE_BOOKS_API_URL, params)
        return [book for book in map(parse_result, payload.get("results", [])) if book]

    return cached_search("apple_books:ua", query, fetch, limit=limit)
