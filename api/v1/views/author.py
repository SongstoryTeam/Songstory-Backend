from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Author, Follow
from api.v1.serializers.author import AuthorSerializer


class AuthorDetailView(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request: Request, slug: str) -> Response:
        author = get_object_or_404(Author, slug=slug)
        serializer = AuthorSerializer(author, context={"request": request})
        data = serializer.data

        book_with_author = (
            author.books.filter(verified_author__isnull=False)
            .select_related("verified_author")
            .first()
        )
        target = book_with_author.verified_author if book_with_author else None

        if request.user.is_authenticated:
            data["is_following"] = (
                Follow.objects.filter(follower=request.user, following=target).exists()
                if target
                else False
            )

        data["followers_count"] = target.followers.count() if target else 0
        return Response(data)


class AuthorFollowView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request, slug: str) -> Response:
        author = get_object_or_404(Author, slug=slug)

        book_with_author = (
            author.books.filter(verified_author__isnull=False)
            .select_related("verified_author")
            .first()
        )
        if not book_with_author:
            return Response(
                {"detail": "This author has no verified user account."},
                status=status.HTTP_404_NOT_FOUND,
            )

        target: User = book_with_author.verified_author

        if target == request.user:
            return Response(
                {"detail": "Cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow, created = Follow.objects.get_or_create(
            follower=request.user, following=target
        )
        if not created:
            follow.delete()
        return Response({"following": created})