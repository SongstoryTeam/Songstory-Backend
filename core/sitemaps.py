from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Book, Chapter


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "daily"

    def items(self):
        return ["core:home"]

    def location(self, item):
        return reverse(item)


class BookSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Book.objects.all().order_by("-created_at")

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return obj.get_absolute_url()


class ChapterSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Chapter.objects.filter(is_approved=True).select_related("book").order_by("-id")

    def location(self, obj):
        return obj.get_absolute_url()
