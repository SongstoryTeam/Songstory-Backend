from django.contrib.sitemaps import Sitemap
from django.db.models import Max
from django.urls import reverse

from .models import Book, Chapter, Genre, Playlist

# Google ігнорує priority та changefreq, тому віддаємо тільки те, що він справді використовує: адреси й lastmod.
# У карту потрапляють лише сторінки, на яких є що слухати: порожні сторінки мають noindex і шкодять якості сайту.


class StaticViewSitemap(Sitemap):
    def items(self):
        return ["core:home", "core:reading_music", "core:book_list", "core:about", "core:privacy", "core:terms"]

    def location(self, item):
        return reverse(item)


class GenreSitemap(Sitemap):
    def items(self):
        return (
            Genre.objects.filter(books__is_approved=True, books__recommendations__isnull=False)
            .annotate(updated=Max("books__recommendations__created_at"))
            .order_by("slug")
        )

    def lastmod(self, obj):
        return obj.updated


class BookSitemap(Sitemap):
    def items(self):
        return (
            Book.objects.filter(is_approved=True, recommendations__isnull=False)
            .annotate(updated=Max("recommendations__created_at"))
            .order_by("pk")
        )

    def lastmod(self, obj):
        return obj.updated


class ChapterSitemap(Sitemap):
    def items(self):
        return (
            Chapter.objects.filter(book__is_approved=True, recommendations__isnull=False)
            .select_related("book")
            .annotate(updated=Max("recommendations__created_at"))
            .order_by("pk")
        )

    def lastmod(self, obj):
        return obj.updated


class PlaylistSitemap(Sitemap):
    def items(self):
        return (
            Playlist.objects.filter(book__is_approved=True, items__isnull=False)
            .select_related("book")
            .distinct()
            .order_by("pk")
        )

    def lastmod(self, obj):
        return obj.created_at
