from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from core import audit
from staffpanel.access import Permission
from staffpanel.services import overview


def always(item, actor) -> bool:
    return True


@dataclass(frozen=True)
class Action:
    key: str
    label: str
    icon: str
    permission: Permission
    flag: int
    log_message: str
    done_message: str
    apply: Callable[[list], None]
    eligible: Callable[[Any, Any], bool] = always
    danger: bool = False
    confirm_title: str = ""
    confirm_message: str = ""


@dataclass(frozen=True)
class Row:
    obj: Any
    actions: list[Action]


Registry = dict[str, Action]


def registry(*actions: Action) -> Registry:
    return {action.key: action for action in actions}


def permitted(actions: Registry, user) -> list[Action]:
    return [action for action in actions.values() if user.has_perm(str(action.permission))]


def available(actions: Registry, user, item) -> list[Action]:
    return [action for action in permitted(actions, user) if action.eligible(item, user)]


def rows(actions: Registry, user, items: Iterable) -> list[Row]:
    allowed = permitted(actions, user)
    return [Row(item, [action for action in allowed if action.eligible(item, user)]) for item in items]


def execute(action: Action, actor, queryset) -> int:
    with transaction.atomic():
        items = [item for item in queryset if action.eligible(item, actor)]
        if items:
            audit.record(actor, items, action.flag, action.log_message)
            action.apply(items)
            transaction.on_commit(overview.invalidate)
    return len(items)
