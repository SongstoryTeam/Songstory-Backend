from functools import wraps
from http import HTTPStatus

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

USER_OR_IP = "user_or_ip"
IP = "ip"
REMOTE_ADDR_META = "REMOTE_ADDR"
FORWARDED_FOR_META = "HTTP_X_FORWARDED_FOR"
RATE_LIMITED_ERROR = "rate_limited"
RATE_LIMITED_TEMPLATE = "429.html"


def client_ip(request) -> str:
    remote = request.META.get(REMOTE_ADDR_META, "")
    proxies = settings.TRUSTED_PROXY_COUNT
    if proxies <= 0:
        return remote
    chain = [part.strip() for part in request.META.get(FORWARDED_FOR_META, "").split(",") if part.strip()]
    if len(chain) < proxies:
        return chain[0] if chain else remote
    return chain[-proxies]


def rate_limited(name: str, *, key: str = USER_OR_IP, methods: tuple[str, ...] = ("POST",), json: bool = False):
    def decorator(view):
        limited = ratelimit(
            key=key,
            rate=lambda group, request: settings.RATE_LIMITS[name],
            method=list(methods),
            group=name,
            block=True,
        )(view)

        @wraps(view)
        def wrapper(request, *args, **kwargs):
            try:
                return limited(request, *args, **kwargs)
            except Ratelimited:
                if json:
                    return JsonResponse({"error": RATE_LIMITED_ERROR}, status=HTTPStatus.TOO_MANY_REQUESTS)
                return render(request, RATE_LIMITED_TEMPLATE, status=HTTPStatus.TOO_MANY_REQUESTS)

        return wrapper

    return decorator
