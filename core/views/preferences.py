from django.shortcuts import render

from core.services.preferences import THEME_OPTIONS


def settings_page(request):
    return render(request, "core/settings.html", {"theme_options": THEME_OPTIONS})
