import time

from django.conf import settings
from django.core.management.base import BaseCommand

from core.services.apple_books import search_apple_books
from core.services.book_search import search_books
from core.services.google_books import search_google_books
from core.services.http import ExternalServiceError, get_json
from core.services.open_library import search_open_library

DEFAULT_QUERY = "Шістка воронів"
PREVIEW_LIMIT = 3
RAW_LIMIT = 6


class Command(BaseCommand):
    help = "Перевіряє кожне джерело пошуку книг окремо та підсумкову видачу: скільки знайшлось і за який час"

    def add_arguments(self, parser):
        parser.add_argument("query", nargs="?", default=DEFAULT_QUERY)

    def handle(self, *args, **options):
        query = options["query"]
        self.stdout.write(f"Запит: {query!r}")
        self.stdout.write(f"Джерела з налаштувань: {', '.join(settings.BOOK_SOURCES) or 'немає'}")
        if not settings.GOOGLE_BOOKS_API_KEY:
            self.stdout.write(self.style.WARNING("GOOGLE_BOOKS_API_KEY не задано: Google Books буде пропущено\n"))

        self.dump_google_raw(query)
        self.report("Google Books", search_google_books, query)
        self.report("Open Library", search_open_library, query)
        self.report("Apple Books", search_apple_books, query)
        self.report("РАЗОМ (після злиття і ранжування)", search_books, query)

    def report(self, label: str, function, query: str) -> None:
        started = time.monotonic()
        result = function(query)
        elapsed = time.monotonic() - started
        if result.unavailable:
            self.stdout.write(self.style.ERROR(f"[{label}] недоступне ({elapsed:.1f} с). Деталі в логах: DJANGO_LOG_LEVEL=INFO"))
            return
        style = self.style.SUCCESS if result.books else self.style.WARNING
        self.stdout.write(style(f"[{label}] знайдено {len(result.books)} ({elapsed:.1f} с)"))
        for book in result.books[:PREVIEW_LIMIT]:
            cover = "є обкладинка" if book.cover_url else "без обкладинки"
            self.stdout.write(f"    {book.title} — {book.author or '—'} ({book.year or '—'}), {cover}, id={book.external_id}")

    def dump_google_raw(self, query: str) -> None:
        """Сирі відповіді Google до будь-яких наших фільтрів: видно, які мови й підзаголовки він віддає насправді."""
        if not settings.GOOGLE_BOOKS_API_KEY:
            return
        params = {"q": query, "printType": "books", "maxResults": 10, "key": settings.GOOGLE_BOOKS_API_KEY}
        try:
            payload = get_json(settings.GOOGLE_BOOKS_API_URL, params)
        except ExternalServiceError as exc:
            self.stdout.write(self.style.ERROR(f"[Google, сирі дані] помилка: HTTP {exc.status or '—'} {exc.detail}"))
            return
        items = payload.get("items", [])
        self.stdout.write(f"[Google, сирі дані без фільтрів] отримано {len(items)}")
        for item in items[:RAW_LIMIT]:
            info = item.get("volumeInfo") or {}
            authors = ", ".join(info.get("authors") or []) or "—"
            self.stdout.write(
                f"    {info.get('title')!r} | підзаголовок: {info.get('subtitle')!r} | мова: {info.get('language')} | {authors}"
            )
        self.stdout.write("")
