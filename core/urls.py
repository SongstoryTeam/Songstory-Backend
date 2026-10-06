from django.urls import path

from core.views import books, catalog, comments, music, accounts, playlists, verification

app_name = "core"

urlpatterns = [
    path("", catalog.home, name="home"),
    path("books/", catalog.book_list, name="book_list"),
    path("search/", catalog.search, name="search"),
    path("search/suggest/", catalog.search_suggest, name="search_suggest"),
    path("book/create/", books.create_book, name="create_book"),
    path("book/import/", books.import_book, name="import_book"),
    path("book/<slug:slug>/", books.book_detail, name="book_detail"),
    path("book/<slug:slug>/chapters/add/", books.add_chapters, name="add_chapters"),
    path("book/<slug:slug>/chapter/<int:number>/", books.chapter_detail, name="chapter_detail"),
    path("book/<slug:slug>/recommend/", music.recommend, name="recommend"),
    path("book/<slug:slug>/playlists/new/", playlists.playlist_create, name="playlist_create"),
    path("book/<slug:slug>/author/apply/", verification.apply_author, name="apply_author"),
    path("recommendations/<int:pk>/delete/", music.recommendation_delete, name="recommendation_delete"),
    path("playlist/<int:pk>/", playlists.playlist_detail, name="playlist_detail"),
    path("playlist/<int:pk>/tracks/add/", playlists.playlist_add_track, name="playlist_add_track"),
    path("playlist/<int:pk>/items/<int:item_pk>/remove/", playlists.playlist_remove_item, name="playlist_remove_item"),
    path("playlist/<int:pk>/delete/", playlists.playlist_delete, name="playlist_delete"),
    path("comments/add/", comments.add_comment, name="add_comment"),
    path("comments/<int:pk>/delete/", comments.delete_comment, name="delete_comment"),
    path("profile/", accounts.profile, name="profile"),
    path("verification/<int:pk>/<str:field>/", verification.proof_download, name="proof_download"),
]
