from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Notification


class NotificationMarkReadView(APIView):
    """
    Kept separate from ProfileNotificationsReadView (which marks *all* as read):
    this marks a single notification.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        notification = generics.get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response({"ok": True})
