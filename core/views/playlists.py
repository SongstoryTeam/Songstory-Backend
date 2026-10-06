from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.forms import CommentForm, PlaylistForm, PlaylistTrackForm
from core.models import Playlist, PlaylistItem
from core.ratelimits import rate_limited
from core.services.recommendations import book_tracks
from core.views.books import get_visible_book, threaded_comments


def get_manageable_playlist(request, pk: int) -> Playlist:
    playlist = get_object_or_404(Playlist.objects.select_related("book", "user"), pk=pk)
    if not playlist.can_manage(request.user):
        raise Http404
    return playlist


@login_required
@rate_limited("playlist")
def playlist_create(request, slug: str):
    book = get_visible_book(request, slug)
    pool = book_tracks(book)
    form = PlaylistForm(request.POST or None, track_queryset=pool)
    if request.method == "POST" and form.is_valid():
        selected = set(track.pk for track in form.cleaned_data["tracks"])
        with transaction.atomic():
            playlist = Playlist.objects.create(
                book=book,
                user=request.user,
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
            )
            PlaylistItem.objects.bulk_create(
                [
                    PlaylistItem(playlist=playlist, track=track, position=index)
                    for index, track in enumerate(track for track in pool if track.pk in selected)
                ]
            )
        messages.success(request, "Плейлист створено.")
        return redirect(playlist)
    return render(request, "core/playlist_create.html", {"book": book, "form": form, "has_pool": pool.exists()})


def playlist_detail(request, pk: int):
    playlist = get_object_or_404(Playlist.objects.select_related("book", "user"), pk=pk)
    if not playlist.book.is_visible_to(request.user):
        raise Http404
    items = playlist.items.select_related("track")
    can_manage = playlist.can_manage(request.user)
    add_form = None
    if can_manage:
        available = book_tracks(playlist.book).exclude(pk__in=playlist.items.values("track_id"))
        add_form = PlaylistTrackForm(track_queryset=available) if available.exists() else None
    return render(
        request,
        "core/playlist_detail.html",
        {
            "playlist": playlist,
            "book": playlist.book,
            "items": items,
            "can_manage": can_manage,
            "add_form": add_form,
            "comments": threaded_comments(playlist=playlist),
            "comment_form": CommentForm(),
            "comment_target": {"playlist": playlist.pk},
        },
    )


@login_required
@require_POST
def playlist_add_track(request, pk: int):
    playlist = get_manageable_playlist(request, pk)
    available = book_tracks(playlist.book).exclude(pk__in=playlist.items.values("track_id"))
    form = PlaylistTrackForm(request.POST, track_queryset=available)
    if form.is_valid():
        last = playlist.items.aggregate(last=Max("position"))["last"]
        PlaylistItem.objects.create(
            playlist=playlist, track=form.cleaned_data["track"], position=0 if last is None else last + 1
        )
        messages.success(request, "Трек додано до плейлиста.")
    else:
        messages.error(request, "Не вдалося додати трек.")
    return redirect(playlist)


@login_required
@require_POST
def playlist_remove_item(request, pk: int, item_pk: int):
    playlist = get_manageable_playlist(request, pk)
    get_object_or_404(PlaylistItem, pk=item_pk, playlist=playlist).delete()
    messages.success(request, "Трек прибрано з плейлиста.")
    return redirect(playlist)


@login_required
@require_POST
def playlist_delete(request, pk: int):
    playlist = get_manageable_playlist(request, pk)
    book = playlist.book
    playlist.delete()
    messages.success(request, "Плейлист видалено.")
    return redirect(book)
