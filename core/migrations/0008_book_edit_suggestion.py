import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_userprofile_accent"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BookEditSuggestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("changes", models.JSONField(default=dict, verbose_name="Зміни")),
                ("reason", models.TextField(blank=True, max_length=1000, verbose_name="Пояснення")),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Очікує"), ("approved", "Схвалено"), ("rejected", "Відхилено")],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("admin_note", models.TextField(blank=True, verbose_name="Нотатка модератора")),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="edit_suggestions",
                        to="core.book",
                        verbose_name="Книга",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_book_edits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="book_edit_suggestions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Автор пропозиції",
                    ),
                ),
            ],
            options={
                "verbose_name": "Пропозиція змін до книги",
                "verbose_name_plural": "Пропозиції змін до книг",
                "ordering": ["-submitted_at", "-pk"],
                "indexes": [models.Index(fields=["status", "-submitted_at"], name="suggestion_status_idx")],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("status", "pending")),
                        fields=("user", "book"),
                        name="single_pending_suggestion_per_user_book",
                    )
                ],
            },
        ),
    ]
