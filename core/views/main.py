
import json
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.generic import DetailView, TemplateView
from django.views.static import serve

from core.forms import (
    AuthorVerificationForm,
    BookForm,
    BookRatingForm,
    BulkChaptersForm,
    CommentForm,
    MusicRecommendationForm,
    PlaylistForm,
    PlaylistTrackForm,
    SignUpForm,
    UserUpdateForm,
)
from core.models import (
    AuthorVerification,
    Book,
    BookRating,
    BookTranslation,
    Chapter,
    ChapterTranslation,
    Comment,
    Follow,
    Language,
    Like,
    MusicRecommendation,
    Playlist,
    SavedBook,
)
from core.notifications import notify_admin_new_verification
from core.rate_limit import (
    add_music_limit,
    comments_limit,
    likes_limit,
    signup_limit,
    youtube_search_limit,
)
from core.utils.slugs import generate_unique_slug

_SORT_MAP = {
    "newest": "-created_at",
    "popular": "-views_count",
    "year": "-year",
    "title": "translations__title",
}

_SORT_OPTIONS = [
    ("newest", "New"),
    ("popular", "Popular"),
    ("year", "By year"),
    ("title", "A–Z"),
]


def _get_uk_language():
    return Language.objects.filter(code="uk").first()


def robots_txt(request):
    content = render_to_string("robots.txt", {"request": request}, request=request)
    return HttpResponse(content, content_type="text/plain")


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)


def too_many_requests(request, exception=None):
    return render(request, "429.html", status=429)


def service_worker(request):
    return serve(request, "sw.js", document_root=settings.BASE_DIR / "static")


@signup_limit
def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to {settings.SITE_NAME}!")
            return redirect("core:home")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get("search", "").strip()
        active_genre = self.request.GET.get("genre", "").strip()
        current_sort = self.request.GET.get("sort", "newest")
        user = self.request.user

        books_qs = Book.published.all() if not (user.is_authenticated and user.is_staff) else Book.objects.all()

        if search_query:
            books_qs = books_qs.filter(
                Q(translations__title__icontains=search_query)
                | Q(author__translations__name__icontains=search_query)
                | Q(genre__translations__name__icontains=search_query)
            ).distinct()

        if active_genre:
            books_qs = books_qs.filter(
                Q(genre__translations__name__iexact=active_genre)
            ).distinct()

        sort_field = _SORT_MAP.get(current_sort, "-created_at")
        if current_sort == "title":
            books_qs = books_qs.order_by(sort_field, "-created_at")
        else:
            books_qs = books_qs.order_by(sort_field)

        section_title = (
            f'Results: "{search_query}"' if search_query
            else active_genre if active_genre
            else "All books"
        )

        paginator = Paginator(books_qs, 8)
        page_obj = paginator.get_page(self.request.GET.get("page"))

        genres = sorted(set(
            Book.published.exclude(genre__isnull=True)
            .values_list("genre__translations__name", flat=True)
            .exclude(genre__translations__name=None)
        ))

        context.update({
            "db_books": page_obj,
            "page_obj": page_obj,
            "search_query": search_query,
            "active_genre": active_genre,
            "current_sort": current_sort,
            "sort_options": _SORT_OPTIONS,
            "books_section_title": section_title,
            "genres": genres,
            "top_music_db": MusicRecommendation.objects.select_related(
                "user", "chapter__book"
            ).order_by("-likes_count")[:6],
        })
        return context


class BookDetailView(DetailView):
    model = Book
    template_name = "core/book_detail.html"
    context_object_name = "book"

    def get_object(self):
        if "slug" in self.kwargs:
            book = get_object_or_404(Book, slug=self.kwargs["slug"])
        else:
            book = get_object_or_404(Book, pk=self.kwargs["pk"])
        if not book.is_visible_to(self.request.user):
            raise Http404
        return book

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.object
        user = self.request.user

        session_key = f"viewed_book_{book.pk}"
        if not self.request.session.get(session_key):
            Book.objects.filter(pk=book.pk).update(views_count=F("views_count") + 1)
            self.request.session[session_key] = True

        is_privileged = user.is_authenticated and (user == book.creator or user.is_staff)
        chapters_qs = book.chapters.all() if is_privileged else book.chapters.filter(is_approved=True)

        context.update({
            "chapters": chapters_qs,
            "popular_playlists": book.playlists.filter(is_public=True).order_by("-likes_count")[:5],
            "top_music": MusicRecommendation.objects.filter(chapter__book=book).order_by("-likes_count")[:10],
            "comments": book.comments.filter(parent=None).select_related("user").prefetch_related("replies__user"),
            "comment_form": CommentForm(),
            "book_id": book.pk,
            "rating_form": BookRatingForm(),
        })

        if user.is_authenticated:
            context["is_saved"] = SavedBook.objects.filter(user=user, book=book).exists()
            context["is_owner"] = is_privileged
            context["user_rating"] = (
                    BookRating.objects.filter(user=user, book=book).values_list("score", flat=True).first() or 0
            )
            has_pending = AuthorVerification.objects.filter(
                user=user, book=book, status=AuthorVerification.STATUS_PENDING
            ).exists()
            has_approved = AuthorVerification.objects.filter(
                user=user, book=book, status=AuthorVerification.STATUS_APPROVED
            ).exists()
            context["can_apply_author"] = not has_pending and not has_approved

        return context


class ChapterDetailView(DetailView):
    model = Chapter
    template_name = "core/chapter_detail.html"
    context_object_name = "chapter"

    def get_object(self):
        chapter = get_object_or_404(
            Chapter,
            book_id=self.kwargs["book_id"],
            number=self.kwargs["chapter_num"],
        )
        user = self.request.user
        is_privileged = user.is_authenticated and (user == chapter.book.creator or user.is_staff)
        if not chapter.is_approved and not is_privileged:
            raise Http404
        return chapter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chapter = self.object
        user = self.request.user
        is_privileged = user.is_authenticated and (user == chapter.book.creator or user.is_staff)

        chapter_qs = Chapter.objects.filter(book=chapter.book)
        if not is_privileged:
            chapter_qs = chapter_qs.filter(is_approved=True)

        verified_author = chapter.book.verified_author
        music_qs = chapter.music_recommendations.select_related("user")

        if verified_author:
            author_music = [m for m in music_qs if m.user_id == verified_author.pk]
            other_music = [m for m in music_qs if m.user_id != verified_author.pk]
        else:
            author_music = []
            other_music = list(music_qs)

        context.update({
            "music_recommendations": music_qs,
            "author_music": author_music,
            "other_music": other_music,
            "verified_author": verified_author,
            "playlists": chapter.playlists.filter(is_public=True),
            "comments": chapter.comments.filter(parent=None).select_related("user").prefetch_related("replies__user"),
            "comment_form": CommentForm(),
            "chapter_id": chapter.pk,
            "prev_chapter": chapter_qs.filter(number__lt=chapter.number).order_by("-number").first(),
            "next_chapter": chapter_qs.filter(number__gt=chapter.number).order_by("number").first(),
        })

        if user.is_authenticated:
            context["liked_music_ids"] = set(
                Like.objects.filter(
                    user=user, music_recommendation__in=music_qs
                ).values_list("music_recommendation_id", flat=True)
            )

        return context


class PlaylistDetailView(DetailView):
    model = Playlist
    template_name = "core/playlist_detail.html"
    context_object_name = "playlist"

    def get_object(self):
        if "slug" in self.kwargs:
            playlist = get_object_or_404(Playlist, slug=self.kwargs["slug"])
        else:
            playlist = get_object_or_404(Playlist, pk=self.kwargs["pk"])

        user = self.request.user
        is_owner = user.is_authenticated and (user == playlist.creator or user.is_staff)
        if not playlist.is_public and not is_owner:
            raise Http404

        return playlist

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "tracks": self.object.tracks.all(),
            "comments": self.object.comments.filter(parent=None).select_related("user").prefetch_related(
                "replies__user"),
            "comment_form": CommentForm(),
            "playlist_id": self.object.pk,
        })
        if self.request.user.is_authenticated:
            context["is_liked"] = Like.objects.filter(user=self.request.user, playlist=self.object).exists()
        return context


def author_profile(request, user_id: int):
    author_user = get_object_or_404(User, id=user_id)
    if not hasattr(author_user, "profile") or not author_user.profile.is_verified_author:
        raise Http404

    authored_books = Book.objects.filter(verified_author=author_user)
    followers_count = author_user.followers.count()
    is_following = (
            request.user.is_authenticated
            and Follow.objects.filter(follower=request.user, following=author_user).exists()
    )

    return render(request, "core/author_profile.html", {
        "author": author_user,
        "authored_books": authored_books,
        "is_following": is_following,
        "followers_count": followers_count,
    })


@login_required
def apply_author_verification(request, book_id: int):
    book = get_object_or_404(Book, id=book_id)

    if AuthorVerification.objects.filter(
            user=request.user, book=book, status=AuthorVerification.STATUS_PENDING
    ).exists():
        messages.info(request, "Your application is already under review.")
        return redirect("core:book_detail", pk=book_id)

    if AuthorVerification.objects.filter(
            user=request.user, book=book, status=AuthorVerification.STATUS_APPROVED
    ).exists():
        messages.info(request, "Your authorship has already been verified.")
        return redirect("core:book_detail", pk=book_id)

    if request.method == "POST":
        form = AuthorVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            verification = form.save(commit=False)
            verification.user = request.user
            verification.book = book
            verification.save()
            notify_admin_new_verification(verification)
            messages.success(request, "Application submitted. We will review it within 3–5 business days.")
            return redirect("core:book_detail", pk=book_id)
    else:
        form = AuthorVerificationForm()

    return render(request, "core/apply_author.html", {"form": form, "book": book})


@login_required
def follow_user(request, user_id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        return redirect("core:author_profile", user_id=user_id)
    follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        follow.delete()
    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def rate_book(request, book_id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    book = get_object_or_404(Book, id=book_id)
    try:
        score = int(request.POST.get("score", 0))
    except (TypeError, ValueError):
        score = 0
    if not 1 <= score <= 5:
        messages.error(request, "Rating must be between 1 and 5.")
        return redirect("core:book_detail", pk=book_id)
    BookRating.objects.update_or_create(user=request.user, book=book, defaults={"score": score})
    return redirect("core:book_detail", pk=book_id)


@youtube_search_limit
def youtube_search(request):
    query = request.GET.get("q", "").strip()[:100]
    if len(query) < 3:
        return JsonResponse({"results": []})

    api_key = getattr(settings, "YOUTUBE_API_KEY", "")
    if not api_key:
        return JsonResponse({"error": "YouTube API key not configured"}, status=503)

    params = urllib.parse.urlencode({
        "part": "snippet",
        "type": "video",
        "maxResults": 5,
        "q": query,
        "key": api_key,
    })
    url = f"https://www.googleapis.com/youtube/v3/search?{params}"

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
    except Exception:
        return JsonResponse({"error": "Search failed"}, status=502)

    results = [
        {
            "id": item["id"].get("videoId"),
            "title": item["snippet"].get("title", ""),
            "channel": item["snippet"].get("channelTitle", ""),
            "thumbnail": item["snippet"].get("thumbnails", {}).get("default", {}).get("url", ""),
        }
        for item in data.get("items", [])
        if item.get("id", {}).get("videoId")
    ]
    return JsonResponse({"results": results})


@login_required
@comments_limit
def add_comment(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    form = CommentForm(request.POST)
    if not form.is_valid():
        return redirect(request.META.get("HTTP_REFERER", "/"))

    book_id = request.POST.get("book_id")
    chapter_id = request.POST.get("chapter_id")
    playlist_id = request.POST.get("playlist_id")

    if not any([book_id, chapter_id, playlist_id]):
        messages.error(request, "A comment must be attached to a book, chapter or playlist.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    comment = form.save(commit=False)
    comment.user = request.user

    if book_id:
        comment.book = get_object_or_404(Book, id=book_id)
    if chapter_id:
        comment.chapter = get_object_or_404(Chapter, id=chapter_id)
    if playlist_id:
        comment.playlist = get_object_or_404(Playlist, id=playlist_id)

    parent_id = request.POST.get("parent_id")
    if parent_id:
        comment.parent = get_object_or_404(Comment, id=parent_id)

    comment.save()
    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def delete_comment(request, comment_id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user == request.user or request.user.is_staff:
        comment.delete()
    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def create_book(request):
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.creator = request.user
            book.slug = generate_unique_slug(Book, form.cleaned_data.get("title", ""))
            book.save()

            uk = _get_uk_language()
            if uk:
                BookTranslation.objects.create(
                    book=book,
                    language=uk,
                    title=form.cleaned_data.get("title", ""),
                    description=form.cleaned_data.get("description", ""),
                )

            chapter = Chapter.objects.create(book=book, number=1, is_approved=True)
            if uk:
                ChapterTranslation.objects.create(chapter=chapter, language=uk, title="Chapter 1")

            messages.success(request, "Book added successfully. It will appear in the catalog once approved.")
            return redirect("core:book_detail", pk=book.pk)
    else:
        form = BookForm()
    return render(request, "core/create_book.html", {"form": form})


@login_required
def save_book(request, book_id: int):
    book = get_object_or_404(Book, id=book_id)
    saved, created = SavedBook.objects.get_or_create(user=request.user, book=book)
    if not created:
        saved.delete()
        messages.success(request, "Book removed from saved.")
    else:
        messages.success(request, "Book saved.")
    return redirect("core:book_detail", pk=book_id)


@login_required
def add_chapters(request, book_id: int):
    book = get_object_or_404(Book, id=book_id)
    uk = _get_uk_language()

    if request.method == "POST":
        form = BulkChaptersForm(request.POST)
        if form.is_valid():
            count = form.cleaned_data["number_of_chapters"]
            last_chapter = book.chapters.order_by("-number").first()
            start_num = (last_chapter.number + 1) if last_chapter else 1
            is_owner = request.user == book.creator or request.user.is_staff

            chapters = Chapter.objects.bulk_create([
                Chapter(book=book, number=start_num + i, is_approved=is_owner)
                for i in range(count)
            ])

            if uk:
                ChapterTranslation.objects.bulk_create([
                    ChapterTranslation(chapter=ch, language=uk, title=f"Chapter {start_num + i}")
                    for i, ch in enumerate(chapters)
                ])

            if is_owner:
                messages.success(request, f"{count} chapters added.")
            else:
                messages.warning(request, f"{count} chapters submitted for review.")

            return redirect("core:book_detail", pk=book.pk)
    else:
        form = BulkChaptersForm()

    return render(request, "core/add_chapters.html", {"form": form, "book": book})


@login_required
@add_music_limit
def add_music_recommendation(request, chapter_id: int):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    if request.method == "POST":
        form = MusicRecommendationForm(request.POST)
        if form.is_valid():
            music = form.save(commit=False)
            music.chapter = chapter
            music.user = request.user
            music.save()
            messages.success(request, "Recommendation added.")
            return redirect("core:chapter_detail", book_id=chapter.book_id, chapter_num=chapter.number)
    else:
        form = MusicRecommendationForm()
    return render(request, "core/add_music.html", {"form": form, "chapter": chapter})


@login_required
@likes_limit
def like_music(request, music_id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    music = get_object_or_404(MusicRecommendation, id=music_id)
    like, created = Like.objects.get_or_create(user=request.user, music_recommendation=music)

    if created:
        MusicRecommendation.objects.filter(pk=music_id).update(likes_count=F("likes_count") + 1)
    else:
        like.delete()
        MusicRecommendation.objects.filter(pk=music_id).update(likes_count=F("likes_count") - 1)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        music.refresh_from_db(fields=["likes_count"])
        return JsonResponse({"likes_count": music.likes_count, "liked": created})

    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def delete_music(request, music_id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    music = get_object_or_404(MusicRecommendation, id=music_id)
    if music.user == request.user or request.user.is_staff:
        url = music.chapter.get_absolute_url()
        music.delete()
        messages.success(request, "Recommendation deleted.")
        return redirect(url)
    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def create_playlist(request, book_id: int):
    book = get_object_or_404(Book, id=book_id)
    if request.method == "POST":
        form = PlaylistForm(request.POST)
        if form.is_valid():
            playlist = form.save(commit=False)
            playlist.book = book
            playlist.creator = request.user
            playlist.slug = generate_unique_slug(Playlist, form.cleaned_data.get("title", ""))
            chapter_id = request.POST.get("chapter_id")
            if chapter_id:
                playlist.chapter_id = chapter_id
            playlist.save()
            messages.success(request, "Playlist created.")
            return redirect("core:playlist_detail", pk=playlist.pk)
    else:
        form = PlaylistForm()

    return render(request, "core/create_playlist.html", {
        "form": form,
        "book": book,
        "chapters": book.chapters.all(),
    })


@login_required
def add_track_to_playlist(request, pk: int):
    playlist = get_object_or_404(Playlist, pk=pk)

    if request.user != playlist.creator:
        messages.error(request, "Only the playlist creator can add tracks.")
        return redirect("core:playlist_detail", pk=pk)

    if request.method == "POST":
        form = PlaylistTrackForm(request.POST)
        if form.is_valid():
            track = form.save(commit=False)
            track.playlist = playlist
            last = playlist.tracks.order_by("-order").first()
            track.order = (last.order + 1) if last else 1
            track.save()
            messages.success(request, "Track added.")
            return redirect("core:playlist_detail", pk=pk)
    else:
        form = PlaylistTrackForm()

    return render(request, "core/add_track.html", {"form": form, "playlist": playlist})


@login_required
@likes_limit
def like_playlist(request, playlist_id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    playlist = get_object_or_404(Playlist, id=playlist_id)
    like, created = Like.objects.get_or_create(user=request.user, playlist=playlist)
    if created:
        Playlist.objects.filter(pk=playlist_id).update(likes_count=F("likes_count") + 1)
    else:
        like.delete()
        Playlist.objects.filter(pk=playlist_id).update(likes_count=F("likes_count") - 1)
    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def profile(request):
    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("core:profile")
    else:
        form = UserUpdateForm(instance=request.user)

    return render(request, "core/profile.html", {
        "form": form,
        "saved_books": SavedBook.objects.filter(user=request.user).select_related("book"),
        "my_playlists": Playlist.objects.filter(creator=request.user).select_related("book"),
        "my_recommendations": MusicRecommendation.objects.filter(
            user=request.user
        ).select_related("chapter__book"),
    })

class AboutView(TemplateView):
    template_name = "core/about.html"
