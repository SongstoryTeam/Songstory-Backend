from django.db import migrations

from core.text import normalize

BATCH_SIZE = 500


def _flush(model, batch: list) -> list:
    if batch:
        model.objects.bulk_update(batch, ["search_key"])
    return []


def rebuild_search_keys(apps, schema_editor):
    Book = apps.get_model("core", "Book")
    Track = apps.get_model("core", "Track")

    pending = []
    for book in Book.objects.select_related("author").iterator(chunk_size=BATCH_SIZE):
        author_name = book.author.name if book.author_id else ""
        key = normalize(f"{book.title} {author_name}")[:600]
        if key != book.search_key:
            book.search_key = key
            pending.append(book)
        if len(pending) >= BATCH_SIZE:
            pending = _flush(Book, pending)
    _flush(Book, pending)

    pending = []
    for track in Track.objects.iterator(chunk_size=BATCH_SIZE):
        key = normalize(f"{track.title} {track.artist}")[:520]
        if key != track.search_key:
            track.search_key = key
            pending.append(track)
        if len(pending) >= BATCH_SIZE:
            pending = _flush(Track, pending)
    _flush(Track, pending)


class Migration(migrations.Migration):
    dependencies = [("core", "0002_book_catalog_indexes")]

    operations = [migrations.RunPython(rebuild_search_keys, migrations.RunPython.noop)]
