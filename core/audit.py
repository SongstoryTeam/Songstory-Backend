from collections.abc import Iterable

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth.models import User
from django.db.models import Model

__all__ = ["ADDITION", "CHANGE", "DELETION", "record"]


def record(actor: User, items: Iterable[Model], flag: int, message: str) -> None:
    LogEntry.objects.log_actions(actor.pk, list(items), flag, message)
