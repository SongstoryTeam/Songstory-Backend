import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="book",
            options={"ordering": ["-created_at"], "verbose_name": "Книга", "verbose_name_plural": "Книги"},
        ),
        migrations.AddField(
            model_name="book",
            name="cover_url",
            field=models.URLField(blank=True, verbose_name="Обкладинка"),
        ),
        migrations.AddField(
            model_name="book",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="book",
            name="description",
            field=models.TextField(blank=True, verbose_name="Опис"),
        ),
        migrations.AddField(
            model_name="book",
            name="genre",
            field=models.CharField(blank=True, max_length=100, verbose_name="Жанр"),
        ),
        migrations.AddField(
            model_name="book",
            name="views_count",
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="book",
            name="author",
            field=models.CharField(max_length=255, verbose_name="Автор"),
        ),
        migrations.AlterField(
            model_name="book",
            name="title",
            field=models.CharField(max_length=255, verbose_name="Назва"),
        ),
        migrations.AlterField(
            model_name="book",
            name="year",
            field=models.IntegerField(verbose_name="Рік"),
        ),
        migrations.CreateModel(
            name="Chapter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, verbose_name="Назва розділу")),
                ("number", models.IntegerField(verbose_name="Номер")),
                ("description", models.TextField(blank=True, verbose_name="Опис")),
                ("mood_tags", models.CharField(blank=True, help_text="Наприклад: спокій, напруга, епічність", max_length=200)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chapters", to="core.book")),
            ],
            options={
                "verbose_name": "Розділ",
                "verbose_name_plural": "Розділи",
                "ordering": ["number"],
                "unique_together": {("book", "number")},
            },
        ),
        migrations.CreateModel(
            name="MusicRecommendation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("track_title", models.CharField(max_length=255, verbose_name="Назва треку")),
                ("artist", models.CharField(max_length=255, verbose_name="Виконавець")),
                ("link_type", models.CharField(choices=[("youtube", "YouTube"), ("spotify", "Spotify"), ("soundcloud", "SoundCloud"), ("other", "Інше")], default="youtube", max_length=20)),
                ("link_url", models.URLField(verbose_name="Посилання")),
                ("embed_code", models.CharField(blank=True, help_text="Для YouTube: ID відео", max_length=100)),
                ("comment", models.TextField(blank=True, verbose_name="Коментар")),
                ("likes_count", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("chapter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="music_recommendations", to="core.chapter")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Музична рекомендація",
                "verbose_name_plural": "Музичні рекомендації",
                "ordering": ["-likes_count", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Playlist",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, verbose_name="Назва")),
                ("description", models.TextField(blank=True, verbose_name="Опис")),
                ("mood", models.CharField(blank=True, max_length=200)),
                ("likes_count", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_public", models.BooleanField(default=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="playlists", to="core.book")),
                ("chapter", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="playlists", to="core.chapter")),
                ("creator", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Плейлист",
                "verbose_name_plural": "Плейлисти",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Comment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField(verbose_name="Коментар")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("book", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="core.book")),
                ("chapter", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="core.chapter")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="replies", to="core.comment")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ("playlist", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="core.playlist")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PlaylistTrack",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("track_title", models.CharField(max_length=255)),
                ("artist", models.CharField(max_length=255)),
                ("link_url", models.URLField()),
                ("embed_code", models.CharField(blank=True, max_length=100)),
                ("order", models.IntegerField(default=0)),
                ("playlist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tracks", to="core.playlist")),
            ],
            options={"ordering": ["order"]},
        ),
        migrations.CreateModel(
            name="Like",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ("music_recommendation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="core.musicrecommendation")),
                ("playlist", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="core.playlist")),
            ],
            options={"unique_together": {("user", "music_recommendation"), ("user", "playlist")}},
        ),
        migrations.CreateModel(
            name="SavedBook",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.book")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("user", "book")}},
        ),
    ]
