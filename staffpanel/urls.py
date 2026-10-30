from django.urls import path

from staffpanel.views import activity, books, comments, dashboard, users, verifications

app_name = "staff"

urlpatterns = [
    path("", dashboard.dashboard, name="dashboard"),
    path("books/", books.book_list, name="books"),
    path("books/bulk/", books.book_bulk, name="book_bulk"),
    path("books/<int:pk>/<slug:action>/", books.book_action, name="book_action"),
    path("verifications/", verifications.verification_list, name="verifications"),
    path("verifications/<int:pk>/", verifications.verification_detail, name="verification_detail"),
    path("verifications/<int:pk>/proof/<str:field>/", verifications.proof_download, name="proof_download"),
    path("users/", users.user_list, name="users"),
    path("users/<int:pk>/", users.user_detail, name="user_detail"),
    path("users/<int:pk>/<slug:action>/", users.user_action, name="user_action"),
    path("comments/", comments.comment_list, name="comments"),
    path("comments/bulk/", comments.comment_bulk, name="comment_bulk"),
    path("comments/<int:pk>/<slug:action>/", comments.comment_action, name="comment_action"),
    path("activity/", activity.activity_list, name="activity"),
]
