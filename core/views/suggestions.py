from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.forms import BookEditSuggestionForm
from core.models import BookEditSuggestion
from core.ratelimits import rate_limited
from core.services import suggestions as suggestion_service
from core.views.books import get_visible_book

SUBMITTED_MESSAGE = "Дякуємо! Пропозицію надіслано на розгляд модератору."
APPLIED_MESSAGE = "Зміни застосовано."


@login_required
@rate_limited("suggest_edit")
def suggest_edit(request, slug: str):
    book = get_visible_book(request, slug)
    if suggestion_service.has_pending_suggestion(request.user, book):
        messages.info(request, suggestion_service.PendingSuggestionExists.default_message)
        return redirect(book)

    form = BookEditSuggestionForm(request.POST or None, book=book, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            suggestion = suggestion_service.submit_suggestion(
                user=request.user,
                book=book,
                changes=form.changes,
                reason=form.cleaned_data["reason"],
            )
        except suggestion_service.SuggestionError as error:
            messages.error(request, str(error))
        else:
            applied = suggestion.status == BookEditSuggestion.Status.APPROVED
            messages.success(request, APPLIED_MESSAGE if applied else SUBMITTED_MESSAGE)
        return redirect(book)
    return render(request, "core/suggest_edit.html", {"form": form, "book": book})
