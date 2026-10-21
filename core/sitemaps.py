from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Book, Chapter

STATIC_PRIORITY = 1.0
BOOK_PRIORITY = 0.8
CHAPTER_PRIORITY = 0.6


class StaticViewSitemap(Sitemap):
    priority = STATIC_PRIORITY
    changefreq = "daily"

    def items(self):
        return ["core:home", "core:book_list"]

    def location(self, item):
        return reverse(item)


class BookSitemap(Sitemap):
    changefreq = "weekly"
    priority = BOOK_PRIORITY

    def items(self):
        return Book.objects.filter(is_approved=True)

    def lastmod(self, obj):
        return obj.created_at


class ChapterSitemap(Sitemap):
    changefreq = "monthly"
    priority = CHAPTER_PRIORITY

    def items(self):
        return Chapter.objects.filter(book__is_approved=True).select_related("book")
