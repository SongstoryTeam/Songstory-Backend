from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0006_backfill_user_profiles")]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="accent",
            field=models.CharField(
                choices=[
                    ("terracotta", "Теракота"),
                    ("rose", "Троянда"),
                    ("amber", "Бурштин"),
                    ("forest", "Хвоя"),
                    ("teal", "Бірюза"),
                    ("ocean", "Океан"),
                    ("indigo", "Індиго"),
                    ("violet", "Фіалка"),
                ],
                default="terracotta",
                max_length=16,
                verbose_name="Акцентний колір",
            ),
        ),
    ]
