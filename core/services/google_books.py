import hashlib
import re
import time

from django.conf import settings
from django.core.cache import cache

from core.text import search_form

from .external import ExternalBook, ExternalSearch
from .http import ExternalServiceError, get_json

YEAR_PATTERN = re.compile(r"^\d{4}")
ISBN_TYPES = ("ISBN_13", "ISBN_10")
INSECURE_SCHEME = "http://"
SECURE_SCHEME = "https://"
CURL_PARAMETER = "&edge=curl"
SERVER_ERROR_FROM = 500
RETRY_DELAY = 0.4
# Параметри, без яких Google іноді відповідає там, де з ними дає 503.
OPTIONAL_PARAMS = ("langRestrict", "printType")


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


def parse_volume(item: dict) -> ExternalBook | None:
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


def book_key(book: "ExternalBook") -> str:
    return search_form(f"{book.title} {book.author}")


def _dedupe(books: list[ExternalBook]) -> list[ExternalBook]:
    unique: dict[str, ExternalBook] = {}
    for book in books:
        key = book_key(book)
        current = unique.get(key)
        if current is None or (not current.cover_url and book.cover_url):
            unique[key] = book
    return list(unique.values())


def _cache_key(query: str) -> str:
    digest = hashlib.sha1(search_form(query).encode("utf-8")).hexdigest()
    return f"google_books:{settings.CATALOG_LANGUAGE}:{digest}"


def _fetch_with_retry(params: dict) -> dict:
    """Google Books час від часу віддає 503 backendFailed без причини. Повторюємо запит, а останню спробу робимо без
    langRestrict/printType: мову все одно перевіряє parse_volume. Помилки клієнта (400, 403, 429) не повторюємо."""
    fallback = {name: value for name, value in params.items() if name not in OPTIONAL_PARAMS}
    attempts = [params, params, fallback]
    for index, attempt in enumerate(attempts):
        try:
            return get_json(settings.GOOGLE_BOOKS_API_URL, attempt)
        except ExternalServiceError as exc:
            retryable = exc.status is not None and exc.status >= SERVER_ERROR_FROM
            if not retryable or index == len(attempts) - 1:
                raise
            time.sleep(RETRY_DELAY)
    raise AssertionError("unreachable")


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
        "maxResults": settings.EXTERNAL_SEARCH_LIMIT,
    }
    if settings.GOOGLE_BOOKS_API_KEY:
        params["key"] = settings.GOOGLE_BOOKS_API_KEY

    try:
        payload = _fetch_with_retry(params)
    except ExternalServiceError:
        return ExternalSearch(books=[], unavailable=True)

    books = _dedupe([book for book in map(parse_volume, payload.get("items", [])) if book])
    if books:
        cache.set(key, books, settings.EXTERNAL_SEARCH_CACHE_TTL)
    return ExternalSearch(books=books[:limit])


def get_google_book(external_id: str) -> ExternalBook | None:
    params = {"key": settings.GOOGLE_BOOKS_API_KEY} if settings.GOOGLE_BOOKS_API_KEY else None
    try:
        payload = get_json(f"{settings.GOOGLE_BOOKS_API_URL}/{external_id}", params)
    except ExternalServiceError:
        return None
    return parse_volume(payload)
