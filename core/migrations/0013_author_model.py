import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_seed_languages"),
    ]

    operations = [
        migrations.CreateModel(
            name="Author",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("photo_url", models.URLField(blank=True)),
                ("birth_year", models.IntegerField(blank=True, null=True)),
                ("open_library_id", models.CharField(blank=True, max_length=50)),
            ],
            options={"verbose_name": "Author", "verbose_name_plural": "Authors", "ordering": ["slug"]},
        ),
        migrations.CreateModel(
            name="AuthorTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("bio", models.TextField(blank=True)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="translations", to="core.author")),
                ("language", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.language")),
            ],
            options={"verbose_name": "Author translation", "verbose_name_plural": "Author translations", "unique_together": {("author", "language")}},
        ),
    ]
