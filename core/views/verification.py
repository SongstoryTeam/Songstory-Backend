from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core import emails
from core.forms import AuthorVerificationForm
from core.views.books import get_visible_book, verification_state

BLOCKING_MESSAGES = {
    "pending": "Вашу заявку вже розглядають.",
    "verified": "Ваше авторство цієї книги вже підтверджено.",
    "taken": "Авторство цієї книги вже підтверджено іншим користувачем.",
}


@login_required
def apply_author(request, slug: str):
    book = get_visible_book(request, slug)
    state = verification_state(request.user, book)
    if state in BLOCKING_MESSAGES:
        messages.info(request, BLOCKING_MESSAGES[state])
        return redirect(book)

    form = AuthorVerificationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        verification = form.save(commit=False)
        verification.user = request.user
        verification.book = book
        verification.save()
        emails.notify_admin_new_verification(verification)
        messages.success(request, "Заявку надіслано. Ми розглянемо її найближчим часом.")
        return redirect(book)
    return render(request, "core/apply_author.html", {"form": form, "book": book})
