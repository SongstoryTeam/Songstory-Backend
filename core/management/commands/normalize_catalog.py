from django.core.management.base import BaseCommand

from core.services.maintenance import normalize_catalog


class Command(BaseCommand):
    help = "Приводить наявні книги й авторів до єдиного формату: зливає дублікати авторів, чистить назви та описи"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="лише показати, що зміниться, нічого не зберігаючи")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        report = normalize_catalog(dry_run=dry_run)
        prefix = "[пробний запуск, нічого не збережено] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}Авторів злито: {report.authors_merged}, перейменовано: {report.authors_renamed}"))
        self.stdout.write(self.style.SUCCESS(f"{prefix}Книг оновлено: {report.books_updated}"))
        if report.duplicate_books:
            self.stdout.write(self.style.WARNING(f"Схожі книги (перевірте вручну в адмінці): {len(report.duplicate_books)}"))
            for title_key, author_key in report.duplicate_books:
                self.stdout.write(f"    {title_key} — {author_key or 'без автора'}")
