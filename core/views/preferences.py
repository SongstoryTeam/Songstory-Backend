from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.forms import AccentForm, AvatarForm
from core.models import UserProfile
from core.ratelimits import rate_limited
from core.services.preferences import THEME_OPTIONS

JSON_MIME = "application/json"
HTML_MIME = "text/html"
SETTINGS_TEMPLATE = "core/settings.html"
AVATAR_ANCHOR = "#avatar"


def settings_context(request, avatar_form: AvatarForm | None = None) -> dict:
    context = {"theme_options": THEME_OPTIONS}
    if request.user.is_authenticated:
        profile = UserProfile.objects.for_user(request.user)
        context["accent_form"] = AccentForm(instance=profile)
        context["avatar_form"] = avatar_form or AvatarForm(instance=profile)
    return context


def settings_page(request):
    return render(request, SETTINGS_TEMPLATE, settings_context(request))


def avatar_redirect():
    return redirect(f"{reverse('core:settings')}{AVATAR_ANCHOR}")


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


@login_required
@require_POST
@rate_limited("avatar")
def update_avatar(request):
    form = AvatarForm(request.POST, instance=UserProfile.objects.for_user(request.user))
    if not form.is_valid():
        return render(request, SETTINGS_TEMPLATE, settings_context(request, avatar_form=form))

    profile = form.save()
    messages.success(request, "Фото профілю оновлено." if profile.has_avatar else "Фото профілю прибрано.")
    return avatar_redirect()


@login_required
@require_POST
@rate_limited("avatar")
def remove_avatar(request):
    UserProfile.objects.for_user(request.user).reset_avatar()
    messages.success(request, "Фото профілю прибрано.")
    return avatar_redirect()
