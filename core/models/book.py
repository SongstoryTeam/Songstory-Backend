
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Avg
from django.urls import reverse

from .language import Language


class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_approved=True)


class ApprovedChapterManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_approved=True)


class Book(models.Model):
    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_books",
        verbose_name="Added by",
    )
    verified_author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_books",
        verbose_name="Verified author",
    )
    author = models.ForeignKey(
        "Author",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books",
        verbose_name="Author",
    )
    genre = models.ForeignKey(
        "Genre",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books",
        verbose_name="Genre",
    )
    slug = models.SlugField(unique=True, blank=True)
    year = models.IntegerField(verbose_name="Year")
    cover_image = models.ImageField(
        upload_to="books/covers/",
        blank=True,
        null=True,
        verbose_name="Cover file",
    )
    cover_url = models.URLField(blank=True, verbose_name="Cover URL")
    is_approved = models.BooleanField(default=False, db_index=True, verbose_name="Approved")
    created_at = models.DateTimeField(auto_now_add=True)
    views_count = models.IntegerField(default=0)
    isbn = models.CharField(max_length=20, blank=True, db_index=True)
    open_library_id = models.CharField(max_length=50, blank=True, unique=True, null=True)
    google_books_id = models.CharField(max_length=50, blank=True)
    canonical_book = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="editions",
    )

    objects = models.Manager()
    published = PublishedManager()

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_title()} — {self.get_author_name()}"

    def get_title(self, lang: str = "uk") -> str:
        translation = self.translations.filter(language__code=lang).first()
        if translation and translation.title:
            return translation.title
        fallback = self.translations.first()
        return fallback.title if fallback else f"Book #{self.pk}"

    def get_description(self, lang: str = "uk") -> str:
        translation = self.translations.filter(language__code=lang).first()
        if translation:
            return translation.description
        fallback = self.translations.first()
        return fallback.description if fallback else ""

    def get_author_name(self, lang: str = "uk") -> str:
        if self.author_id:
            return self.author.get_name(lang)
        return ""

    def get_genre_name(self, lang: str = "uk") -> str:
        if self.genre_id:
            return self.genre.get_name(lang)
        return ""

    def get_cover(self) -> str | None:
        if self.cover_image:
            return self.cover_image.url
        return self.cover_url or None

    def get_absolute_url(self) -> str:
        if self.slug:
            return reverse("core:book_detail_slug", kwargs={"slug": self.slug})
        return reverse("core:book_detail", kwargs={"pk": self.pk})

    def is_visible_to(self, user) -> bool:
        if self.is_approved:
            return True
        return user.is_authenticated and (user == self.creator or user.is_staff)

    @property
    def average_rating(self) -> float:
        result = self.ratings.aggregate(avg=Avg("score"))
        return round(result["avg"] or 0, 1)


class BookTranslation(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ["book", "language"]
        verbose_name = "Book translation"
        verbose_name_plural = "Book translations"

    def __str__(self) -> str:
        return f"{self.title} [{self.language.code}]"


class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    number = models.IntegerField(verbose_name="Number")
    is_approved = models.BooleanField(default=False, verbose_name="Approved")

    objects = models.Manager()
    approved = ApprovedChapterManager()

    class Meta:
        verbose_name = "Chapter"
        verbose_name_plural = "Chapters"
        ordering = ["number"]

    def __str__(self) -> str:
        return f"Ch.{self.number}: {self.get_title()}"

    def get_title(self, lang: str = "uk") -> str:
        translation = self.translations.filter(language__code=lang).first()
        if translation and translation.title:
            return translation.title
        fallback = self.translations.first()
        return fallback.title if fallback else f"Chapter {self.number}"

    def get_description(self, lang: str = "uk") -> str:
        translation = self.translations.filter(language__code=lang).first()
        if translation:
            return translation.description
        fallback = self.translations.first()
        return fallback.description if fallback else ""

    def get_mood_tags(self, lang: str = "uk") -> str:
        translation = self.translations.filter(language__code=lang).first()
        if translation:
            return translation.mood_tags
        fallback = self.translations.first()
        return fallback.mood_tags if fallback else ""

    def get_absolute_url(self) -> str:
        return reverse(
            "core:chapter_detail",
            kwargs={"book_id": self.book_id, "chapter_num": self.number},
        )


class ChapterTranslation(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    mood_tags = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ["chapter", "language"]
        verbose_name = "Chapter translation"
        verbose_name_plural = "Chapter translations"

    def __str__(self) -> str:
        return f"Ch.{self.chapter.number} [{self.language.code}] — {self.title}"
