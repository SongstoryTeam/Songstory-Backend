from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.forms import AccentForm
from core.models import UserProfile
from core.ratelimits import rate_limited
from core.services.preferences import THEME_OPTIONS

JSON_MIME = "application/json"
HTML_MIME = "text/html"


def settings_page(request):
    context = {"theme_options": THEME_OPTIONS}
    if request.user.is_authenticated:
        context["accent_form"] = AccentForm(instance=UserProfile.objects.for_user(request.user))
    return render(request, "core/settings.html", context)


@login_required
@require_POST
@rate_limited("accent")
def update_accent(request):
    form = AccentForm(request.POST, instance=UserProfile.objects.for_user(request.user))
    wants_json = request.get_preferred_type([HTML_MIME, JSON_MIME]) == JSON_MIME

    if not form.is_valid():
        if wants_json:
            return JsonResponse({"errors": form.errors.get_json_data()}, status=HTTPStatus.BAD_REQUEST)
        messages.error(request, "Оберіть колір зі списку.")
        return redirect("core:settings")

    profile = form.save()
    if wants_json:
        return JsonResponse({"accent": profile.accent})
    messages.success(request, "Колір оновлено.")
    return redirect("core:settings")
