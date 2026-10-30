from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone

from core.models import AuthorVerification, Book, Comment, Recommendation, Track
from staffpanel.access import Permission

BADGES_KEY = "staff:badges"
METRICS_KEY = "staff:metrics"


class Badge(models.TextChoices):
    BOOKS = "books"
    VERIFICATIONS = "verifications"


@dataclass(frozen=True)
class Metric:
    label: str
    total: int
    recent: int
    icon: str
    permission: Permission


def pending_counts() -> dict[str, int]:
    counts = cache.get(BADGES_KEY)
    if counts is None:
        counts = {
            Badge.BOOKS.value: Book.objects.filter(is_approved=False).count(),
            Badge.VERIFICATIONS.value: AuthorVerification.objects.filter(
                status=AuthorVerification.Status.PENDING
            ).count(),
        }
        cache.set(BADGES_KEY, counts, settings.STAFF_BADGE_CACHE_TTL)
    return counts


def _totals(model, moment_field: str, since) -> tuple[int, int]:
    row = model.objects.aggregate(
        total=Count("pk"),
        recent=Count("pk", filter=Q(**{f"{moment_field}__gte": since})),
    )
    return row["total"], row["recent"]


def metrics() -> list[Metric]:
    cached = cache.get(METRICS_KEY)
    if cached is not None:
        return cached
    since = timezone.now() - timedelta(days=settings.STAFF_TREND_DAYS)
    sources = (
        ("Книги", Book, "created_at", "book-open", Permission.BOOKS_VIEW),
        ("Рекомендації", Recommendation, "created_at", "disc-3", Permission.BOOKS_VIEW),
        ("Треки", Track, "created_at", "music", Permission.BOOKS_VIEW),
        ("Коментарі", Comment, "created_at", "message-square", Permission.COMMENTS_VIEW),
        ("Користувачі", User, "date_joined", "users", Permission.USERS_VIEW),
    )
    result = [
        Metric(label, *_totals(model, field, since), icon, permission)
        for label, model, field, icon, permission in sources
    ]
    cache.set(METRICS_KEY, result, settings.STAFF_STATS_CACHE_TTL)
    return result


def invalidate() -> None:
    cache.delete_many([BADGES_KEY, METRICS_KEY])
