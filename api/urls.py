from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from api.v1.views.auth import LoginView, MeView, RegisterView
from api.v1.views.books import (
    BookListView,
    BookDetailView,
    BookChaptersView,
    BookTopMusicView,
    BookPlaylistsView,
    SaveBookView,
    RateBookView,
)
from api.v1.views.chapters import (
    ChapterDetailView,
    ChapterMusicView,
    AddBulkChaptersView,
    MusicLikeView,
    MusicDeleteView,
)
from api.v1.views.playlists import (
    PlaylistDetailView,
    PlaylistCreateView,
    PlaylistLikeView,
    PlaylistAddTrackView,
)
from api.v1.views.comments import CommentCreateView, CommentDeleteView
from api.v1.views.social import (
    AuthorProfileView,
    FollowUserView,
    NotificationListView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
)
from api.v1.views.youtube import YouTubeSearchView

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────
    path("auth/token/", LoginView.as_view(), name="api_token_obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="api_token_refresh"),
    path("auth/register/", RegisterView.as_view(), name="api_register"),
    path("auth/me/", MeView.as_view(), name="api_me"),

    # ── Books ─────────────────────────────────────────────────────────────
    path("books/", BookListView.as_view(), name="api_books_list"),
    path("books/<str:slug>/", BookDetailView.as_view(), name="api_book_detail"),
    path("books/<int:pk>/chapters/", BookChaptersView.as_view(), name="api_book_chapters"),
    path("books/<int:pk>/top-music/", BookTopMusicView.as_view(), name="api_book_top_music"),
    path("books/<int:pk>/playlists/", BookPlaylistsView.as_view(), name="api_book_playlists"),
    path("books/<int:pk>/save/", SaveBookView.as_view(), name="api_book_save"),
    path("books/<int:pk>/rate/", RateBookView.as_view(), name="api_book_rate"),
    path("books/<int:book_id>/chapters/bulk/", AddBulkChaptersView.as_view(), name="api_chapters_bulk"),

    # ── Chapters ──────────────────────────────────────────────────────────
    path(
        "books/<int:book_id>/chapters/<int:num>/",
        ChapterDetailView.as_view(),
        name="api_chapter_detail",
    ),
    path("chapters/<int:chapter_id>/music/", ChapterMusicView.as_view(), name="api_chapter_music"),

    # ── Music ─────────────────────────────────────────────────────────────
    path("music/<int:pk>/like/", MusicLikeView.as_view(), name="api_music_like"),
    path("music/<int:pk>/", MusicDeleteView.as_view(), name="api_music_delete"),

    # ── Playlists ─────────────────────────────────────────────────────────
    path("playlists/", PlaylistCreateView.as_view(), name="api_playlists_create"),
    path("playlists/<str:slug>/", PlaylistDetailView.as_view(), name="api_playlist_detail"),
    path("playlists/<int:pk>/like/", PlaylistLikeView.as_view(), name="api_playlist_like"),
    path("playlists/<int:pk>/tracks/", PlaylistAddTrackView.as_view(), name="api_playlist_add_track"),

    # ── Comments ──────────────────────────────────────────────────────────
    path("comments/add/", CommentCreateView.as_view(), name="api_comment_add"),
    path("comments/<int:pk>/delete/", CommentDeleteView.as_view(), name="api_comment_delete"),

    # ── Social ────────────────────────────────────────────────────────────
    path("author/<int:pk>/", AuthorProfileView.as_view(), name="api_author_profile"),
    path("user/<int:pk>/follow/", FollowUserView.as_view(), name="api_follow_user"),

    # ── Notifications ─────────────────────────────────────────────────────
    path("notifications/", NotificationListView.as_view(), name="api_notifications"),
    path("notifications/<int:pk>/read/", NotificationMarkReadView.as_view(), name="api_notification_read"),
    path("notifications/read-all/", NotificationMarkAllReadView.as_view(), name="api_notifications_read_all"),

    # ── Utilities ─────────────────────────────────────────────────────────
    path("youtube-search/", YouTubeSearchView.as_view(), name="api_youtube_search"),
]
