import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_book_verified_author"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="musicrecommendation",
            name="mood",
            field=models.CharField(
                blank=True,
                choices=[
                    ("epic", "Epic"),
                    ("sad", "Melancholic"),
                    ("calm", "Calm"),
                    ("tense", "Tense"),
                    ("romantic", "Romantic"),
                    ("dark", "Dark"),
                    ("uplifting", "Uplifting"),
                    ("mysterious", "Mysterious"),
                ],
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="AuthorVerification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("proof_document", models.FileField(
                    help_text="PDF or image",
                    upload_to="author_proofs/",
                    verbose_name="Identity document",
                )),
                ("proof_authorship", models.FileField(
                    help_text="Publisher contract, book page, etc.",
                    upload_to="author_proofs/",
                    verbose_name="Authorship proof",
                )),
                ("publisher_url", models.URLField(blank=True, verbose_name="Official publisher page")),
                ("additional_notes", models.TextField(blank=True)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("approved", "Approved"),
                        ("rejected", "Rejected"),
                    ],
                    db_index=True,
                    default="pending",
                    max_length=20,
                )),
                ("admin_note", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("book", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="author_verifications",
                    to="core.book",
                )),
                ("reviewed_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="reviewed_verifications",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="author_verification",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"verbose_name": "Author verification", "verbose_name_plural": "Author verifications"},
        ),
        migrations.CreateModel(
            name="Follow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("follower", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="following",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("following", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="followers",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"unique_together": {("follower", "following")}},
        ),
        migrations.CreateModel(
            name="BookRating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveSmallIntegerField()),
                ("book", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="ratings",
                    to="core.book",
                )),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"unique_together": {("user", "book")}},
        ),
    ]
