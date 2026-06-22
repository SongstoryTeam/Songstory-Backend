from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_alter_chapter_unique_together_book_creator_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="playlist",
            name="external_link",
            field=models.URLField(blank=True, verbose_name="Посилання на плейлист (YouTube/Spotify)"),
        ),
    ]
