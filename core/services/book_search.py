"""Єдиний зовнішній пошук книг: опитує кілька безкоштовних джерел паралельно, зливає дублікати й ранжує результати."""

import logging
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import replace

from django.conf import settings
from django.core.cache import cache

from core.text import search_terms, title_identity

from .apple_books import search_apple_books
from .external import ExternalBook, ExternalSearch, has_cyrillic, has_ukrainian_letters, loose_form
from .google_books import get_google_book, search_google_books
from .open_library import search_open_library

logger = logging.getLogger(__name__)

SHORT_TERM = 4
INFLECTION_TAIL = 2
EXACT_TITLE_SCORE = 100
PREFIX_TITLE_SCORE = 70
PHRASE_TITLE_SCORE = 60
ALL_TERMS_SCORE = 50
PARTIAL_TERMS_SCORE = 20
COVER_BONUS = 8
UKRAINIAN_LETTERS_BONUS = 6
CYRILLIC_AUTHOR_BONUS = 3
NO_AUTHOR_PENALTY = 10
EXTERNAL_ID_SEPARATOR = ":"
SOURCE_LABELS = {"google": "Google Books", "openlibrary": "Open Library", "apple": "Apple Books"}


def _providers() -> list[tuple[str, callable]]:
    """Список (назва, функція пошуку) у порядку з BOOK_SOURCES. Google без ключа пропускаємо."""
    available = {"google": search_google_books, "openlibrary": search_open_library, "apple": search_apple_books}
    selected = []
    for name in settings.BOOK_SOURCES:
        if name not in available:
            continue
        if name == "google" and not settings.GOOGLE_BOOKS_API_KEY:
            continue
        selected.append((name, available[name]))
    return selected


def _run_parallel(providers: list[tuple[str, callable]], query: str) -> list[ExternalSearch | None]:
    """Опитує всі джерела одночасно, тож час відповіді дорівнює найповільнішому, а не сумі. Збій одного не ламає решту."""
    pool = ThreadPoolExecutor(max_workers=len(providers))
    futures = [pool.submit(function, query) for _, function in providers]
    done, _ = wait(futures, timeout=settings.EXTERNAL_HTTP_TIMEOUT + 2)
    pool.shutdown(wait=False, cancel_futures=True)
    results: list[ExternalSearch | None] = []
    for (name, _), future in zip(providers, futures):
        if future not in done:
            logger.warning("Book source %s timed out", name)
            results.append(None)
            continue
        try:
            results.append(future.result())
        except Exception:  # noqa: BLE001 — один зламаний провайдер не повинен ламати весь пошук
            logger.exception("Book source %s crashed", name)
            results.append(None)
    return results


def _stem(term: str) -> str:
    """Грубе відсікання закінчення, щоб «воронів» знаходило «Ворони», а «шістка» — «Шістку»."""
    return term if len(term) <= SHORT_TERM else term[:-INFLECTION_TAIL]


def _haystack(book: ExternalBook) -> str:
    return loose_form(f"{book.title} {book.original_title} {book.author}")


def _matched_terms(book: ExternalBook, terms: list[str]) -> int:
    haystack = _haystack(book)
    return sum(1 for term in terms if _stem(term) in haystack)


def _is_relevant(book: ExternalBook, terms: list[str]) -> bool:
    return _matched_terms(book, terms) >= max(1, (len(terms) + 1) // 2)


def _score(book: ExternalBook, terms: list[str]) -> int:
    phrase = " ".join(terms)
    title = loose_form(book.title)
    if title == phrase:
        score = EXACT_TITLE_SCORE
    elif title.startswith(phrase):
        score = PREFIX_TITLE_SCORE
    elif phrase in title:
        score = PHRASE_TITLE_SCORE
    elif all(_stem(term) in title for term in terms):
        score = ALL_TERMS_SCORE
    else:
        score = PARTIAL_TERMS_SCORE * _matched_terms(book, terms) // len(terms)
    if book.cover_url:
        score += COVER_BONUS
    if has_ukrainian_letters(book.title):
        score += UKRAINIAN_LETTERS_BONUS
    if has_cyrillic(book.author):
        score += CYRILLIC_AUTHOR_BONUS
    if not book.author:
        score -= NO_AUTHOR_PENALTY
    return score


def _authors_compatible(first: str, second: str) -> bool:
    """Автори збігаються, якщо порожні, мають спільне слово або записані різними абетками («Лі Бардуго» і «Leigh Bardugo»)."""
    if not first or not second:
        return True
    first_tokens = {token for token in loose_form(first).split() if len(token) > 2}
    second_tokens = {token for token in loose_form(second).split() if len(token) > 2}
    if first_tokens & second_tokens:
        return True
    return has_cyrillic(first) != has_cyrillic(second)


def _quality(book: ExternalBook) -> tuple[bool, bool, bool]:
    return bool(book.cover_url), has_cyrillic(book.author), bool(book.description)


def _merge(first: ExternalBook, second: ExternalBook) -> ExternalBook:
    primary, other = (first, second) if _quality(first) >= _quality(second) else (second, first)
    # Назва кирилицею важливіша за якість запису: читач шукає українською. Іншу назву лишаємо як оригінальну.
    title, alternative = primary.title, other.title
    if has_cyrillic(other.title) and not has_cyrillic(primary.title):
        title, alternative = other.title, primary.title
    original = primary.original_title or other.original_title
    if not original and loose_form(alternative) != loose_form(title):
        original = alternative
    return replace(
        primary,
        title=title,
        author=primary.author or other.author,
        year=primary.year or other.year,
        cover_url=primary.cover_url or other.cover_url,
        description=primary.description or other.description,
        isbn=primary.isbn or other.isbn,
        original_title=original,
    )


def _same_book(first: ExternalBook, second: ExternalBook) -> bool:
    """Той самий ISBN, або та сама назва (з точністю до «Кн. 1») і сумісні автори."""
    if first.isbn and first.isbn == second.isbn:
        return True
    return title_identity(first.title) == title_identity(second.title) and _authors_compatible(first.author, second.author)


def _merge_duplicates(books: list[ExternalBook]) -> list[ExternalBook]:
    merged: list[ExternalBook] = []
    for book in books:
        for index, existing in enumerate(merged):
            if _same_book(existing, book):
                merged[index] = _merge(existing, book)
                break
        else:
            merged.append(book)
    return merged


def _book_cache_key(external_id: str) -> str:
    return f"external_book:{external_id}"


def _remember(books: list[ExternalBook]) -> None:
    cache.set_many({_book_cache_key(book.external_id): book for book in books}, settings.EXTERNAL_BOOK_CACHE_TTL)


def search_books(query: str, limit: int | None = None) -> ExternalSearch:
    limit = limit or settings.EXTERNAL_SEARCH_LIMIT
    terms = [loose_form(term) for term in search_terms(query)]
    providers = _providers()
    if not terms or not providers:
        return ExternalSearch(books=[], unavailable=not providers)

    results = _run_parallel(providers, query)
    collected = [book for result in results if result for book in result.books]
    candidates = [book for book in _merge_duplicates(collected) if _is_relevant(book, terms)]
    # sorted() стабільний: за однакового балу лишається порядок джерел із налаштувань.
    ranked = sorted(candidates, key=lambda book: -_score(book, terms))[:limit]
    _remember(ranked)
    failed = tuple(
        SOURCE_LABELS[name] for (name, _), result in zip(providers, results) if result is None or result.unavailable
    )
    all_failed = len(failed) == len(providers)
    return ExternalSearch(books=ranked, unavailable=all_failed and not ranked, failed=failed)


def get_external_book(external_id: str) -> ExternalBook | None:
    """Книга для імпорту: спершу з кешу пошуку (працює для всіх джерел), інакше напряму з Google за «голим» id."""
    if not external_id:
        return None
    cached = cache.get(_book_cache_key(external_id))
    if cached is not None:
        return cached
    if EXTERNAL_ID_SEPARATOR in external_id:
        return None
    return get_google_book(external_id)
