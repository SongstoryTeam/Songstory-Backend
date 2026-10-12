from django.db import migrations, models

from core.text import search_form

BATCH_SIZE = 500


def reindex(apps, schema_editor):
    Book = apps.get_model("core", "Book")
    Track = apps.get_model("core", "Track")

    books = []
    for book in Book.objects.select_related("author").iterator(chunk_size=BATCH_SIZE):
        author_name = book.author.name if book.author_id else ""
        book.search_key = search_form(f"{book.title} {author_name}")[:600]
        book.title_key = search_form(book.title)[:255]
        books.append(book)
        if len(books) >= BATCH_SIZE:
            Book.objects.bulk_update(books, ["search_key", "title_key"])
            books = []
    if books:
        Book.objects.bulk_update(books, ["search_key", "title_key"])

    tracks = []
    for track in Track.objects.iterator(chunk_size=BATCH_SIZE):
        track.search_key = search_form(f"{track.title} {track.artist}")[:520]
        tracks.append(track)
        if len(tracks) >= BATCH_SIZE:
            Track.objects.bulk_update(tracks, ["search_key"])
            tracks = []
    if tracks:
        Track.objects.bulk_update(tracks, ["search_key"])


class Migration(migrations.Migration):
    dependencies = [("core", "0003_rebuild_search_keys")]

    operations = [
        migrations.AddField(
            model_name="book",
            name="title_key",
            field=models.CharField(db_index=True, default="", editable=False, max_length=255),
        ),
        migrations.RunPython(reindex, migrations.RunPython.noop),
    ]
