from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core.models import Book
from staffpanel.access import Permission, staff_action, staff_view
from staffpanel.actions import permitted, rows
from staffpanel.forms import read_filters
from staffpanel.pagination import paginate
from staffpanel.services import overview
from staffpanel.services.books import BOOK_ACTIONS, DEFAULT_STATE, BookState, book_queryset
from staffpanel.views.common import ACTION_PARAM, run_action, selected_ids


@staff_view(Permission.BOOKS_VIEW)
def book_list(request):
    filters = read_filters(request, "Назва або автор")
    state = filters.state if filters.state in BookState.values else DEFAULT_STATE.value
    page, page_range = paginate(request, book_queryset(state=state, query=filters.query))
    return render(
        request,
        "staffpanel/books/list.html",
        {
            "page": page,
            "page_range": page_range,
            "rows": rows(BOOK_ACTIONS, request.user, page.object_list),
            "bulk_actions": permitted(BOOK_ACTIONS, request.user),
            "filters": filters,
            "current_state": state,
            "states": BookState.choices,
            "pending_state": BookState.PENDING.value,
            "pending_total": overview.pending_counts()[overview.Badge.BOOKS.value],
        },
    )


@staff_action(Permission.BOOKS_VIEW)
def book_action(request, pk: int, action: str):
    get_object_or_404(Book, pk=pk)
    return run_action(request, BOOK_ACTIONS, action, Book.objects.filter(pk=pk), reverse("staff:books"))


@staff_action(Permission.BOOKS_VIEW)
def book_bulk(request):
    queryset = Book.objects.filter(pk__in=selected_ids(request))
    return run_action(request, BOOK_ACTIONS, request.POST.get(ACTION_PARAM, ""), queryset, reverse("staff:books"))
