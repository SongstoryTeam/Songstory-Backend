import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ExternalServiceError(Exception):
    pass


def get_json(url: str, params: dict | None = None) -> dict:
    try:
        response = requests.get(url, params=params, timeout=settings.EXTERNAL_HTTP_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("External request to %s failed: %s", url, exc)
        raise ExternalServiceError(str(exc)) from exc
