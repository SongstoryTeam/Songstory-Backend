import re
from dataclasses import dataclass
from urllib.parse import quote

from core.models.music import Platform

from .http import ExternalServiceError, get_json


@dataclass(frozen=True)
class PlatformSpec:
    patterns: tuple[re.Pattern, ...]
    canonical_url: str
    embed_url: str
    oembed_url: str


PLATFORMS: dict[str, PlatformSpec] = {
    Platform.YOUTUBE: PlatformSpec(
        patterns=(
            re.compile(r"^(?:https?://)?(?:www\.|m\.|music\.)?youtube\.com/watch\?(?:[^#]*&)?v=([\w-]{11})"),
            re.compile(r"^(?:https?://)?(?:www\.|m\.)?youtube\.com/(?:embed|shorts|live)/([\w-]{11})"),
            re.compile(r"^(?:https?://)?youtu\.be/([\w-]{11})"),
        ),
        canonical_url="https://www.youtube.com/watch?v={id}",
        embed_url="https://www.youtube-nocookie.com/embed/{id}",
        oembed_url="https://www.youtube.com/oembed?format=json&url={url}",
    ),
    Platform.SPOTIFY: PlatformSpec(
        patterns=(
            re.compile(r"^(?:https?://)?open\.spotify\.com/(?:intl-[a-z]{2}/)?track/([A-Za-z0-9]{22})"),
            re.compile(r"^spotify:track:([A-Za-z0-9]{22})$"),
        ),
        canonical_url="https://open.spotify.com/track/{id}",
        embed_url="https://open.spotify.com/embed/track/{id}",
        oembed_url="https://open.spotify.com/oembed?url={url}",
    ),
}

YOUTUBE_TOPIC_SUFFIX = " - Topic"


@dataclass(frozen=True)
class ParsedLink:
    platform: str
    external_id: str


@dataclass(frozen=True)
class TrackMetadata:
    title: str
    artist: str


def parse_link(raw_url: str) -> ParsedLink | None:
    candidate = raw_url.strip()
    for platform, spec in PLATFORMS.items():
        for pattern in spec.patterns:
            match = pattern.match(candidate)
            if match:
                return ParsedLink(platform=str(platform), external_id=match.group(1))
    return None


def canonical_url(platform: str, external_id: str) -> str:
    return PLATFORMS[platform].canonical_url.format(id=external_id)


def embed_url(platform: str, external_id: str) -> str:
    return PLATFORMS[platform].embed_url.format(id=external_id)


def fetch_metadata(link: ParsedLink) -> TrackMetadata | None:
    spec = PLATFORMS[link.platform]
    url = spec.oembed_url.format(url=quote(canonical_url(link.platform, link.external_id), safe=""))
    try:
        payload = get_json(url)
    except ExternalServiceError:
        return None
    title = str(payload.get("title", "")).strip()
    if not title:
        return None
    artist = str(payload.get("author_name", "")).strip().removesuffix(YOUTUBE_TOPIC_SUFFIX)
    return TrackMetadata(title=title, artist=artist)
