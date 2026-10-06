import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Створює суперкористувача зі змінних DJANGO_SUPERUSER_*, якщо його ще немає"

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if not (username and password):
            self.stdout.write("DJANGO_SUPERUSER_USERNAME та DJANGO_SUPERUSER_PASSWORD не задано, пропускаю.")
            return
        user_model = get_user_model()
        if user_model.objects.filter(username=username).exists():
            self.stdout.write(f"Користувач {username} уже існує.")
            return
        user_model.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Створено суперкористувача {username}."))
