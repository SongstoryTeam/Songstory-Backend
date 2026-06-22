import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_author_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="author_legacy",
            field=models.CharField(blank=True, max_length=255, verbose_name="Author (legacy)"),
        ),
        migrations.AddField(
            model_name="book",
            name="author",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="books",
                to="core.author",
                verbose_name="Author",
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="genre_legacy",
            field=models.CharField(blank=True, max_length=100, verbose_name="Genre (legacy)"),
        ),
        migrations.AddField(
            model_name="book",
            name="genre",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="books",
                to="core.genre",
                verbose_name="Genre",
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="slug",
            field=models.SlugField(blank=True, unique=True, null=True),
        ),
        migrations.AddField(
            model_name="book",
            name="isbn",
            field=models.CharField(blank=True, db_index=True, max_length=20),
        ),
        migrations.AddField(
            model_name="book",
            name="open_library_id",
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="book",
            name="google_books_id",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="book",
            name="canonical_book",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="editions",
                to="core.book",
            ),
        ),
        migrations.AddField(
            model_name="playlist",
            name="slug",
            field=models.SlugField(blank=True, unique=True, null=True),
        ),
    ]
