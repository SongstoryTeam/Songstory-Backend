"""Спільні типи та допоміжні функції для зовнішніх джерел книжок (Google Books, Open Library, Apple Books)."""

import hashlib
import html
import re
from collections.abc import Callable
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from core.text import search_form

from .http import ExternalServiceError

CYRILLIC = re.compile(r"[\u0400-\u04FF]")
# Літери, яких немає в українській абетці, але є в російській. Книга з такими літерами в назві — не українська.
NON_UKRAINIAN_LETTERS = re.compile(r"[ыэъёЫЭЪЁ]")
UKRAINIAN_ONLY_LETTERS = re.compile(r"[іїєґІЇЄҐ]")
# Службові слова, яких немає в українській: ловлять «Мастер и Маргарита», навіть коли в назві немає суто російських літер.
RUSSIAN_FUNCTION_WORDS = frozenset({"и", "что", "как", "это", "или", "они", "его", "мне", "всё", "ещё", "который"})
HTML_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class ExternalBook:
    external_id: str
    title: str
    author: str
    year: int | None
    cover_url: str
    description: str
    isbn: str
    original_title: str = ""


@dataclass(frozen=True)
class ExternalSearch:
    books: list[ExternalBook]
    unavailable: bool = False


def has_cyrillic(text: str) -> bool:
    return bool(CYRILLIC.search(text or ""))


def has_ukrainian_letters(text: str) -> bool:
    return bool(UKRAINIAN_ONLY_LETTERS.search(text or ""))


def looks_ukrainian(text: str) -> bool:
    """Назва кирилицею без суто російських літер і слів. Евристика для джерел, що не вказують мову книги:
    назву на кшталт «Шесть ворон» вона пропустить, бо за самими літерами її не відрізнити від української."""
    if not has_cyrillic(text) or NON_UKRAINIAN_LETTERS.search(text):
        return False
    return not RUSSIAN_FUNCTION_WORDS & set(text.casefold().split())


def strip_html(text: str) -> str:
    return " ".join(html.unescape(HTML_TAG.sub(" ", text or "")).split())


def loose_form(text: str) -> str:
    """Форма для порівняння між різними джерелами: «Бардуґо» і «Бардуго» — те саме."""
    return search_form(text).replace("ґ", "г")


def cached_search(
    namespace: str, query: str, fetch: Callable[[], list[ExternalBook]], *, limit: int
) -> ExternalSearch:
    """Кешує результати джерела, а після збою ненадовго «відпочиває», щоб не бомбардувати сервіс запитами."""
    digest = hashlib.sha1(search_form(query).encode("utf-8")).hexdigest()
    key = f"{namespace}:{digest}"
    cooldown_key = f"{namespace}:cooldown"
    cached = cache.get(key)
    if cached is not None:
        return ExternalSearch(books=cached[:limit])
    if cache.get(cooldown_key):
        return ExternalSearch(books=[], unavailable=True)
    try:
        books = fetch()
    except ExternalServiceError:
        cache.set(cooldown_key, True, settings.EXTERNAL_FAILURE_COOLDOWN)
        return ExternalSearch(books=[], unavailable=True)
    if books:
        cache.set(key, books, settings.EXTERNAL_SEARCH_CACHE_TTL)
    return ExternalSearch(books=books[:limit])
