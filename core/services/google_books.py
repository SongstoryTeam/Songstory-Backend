import re
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from core.text import normalize

from .http import ExternalServiceError, get_json

YEAR_PATTERN = re.compile(r"^\d{4}")
ISBN_TYPES = ("ISBN_13", "ISBN_10")
INSECURE_SCHEME = "http://"
SECURE_SCHEME = "https://"
CURL_PARAMETER = "&edge=curl"


@dataclass(frozen=True)
class ExternalBook:
    external_id: str
    title: str
    author: str
    year: int | None
    cover_url: str
    description: str
    isbn: str


@dataclass(frozen=True)
class ExternalSearch:
    books: list[ExternalBook]
    unavailable: bool = False


def _parse_year(value: str) -> int | None:
    match = YEAR_PATTERN.match(value or "")
    return int(match.group()) if match else None


def _parse_cover(info: dict) -> str:
    links = info.get("imageLinks") or {}
    url = links.get("thumbnail") or links.get("smallThumbnail") or ""
    return url.replace(INSECURE_SCHEME, SECURE_SCHEME).replace(CURL_PARAMETER, "")


def _parse_isbn(info: dict) -> str:
    identifiers = {item.get("type"): item.get("identifier", "") for item in info.get("industryIdentifiers", [])}
    for kind in ISBN_TYPES:
        if identifiers.get(kind):
            return identifiers[kind]
    return ""


def _parse_item(item: dict) -> ExternalBook | None:
    info = item.get("volumeInfo") or {}
    title = (info.get("title") or "").strip()
    if not title or info.get("language") != settings.CATALOG_LANGUAGE:
        return None
    return ExternalBook(
        external_id=item["id"],
        title=title,
        author=", ".join(info.get("authors") or []),
        year=_parse_year(info.get("publishedDate", "")),
        cover_url=_parse_cover(info),
        description=(info.get("description") or "").strip(),
        isbn=_parse_isbn(info),
    )


def _cache_key(query: str) -> str:
    return f"google_books:{settings.CATALOG_LANGUAGE}:{normalize(query)}"


def search_google_books(query: str, limit: int | None = None) -> ExternalSearch:
    limit = limit or settings.EXTERNAL_SEARCH_LIMIT
    key = _cache_key(query)
    cached = cache.get(key)
    if cached is not None:
        return ExternalSearch(books=cached[:limit])

    params = {
        "q": query,
        "langRestrict": settings.CATALOG_LANGUAGE,
        "printType": "books",
        "maxResults": limit,
    }
    if settings.GOOGLE_BOOKS_API_KEY:
        params["key"] = settings.GOOGLE_BOOKS_API_KEY

    try:
        payload = get_json(settings.GOOGLE_BOOKS_API_URL, params)
    except ExternalServiceError:
        return ExternalSearch(books=[], unavailable=True)

    books = [book for book in map(_parse_item, payload.get("items", [])) if book]
    cache.set(key, books, settings.EXTERNAL_SEARCH_CACHE_TTL)
    return ExternalSearch(books=books[:limit])


def get_google_book(external_id: str) -> ExternalBook | None:
    params = {"key": settings.GOOGLE_BOOKS_API_KEY} if settings.GOOGLE_BOOKS_API_KEY else None
    try:
        payload = get_json(f"{settings.GOOGLE_BOOKS_API_URL}/{external_id}", params)
    except ExternalServiceError:
        return None
    return _parse_item(payload)
