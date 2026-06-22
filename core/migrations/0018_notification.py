import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("core", "0017_data_book_chapter_translations"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(
                    choices=[
                        ("like_music", "Music liked"),
                        ("comment_reply", "Comment reply"),
                        ("verification_approved", "Verification approved"),
                        ("verification_rejected", "Verification rejected"),
                    ],
                    db_index=True,
                    max_length=30,
                )),
                ("is_read", models.BooleanField(default=False, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("object_id", models.PositiveIntegerField(blank=True, null=True)),
                ("content_type", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to="contenttypes.contenttype",
                )),
                ("recipient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notifications",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"verbose_name": "Notification", "verbose_name_plural": "Notifications", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["recipient", "is_read"], name="core_notif_recip_read_idx"),
        ),
    ]
