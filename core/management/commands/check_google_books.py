from django.conf import settings
from django.core.management.base import BaseCommand

from core.services.google_books import parse_volume
from core.services.http import ExternalServiceError, get_json

KEY_PREVIEW_HEAD = 4
KEY_PREVIEW_TAIL = 2
SAMPLE_SIZE = 3
DEFAULT_QUERY = "Кобзар"


def describe_key(key: str) -> str:
    if not key:
        return "НЕ ЗАДАНО (змінна GOOGLE_BOOKS_API_KEY порожня)"
    preview = f"{key[:KEY_PREVIEW_HEAD]}…{key[-KEY_PREVIEW_TAIL:]}"
    return f"задано ({preview}, {len(key)} символів)"


class Command(BaseCommand):
    help = "Перевіряє доступ до Google Books API: ключ, відповідь сервера та фільтр мови"

    def add_arguments(self, parser):
        parser.add_argument("query", nargs="?", default=DEFAULT_QUERY)

    def handle(self, *args, **options):
        query = options["query"]
        key = settings.GOOGLE_BOOKS_API_KEY
        self.stdout.write(f"Адреса: {settings.GOOGLE_BOOKS_API_URL}")
        self.stdout.write(f"Ключ: {describe_key(key)}")
        self.stdout.write(f"Запит: {query!r}, мова: {settings.CATALOG_LANGUAGE}\n")

        attempts = [("без ключа", {})]
        if key:
            attempts.append(("з ключем", {"key": key}))

        for label, extra in attempts:
            params = {
                "q": query,
                "langRestrict": settings.CATALOG_LANGUAGE,
                "printType": "books",
                "maxResults": settings.EXTERNAL_SEARCH_LIMIT,
                **extra,
            }
            self.report(label, params)

    def report(self, label: str, params: dict) -> None:
        try:
            payload = get_json(settings.GOOGLE_BOOKS_API_URL, params)
        except ExternalServiceError as exc:
            status = f"HTTP {exc.status}" if exc.status else "немає відповіді"
            self.stdout.write(self.style.ERROR(f"[{label}] ПОМИЛКА: {status}. {exc.detail or exc}"))
            return

        items = payload.get("items", [])
        parsed = [book for book in map(parse_volume, items) if book]
        line = f"[{label}] OK: від Google {len(items)}, після фільтра мови {len(parsed)}"
        self.stdout.write(self.style.SUCCESS(line))
        for book in parsed[:SAMPLE_SIZE]:
            self.stdout.write(f"    {book.title} — {book.author or '—'} ({book.year or '—'})")
