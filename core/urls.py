from django.urls import path

from core import views
from core.views.notifications import (
    notification_list,
    notification_mark_read,
    notification_mark_all_read,
)

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),

    path("book/<int:pk>/", views.BookDetailView.as_view(), name="book_detail"),
    path("book/<slug:slug>/", views.BookDetailView.as_view(), name="book_detail_slug"),
    path("book/<int:book_id>/save/", views.save_book, name="save_book"),
    path("book/<int:book_id>/rate/", views.rate_book, name="rate_book"),
    path("book/create/", views.create_book, name="create_book"),

    path("book/<int:book_id>/chapter/<int:chapter_num>/", views.ChapterDetailView.as_view(), name="chapter_detail"),
    path("chapter/<int:chapter_id>/add-music/", views.add_music_recommendation, name="add_music"),
    path("music/<int:music_id>/like/", views.like_music, name="like_music"),
    path("music/<int:music_id>/delete/", views.delete_music, name="delete_music"),
    path("book/<int:book_id>/add-chapters/", views.add_chapters, name="add_chapters"),

    path("book/<int:book_id>/create-playlist/", views.create_playlist, name="create_playlist"),
    path("playlist/<int:pk>/", views.PlaylistDetailView.as_view(), name="playlist_detail"),
    path("playlist/<slug:slug>/", views.PlaylistDetailView.as_view(), name="playlist_detail_slug"),
    path("playlist/<int:playlist_id>/like/", views.like_playlist, name="like_playlist"),
    path("playlist/<int:pk>/add-track/", views.add_track_to_playlist, name="add_track"),

    path("comments/add/", views.add_comment, name="add_comment"),
    path("comments/<int:comment_id>/delete/", views.delete_comment, name="delete_comment"),

    path("author/apply/<int:book_id>/", views.apply_author_verification, name="apply_author"),
    path("author/<int:user_id>/", views.author_profile, name="author_profile"),

    path("user/<int:user_id>/follow/", views.follow_user, name="follow_user"),

    path("youtube-search/", views.youtube_search, name="youtube_search"),

    path("profile/", views.profile, name="profile"),

    path("notifications/", notification_list, name="notifications"),
    path("notifications/<int:pk>/read/", notification_mark_read, name="notification_read"),
    path("notifications/read-all/", notification_mark_all_read, name="notifications_read_all"),

    path("about/", views.AboutView.as_view(), name="about"),
]
