from importlib import import_module

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Каталог"

    def ready(self) -> None:
        import_module("core.signals")
