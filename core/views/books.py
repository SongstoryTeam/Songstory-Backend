from http import HTTPStatus
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.forms import BookCreateForm, ChapterCountForm, CommentForm
from core.models import AuthorVerification, Book, Comment
from core.ratelimits import IP, rate_limited
from core.seo import book_json_ld
from core.services import books as book_service
from core.services import suggestions as suggestion_service
from core.services.book_search import get_external_book
from core.services.normalize import clean_person_name, clean_title
from core.services.recommendations import grouped_recommendations


ORIGINAL_VIEW_PARAM = "view"
ORIGINAL_VIEW_VALUE = "original"


def get_visible_book(request, slug: str) -> Book:
    book = get_object_or_404(Book.objects.select_related("author", "genre", "verified_author"), slug=slug)
    if not book.is_visible_to(request.user):
        raise Http404
    return book


def threaded_comments(**target):
    return (
        Comment.objects.filter(parent__isnull=True, **target)
        .select_related("user__profile")
        .prefetch_related("replies__user__profile")
    )


def verification_state(user, book: Book) -> str:
    if not user.is_authenticated:
        return "anonymous"
    if book.verified_author_id == user.pk:
        return "verified"
    statuses = set(AuthorVerification.objects.filter(user=user, book=book).values_list("status", flat=True))
    if AuthorVerification.Status.PENDING in statuses:
        return "pending"
    if book.verified_author_id:
        return "taken"
    return "available"


def book_detail(request, slug: str):
    book = get_visible_book(request, slug)
    suggestion = suggestion_service.pending_for(request.user, book)
    outdated_fields = suggestion_service.outdated_fields(suggestion, book)
    showing_original = request.GET.get(ORIGINAL_VIEW_PARAM) == ORIGINAL_VIEW_VALUE
    if suggestion and not showing_original:
        suggestion_service.preview(book, suggestion)
    chapters = book.chapters.annotate(recommendations_total=Count("recommendations"))
    playlists = book.playlists.select_related("user").annotate(tracks_total=Count("items"))
    return render(
        request,
        "core/book_detail.html",
        {
            "book": book,
            "chapters": chapters,
            "groups": grouped_recommendations(book, None, request.user),
            "playlists": playlists,
            "comments": threaded_comments(book=book),
            "comment_form": CommentForm(),
            "comment_target": {"book": book.pk},
            "can_manage": book.can_manage(request.user),
            "verification_state": verification_state(request.user, book),
            "structured_data": book_json_ld(book),
            "suggestion": suggestion,
            "showing_original": showing_original,
            "original_view_query": urlencode({ORIGINAL_VIEW_PARAM: ORIGINAL_VIEW_VALUE}),
            "outdated_fields": outdated_fields,
        },
    )


def chapter_detail(request, slug: str, number: int):
    book = get_visible_book(request, slug)
    chapter = get_object_or_404(book.chapters, number=number)
    siblings = list(book.chapters.values_list("number", flat=True))
    index = siblings.index(chapter.number)
    return render(
        request,
        "core/chapter_detail.html",
        {
            "book": book,
            "chapter": chapter,
            "groups": grouped_recommendations(book, chapter, request.user),
            "previous_number": siblings[index - 1] if index > 0 else None,
            "next_number": siblings[index + 1] if index < len(siblings) - 1 else None,
            "comments": threaded_comments(chapter=chapter),
            "comment_form": CommentForm(),
            "comment_target": {"chapter": chapter.pk},
        },
    )


def describe_duplicate(book: Book | None, user) -> dict | None:
    if book is None:
        return None
    if book.is_visible_to(user):
        return {"title": book.title, "url": book.get_absolute_url()}
    return {"pending": True}


def create_book_prefill(request) -> dict:
    return {"title": clean_title(request.GET.get("title", ""))}


@login_required
@rate_limited("create_book")
def create_book(request):
    form = BookCreateForm(request.POST or None, initial=create_book_prefill(request), user=request.user)
    if request.method == "POST" and form.is_valid():
        book = book_service.create_book(user=request.user, **form.cleaned_data)
        if book.is_approved:
            messages.success(request, "Книгу додано.")
        else:
            messages.info(request, "Книгу надіслано на перевірку. Ви бачите її лише ви, доки її не схвалять.")
        return redirect(book)
    return render(
        request,
        "core/create_book.html",
        {
            "form": form,
            "duplicate": describe_duplicate(form.duplicate, request.user),
            "pending_left": book_service.pending_books_left(request.user),
            "pending_limit": settings.PENDING_BOOKS_LIMIT,
        },
    )


@login_required
@rate_limited("book_check", key=IP, methods=("GET",), json=True)
def check_book(request):
    title = clean_title(request.GET.get("title", ""))
    author = clean_person_name(request.GET.get("author", ""))
    duplicate = book_service.find_duplicate(title, author) if title and author else None
    return JsonResponse({"duplicate": describe_duplicate(duplicate, request.user)})


def wants_json(request) -> bool:
    return request.headers.get("accept", "").startswith("application/json")


def respond_with_location(request, location: str, status: int = HTTPStatus.OK):
    if wants_json(request):
        return JsonResponse({"url": location}, status=status)
    return redirect(location)


@login_required
@require_POST
@rate_limited("import_book")
def import_book(request):
    external = get_external_book(request.POST.get("external_id", "").strip(), request.POST.get("query", ""))
    if external is None:
        messages.error(request, "Не вдалося отримати дані про книгу. Спробуйте пізніше.")
        return respond_with_location(request, reverse("core:search"), status=HTTPStatus.BAD_GATEWAY)
    book, created = book_service.import_external_book(external, request.user)
    messages.success(request, "Книгу додано до каталогу." if created else "Ця книга вже є в каталозі.")
    return respond_with_location(request, book.get_absolute_url())


@login_required
def add_chapters(request, slug: str):
    book = get_visible_book(request, slug)
    if not book.can_manage(request.user):
        raise Http404
    form = ChapterCountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        book_service.add_chapters(book, form.cleaned_data["count"])
        messages.success(request, "Розділи додано.")
        return redirect(book)
    return render(request, "core/add_chapters.html", {"book": book, "form": form})
