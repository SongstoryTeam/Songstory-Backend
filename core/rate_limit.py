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
    """
    Works both on plain Django function-based views `def view(request, ...)`
    and on DRF class-based view methods `def get(self, request, ...)`.

    django_ratelimit's own decorator assumes the request is the first
    positional argument, which breaks for unbound class methods (where the
    first argument is `self`). We detect which shape we're dealing with and
    always present django_ratelimit with a plain (request, ...) call.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if args and hasattr(args[0], "META") and hasattr(args[0], "method"):
                self_obj, request, rest = None, args[0], args[1:]
            elif len(args) > 1 and hasattr(args[1], "META") and hasattr(args[1], "method"):
                self_obj, request, rest = args[0], args[1], args[2:]
            else:
                raise TypeError("rate_limit could not locate the HttpRequest argument")

            def _call(req, *a, **kw):
                if self_obj is None:
                    return view_func(req, *a, **kw)
                return view_func(self_obj, req, *a, **kw)

            is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
            decorated = ratelimit(key=key, rate=rate, method=method, block=block)(_call)
            try:
                return decorated(request, *rest, **kwargs)
            except Ratelimited:
                return _handle_ratelimited(request, is_ajax)

        return wrapped

    return decorator


likes_limit = rate_limit(key="user_or_ip:id", rate="30/m")
comments_limit = rate_limit(key="user_or_ip:id", rate="10/m")
add_music_limit = rate_limit(key="user_or_ip:id", rate="20/h")
signup_limit = rate_limit(key="ip", rate="5/h")
youtube_search_limit = rate_limit(key="ip", rate="60/m", method="GET")
search_limit = rate_limit(key="ip", rate="60/m", method="GET")
book_import_limit = rate_limit(key="user_or_ip:id", rate="20/h")
