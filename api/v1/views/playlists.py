from django.db.models import F
from django.http import Http404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Book, Chapter, Like, Playlist, PlaylistTrack
from core.utils.slugs import generate_unique_slug
from api.v1.serializers.books import PlaylistSerializer


class PlaylistDetailView(generics.RetrieveAPIView):
    serializer_class = PlaylistSerializer
    lookup_field = "slug"

    def get_object(self):
        lookup = self.kwargs.get("slug")
        try:
            playlist = Playlist.objects.get(slug=lookup)
        except Playlist.DoesNotExist:
            playlist = generics.get_object_or_404(Playlist, pk=lookup)

        user = self.request.user
        is_owner_or_staff = user.is_authenticated and (user == playlist.creator or user.is_staff)
        if not playlist.is_public and not is_owner_or_staff:
            raise Http404

        return playlist


class PlaylistCreateView(generics.CreateAPIView):
    serializer_class = PlaylistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        book = generics.get_object_or_404(Book, pk=self.request.data.get("book"))
        chapter_id = self.request.data.get("chapter")
        chapter = Chapter.objects.filter(pk=chapter_id).first() if chapter_id else None
        slug = generate_unique_slug(Playlist, self.request.data.get("title", ""))
        serializer.save(book=book, chapter=chapter, creator=self.request.user, slug=slug)


class PlaylistLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        playlist = generics.get_object_or_404(Playlist, pk=pk)
        like, created = Like.objects.get_or_create(user=request.user, playlist=playlist)

        if created:
            Playlist.objects.filter(pk=pk).update(likes_count=F("likes_count") + 1)
        else:
            like.delete()
            Playlist.objects.filter(pk=pk).update(likes_count=F("likes_count") - 1)

        playlist.refresh_from_db(fields=["likes_count"])
        return Response({"liked": created, "likes_count": playlist.likes_count})


class PlaylistAddTrackView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        playlist = generics.get_object_or_404(Playlist, pk=pk)
        if request.user != playlist.creator:
            return Response({"error": "Only the playlist creator can add tracks."}, status=403)

        last = playlist.tracks.order_by("-order").first()
        order = (last.order + 1) if last else 1

        track = PlaylistTrack.objects.create(
            playlist=playlist,
            track_title=request.data.get("track_title", ""),
            artist=request.data.get("artist", ""),
            link_url=request.data.get("link_url", ""),
            order=order,
        )

        return Response(
            {
                "id": track.id,
                "trackTitle": track.track_title,
                "artist": track.artist,
                "linkUrl": track.link_url,
                "order": track.order,
            },
            status=201,
        )
