import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_data_author_genre_slugs"),
    ]

    operations = [
        migrations.CreateModel(
            name="BookTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="translations", to="core.book")),
                ("language", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.language")),
            ],
            options={"verbose_name": "Book translation", "verbose_name_plural": "Book translations", "unique_together": {("book", "language")}},
        ),
        migrations.CreateModel(
            name="ChapterTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("mood_tags", models.CharField(blank=True, max_length=200)),
                ("chapter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="translations", to="core.chapter")),
                ("language", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.language")),
            ],
            options={"verbose_name": "Chapter translation", "verbose_name_plural": "Chapter translations", "unique_together": {("chapter", "language")}},
        ),
    ]
