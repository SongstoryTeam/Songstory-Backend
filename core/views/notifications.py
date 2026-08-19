from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, render

from core.models.notification import Notification

FEED_SIZE = 8
PAGE_SIZE = 20


def _serialize(notification: Notification) -> dict:
    return {
        "id": notification.pk,
        "type": notification.type,
        "message": notification.get_message(),
        "url": notification.get_absolute_url(),
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
    }


def _notification_queryset(user):
    return (
        Notification.objects.filter(recipient=user)
        .select_related("content_type")
        .prefetch_related("content_object")
    )


@login_required
def notification_list(request):
    notifications = _notification_queryset(request.user).order_by("-created_at")
    paginator = Paginator(notifications, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "core/notifications.html",
        {"page_obj": page_obj, "notifications": page_obj.object_list},
    )


@login_required
def notification_feed(request):
    """Latest notifications for the topbar dropdown, as JSON."""
    notifications = _notification_queryset(request.user).order_by("-created_at")[:FEED_SIZE]
    return JsonResponse(
        {
            "notifications": [_serialize(n) for n in notifications],
            "unread_count": Notification.unread_count(request.user),
        }
    )


@login_required
def notification_mark_read(request, pk: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return JsonResponse({"ok": True, "unread_count": Notification.unread_count(request.user)})


@login_required
def notification_mark_all_read(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    count = Notification.mark_all_read(request.user)
    return JsonResponse({"marked": count, "unread_count": 0})
