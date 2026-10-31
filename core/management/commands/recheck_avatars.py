from django.core.management.base import BaseCommand

from core.models import UserProfile
from core.services.avatars import AvatarRejected, validate_avatar_url


class Command(BaseCommand):
    help = "Повторно перевіряє фото профілів і прибирає ті, що більше не відповідають вимогам"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="лише показати, що буде прибрано, нічого не змінюючи")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        removed = skipped = 0

        for profile in UserProfile.objects.exclude(avatar_url="").select_related("user").iterator():
            try:
                validate_avatar_url(profile.avatar_url)
            except AvatarRejected as rejection:
                if rejection.is_transient:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"{profile.user.username}: пропущено ({rejection})"))
                    continue
                removed += 1
                self.stdout.write(f"{profile.user.username}: {rejection}")
                if not dry_run:
                    profile.reset_avatar()

        prefix = "[пробний запуск, нічого не змінено] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}Фото прибрано: {removed}, пропущено через збій мережі: {skipped}"))
