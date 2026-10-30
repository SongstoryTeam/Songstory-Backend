from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect

from core.utils.redirects import safe_redirect_target
from staffpanel.actions import Registry, execute

NOTHING_TO_DO = "Немає елементів, до яких можна застосувати цю дію."
ACTION_PARAM = "action"
IDS_PARAM = "ids"


def selected_ids(request) -> list[int]:
    raw = request.POST.getlist(IDS_PARAM)[: settings.STAFF_BULK_MAX]
    return [int(value) for value in raw if value.isdigit()]


def run_action(request, actions: Registry, key: str, queryset, fallback: str):
    action = actions.get(key)
    if action is None or not request.user.has_perm(str(action.permission)):
        raise Http404
    count = execute(action, request.user, queryset)
    if count:
        messages.success(request, action.done_message.format(count=count))
    else:
        messages.info(request, NOTHING_TO_DO)
    return redirect(safe_redirect_target(request, fallback))
