from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, QuerySet

from core import audit
from core.models import Book, Comment, Playlist, Recommendation, UserProfile
from staffpanel.access import Permission
from staffpanel.actions import Action, registry
from staffpanel.services.common import pks


class UserState(models.TextChoices):
    ALL = "all", "Усі"
    ACTIVE = "active", "Активні"
    INACTIVE = "inactive", "Заблоковані"
    STAFF = "staff", "Персонал"
    AUTHORS = "authors", "Автори"


DEFAULT_STATE = UserState.ALL

_STATE_FILTERS = {
    UserState.ALL: {},
    UserState.ACTIVE: {"is_active": True},
    UserState.INACTIVE: {"is_active": False},
    UserState.STAFF: {"is_staff": True},
    UserState.AUTHORS: {"profile__is_verified_author": True},
}


def user_queryset(*, state: str, query: str) -> QuerySet[User]:
    state = UserState(state) if state in UserState.values else DEFAULT_STATE
    queryset = User.objects.select_related("profile").filter(**_STATE_FILTERS[state])
    if query:
        queryset = queryset.filter(Q(username__icontains=query) | Q(email__icontains=query))
    return queryset.order_by("-date_joined", "-pk")


def can_manage(actor: User, target: User) -> bool:
    if actor.pk == target.pk or target.is_superuser:
        return False
    return actor.is_superuser or not target.is_staff


def is_verified_author(user: User) -> bool:
    profile = getattr(user, "profile", None)
    return bool(profile and profile.is_verified_author)


def activity_summary(user: User) -> dict[str, int]:
    return {
        "recommendations": Recommendation.objects.filter(user=user).count(),
        "playlists": Playlist.objects.filter(user=user).count(),
        "comments": Comment.objects.filter(user=user).count(),
        "books": Book.objects.filter(creator=user).count(),
    }


def _set_active(value: bool):
    def apply(users: list[User]) -> None:
        User.objects.filter(pk__in=pks(users)).update(is_active=value)

    return apply


def _revoke_author(users: list[User]) -> None:
    UserProfile.objects.filter(user__in=users).update(is_verified_author=False)
    Book.objects.filter(verified_author__in=users).update(verified_author=None)


def _can_block(user: User, actor: User) -> bool:
    return user.is_active and can_manage(actor, user)


def _can_unblock(user: User, actor: User) -> bool:
    return not user.is_active and can_manage(actor, user)


def _can_revoke(user: User, actor: User) -> bool:
    return is_verified_author(user) and can_manage(actor, user)


USER_ACTIONS = registry(
    Action(
        key="deactivate",
        label="Заблокувати",
        icon="user-x",
        permission=Permission.USERS_CHANGE,
        flag=audit.CHANGE,
        log_message="Користувача заблоковано",
        done_message="Заблоковано користувачів: {count}.",
        apply=_set_active(False),
        eligible=_can_block,
        danger=True,
        confirm_title="Заблокувати користувача?",
        confirm_message="Він більше не зможе увійти в акаунт. Його внесок залишиться на сайті.",
    ),
    Action(
        key="activate",
        label="Розблокувати",
        icon="user-check",
        permission=Permission.USERS_CHANGE,
        flag=audit.CHANGE,
        log_message="Користувача розблоковано",
        done_message="Розблоковано користувачів: {count}.",
        apply=_set_active(True),
        eligible=_can_unblock,
    ),
    Action(
        key="revoke-author",
        label="Зняти статус автора",
        icon="badge-x",
        permission=Permission.USERS_CHANGE,
        flag=audit.CHANGE,
        log_message="Знято статус підтвердженого автора",
        done_message="Знято статус автора: {count}.",
        apply=_revoke_author,
        eligible=_can_revoke,
        danger=True,
        confirm_title="Зняти статус автора?",
        confirm_message="Позначка підтвердженого автора зникне з профілю та з усіх його книг.",
    ),
)
