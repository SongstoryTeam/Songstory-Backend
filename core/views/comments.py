from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from core.forms import CommentForm
from core.models import Book, Chapter, Comment, Playlist
from core.ratelimits import rate_limited

TARGET_MODELS = {"book": Book, "chapter": Chapter, "playlist": Playlist}
COMMENTS_ANCHOR = "#comments"


def resolve_target(post):
    for field, model in TARGET_MODELS.items():
        raw = post.get(field)
        if raw and raw.isdigit():
            return field, get_object_or_404(model, pk=int(raw))
    raise Http404


def parent_book(target) -> Book:
    return target if isinstance(target, Book) else target.book


@login_required
@require_POST
@rate_limited("comment")
def add_comment(request):
    field, target = resolve_target(request.POST)
    if not parent_book(target).is_visible_to(request.user):
        raise Http404
    form = CommentForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Коментар не може бути порожнім або надто довгим.")
        return redirect(target.get_absolute_url())

    parent = None
    parent_id = request.POST.get("parent")
    if parent_id:
        if not parent_id.isdigit():
            raise Http404
        parent = get_object_or_404(Comment, pk=int(parent_id), parent__isnull=True, **{field: target})

    Comment.objects.create(user=request.user, text=form.cleaned_data["text"], parent=parent, **{field: target})
    return redirect(f"{target.get_absolute_url()}{COMMENTS_ANCHOR}")


@login_required
@require_POST
def delete_comment(request, pk: int):
    comment = get_object_or_404(Comment, pk=pk)
    destination = comment.target.get_absolute_url()
    if comment.user_id == request.user.pk or request.user.is_staff:
        comment.delete()
        messages.success(request, "Коментар видалено.")
    return redirect(f"{destination}{COMMENTS_ANCHOR}")
