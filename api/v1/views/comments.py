from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Book, Chapter, Comment, Playlist
from api.v1.serializers.comments import CommentSerializer


class CommentCreateView(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        data = self.request.data
        book = Book.objects.filter(pk=data.get("book_id")).first() if data.get("book_id") else None
        chapter = Chapter.objects.filter(pk=data.get("chapter_id")).first() if data.get("chapter_id") else None
        playlist = Playlist.objects.filter(pk=data.get("playlist_id")).first() if data.get("playlist_id") else None
        parent = Comment.objects.filter(pk=data.get("parent_id")).first() if data.get("parent_id") else None

        serializer.save(
            user=self.request.user,
            book=book,
            chapter=chapter,
            playlist=playlist,
            parent=parent,
        )


class CommentDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk: int):
        comment = generics.get_object_or_404(Comment, pk=pk)
        if comment.user != request.user and not request.user.is_staff:
            return Response({"error": "Forbidden"}, status=403)
        comment.delete()
        return Response(status=204)
