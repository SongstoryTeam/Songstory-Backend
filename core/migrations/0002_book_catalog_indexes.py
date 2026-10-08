import logging

from django.db import DatabaseError, migrations, models, transaction

logger = logging.getLogger(__name__)

TRIGRAM_INDEX = "book_search_key_trgm_idx"


def create_trigram_index(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    try:
        with transaction.atomic(using=connection.alias), connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS {TRIGRAM_INDEX} ON core_book USING gin (search_key gin_trgm_ops)"
            )
    except DatabaseError as exc:
        logger.warning("Skipped trigram index for book search: %s", exc)


def drop_trigram_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"DROP INDEX IF EXISTS {TRIGRAM_INDEX}")


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.AddIndex(
            model_name="book",
            index=models.Index(fields=["is_approved", "-created_at"], name="book_approved_created_idx"),
        ),
        migrations.RunPython(create_trigram_index, drop_trigram_index),
    ]
