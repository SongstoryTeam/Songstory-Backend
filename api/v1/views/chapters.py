from django.db.models import F
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Chapter, ChapterTranslation, Language, Like, MusicRecommendation
from core.rate_limit import add_music_limit, likes_limit
from api.v1.serializers.books import ChapterSerializer, MusicRecommendationSerializer


class ChapterDetailView(generics.RetrieveAPIView):
    serializer_class = ChapterSerializer

    def get_object(self):
        chapter = generics.get_object_or_404(
            Chapter, book_id=self.kwargs["book_id"], number=self.kwargs["num"]
        )
        user = self.request.user
        is_privileged = user.is_authenticated and (
            user == chapter.book.creator or user.is_staff
        )
        if not chapter.is_approved and not is_privileged:
            from django.http import Http404
            raise Http404
        return chapter


class ChapterMusicView(generics.ListCreateAPIView):
    serializer_class = MusicRecommendationSerializer

    def get_queryset(self):
        return MusicRecommendation.objects.filter(
            chapter_id=self.kwargs["chapter_id"]
        ).select_related("user").order_by("-likes_count", "-created_at")

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        chapter = generics.get_object_or_404(Chapter, pk=self.kwargs["chapter_id"])
        serializer.save(chapter=chapter, user=self.request.user)


class AddBulkChaptersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, book_id: int):
        from core.models import Book

        book = generics.get_object_or_404(Book, pk=book_id)
        try:
            count = int(request.data.get("number_of_chapters", 0))
        except (TypeError, ValueError):
            count = 0
        if not 1 <= count <= 100:
            return Response({"error": "Invalid chapter count"}, status=400)

        last_chapter = book.chapters.order_by("-number").first()
        start_num = (last_chapter.number + 1) if last_chapter else 1
        is_owner = request.user == book.creator or request.user.is_staff

        chapters = Chapter.objects.bulk_create([
            Chapter(book=book, number=start_num + i, is_approved=is_owner)
            for i in range(count)
        ])

        uk = Language.objects.filter(code="uk").first()
        if uk:
            ChapterTranslation.objects.bulk_create([
                ChapterTranslation(chapter=ch, language=uk, title=f"Chapter {start_num + i}")
                for i, ch in enumerate(chapters)
            ])

        serializer = ChapterSerializer(chapters, many=True, context={"request": request})
        return Response(serializer.data, status=201)


class MusicLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        music = generics.get_object_or_404(MusicRecommendation, pk=pk)
        like, created = Like.objects.get_or_create(user=request.user, music_recommendation=music)

        if created:
            MusicRecommendation.objects.filter(pk=pk).update(likes_count=F("likes_count") + 1)
        else:
            like.delete()
            MusicRecommendation.objects.filter(pk=pk).update(likes_count=F("likes_count") - 1)

        music.refresh_from_db(fields=["likes_count"])
        return Response({"liked": created, "likes_count": music.likes_count})


class MusicDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk: int):
        music = generics.get_object_or_404(MusicRecommendation, pk=pk)
        if music.user != request.user and not request.user.is_staff:
            return Response({"error": "Forbidden"}, status=403)
        music.delete()
        return Response(status=204)
