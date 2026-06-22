import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_phase2_features"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="is_approved",
            field=models.BooleanField(default=False, db_index=True, verbose_name="Approved"),
        ),
        migrations.RunSQL(
            sql="UPDATE core_book SET is_approved = TRUE;",
            reverse_sql="UPDATE core_book SET is_approved = FALSE;",
        ),
        migrations.AlterField(
            model_name="authorverification",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="author_verifications",
                to=settings.AUTH_USER_MODEL,
                verbose_name="User",
            ),
        ),
    ]
