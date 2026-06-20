from django.db.models import F, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, filters as drf_filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Book, BookRating, Chapter, MusicRecommendation, Playlist, SavedBook
from api.v1.serializers.books import (
    BookListSerializer,
    ChapterSerializer,
    MusicRecommendationSerializer,
    PlaylistSerializer,
)

_SORT_MAP = {
    "newest": "-created_at",
    "popular": "-views_count",
    "year": "-year",
    "title": "translations__title",
}


class BookListView(generics.ListAPIView):
    serializer_class = BookListSerializer
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]

    def get_queryset(self):
        user = self.request.user
        qs = Book.published.all() if not (user.is_authenticated and user.is_staff) else Book.objects.all()

        search = self.request.query_params.get("search", "").strip()
        genre = self.request.query_params.get("genre", "").strip()
        sort = self.request.query_params.get("sort", "newest")

        if search:
            qs = qs.filter(
                Q(translations__title__icontains=search)
                | Q(author__translations__name__icontains=search)
                | Q(author_legacy__icontains=search)
                | Q(genre__translations__name__icontains=search)
                | Q(genre_legacy__icontains=search)
            ).distinct()

        if genre:
            qs = qs.filter(
                Q(genre__translations__name__iexact=genre) | Q(genre_legacy__iexact=genre)
            ).distinct()

        sort_field = _SORT_MAP.get(sort, "-created_at")
        if sort == "title":
            qs = qs.order_by(sort_field, "-created_at")
        else:
            qs = qs.order_by(sort_field)

        return qs


class BookDetailView(generics.RetrieveAPIView):
    serializer_class = BookListSerializer
    lookup_field = "slug"

    def get_object(self):
        lookup = self.kwargs.get("slug")
        try:
            book = Book.objects.get(slug=lookup)
        except Book.DoesNotExist:
            book = generics.get_object_or_404(Book, pk=lookup)

        if not book.is_visible_to(self.request.user):
            from django.http import Http404
            raise Http404

        session_key = f"viewed_book_{book.pk}"
        if not self.request.session.get(session_key):
            Book.objects.filter(pk=book.pk).update(views_count=F("views_count") + 1)
            self.request.session[session_key] = True

        return book


class BookChaptersView(generics.ListAPIView):
    serializer_class = ChapterSerializer

    def get_queryset(self):
        book = generics.get_object_or_404(Book, pk=self.kwargs["pk"])
        user = self.request.user
        is_privileged = user.is_authenticated and (user == book.creator or user.is_staff)
        qs = book.chapters.all() if is_privileged else book.chapters.filter(is_approved=True)
        return qs.order_by("number")


class BookTopMusicView(generics.ListAPIView):
    serializer_class = MusicRecommendationSerializer

    def get_queryset(self):
        return MusicRecommendation.objects.filter(
            chapter__book_id=self.kwargs["pk"]
        ).select_related("user", "chapter").order_by("-likes_count")[:10]


class BookPlaylistsView(generics.ListAPIView):
    serializer_class = PlaylistSerializer

    def get_queryset(self):
        return Playlist.objects.filter(
            book_id=self.kwargs["pk"], is_public=True
        ).select_related("creator", "book").order_by("-likes_count")[:10]


class SaveBookView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        book = generics.get_object_or_404(Book, pk=pk)
        saved, created = SavedBook.objects.get_or_create(user=request.user, book=book)
        if not created:
            saved.delete()
            return Response({"saved": False})
        return Response({"saved": True})


class RateBookView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        book = generics.get_object_or_404(Book, pk=pk)
        try:
            score = int(request.data.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        if not 1 <= score <= 5:
            return Response({"error": "Score must be between 1 and 5"}, status=400)
        BookRating.objects.update_or_create(user=request.user, book=book, defaults={"score": score})
        return Response({"score": score})
