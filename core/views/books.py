from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from api.v1.services.book_import import import_book_from_open_library
from core.rate_limit import book_import_limit

MESSAGE_BOOK_CREATED = "Книгу додано до каталогу."
MESSAGE_BOOK_ALREADY_EXISTS = "Ця книга вже є в каталозі."
ERROR_MISSING_ID = "open_library_id is required"
ERROR_UNSUPPORTED_LANGUAGE = "Ця книга не має підтвердженої версії українською."


@method_decorator(login_required, name="dispatch")
class BookImportView(View):
    http_method_names = ["post"]

    @book_import_limit
    def post(self, request):
        open_library_id = request.POST.get("open_library_id", "").strip()
        if not open_library_id:
            return JsonResponse({"error": ERROR_MISSING_ID}, status=400)

        try:
            book, created = import_book_from_open_library(
                open_library_id=open_library_id,
                title=request.POST.get("title", ""),
                author=request.POST.get("author", ""),
                year=request.POST.get("year", ""),
                isbn=request.POST.get("isbn", ""),
                cover_url=request.POST.get("cover_url", ""),
                description=request.POST.get("description", ""),
                language_code=request.POST.get("language", ""),
                creator=request.user,
            )
        except ValueError:
            return JsonResponse({"error": ERROR_UNSUPPORTED_LANGUAGE}, status=400)

        messages.success(
            request,
            MESSAGE_BOOK_CREATED if created else MESSAGE_BOOK_ALREADY_EXISTS,
        )
        return JsonResponse({"url": reverse("core:book_detail", args=[book.pk])})
