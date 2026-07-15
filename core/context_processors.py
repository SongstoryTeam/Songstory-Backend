from django.conf import settings


def site(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_DOMAIN": settings.SITE_DOMAIN,
        "CANONICAL_URL": f"https://{settings.SITE_DOMAIN}{request.path}",
        "PLAUSIBLE_DOMAIN": getattr(settings, "PLAUSIBLE_DOMAIN", ""),
        "GOOGLE_SITE_VERIFICATION": getattr(settings, "GOOGLE_SITE_VERIFICATION", ""),
    }


def notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notifications": 0}
    from .models.notification import Notification
    return {"unread_notifications": Notification.unread_count(request.user)}
