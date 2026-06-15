from django.conf import settings


def site(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
        'PLAUSIBLE_DOMAIN': getattr(settings, 'PLAUSIBLE_DOMAIN', ''),
        'GOOGLE_SITE_VERIFICATION': getattr(settings, 'GOOGLE_SITE_VERIFICATION', ''),
    }
