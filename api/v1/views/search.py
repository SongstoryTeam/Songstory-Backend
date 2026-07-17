from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.services.open_library import open_library_client
from api.v1.services.spotify import SpotifyError, spotify_client
from core.rate_limit import search_limit


class MusicSearchView(APIView):
    permission_classes = (AllowAny,)

    @search_limit
    def get(self, request: Request) -> Response:
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response({"results": []})

        try:
            tracks = spotify_client.search_tracks(query, limit=10)
        except SpotifyError as exc:
            return Response({"error": str(exc), "results": []}, status=502)

        results = [
            {
                "spotify_id": t.spotify_id,
                "title": t.title,
                "artist": t.artist,
                "album": t.album,
                "cover_url": t.cover_url,
                "preview_url": t.preview_url,
                "spotify_url": t.spotify_url,
            }
            for t in tracks
        ]
        return Response({"results": results})


class BookSearchView(APIView):
    permission_classes = (AllowAny,)

    @search_limit
    def get(self, request: Request) -> Response:
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response({"results": []})

        books = open_library_client.search(query, limit=10)
        results = [
            {
                "open_library_id": b.open_library_id,
                "title": b.title,
                "author": b.author,
                "year": b.year,
                "isbn": b.isbn,
                "description": b.description,
                "cover_url": b.cover_url,
            }
            for b in books
        ]
        return Response({"results": results})