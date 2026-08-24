from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache

_TOKEN_CACHE_KEY = "spotify:access_token"
_TOKEN_TTL = 60 * 55
_SEARCH_TTL = 60 * 60
_SEARCH_CACHE_PREFIX = "spotify:search:"


@dataclass(frozen=True)
class SpotifyTrack:
    spotify_id: str
    title: str
    artist: str
    album: str
    cover_url: str
    preview_url: str | None
    spotify_url: str


class SpotifyError(Exception):
    pass


class SpotifyClient:
    _API_BASE = "https://api.spotify.com/v1"
    _TOKEN_URL = "https://accounts.spotify.com/api/token"

    def __init__(self) -> None:
        self._client_id: str = getattr(settings, "SPOTIFY_CLIENT_ID", "")
        self._client_secret: str = getattr(settings, "SPOTIFY_CLIENT_SECRET", "")

    def _fetch_token(self) -> str:
        if not self._client_id or not self._client_secret:
            raise SpotifyError("Spotify credentials not configured.")

        credentials = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()

        body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
        req = urllib.request.Request(
            self._TOKEN_URL,
            data=body,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data: dict[str, Any] = json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            raise SpotifyError(f"Token request failed: {exc}") from exc

        token: str = data.get("access_token", "")
        if not token:
            raise SpotifyError("Empty access token received.")

        cache.set(_TOKEN_CACHE_KEY, token, _TOKEN_TTL)
        return token

    def _get_token(self) -> str:
        token = cache.get(_TOKEN_CACHE_KEY)
        return token if token else self._fetch_token()

    def _request(self, path: str, params: dict[str, str] | None = None) -> Any:
        url = f"{self._API_BASE}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self._get_token()}"},
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                cache.delete(_TOKEN_CACHE_KEY)
                req.add_header("Authorization", f"Bearer {self._fetch_token()}")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read())
            raise SpotifyError(f"Spotify API error {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise SpotifyError(f"Network error: {exc}") from exc

    def search_tracks(self, query: str, limit: int = 10) -> list[SpotifyTrack]:
        cache_key = f"{_SEARCH_CACHE_PREFIX}{query.lower()}:{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        data = self._request("/search", {"q": query, "type": "track", "limit": str(limit)})
        items = data.get("tracks", {}).get("items", [])
        tracks = [self._parse_track(item) for item in items if item]
        cache.set(cache_key, tracks, _SEARCH_TTL)
        return tracks

    @staticmethod
    def _parse_track(item: dict[str, Any]) -> SpotifyTrack:
        artists = ", ".join(a["name"] for a in item.get("artists", []))
        album = item.get("album", {})
        images = album.get("images", [])
        cover_url = images[0]["url"] if images else ""
        external_urls = item.get("external_urls", {})
        return SpotifyTrack(
            spotify_id=item["id"],
            title=item.get("name", ""),
            artist=artists,
            album=album.get("name", ""),
            cover_url=cover_url,
            preview_url=item.get("preview_url"),
            spotify_url=external_urls.get("spotify", ""),
        )


spotify_client = SpotifyClient()