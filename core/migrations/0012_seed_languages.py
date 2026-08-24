from django.db import migrations


def seed_languages(apps, schema_editor):
    Language = apps.get_model("core", "Language")
    Language.objects.get_or_create(code="uk", defaults={"name": "Українська"})
    Language.objects.get_or_create(code="en", defaults={"name": "English"})


def reverse_seed_languages(apps, schema_editor):
    Language = apps.get_model("core", "Language")
    Language.objects.filter(code__in=["uk", "en"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_language_genre"),
    ]

    operations = [
        migrations.RunPython(seed_languages, reverse_seed_languages),
    ]