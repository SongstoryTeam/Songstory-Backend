from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from urllib.parse import urlencode

from core.models import Book
from core.ratelimits import IP, rate_limited
from core.services import catalog
from core.services.book_search import search_books
from core.services.external import ExternalBook
from core.text import clean_query, search_form

MIN_EXTERNAL_QUERY_LENGTH = 2
GENRE_PARAM = "genre"
SORT_PARAM = "sort"
MUSIC_PARAM = "music"
PAGE_PARAM = "page"
MUSIC_ENABLED = "1"


def home(request):
    return render(
        request,
        "core/home.html",
        {"shelves": catalog.home_shelves(request.user), "genres": catalog.genres_in_use()},
    )


def book_list(request):
    result = catalog.catalog_page(
        request.user,
        genre_slug=request.GET.get(GENRE_PARAM, ""),
        sort=request.GET.get(SORT_PARAM, ""),
        with_music=request.GET.get(MUSIC_PARAM) == MUSIC_ENABLED,
        page_number=request.GET.get(PAGE_PARAM, 1),
    )
    return render(
        request,
        "core/book_list.html",
        {
            "result": result,
            "page": result.page,
            "genres": catalog.genres_in_use(),
            "catalog_total": catalog.approved_total(),
            "sort_options": [(key, label) for key, (label, _) in catalog.SORT_OPTIONS.items()],
            "params": {"genre": GENRE_PARAM, "sort": SORT_PARAM, "music": MUSIC_PARAM, "page": PAGE_PARAM},
            "music_enabled": MUSIC_ENABLED,
        },
    )


@rate_limited("search", key=IP, methods=("GET",))
def search(request):
    query = clean_query(request.GET.get("q", ""))
    context = {
        "query": query,
        "local_books": [],
        "external_books": [],
        "external_unavailable": False,
        "external_failed": [],
    }
    if query:
        context["local_books"] = catalog.search_local(request.user, query, settings.SEARCH_PAGE_SIZE)
        if len(search_form(query)) >= MIN_EXTERNAL_QUERY_LENGTH:
            external = search_books(query)
            context["external_books"] = catalog.exclude_known(external.books)
            context["external_unavailable"] = external.unavailable
            context["external_failed"] = list(external.failed)
    return render(request, "core/search_results.html", context)


def serialize_book(book: Book) -> dict:
    return {
        "title": book.title,
        "author": book.author.name if book.author else "",
        "cover_url": book.cover_url,
        "url": book.get_absolute_url(),
    }


def serialize_external(item: ExternalBook) -> dict:
    return {
        "external_id": item.external_id,
        "title": item.title,
        "author": item.author,
        "year": item.year,
        "cover_url": item.cover_url,
    }


@rate_limited("search_suggest", key=IP, methods=("GET",), json=True)
def search_suggest(request):
    query = clean_query(request.GET.get("q", ""))
    search_url = reverse("core:search")
    all_url = f"{search_url}?{urlencode({'q': query})}"
    payload = {
        "results": [],
        "external": [],
        "external_unavailable": False,
        "external_failed": [],
        "all_url": all_url,
    }
    if len(query) < settings.SEARCH_SUGGEST_MIN_LENGTH or not search_form(query):
        return JsonResponse(payload)

    local = catalog.search_local(request.user, query, settings.SEARCH_SUGGEST_LIMIT)
    payload["results"] = [serialize_book(book) for book in local]

    wants_external = (
        len(search_form(query)) >= settings.SEARCH_SUGGEST_EXTERNAL_MIN_LENGTH
        and len(local) < settings.SEARCH_SUGGEST_LIMIT
    )
    if wants_external:
        external = search_books(query, limit=settings.SEARCH_SUGGEST_EXTERNAL_LIMIT)
        payload["external"] = [serialize_external(item) for item in catalog.exclude_known(external.books)]
        payload["external_unavailable"] = external.unavailable
        payload["external_failed"] = list(external.failed)

    payload.update(
        import_url=reverse("core:import_book"),
        login_url=f"{reverse('login')}?{urlencode({'next': all_url})}",
        can_import=request.user.is_authenticated,
    )
    return JsonResponse(payload)
