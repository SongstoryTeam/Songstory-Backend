from django.contrib.admin.models import LogEntry
from django.db import models
from django.db.models import Q, QuerySet

from core import audit


class ActivityKind(models.TextChoices):
    ALL = "all", "Усі"
    CREATED = "created", "Додавання"
    CHANGED = "changed", "Зміни"
    DELETED = "deleted", "Видалення"


DEFAULT_KIND = ActivityKind.ALL

_FLAGS = {
    ActivityKind.CREATED: audit.ADDITION,
    ActivityKind.CHANGED: audit.CHANGE,
    ActivityKind.DELETED: audit.DELETION,
}


def activity_queryset(*, kind: str, query: str) -> QuerySet[LogEntry]:
    kind = ActivityKind(kind) if kind in ActivityKind.values else DEFAULT_KIND
    queryset = LogEntry.objects.select_related("user", "content_type")
    if kind in _FLAGS:
        queryset = queryset.filter(action_flag=_FLAGS[kind])
    if query:
        queryset = queryset.filter(Q(object_repr__icontains=query) | Q(user__username__icontains=query))
    return queryset.order_by("-action_time", "-pk")
