from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

USER_OR_IP = "user_or_ip"
IP = "ip"


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
