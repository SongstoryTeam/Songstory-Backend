from dataclasses import dataclass, field

from django.contrib.auth.models import User

from core.models import Book, Chapter, Recommendation, Track


@dataclass
class TrackGroup:
    track: Track
    recommendations: list[Recommendation] = field(default_factory=list)
    mine: Recommendation | None = None
    by_verified_author: bool = False

    @property
    def count(self) -> int:
        return len(self.recommendations)

    @property
    def comments(self) -> list[Recommendation]:
        return [item for item in self.recommendations if item.comment]


def recommend(user: User, track: Track, book: Book, chapter: Chapter | None = None, comment: str = "") -> tuple[Recommendation, bool]:
    return Recommendation.objects.get_or_create(
        user=user, track=track, book=book, chapter=chapter, defaults={"comment": comment.strip()}
    )


def grouped_recommendations(book: Book, chapter: Chapter | None, user) -> list[TrackGroup]:
    queryset = (
        Recommendation.objects.filter(book=book, chapter=chapter)
        .select_related("track", "user")
        .order_by("created_at", "pk")
    )
    groups: dict[int, TrackGroup] = {}
    for item in queryset:
        group = groups.setdefault(item.track_id, TrackGroup(track=item.track))
        group.recommendations.append(item)
        if user.is_authenticated and item.user_id == user.pk:
            group.mine = item
        if book.verified_author_id and item.user_id == book.verified_author_id:
            group.by_verified_author = True
    return sorted(groups.values(), key=lambda group: (not group.by_verified_author, -group.count))


def book_tracks(book: Book):
    return Track.objects.filter(recommendations__book=book).distinct().order_by("title")
