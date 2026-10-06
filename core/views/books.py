from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.forms import BookCreateForm, ChapterCountForm, CommentForm
from core.models import AuthorVerification, Book, Comment
from core.ratelimits import rate_limited
from core.seo import book_json_ld
from core.services import books as book_service
from core.services.google_books import get_google_book
from core.services.recommendations import grouped_recommendations


def get_visible_book(request, slug: str) -> Book:
    book = get_object_or_404(Book.objects.select_related("author", "genre", "verified_author"), slug=slug)
    if not book.is_visible_to(request.user):
        raise Http404
    return book


def threaded_comments(**target):
    return (
        Comment.objects.filter(parent__isnull=True, **target)
        .select_related("user")
        .prefetch_related("replies__user")
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


@login_required
def create_book(request):
    form = BookCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        book = book_service.create_book(user=request.user, **form.cleaned_data)
        if book.is_approved:
            messages.success(request, "Книгу додано.")
        else:
            messages.info(request, "Книгу надіслано на перевірку. Ви бачите її лише ви, доки її не схвалять.")
        return redirect(book)
    return render(request, "core/create_book.html", {"form": form, "duplicate": form.duplicate})


@login_required
@require_POST
@rate_limited("import_book")
def import_book(request):
    external = get_google_book(request.POST.get("external_id", "").strip())
    if external is None:
        messages.error(request, "Не вдалося отримати дані про книгу. Спробуйте пізніше.")
        return redirect("core:search")
    book, created = book_service.import_external_book(external, request.user)
    messages.success(request, "Книгу додано до каталогу." if created else "Ця книга вже є в каталозі.")
    return redirect(book)


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
