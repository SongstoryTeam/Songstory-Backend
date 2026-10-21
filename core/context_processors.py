from django.conf import settings
from django.utils.text import slugify


def site(request) -> dict:
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_DOMAIN": settings.SITE_DOMAIN,
        "SITE_CONTACT_EMAIL": settings.SITE_CONTACT_EMAIL,
        "CANONICAL_URL": f"{request.scheme}://{settings.SITE_DOMAIN}{request.path}",
        "GOOGLE_AUTH_ENABLED": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "PLAUSIBLE_DOMAIN": settings.PLAUSIBLE_DOMAIN,
        "SERVICE_WORKER_ENABLED": not settings.DEBUG,
        "CACHE_PREFIX": f"{slugify(settings.SITE_NAME)}-",
        "PWA_CACHE_VERSION": settings.PWA_CACHE_VERSION,
        "PWA_THEME_COLOR": settings.PWA_THEME_COLOR,
        "PWA_BACKGROUND_COLOR": settings.PWA_BACKGROUND_COLOR,
        "SITE_DESCRIPTION": settings.SITE_DESCRIPTION,
        "PWA_ICONS": [
            {"path": settings.PWA_ICON_PATH.format(size=size), "sizes": f"{size}x{size}"}
            for size in settings.PWA_ICON_SIZES
        ],
        "FAVICON_PATH": settings.PWA_ICON_PATH.format(size=settings.PWA_FAVICON_SIZE),
        "FAVICON_SIZES": f"{settings.PWA_FAVICON_SIZE}x{settings.PWA_FAVICON_SIZE}",
        "GOOGLE_SITE_VERIFICATION": settings.GOOGLE_SITE_VERIFICATION,
        "SEARCH_SUGGEST_MIN_LENGTH": settings.SEARCH_SUGGEST_MIN_LENGTH,
        "SEARCH_SUGGEST_DEBOUNCE_MS": settings.SEARCH_SUGGEST_DEBOUNCE_MS,
    }
