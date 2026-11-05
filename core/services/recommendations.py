from dataclasses import dataclass, field

from django.contrib.auth.models import User
from django.db.models import Count, Min, Q, QuerySet

from core import limits
from core.models import Book, Chapter, Recommendation, Track


@dataclass
class TrackGroup:
    track: Track
    recommendations: list[Recommendation] = field(default_factory=list)
    mine: Recommendation | None = None
    by_verified_author: bool = False
    chapters: list[Chapter] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.recommendations)

    @property
    def comments(self) -> list[Recommendation]:
        return [item for item in self.recommendations if item.comment]


@dataclass
class TrackPage:
    groups: list[TrackGroup]
    remaining: int
    next_offset: int


def recommend(user: User, track: Track, book: Book, chapter: Chapter | None = None, comment: str = "") -> tuple[Recommendation, bool]:
    return Recommendation.objects.get_or_create(
        user=user, track=track, book=book, chapter=chapter, defaults={"comment": comment.strip()}
    )


def build_groups(queryset, book: Book, user) -> list[TrackGroup]:
    groups: dict[int, TrackGroup] = {}
    for item in queryset:
        group = groups.setdefault(item.track_id, TrackGroup(track=item.track))
        group.recommendations.append(item)
        if user.is_authenticated and item.user_id == user.pk:
            group.mine = item
        if book.verified_author_id and item.user_id == book.verified_author_id:
            group.by_verified_author = True
        if item.chapter_id and all(chapter.pk != item.chapter_id for chapter in group.chapters):
            group.chapters.append(item.chapter)
    for group in groups.values():
        group.chapters.sort(key=lambda chapter: chapter.number)
    return sorted(groups.values(), key=lambda group: (not group.by_verified_author, -group.count))


def chapter_scope(book: Book, chapter: Chapter | None) -> QuerySet:
    return Recommendation.objects.filter(book=book, chapter=chapter)


def book_scope(book: Book) -> tuple[QuerySet, bool]:
    direct = chapter_scope(book, None)
    if direct.exists():
        return direct, False
    return Recommendation.objects.filter(book=book, chapter__isnull=False), True


def with_relations(queryset: QuerySet) -> QuerySet:
    return queryset.select_related("track", "user", "chapter").order_by("created_at", "pk")


def grouped_recommendations(book: Book, chapter: Chapter | None, user) -> list[TrackGroup]:
    return build_groups(with_relations(chapter_scope(book, chapter)), book, user)


def scope_page(scope: QuerySet, book: Book, user, offset: int = 0, size: int = limits.TRACKS_PAGE_SIZE) -> TrackPage:
    ranking = (
        scope.order_by()
        .values("track_id")
        .annotate(
            total=Count("pk"),
            author_picks=Count("pk", filter=Q(user_id=book.verified_author_id)),
            first_at=Min("created_at"),
        )
        .order_by("-author_picks", "-total", "first_at", "track_id")
    )
    track_ids = [row["track_id"] for row in ranking[offset : offset + size]]
    position = {track_id: index for index, track_id in enumerate(track_ids)}
    groups = build_groups(with_relations(scope.filter(track_id__in=track_ids)), book, user)
    groups.sort(key=lambda group: position[group.track.pk])
    full_page = len(track_ids) == size
    remaining = max(ranking.count() - offset - size, 0) if full_page else 0
    return TrackPage(groups=groups, remaining=remaining, next_offset=offset + len(track_ids))


def book_tracks(book: Book):
    return Track.objects.filter(recommendations__book=book).distinct().order_by("title")
