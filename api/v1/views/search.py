from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.services.google_books import GoogleBook, google_books_client
from api.v1.services.open_library import OpenLibraryBook, open_library_client
from api.v1.services.spotify import SpotifyError, spotify_client
from core.rate_limit import search_limit

GOOGLE_BOOKS_ID_PREFIX = "gbooks:"
BOOK_SEARCH_RESULT_LIMIT = 10


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

        results = [
                      self._serialize_google_book(book)
                      for book in google_books_client.search(query, limit=BOOK_SEARCH_RESULT_LIMIT)
                  ] + [
                      self._serialize_open_library_book(book)
                      for book in open_library_client.search(query, limit=BOOK_SEARCH_RESULT_LIMIT)
                  ]
        return Response({"results": results[:BOOK_SEARCH_RESULT_LIMIT]})

    @staticmethod
    def _serialize_open_library_book(book: OpenLibraryBook) -> dict:
        return {
            "open_library_id": book.open_library_id,
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
            "description": book.description,
            "cover_url": book.cover_url,
        }

    @staticmethod
    def _serialize_google_book(book: GoogleBook) -> dict:
        return {
            "open_library_id": f"{GOOGLE_BOOKS_ID_PREFIX}{book.external_id}",
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
            "description": book.description,
            "cover_url": book.cover_url,
        }
