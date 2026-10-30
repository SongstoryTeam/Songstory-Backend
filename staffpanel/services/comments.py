from dataclasses import dataclass

from django.db.models import Q, QuerySet

from core import audit
from core.models import Comment
from staffpanel.access import Permission
from staffpanel.actions import Action, registry
from staffpanel.services.common import pks


@dataclass(frozen=True)
class Target:
    label: str
    url: str


def comment_queryset(*, query: str) -> QuerySet[Comment]:
    queryset = Comment.objects.select_related("user", "book", "chapter__book", "playlist")
    if query:
        queryset = queryset.filter(Q(text__icontains=query) | Q(user__username__icontains=query))
    return queryset.order_by("-created_at", "-pk")


def describe_target(comment: Comment) -> Target:
    target = comment.target
    if comment.chapter_id:
        return Target(f"{target.book.title}, {target.display_title}", target.get_absolute_url())
    return Target(target.title, target.get_absolute_url())


def _delete(comments: list[Comment]) -> None:
    Comment.objects.filter(pk__in=pks(comments)).delete()


COMMENT_ACTIONS = registry(
    Action(
        key="delete",
        label="Видалити",
        icon="trash-2",
        permission=Permission.COMMENTS_DELETE,
        flag=audit.DELETION,
        log_message="Коментар видалено",
        done_message="Видалено коментарів: {count}.",
        apply=_delete,
        danger=True,
        confirm_title="Видалити коментарі?",
        confirm_message="Відповіді на видалені коментарі теж зникнуть.",
    ),
)
