
from django.db import migrations


def drop_orphaned_columns(apps, schema_editor):
    """
    Migrations 0002 / 0011 originally defined `author` and `genre` as
    plain, required CharFields on Book. Migration 0014 later introduced
    `Book.author` / `Book.genre` as ForeignKeys to the new Author/Genre
    models, reusing the same field names. Django's migration state keys
    fields by name, so the ForeignKey definitions silently replaced the
    CharField ones in the model state -- but no migration ever explicitly
    dropped the original `author` / `genre` text columns.

    On backends that rebuild the whole table for later AlterField
    operations (e.g. SQLite), those orphaned columns already vanished as
    a side effect. On backends that alter columns in place (e.g.
    PostgreSQL), they are still physically present: NOT NULL, no
    default, and untracked by the current model state, so every INSERT
    into core_book fails with a not-null violation on them.

    This only drops the columns if they still exist, making it safe to
    run regardless of which backend produced the current schema.
    """
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        existing_columns = {
            column.name for column in connection.introspection.get_table_description(cursor, "core_book")
        }
    for column_name in ("author", "genre"):
        if column_name in existing_columns:
            schema_editor.execute(f'ALTER TABLE core_book DROP COLUMN "{column_name}"')


def restore_orphaned_columns(apps, schema_editor):
    schema_editor.execute("ALTER TABLE core_book ADD COLUMN genre varchar(100) NOT NULL DEFAULT ''")
    schema_editor.execute("ALTER TABLE core_book ADD COLUMN author varchar(255) NOT NULL DEFAULT ''")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_remove_legacy_translated_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="book",
            name="author_legacy",
        ),
        migrations.RemoveField(
            model_name="book",
            name="genre_legacy",
        ),
        migrations.RunPython(
            drop_orphaned_columns,
            reverse_code=restore_orphaned_columns,
        ),
    ]
