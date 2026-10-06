from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Book, Chapter


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "daily"

    def items(self):
        return ["core:home", "core:book_list"]

    def location(self, item):
        return reverse(item)


class BookSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Book.objects.filter(is_approved=True)

    def lastmod(self, obj):
        return obj.created_at


class ChapterSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Chapter.objects.filter(book__is_approved=True).select_related("book")
