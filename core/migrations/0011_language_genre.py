import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_phase3_moderation"),
    ]

    operations = [
        migrations.CreateModel(
            name="Language",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=10, unique=True)),
                ("name", models.CharField(max_length=50)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "Language", "verbose_name_plural": "Languages", "ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="Genre",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
            ],
            options={"verbose_name": "Genre", "verbose_name_plural": "Genres", "ordering": ["slug"]},
        ),
        migrations.CreateModel(
            name="GenreTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("genre", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="translations", to="core.genre")),
                ("language", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.language")),
            ],
            options={"verbose_name": "Genre translation", "verbose_name_plural": "Genre translations", "unique_together": {("genre", "language")}},
        ),
    ]
