import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SECRET_PARAM = re.compile(r"(key=)[^&\s'\"]+")
MAX_DETAIL_LENGTH = 300


class ExternalServiceError(Exception):
    def __init__(self, message: str, status: int | None = None, detail: str = ""):
        super().__init__(message)
        self.status = status
        self.detail = detail


def redact(text: str) -> str:
    return SECRET_PARAM.sub(r"\1***", text)


def _error_detail(response: requests.Response) -> str:
    try:
        message = response.json().get("error", {}).get("message", "")
    except (ValueError, AttributeError):
        message = response.text
    return redact(str(message))[:MAX_DETAIL_LENGTH]


def _headers() -> dict:
    # Open Library просить представлятися у User-Agent; іншим джерелам це не шкодить.
    return {"User-Agent": settings.EXTERNAL_HTTP_USER_AGENT, "Accept": "application/json"}


def get_json(url: str, params: dict | None = None) -> dict:
    try:
        response = requests.get(
            url, params=params, headers=_headers(), timeout=settings.EXTERNAL_HTTP_TIMEOUT
        )
    except requests.RequestException as exc:
        message = redact(str(exc))
        logger.warning("External request to %s failed: %s", url, message)
        raise ExternalServiceError(message) from None

    if not response.ok:
        detail = _error_detail(response)
        logger.warning("External request to %s failed: HTTP %s %s", url, response.status_code, detail)
        raise ExternalServiceError(f"HTTP {response.status_code}", status=response.status_code, detail=detail)

    try:
        return response.json()
    except ValueError:
        logger.warning("External request to %s returned invalid JSON", url)
        raise ExternalServiceError("Invalid JSON") from None
