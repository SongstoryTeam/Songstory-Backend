import urllib.error
import urllib.request

from django.core.exceptions import ValidationError

_ALLOWED_CONTENT_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/avif",
})

_TIMEOUT = 5


def validate_image_url(url: str) -> None:
    if not url:
        return
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError):
        raise ValidationError("Could not reach the URL. Make sure it is publicly accessible.")

    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise ValidationError(f'URL does not point to an image (got "{content_type}").')
