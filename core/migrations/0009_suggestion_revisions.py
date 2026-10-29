from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_book_edit_suggestion"),
    ]

    operations = [
        migrations.AddField(
            model_name="bookeditsuggestion",
            name="revision",
            field=models.PositiveSmallIntegerField(default=1, verbose_name="Редакція"),
        ),
        migrations.AddField(
            model_name="bookeditsuggestion",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="bookeditsuggestion",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Очікує"),
                    ("approved", "Схвалено"),
                    ("rejected", "Відхилено"),
                    ("withdrawn", "Відкликано"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
