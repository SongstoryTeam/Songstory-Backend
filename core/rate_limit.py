from functools import wraps

from django.http import JsonResponse
from django.shortcuts import render
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited


def _handle_ratelimited(request, is_ajax: bool):
    if is_ajax:
        return JsonResponse({"error": "Too many requests. Please slow down."}, status=429)
    return render(request, "429.html", status=429)


def rate_limit(key: str, rate: str, method: str = "POST", block: bool = True):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
            decorated = ratelimit(key=key, rate=rate, method=method, block=block)(view_func)
            try:
                return decorated(request, *args, **kwargs)
            except Ratelimited:
                return _handle_ratelimited(request, is_ajax)
        return wrapped
    return decorator


likes_limit = rate_limit(key="user_or_ip:id", rate="30/m")
comments_limit = rate_limit(key="user_or_ip:id", rate="10/m")
add_music_limit = rate_limit(key="user_or_ip:id", rate="20/h")
signup_limit = rate_limit(key="ip", rate="5/h")
youtube_search_limit = rate_limit(key="ip", rate="60/m", method="GET")
