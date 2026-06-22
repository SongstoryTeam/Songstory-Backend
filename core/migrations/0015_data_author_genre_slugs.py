from django.db import migrations
from django.utils.text import slugify as django_slugify


def _safe_slug(text: str, seen: set, prefix: str = "") -> str:
    base = django_slugify((prefix + text) or "item")[:48] or "item"
    slug = base
    counter = 2
    while slug in seen:
        slug = f"{base}-{counter}"
        counter += 1
    seen.add(slug)
    return slug


def forward(apps, schema_editor):
    Book = apps.get_model("core", "Book")
    Playlist = apps.get_model("core", "Playlist")
    Author = apps.get_model("core", "Author")
    AuthorTranslation = apps.get_model("core", "AuthorTranslation")
    Genre = apps.get_model("core", "Genre")
    GenreTranslation = apps.get_model("core", "GenreTranslation")
    Language = apps.get_model("core", "Language")

    uk = Language.objects.get(code="uk")

    for book in Book.objects.all():
        book.author_legacy = book.author if isinstance(book.author, str) else ""
        book.genre_legacy = book.genre if isinstance(book.genre, str) else ""
        book.save(update_fields=["author_legacy", "genre_legacy"])

    seen_slugs: set = set(Author.objects.values_list("slug", flat=True))
    author_map: dict[str, int] = {}

    for name in Book.objects.exclude(author_legacy="").values_list("author_legacy", flat=True).distinct():
        slug = _safe_slug(name, seen_slugs)
        author, created = Author.objects.get_or_create(slug=slug)
        if created:
            AuthorTranslation.objects.create(author=author, language=uk, name=name)
        else:
            AuthorTranslation.objects.get_or_create(author=author, language=uk, defaults={"name": name})
        author_map[name] = author.pk

    seen_slugs2: set = set(Genre.objects.values_list("slug", flat=True))
    genre_map: dict[str, int] = {}

    for name in Book.objects.exclude(genre_legacy="").values_list("genre_legacy", flat=True).distinct():
        slug = _safe_slug(name, seen_slugs2)
        genre, created = Genre.objects.get_or_create(slug=slug)
        if created:
            GenreTranslation.objects.create(genre=genre, language=uk, name=name)
        else:
            GenreTranslation.objects.get_or_create(genre=genre, language=uk, defaults={"name": name})
        genre_map[name] = genre.pk

    seen_book_slugs: set = set()
    for book in Book.objects.all():
        if book.author_legacy and book.author_legacy in author_map:
            book.author_id = author_map[book.author_legacy]
        if book.genre_legacy and book.genre_legacy in genre_map:
            book.genre_id = genre_map[book.genre_legacy]
        book.slug = _safe_slug(book.title or f"book-{book.pk}", seen_book_slugs)
        book.save(update_fields=["author_id", "genre_id", "slug"])

    seen_pl_slugs: set = set()
    for pl in Playlist.objects.all():
        pl.slug = _safe_slug(pl.title or f"playlist-{pl.pk}", seen_pl_slugs, prefix="")
        pl.save(update_fields=["slug"])


def reverse(apps, schema_editor):
    Book = apps.get_model("core", "Book")
    Playlist = apps.get_model("core", "Playlist")
    Book.objects.all().update(author_id=None, genre_id=None, slug=None)
    Playlist.objects.all().update(slug=None)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_book_author_genre_slug"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
