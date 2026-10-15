from django.db import migrations, models

from core.services.normalize import clean_person_name
from core.text import name_key, search_form

BATCH_SIZE = 500


def _flush(model, batch: list, fields: list[str]) -> list:
    if batch:
        model.objects.bulk_update(batch, fields)
    return []


def fill_keys(apps, schema_editor):
    """Заповнює name_key авторів і перебудовує ключі пошуку, бо search_form тепер зводить «ґ» до «г»."""
    Author = apps.get_model("core", "Author")
    Book = apps.get_model("core", "Book")

    pending = []
    for author in Author.objects.iterator(chunk_size=BATCH_SIZE):
        author.name_key = name_key(clean_person_name(author.name))
        pending.append(author)
        if len(pending) >= BATCH_SIZE:
            pending = _flush(Author, pending, ["name_key"])
    _flush(Author, pending, ["name_key"])

    pending = []
    for book in Book.objects.select_related("author").iterator(chunk_size=BATCH_SIZE):
        author_name = book.author.name if book.author_id else ""
        book.search_key = search_form(f"{book.title} {author_name}")[:600]
        book.title_key = search_form(book.title)[:255]
        pending.append(book)
        if len(pending) >= BATCH_SIZE:
            pending = _flush(Book, pending, ["search_key", "title_key"])
    _flush(Book, pending, ["search_key", "title_key"])


class Migration(migrations.Migration):
    dependencies = [("core", "0004_book_title_key")]

    operations = [
        migrations.AddField(
            model_name="author",
            name="name_key",
            field=models.CharField(db_index=True, default="", editable=False, max_length=255),
        ),
        migrations.RunPython(fill_keys, migrations.RunPython.noop),
    ]
