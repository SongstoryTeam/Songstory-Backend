import ipaddress
from enum import Enum
from urllib.parse import SplitResult, urlsplit

from django.conf import settings

from core.validators import BYTES_PER_MEGABYTE

from .normalize import clean_cover_url as clean_image_url
from .remote_image import HTTPS_PORT, Failure, FetchPolicy, RemoteImageError, fetch_image_type


class Rejection(Enum):
    INVALID_URL = "Потрібне пряме https-посилання на фото."
    FORBIDDEN_HOST = "Це джерело не підтримується. Використайте інший хостинг зображень."
    UNREACHABLE = "Не вдалося завантажити фото за цим посиланням. Перевірте його й спробуйте ще раз."
    NOT_AN_IMAGE = "Посилання має вести на фото у форматі {formats}."
    TOO_LARGE = "Фото завелике. Максимальний розмір — {limit} МБ."


TRANSIENT_REJECTIONS = frozenset({Rejection.UNREACHABLE})

FAILURE_REJECTIONS = {
    Failure.UNREACHABLE: Rejection.UNREACHABLE,
    Failure.FORBIDDEN_ADDRESS: Rejection.FORBIDDEN_HOST,
    Failure.NOT_AN_IMAGE: Rejection.NOT_AN_IMAGE,
    Failure.TOO_LARGE: Rejection.TOO_LARGE,
}


def supported_formats() -> str:
    return ", ".join(sorted({content_type.split("/")[1].upper() for content_type in settings.AVATAR_CONTENT_TYPES}))


class AvatarRejected(Exception):
    def __init__(self, rejection: Rejection):
        self.rejection = rejection
        message = rejection.value.format(
            formats=supported_formats(), limit=settings.AVATAR_MAX_BYTES // BYTES_PER_MEGABYTE
        )
        super().__init__(message)

    @property
    def is_transient(self) -> bool:
        return self.rejection in TRANSIENT_REJECTIONS


def is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def is_blocked_host(host: str) -> bool:
    return any(host == blocked or host.endswith(f".{blocked}") for blocked in settings.AVATAR_BLOCKED_HOSTS)


def check_location(parts: SplitResult) -> None:
    try:
        port = parts.port
    except ValueError:
        raise AvatarRejected(Rejection.INVALID_URL) from None

    host = parts.hostname or ""
    has_credentials = bool(parts.username or parts.password)
    if has_credentials or port not in (None, HTTPS_PORT) or not host.isascii() or "." not in host:
        raise AvatarRejected(Rejection.INVALID_URL)
    if is_ip_literal(host) or is_blocked_host(host):
        raise AvatarRejected(Rejection.FORBIDDEN_HOST)


def fetch_policy() -> FetchPolicy:
    return FetchPolicy(
        allowed_types=frozenset(settings.AVATAR_CONTENT_TYPES),
        max_bytes=settings.AVATAR_MAX_BYTES,
        timeout=settings.AVATAR_FETCH_TIMEOUT,
        deadline=settings.AVATAR_FETCH_DEADLINE,
        user_agent=settings.EXTERNAL_HTTP_USER_AGENT,
    )


def validate_avatar_url(raw: str) -> str:
    url = clean_image_url(raw)
    if not url:
        raise AvatarRejected(Rejection.INVALID_URL)
    check_location(urlsplit(url))
    try:
        fetch_image_type(url, fetch_policy())
    except RemoteImageError as error:
        raise AvatarRejected(FAILURE_REJECTIONS[error.failure]) from None
    return url
