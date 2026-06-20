from django.contrib.auth.models import User
from django.http import Http404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Book, Follow, Notification
from api.v1.serializers.books import BookListSerializer


class AuthorProfileView(APIView):
    def get(self, request, pk: int):
        author_user = generics.get_object_or_404(User, pk=pk)
        if not hasattr(author_user, "profile") or not author_user.profile.is_verified_author:
            raise Http404

        authored_books = Book.objects.filter(verified_author=author_user)
        followers_count = author_user.followers.count()
        is_following = (
            request.user.is_authenticated
            and Follow.objects.filter(follower=request.user, following=author_user).exists()
        )

        return Response(
            {
                "id": author_user.id,
                "username": author_user.username,
                "fullName": author_user.get_full_name() or author_user.username,
                "bio": getattr(author_user.profile, "bio", ""),
                "followersCount": followers_count,
                "isFollowing": is_following,
                "books": BookListSerializer(
                    authored_books, many=True, context={"request": request}
                ).data,
            }
        )


class FollowUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        target = generics.get_object_or_404(User, pk=pk)
        if target == request.user:
            return Response({"error": "Cannot follow yourself"}, status=400)
        follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
        if not created:
            follow.delete()
            return Response({"following": False})
        return Response({"following": True})


class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        notifications = (
            Notification.objects.filter(recipient=request.user)
            .select_related("content_type")
            .order_by("-created_at")[:20]
        )
        data = [
            {
                "id": n.pk,
                "type": n.type,
                "typeDisplay": n.get_type_display(),
                "isRead": n.is_read,
                "createdAt": n.created_at.isoformat(),
            }
            for n in notifications
        ]
        return Response({"notifications": data, "unreadCount": Notification.unread_count(request.user)})


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        notification = generics.get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response({"ok": True})


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        count = Notification.mark_all_read(request.user)
        return Response({"marked": count})
