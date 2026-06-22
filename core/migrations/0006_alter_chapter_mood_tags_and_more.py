from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_playlist_external_link"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chapter",
            name="mood_tags",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name="musicrecommendation",
            name="embed_code",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
