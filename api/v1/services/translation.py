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

_API_BASE = "https://translation.googleapis.com/language/translate/v2"
_REQUEST_TIMEOUT = 5
_CACHE_TTL = 60 * 60 * 24 * 7  # a title's translation doesn't change; cache generously
_CACHE_PREFIX = "translate:uk-en:"
_MISS_SENTINEL = "__miss__"

# Anything containing Cyrillic can't realistically match Google Books/Open
# Library's overwhelmingly English/Latin-script metadata verbatim. This is
# the signal we use to decide a query is worth translating before the
# external lookup, rather than trying to translate every query blindly.
_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def needs_translation(text: str) -> bool:
    """Whether `text` contains Cyrillic and therefore is unlikely to find
    anything by itself in external, mostly English-indexed book catalogs."""
    return bool(_CYRILLIC_RE.search(text))


def translate_to_english(text: str) -> str | None:
    """Best-effort translation of a Ukrainian (or other Cyrillic) search
    query into English so it can be matched against external book catalogs.

    Returns None — never raises — if translation isn't configured or the
    request fails. External search is a nice-to-have on top of the local
    catalog, not a hard dependency, so a translation failure must never
    break the surrounding search.
    """
    text = text.strip()
    if not text:
        return None

    cache_key = f"{_CACHE_PREFIX}{text.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return None if cached == _MISS_SENTINEL else cached

    api_key = getattr(settings, "GOOGLE_TRANSLATE_API_KEY", "")
    if not api_key:
        return None

    params = urllib.parse.urlencode(
        {"q": text, "source": "uk", "target": "en", "format": "text", "key": api_key}
    )
    request = urllib.request.Request(f"{_API_BASE}?{params}", method="POST")

    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
            data = json.loads(response.read())
        translated: str = data["data"]["translations"][0]["translatedText"]
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, ValueError) as exc:
        logger.warning("Query translation failed for %r: %s", text, exc)
        cache.set(cache_key, _MISS_SENTINEL, _CACHE_TTL)
        return None

    translated = translated.strip()
    cache.set(cache_key, translated or _MISS_SENTINEL, _CACHE_TTL)
    return translated or None
