from django.db import models, transaction
from django.db.models import Q, QuerySet

from core import audit
from core.models import AuthorVerification, Book
from staffpanel.services import overview

ALREADY_REVIEWED = "Цю заявку вже розглянуто."
AUTHORSHIP_TAKEN = "Авторство цієї книги вже підтверджено іншим користувачем."


class ReviewError(Exception):
    pass


class Decision(models.TextChoices):
    APPROVE = "approve", "Схвалити"
    REJECT = "reject", "Відхилити"


class VerificationState(models.TextChoices):
    PENDING = AuthorVerification.Status.PENDING.value, "Очікують"
    APPROVED = AuthorVerification.Status.APPROVED.value, "Схвалені"
    REJECTED = AuthorVerification.Status.REJECTED.value, "Відхилені"
    ALL = "all", "Усі"


DEFAULT_STATE = VerificationState.PENDING

_HANDLERS = {
    Decision.APPROVE: AuthorVerification.approve,
    Decision.REJECT: AuthorVerification.reject,
}


def verification_queryset(*, state: str, query: str) -> QuerySet[AuthorVerification]:
    state = VerificationState(state) if state in VerificationState.values else DEFAULT_STATE
    queryset = AuthorVerification.objects.select_related("user", "book", "reviewed_by")
    if state is not VerificationState.ALL:
        queryset = queryset.filter(status=state.value)
    if query:
        queryset = queryset.filter(Q(user__username__icontains=query) | Q(book__title__icontains=query))
    ordering = ("submitted_at", "pk") if state is VerificationState.PENDING else ("-submitted_at", "-pk")
    return queryset.order_by(*ordering)


def authorship_taken(verification: AuthorVerification) -> bool:
    holder = verification.book.verified_author_id
    return holder is not None and holder != verification.user_id


def review(pk: int, reviewer, decision: Decision, note: str) -> AuthorVerification:
    with transaction.atomic():
        verification = (
            AuthorVerification.objects.select_for_update(of=("self",)).select_related("user").get(pk=pk)
        )
        verification.book = Book.objects.select_for_update().get(pk=verification.book_id)
        if verification.status != AuthorVerification.Status.PENDING:
            raise ReviewError(ALREADY_REVIEWED)
        if decision is Decision.APPROVE and authorship_taken(verification):
            raise ReviewError(AUTHORSHIP_TAKEN)
        _HANDLERS[decision](verification, reviewer, note)
        audit.record(reviewer, [verification], audit.CHANGE, f"{decision.label}: заявка на підтвердження авторства")
        transaction.on_commit(overview.invalidate)
    return verification
