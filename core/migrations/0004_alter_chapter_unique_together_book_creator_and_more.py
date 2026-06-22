import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_book_cover_image_alter_book_cover_url"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="chapter",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="book",
            name="creator",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name="Створив"),
        ),
        migrations.AddField(
            model_name="chapter",
            name="is_approved",
            field=models.BooleanField(default=False, verbose_name="Підтверджено"),
        ),
        migrations.AlterField(
            model_name="book",
            name="cover_url",
            field=models.URLField(blank=True, verbose_name="Посилання на обкладинку"),
        ),
    ]
