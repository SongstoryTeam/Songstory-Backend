from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache

_SEARCH_TTL = 60 * 60
_SEARCH_CACHE_PREFIX = "openlibrary:search:"
_API_BASE = "https://openlibrary.org"
_COVERS_BASE = "https://covers.openlibrary.org/b"

# Open Library's search index uses ISO 639-2/B codes, not the ISO 639-1
# codes our Language model stores, so callers pass the codes they know and
# the client maps them itself.
_LANGUAGE_QUERY_CODES = {"uk": "ukr"}


@dataclass(frozen=True)
class OpenLibraryBook:
    open_library_id: str
    title: str
    author: str
    year: int | None
    isbn: str
    description: str
    cover_url: str
    language: str = ""
    editions: list[str] = field(default_factory=list)


class OpenLibraryClient:
    def search(self, query: str, limit: int = 10, language: str | None = None) -> list[OpenLibraryBook]:
        cache_key = f"{_SEARCH_CACHE_PREFIX}{query.lower()}:{limit}:{language or ''}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        search_query = query
        language_code = _LANGUAGE_QUERY_CODES.get(language or "")
        if language_code:
            search_query = f"{query} language:{language_code}"

        params = urllib.parse.urlencode({
            "q": search_query,
            "limit": str(limit),
            "fields": "key,title,author_name,first_publish_year,isbn,description,cover_i,edition_key,language",
        })
        url = f"{_API_BASE}/search.json?{params}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Songstery/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data: dict[str, Any] = json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError):
            return []

        books = [
            book
            for doc in data.get("docs", [])
            if (book := self._parse_doc(doc)) is not None
        ]

        cache.set(cache_key, books, _SEARCH_TTL)
        return books

    def get_book_data(self, open_library_id: str) -> OpenLibraryBook | None:
        url = f"{_API_BASE}/works/{open_library_id}.json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Songstery/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data: dict[str, Any] = json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError):
            return None

        return self._parse_work(open_library_id, data)

    @staticmethod
    def _cover_url(cover_id: int | None, size: str = "L") -> str:
        if not cover_id:
            return ""
        return f"{_COVERS_BASE}/id/{cover_id}-{size}.jpg"

    @staticmethod
    def _extract_description(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return value.get("value", "")
        return ""

    def _parse_doc(self, doc: dict[str, Any]) -> OpenLibraryBook | None:
        key = doc.get("key", "")
        ol_id = key.split("/")[-1] if key else ""
        if not ol_id:
            return None

        isbn_list: list[str] = doc.get("isbn", [])
        return OpenLibraryBook(
            open_library_id=ol_id,
            title=doc.get("title", ""),
            author=", ".join(doc.get("author_name", [])),
            year=doc.get("first_publish_year"),
            isbn=isbn_list[0] if isbn_list else "",
            description=self._extract_description(doc.get("description", "")),
            cover_url=self._cover_url(doc.get("cover_i")),
            language=self._resolve_language(doc.get("language", [])),
            editions=doc.get("edition_key", [])[:5],
        )

    @staticmethod
    def _resolve_language(edition_language_codes: list[str]) -> str:
        """Map Open Library's ISO 639-2/B edition language codes back to
        the ISO 639-1 codes used elsewhere in the catalog. Only languages
        we can confidently recognise are returned; anything else is left
        unconfirmed rather than guessed."""
        codes_by_iso1 = {code: iso1 for iso1, code in _LANGUAGE_QUERY_CODES.items()}
        for code in edition_language_codes:
            if code in codes_by_iso1:
                return codes_by_iso1[code]
        return ""

    def _parse_work(self, ol_id: str, data: dict[str, Any]) -> OpenLibraryBook:
        covers = data.get("covers", [])
        return OpenLibraryBook(
            open_library_id=ol_id,
            title=data.get("title", ""),
            author="",
            year=None,
            isbn="",
            description=self._extract_description(data.get("description", "")),
            cover_url=self._cover_url(covers[0] if covers else None),
        )


open_library_client = OpenLibraryClient()