from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import AuthorVerification, Book
from core.notifications import notify_admin_new_verification


class AuthorVerificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorVerification
        fields = (
            "book",
            "proof_document",
            "proof_authorship",
            "publisher_url",
            "additional_notes",
        )


class AuthorVerificationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        serializer = AuthorVerificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        book: Book = serializer.validated_data["book"]

        if AuthorVerification.objects.filter(
            user=request.user,
            book=book,
            status=AuthorVerification.STATUS_PENDING,
        ).exists():
            return Response(
                {"detail": "Application already under review."},
                status=status.HTTP_409_CONFLICT,
            )

        if AuthorVerification.objects.filter(
            user=request.user,
            book=book,
            status=AuthorVerification.STATUS_APPROVED,
        ).exists():
            return Response(
                {"detail": "Authorship already verified."},
                status=status.HTTP_409_CONFLICT,
            )

        verification = serializer.save(user=request.user)
        notify_admin_new_verification(verification)
        return Response(
            {"detail": "Application submitted successfully."},
            status=status.HTTP_201_CREATED,
        )