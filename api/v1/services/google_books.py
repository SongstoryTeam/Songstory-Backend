from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache

API_BASE = "https://www.googleapis.com/books/v1/volumes"
REQUEST_TIMEOUT = 10
SEARCH_CACHE_TTL = 60 * 60
SEARCH_CACHE_PREFIX = "googlebooks:search:"
USER_AGENT = "Songstery/1.0"


@dataclass(frozen=True)
class GoogleBook:
    external_id: str
    title: str
    author: str
    year: int | None
    isbn: str
    description: str
    cover_url: str
    language: str


class GoogleBooksClient:
    def search(self, query: str, limit: int = 10) -> list[GoogleBook]:
        cache_key = f"{SEARCH_CACHE_PREFIX}{query.lower()}:{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        data = self._fetch(query, limit)
        books = [
            book
            for item in data.get("items", [])
            if (book := self._parse_item(item)) is not None
        ]

        cache.set(cache_key, books, SEARCH_CACHE_TTL)
        return books

    def _fetch(self, query: str, limit: int) -> dict[str, Any]:
        params = {"q": query, "maxResults": str(limit)}
        api_key = getattr(settings, "GOOGLE_BOOKS_API_KEY", "")
        if api_key:
            params["key"] = api_key

        url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, urllib.error.HTTPError):
            return {}

    @staticmethod
    def _parse_item(item: dict[str, Any]) -> GoogleBook | None:
        info = item.get("volumeInfo", {})
        title = info.get("title", "")
        if not title:
            return None

        isbn = ""
        for identifier in info.get("industryIdentifiers", []):
            if identifier.get("type") in ("ISBN_13", "ISBN_10"):
                isbn = identifier["identifier"]
                break

        year = None
        published_date = info.get("publishedDate", "")
        if published_date[:4].isdigit():
            year = int(published_date[:4])

        cover_url = info.get("imageLinks", {}).get("thumbnail", "")

        return GoogleBook(
            external_id=item.get("id", ""),
            title=title,
            author=", ".join(info.get("authors", [])),
            year=year,
            isbn=isbn,
            description=info.get("description", ""),
            cover_url=cover_url.replace("http://", "https://"),
            language=info.get("language", ""),
        )


google_books_client = GoogleBooksClient()
