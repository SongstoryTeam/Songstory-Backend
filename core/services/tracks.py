from django.conf import settings
from django.contrib.auth.models import User

from core.models import Track

from .music_links import ParsedLink


def find_track(link: ParsedLink) -> Track | None:
    return Track.objects.filter(platform=link.platform, external_id=link.external_id).first()


def get_or_create_track(link: ParsedLink, title: str, artist: str, user: User | None) -> tuple[Track, bool]:
    return Track.objects.get_or_create(
        platform=link.platform,
        external_id=link.external_id,
        defaults={"title": title.strip(), "artist": artist.strip(), "created_by": user},
    )


def search_tracks(query: str, limit: int | None = None):
    limit = limit or settings.TRACK_SEARCH_LIMIT
    return Track.objects.search(query)[:limit]
