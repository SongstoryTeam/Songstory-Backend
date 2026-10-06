from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from urllib.parse import urlencode

from core.models import Book
from core.ratelimits import IP, rate_limited
from core.services import catalog
from core.services.google_books import search_google_books
from core.text import normalize

MIN_EXTERNAL_QUERY_LENGTH = 2


def home(request):
    return render(
        request,
        "core/home.html",
        {"shelves": catalog.home_shelves(request.user), "genres": catalog.genres_in_use()},
    )


def book_list(request):
    genre_slug = request.GET.get("genre", "")
    page, sort_key = catalog.catalog_page(
        request.user,
        genre_slug=genre_slug,
        sort=request.GET.get("sort", ""),
        page_number=request.GET.get("page", 1),
    )
    return render(
        request,
        "core/book_list.html",
        {
            "page": page,
            "genres": catalog.genres_in_use(),
            "active_genre": genre_slug,
            "active_sort": sort_key,
            "sort_options": [(key, label) for key, (label, _) in catalog.SORT_OPTIONS.items()],
            "pagination_query": urlencode({k: v for k, v in (("genre", genre_slug), ("sort", sort_key)) if v}) + "&",
        },
    )


@rate_limited("search", key=IP, methods=("GET",))
def search(request):
    query = request.GET.get("q", "").strip()
    context = {"query": query, "local_books": [], "external_books": [], "external_unavailable": False}
    if query:
        local_books = catalog.search_local(request.user, query, settings.SEARCH_PAGE_SIZE)
        context["local_books"] = local_books
        if len(query) >= MIN_EXTERNAL_QUERY_LENGTH:
            external = search_google_books(query)
            known_ids = set(
                Book.objects.filter(google_books_id__in=[item.external_id for item in external.books]).values_list(
                    "google_books_id", flat=True
                )
            )
            known_keys = {normalize(f"{book.title} {book.author.name if book.author else ''}") for book in local_books}
            context["external_books"] = [
                item
                for item in external.books
                if item.external_id not in known_ids and normalize(f"{item.title} {item.author}") not in known_keys
            ]
            context["external_unavailable"] = external.unavailable
    return render(request, "core/search_results.html", context)


@rate_limited("search", key=IP, methods=("GET",), json=True)
def search_suggest(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": []})
    books = catalog.search_local(request.user, query, settings.SEARCH_SUGGEST_LIMIT)
    return JsonResponse(
        {
            "results": [
                {
                    "title": book.title,
                    "author": book.author.name if book.author else "",
                    "cover_url": book.cover_url,
                    "url": book.get_absolute_url(),
                }
                for book in books
            ],
            "all_url": f"{reverse('core:search')}?{urlencode({'q': query})}",
        }
    )
