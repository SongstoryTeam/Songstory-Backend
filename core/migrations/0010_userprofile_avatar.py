import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0009_suggestion_revisions")]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="avatar_url",
            field=models.URLField(blank=True, max_length=500, verbose_name="Фото профілю"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="avatar_x",
            field=models.PositiveSmallIntegerField(
                default=50,
                validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
                verbose_name="Кадр фото: горизонталь",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="avatar_y",
            field=models.PositiveSmallIntegerField(
                default=50,
                validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
                verbose_name="Кадр фото: вертикаль",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="avatar_zoom",
            field=models.PositiveSmallIntegerField(
                default=100,
                validators=[django.core.validators.MinValueValidator(100), django.core.validators.MaxValueValidator(300)],
                verbose_name="Кадр фото: масштаб",
            ),
        ),
    ]
