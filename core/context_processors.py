from django.conf import settings


def site(request) -> dict:
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_DOMAIN": settings.SITE_DOMAIN,
        "SITE_CONTACT_EMAIL": settings.SITE_CONTACT_EMAIL,
        "CANONICAL_URL": f"{request.scheme}://{settings.SITE_DOMAIN}{request.path}",
        "GOOGLE_AUTH_ENABLED": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "PLAUSIBLE_DOMAIN": settings.PLAUSIBLE_DOMAIN,
        "GOOGLE_SITE_VERIFICATION": settings.GOOGLE_SITE_VERIFICATION,
        "SEARCH_SUGGEST_MIN_LENGTH": settings.SEARCH_SUGGEST_MIN_LENGTH,
        "SEARCH_SUGGEST_DEBOUNCE_MS": settings.SEARCH_SUGGEST_DEBOUNCE_MS,
    }
