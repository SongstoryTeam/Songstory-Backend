from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# MyMemory: free, no API key, no billing account required. Anonymous
# requests get 5,000 words/day per IP; passing `de` (a contact email, any
# email works — it doesn't need to be verified) raises that to 10,000/day
# at no cost. See https://mymemory.translated.net/doc/spec.php
_API_BASE = "https://api.mymemory.translated.net/get"
_REQUEST_TIMEOUT = 5
_CACHE_TTL = 60 * 60 * 24 * 7  # a title's translation doesn't change; cache generously
_CACHE_PREFIX = "translate:uk-en:"
_MISS_SENTINEL = "__miss__"
_MAX_QUERY_LENGTH = 500  # MyMemory rejects anything much longer; queries are short anyway

_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def needs_translation(text: str) -> bool:
    """Whether `text` contains Cyrillic and therefore is unlikely to find
    anything by itself in external, mostly English-indexed book catalogs."""
    return bool(_CYRILLIC_RE.search(text))


def translate_to_english(text: str) -> str | None:
    """Best-effort translation of a Ukrainian (or other Cyrillic) search
    query into English so it can be matched against external book catalogs.

    Returns None — never raises — if the request fails or MyMemory can't
    produce a confident translation. External search is a nice-to-have on
    top of the local catalog, not a hard dependency, so a translation
    failure must never break the surrounding search.
    """
    text = text.strip()
    if not text or len(text) > _MAX_QUERY_LENGTH:
        return None

    cache_key = f"{_CACHE_PREFIX}{text.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return None if cached == _MISS_SENTINEL else cached

    params = {"q": text, "langpair": "uk|en"}
    contact_email = getattr(settings, "MYMEMORY_CONTACT_EMAIL", "")
    if contact_email:
        params["de"] = contact_email

    url = f"{_API_BASE}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "Songstery/1.0"})

    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
            data = json.loads(response.read())
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as exc:
        logger.warning("Query translation failed for %r: %s", text, exc)
        cache.set(cache_key, _MISS_SENTINEL, _CACHE_TTL)
        return None

    # MyMemory returns responseStatus 200 even for low-confidence guesses,
    # so we prefer the primary translation but fall back to the best-scored
    # alternative match if the primary one looks like a warning/placeholder.
    response_data = data.get("responseData") or {}
    translated = (response_data.get("translatedText") or "").strip()

    if not translated or "MYMEMORY WARNING" in translated.upper():
        translated = _best_alternative(data.get("matches", []))

    cache.set(cache_key, translated or _MISS_SENTINEL, _CACHE_TTL)
    return translated or None


def _best_alternative(matches: list[dict]) -> str | None:
    usable = [m for m in matches if m.get("translation")]
    if not usable:
        return None
    best = max(usable, key=lambda m: _as_float(m.get("match")) or 0.0)
    return (best.get("translation") or "").strip() or None


def _as_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
