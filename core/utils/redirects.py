from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme

NEXT_PARAM = "next"


def safe_redirect_target(request: HttpRequest, fallback) -> str:
    candidate = request.POST.get(NEXT_PARAM, "")
    allowed = url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return candidate if candidate and allowed else resolve_url(fallback)
