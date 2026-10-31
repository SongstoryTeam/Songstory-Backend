import ipaddress
import socket
import time
from dataclasses import dataclass
from enum import Enum
from urllib.parse import SplitResult, urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter

HTTPS_PORT = 443
IPV6_VERSION = 6
READ_CHUNK_BYTES = 16 * 1024
SIGNATURE_BYTES = 16

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class Failure(Enum):
    UNREACHABLE = "unreachable"
    FORBIDDEN_ADDRESS = "forbidden_address"
    NOT_AN_IMAGE = "not_an_image"
    TOO_LARGE = "too_large"


class RemoteImageError(Exception):
    def __init__(self, failure: Failure):
        super().__init__(failure.value)
        self.failure = failure


@dataclass(frozen=True)
class Signature:
    content_type: str
    marks: tuple[tuple[int, bytes], ...]

    def matches(self, head: bytes) -> bool:
        return all(head[offset : offset + len(mark)] == mark for offset, mark in self.marks)


SIGNATURES = (
    Signature("image/jpeg", ((0, b"\xff\xd8\xff"),)),
    Signature("image/png", ((0, b"\x89PNG\r\n\x1a\n"),)),
    Signature("image/gif", ((0, b"GIF87a"),)),
    Signature("image/gif", ((0, b"GIF89a"),)),
    Signature("image/webp", ((0, b"RIFF"), (8, b"WEBP"))),
)


@dataclass(frozen=True)
class FetchPolicy:
    allowed_types: frozenset[str]
    max_bytes: int
    timeout: float
    deadline: float
    user_agent: str


class PinnedAdapter(HTTPAdapter):
    def __init__(self, hostname: str):
        self.hostname = hostname
        super().__init__()

    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, server_hostname=self.hostname, assert_hostname=self.hostname, **kwargs)


def sniff_content_type(head: bytes) -> str | None:
    return next((item.content_type for item in SIGNATURES if item.matches(head)), None)


def authority(host: str, port: int | None) -> str:
    return host if port in (None, HTTPS_PORT) else f"{host}:{port}"


def resolve_public_address(host: str, port: int) -> IPAddress:
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        raise RemoteImageError(Failure.UNREACHABLE) from None

    addresses = []
    for record in records:
        address = ipaddress.ip_address(record[4][0].split("%")[0])
        addresses.append(getattr(address, "ipv4_mapped", None) or address)
    if not addresses or not all(address.is_global for address in addresses):
        raise RemoteImageError(Failure.FORBIDDEN_ADDRESS)
    return min(addresses, key=lambda address: address.version)


def pinned_url(parts: SplitResult, address: IPAddress) -> str:
    host = f"[{address}]" if address.version == IPV6_VERSION else str(address)
    return urlunsplit(parts._replace(netloc=authority(host, parts.port)))


def declared_size(response: requests.Response) -> int | None:
    value = response.headers.get("Content-Length", "")
    return int(value) if value.isdigit() else None


def read_head(response: requests.Response, policy: FetchPolicy) -> bytes:
    size = declared_size(response)
    if size is not None and size > policy.max_bytes:
        raise RemoteImageError(Failure.TOO_LARGE)

    head = b""
    received = 0
    started = time.monotonic()
    try:
        for chunk in response.iter_content(READ_CHUNK_BYTES):
            head = (head + chunk)[:SIGNATURE_BYTES]
            received += len(chunk)
            if received > policy.max_bytes:
                raise RemoteImageError(Failure.TOO_LARGE)
            if time.monotonic() - started > policy.deadline:
                raise RemoteImageError(Failure.UNREACHABLE)
            if size is not None and len(head) == SIGNATURE_BYTES:
                break
    except requests.RequestException:
        raise RemoteImageError(Failure.UNREACHABLE) from None
    return head


def fetch_image_type(url: str, policy: FetchPolicy) -> str:
    parts = urlsplit(url)
    address = resolve_public_address(parts.hostname, parts.port or HTTPS_PORT)
    headers = {
        "Host": authority(parts.hostname, parts.port),
        "User-Agent": policy.user_agent,
        "Accept": "image/*",
        "Accept-Encoding": "identity",
    }

    with requests.Session() as session:
        session.trust_env = False
        session.mount("https://", PinnedAdapter(parts.hostname))
        try:
            response = session.get(
                pinned_url(parts, address),
                headers=headers,
                timeout=policy.timeout,
                stream=True,
                allow_redirects=False,
            )
        except requests.RequestException:
            raise RemoteImageError(Failure.UNREACHABLE) from None
        try:
            if response.status_code != requests.codes.ok:
                raise RemoteImageError(Failure.UNREACHABLE)
            content_type = sniff_content_type(read_head(response, policy))
        finally:
            response.close()

    if content_type not in policy.allowed_types:
        raise RemoteImageError(Failure.NOT_AN_IMAGE)
    return content_type
