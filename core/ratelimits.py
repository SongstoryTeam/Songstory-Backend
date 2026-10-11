from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

USER_OR_IP = "user_or_ip"
IP = "ip"


def client_ip(request) -> str:
    """IP клієнта з урахуванням довірених проксі.

    За reverse-proxy (Render, Fly, Nginx…) `REMOTE_ADDR` — це адреса самого проксі,
    тож усі відвідувачі потрапляють в один спільний ліміт. Кількість довірених
    проксі задається `TRUSTED_PROXY_COUNT`; IP береться з кінця `X-Forwarded-For`,
    бо ліву частину заголовка клієнт може підробити.
    """
    remote = request.META.get("REMOTE_ADDR", "")
    proxies = getattr(settings, "TRUSTED_PROXY_COUNT", 0)
    if proxies <= 0:
        return remote
    chain = [part.strip() for part in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if part.strip()]
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
                    return JsonResponse({"error": "rate_limited"}, status=429)
                return render(request, "429.html", status=429)

        return wrapper

    return decorator
