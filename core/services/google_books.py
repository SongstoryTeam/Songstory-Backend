import hashlib
import re
import time

from django.conf import settings
from django.core.cache import cache

from core.text import search_form

from .external import ExternalBook, ExternalSearch, has_ukrainian_letters, looks_ukrainian
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
# Якщо з langRestrict знайшлося менше книг, шукаємо ще раз без нього: Google часто не ставить мову або ставить хибну.
SPARSE_RESULTS = 3
# Підзаголовки-жанри не є частиною назви: «Тигролови. Роман» мало б збігатися з «Тигролови».
GENERIC_SUBTITLES = frozenset(
    {"роман", "повість", "оповідання", "збірка", "поезії", "вірші", "поема", "казка", "казки", "п єса", "novel", "a novel", "stories", "poems"}
)


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


def _full_title(info: dict) -> str:
    """Українські видання серій записують так: title «Кров і попіл», subtitle «Книга 1. Із крові й попелу»."""
    title = (info.get("title") or "").strip()
    subtitle = (info.get("subtitle") or "").strip()
    folded = search_form(subtitle)
    if not subtitle or folded in GENERIC_SUBTITLES or folded in search_form(title):
        return title
    return f"{title}. {subtitle}"


def _is_ukrainian_volume(info: dict, title: str) -> bool:
    language = info.get("language") or ""
    if language == settings.CATALOG_LANGUAGE:
        return True
    if language in ("", "und"):
        return looks_ukrainian(title)
    # Мова позначена хибно (наприклад, «ru»), але в назві є суто українські літери: це українське видання.
    return has_ukrainian_letters(title) and looks_ukrainian(title)


def parse_volume(item: dict) -> ExternalBook | None:
    info = item.get("volumeInfo") or {}
    title = _full_title(info)
    if not title or not _is_ukrainian_volume(info, title):
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
    if len(books) < SPARSE_RESULTS:
        books = _dedupe(books + _search_without_language(params))
    if books:
        cache.set(key, books, settings.EXTERNAL_SEARCH_CACHE_TTL)
    return ExternalSearch(books=books[:limit])


def _search_without_language(params: dict) -> list[ExternalBook]:
    """Другий прохід без langRestrict. Мову все одно перевіряє parse_volume, тож чужі книги не пролізуть."""
    loose = {name: value for name, value in params.items() if name != "langRestrict"}
    try:
        payload = _fetch_with_retry(loose)
    except ExternalServiceError:
        return []
    return [book for book in map(parse_volume, payload.get("items", [])) if book]


def get_google_book(external_id: str) -> ExternalBook | None:
    params = {"key": settings.GOOGLE_BOOKS_API_KEY} if settings.GOOGLE_BOOKS_API_KEY else None
    try:
        payload = get_json(f"{settings.GOOGLE_BOOKS_API_URL}/{external_id}", params)
    except ExternalServiceError:
        return None
    return parse_volume(payload)
