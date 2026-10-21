from django.db import migrations

BATCH_SIZE = 500


def backfill(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("core", "UserProfile")
    missing = User.objects.filter(profile__isnull=True).values_list("pk", flat=True)
    UserProfile.objects.bulk_create(
        [UserProfile(user_id=pk) for pk in missing.iterator(chunk_size=BATCH_SIZE)],
        batch_size=BATCH_SIZE,
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0005_author_name_key"),
    ]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
