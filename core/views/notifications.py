from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404

from core.models.notification import Notification


@login_required
def notification_list(request):
    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("content_type")
        .order_by("-created_at")[:20]
    )
    data = [
        {
            "id": n.pk,
            "type": n.type,
            "type_display": n.get_type_display(),
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]
    return JsonResponse({"notifications": data, "unread_count": Notification.unread_count(request.user)})


@login_required
def notification_mark_read(request, pk: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return JsonResponse({"ok": True})


@login_required
def notification_mark_all_read(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    count = Notification.mark_all_read(request.user)
    return JsonResponse({"marked": count})
