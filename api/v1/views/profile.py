from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import MusicRecommendation, Notification, Playlist, SavedBook
from api.v1.filters.pagination import NotificationCursorPagination
from api.v1.serializers.books import BookListSerializer
from api.v1.serializers.music import MusicRecommendationSerializer, PlaylistSerializer
from api.v1.serializers.notification import NotificationSerializer
from api.v1.serializers.user import UserSerializer, UserUpdateSerializer


class ProfileMeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    def patch(self, request: Request) -> Response:
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user, context={"request": request}).data)


class ProfileSavedView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        books = [
            s.book
            for s in SavedBook.objects.filter(user=request.user)
            .select_related("book__author", "book__genre")
            .prefetch_related("book__translations")
        ]
        serializer = BookListSerializer(books, many=True, context={"request": request})
        return Response(serializer.data)


class ProfilePlaylistsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        qs = Playlist.objects.filter(creator=request.user).select_related("book")
        serializer = PlaylistSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class ProfileRecommendationsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        qs = MusicRecommendation.objects.filter(user=request.user).select_related(
            "chapter__book"
        )
        serializer = MusicRecommendationSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data)


class ProfileNotificationsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        qs = Notification.objects.filter(recipient=request.user)
        paginator = NotificationCursorPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ProfileNotificationsReadView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        count = Notification.mark_all_read(request.user)
        return Response({"marked": count})