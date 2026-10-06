from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.forms import PickTrackForm, TrackDraftForm, TrackLinkForm
from core.models import Recommendation
from core.ratelimits import rate_limited
from core.services import recommendations as recommendation_service
from core.services import tracks as track_service
from core.services.music_links import ParsedLink, fetch_metadata
from core.views.books import get_visible_book

ACTION_PICK = "pick"
ACTION_LINK = "link"
ACTION_DRAFT = "draft"


def target_url(book, chapter):
    return chapter.get_absolute_url() if chapter else book.get_absolute_url()


def resolve_chapter(request, book):
    raw = request.POST.get("chapter") or request.GET.get("chapter")
    if not raw:
        return None
    if not raw.isdigit():
        raise Http404
    return get_object_or_404(book.chapters, number=int(raw))


def finish(request, user, track, book, chapter, comment):
    _, created = recommendation_service.recommend(user, track, book, chapter, comment)
    if created:
        messages.success(request, "Рекомендацію додано.")
    else:
        messages.info(request, "Ви вже радили цей трек сюди.")
    return redirect(target_url(book, chapter))


@login_required
@rate_limited("recommend")
def recommend(request, slug: str):
    book = get_visible_book(request, slug)
    chapter = resolve_chapter(request, book)
    query = request.GET.get("q", "").strip()
    link_form = TrackLinkForm()
    draft_form = None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == ACTION_PICK:
            form = PickTrackForm(request.POST)
            if form.is_valid():
                return finish(request, request.user, form.cleaned_data["track"], book, chapter, form.cleaned_data["comment"])
            messages.error(request, "Не вдалося вибрати трек.")
        elif action == ACTION_LINK:
            link_form = TrackLinkForm(request.POST)
            if link_form.is_valid():
                link = link_form.link
                comment = link_form.cleaned_data["comment"]
                track = track_service.find_track(link)
                if track is None:
                    metadata = fetch_metadata(link)
                    if metadata is None:
                        draft_form = TrackDraftForm(
                            initial={"platform": link.platform, "external_id": link.external_id, "comment": comment}
                        )
                        messages.info(request, "Не вдалося отримати назву автоматично. Введіть її вручну.")
                    else:
                        track, _ = track_service.get_or_create_track(link, metadata.title, metadata.artist, request.user)
                if track is not None:
                    return finish(request, request.user, track, book, chapter, comment)
        elif action == ACTION_DRAFT:
            draft_form = TrackDraftForm(request.POST)
            if draft_form.is_valid():
                data = draft_form.cleaned_data
                link = ParsedLink(platform=data["platform"], external_id=data["external_id"])
                track, _ = track_service.get_or_create_track(link, data["title"], data["artist"], request.user)
                return finish(request, request.user, track, book, chapter, data["comment"])

    found = list(track_service.search_tracks(query)) if query else []
    already = set(
        Recommendation.objects.filter(user=request.user, book=book, chapter=chapter).values_list("track_id", flat=True)
    )
    return render(
        request,
        "core/recommend.html",
        {
            "book": book,
            "chapter": chapter,
            "query": query,
            "found": found,
            "already": already,
            "link_form": link_form,
            "draft_form": draft_form,
        },
    )


@login_required
@require_POST
def recommendation_delete(request, pk: int):
    recommendation = get_object_or_404(Recommendation.objects.select_related("book", "chapter"), pk=pk)
    if recommendation.user_id != request.user.pk and not request.user.is_staff:
        return redirect(target_url(recommendation.book, recommendation.chapter))
    destination = target_url(recommendation.book, recommendation.chapter)
    recommendation.delete()
    messages.success(request, "Рекомендацію видалено.")
    return redirect(destination)
