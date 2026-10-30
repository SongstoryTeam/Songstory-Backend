from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Створює групи персоналу з STAFF_ROLES і виставляє їм дозволи"

    def handle(self, *args, **options):
        available = {
            f"{permission.content_type.app_label}.{permission.codename}": permission
            for permission in Permission.objects.select_related("content_type")
        }
        for role, codenames in settings.STAFF_ROLES.items():
            missing = [codename for codename in codenames if codename not in available]
            if missing:
                raise CommandError(f"Невідомі дозволи для ролі «{role}»: {', '.join(missing)}")
            group, created = Group.objects.get_or_create(name=role)
            group.permissions.set([available[codename] for codename in codenames])
            verb = "Створено" if created else "Оновлено"
            self.stdout.write(self.style.SUCCESS(f"{verb} роль «{role}»: {len(codenames)} дозволів"))
