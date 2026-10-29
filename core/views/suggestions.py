from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.forms import BookEditSuggestionForm
from core.models import BookEditSuggestion
from core.ratelimits import rate_limited
from core.services import suggestions as suggestion_service
from core.utils.pagination import paginate
from core.utils.redirects import safe_redirect_target
from core.views.books import get_visible_book

SUBMITTED_MESSAGE = "Дякуємо! Пропозицію надіслано на розгляд модератору."
APPLIED_MESSAGE = "Зміни застосовано."
REVISED_MESSAGE = "Пропозицію оновлено."
WITHDRAWN_MESSAGE = "Пропозицію відкликано."
PAGE_PARAM = "page"
Status = BookEditSuggestion.Status


def persist(request, form, book, suggestion) -> str:
    reason = form.cleaned_data["reason"]
    if suggestion:
        suggestion_service.revise_suggestion(suggestion, changes=form.changes, reason=reason)
        return REVISED_MESSAGE
    created = suggestion_service.submit_suggestion(user=request.user, book=book, changes=form.changes, reason=reason)
    return APPLIED_MESSAGE if created.status == Status.APPROVED else SUBMITTED_MESSAGE


@login_required
@rate_limited("suggest_edit")
def suggest_edit(request, slug: str):
    book = get_visible_book(request, slug)
    suggestion = suggestion_service.pending_for(request.user, book)
    form = BookEditSuggestionForm(request.POST or None, book=book, user=request.user, suggestion=suggestion)
    if request.method == "POST" and form.is_valid():
        try:
            messages.success(request, persist(request, form, book, suggestion))
        except suggestion_service.SuggestionError as error:
            messages.error(request, str(error))
        return redirect(book)
    return render(
        request,
        "core/suggest_edit.html",
        {
            "form": form,
            "book": book,
            "suggestion": suggestion,
            "outdated_fields": suggestion_service.outdated_fields(suggestion, book),
        },
    )


@login_required
@require_POST
@rate_limited("suggestion_withdraw")
def withdraw_suggestion(request, pk: int):
    suggestion = get_object_or_404(BookEditSuggestion.objects.select_related("book"), pk=pk, user=request.user)
    try:
        suggestion_service.withdraw_suggestion(suggestion)
    except suggestion_service.SuggestionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, WITHDRAWN_MESSAGE)
    return redirect(safe_redirect_target(request, fallback=suggestion.book))


@login_required
def my_suggestions(request):
    own = BookEditSuggestion.objects.filter(user=request.user).select_related("book__author", "book__genre")
    pending = [
        {"suggestion": suggestion, "outdated_fields": suggestion_service.outdated_fields(suggestion, suggestion.book)}
        for suggestion in own.filter(status=Status.PENDING)
    ]
    history = paginate(
        own.exclude(status=Status.PENDING), request.GET.get(PAGE_PARAM, 1), settings.SUGGESTION_HISTORY_PAGE_SIZE
    )
    return render(
        request,
        "core/my_suggestions.html",
        {
            "pending": pending,
            "pending_left": suggestion_service.pending_suggestions_left(request.user),
            "pending_limit": settings.PENDING_SUGGESTIONS_LIMIT,
            "page": history.page,
            "page_range": history.page_range,
        },
    )
