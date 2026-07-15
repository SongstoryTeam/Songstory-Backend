from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sync the django.contrib.sites Site record with SITE_DOMAIN/SITE_NAME env settings."

    def handle(self, *args, **options):
        site, created = Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={"domain": settings.SITE_DOMAIN, "name": settings.SITE_NAME},
        )
        verb = "Створено" if created else "Оновлено"
        self.stdout.write(self.style.SUCCESS(f"{verb} Site: {site.domain}"))
