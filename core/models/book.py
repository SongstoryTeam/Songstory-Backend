from django.contrib.auth.models import User
from django.db import models
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.urls import reverse

from core.text import search_form, search_terms
from core.utils.slugs import generate_unique_slug


class Genre(models.Model):
    name = models.CharField("Назва", max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Жанр"
        verbose_name_plural = "Жанри"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = generate_unique_slug(Genre, self.name, self)
        super().save(*args, **kwargs)


class Author(models.Model):
    name = models.CharField("Ім'я", max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Автор"
        verbose_name_plural = "Автори"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = generate_unique_slug(Author, self.name, self)
        super().save(*args, **kwargs)
        for book in self.books.all():
            book.save(update_fields=["search_key"])


class BookQuerySet(models.QuerySet):
    def visible_to(self, user) -> "BookQuerySet":
        if user.is_authenticated and user.is_staff:
            return self
        condition = Q(is_approved=True)
        if user.is_authenticated:
            condition |= Q(creator=user)
        return self.filter(condition)

    def search(self, query: str) -> "BookQuerySet":
        terms = search_terms(query)
        if not terms:
            return self.none()
        queryset = self
        for term in terms:
            queryset = queryset.filter(search_key__contains=term)
        phrase = " ".join(terms)
        return queryset.annotate(
            match_rank=Case(
                When(title_key=phrase, then=Value(0)),
                When(title_key__startswith=phrase, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        ).order_by("match_rank", "-created_at", "-pk")

    def with_recommendation_count(self) -> "BookQuerySet":
        return self.annotate(recommendations_total=Count("recommendations", distinct=True))


class Book(models.Model):
    title = models.CharField("Назва", max_length=255)
    description = models.TextField("Опис", blank=True)
    slug = models.SlugField(unique=True, blank=True)
    author = models.ForeignKey(
        Author, on_delete=models.SET_NULL, null=True, blank=True, related_name="books", verbose_name="Автор"
    )
    genre = models.ForeignKey(
        Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name="books", verbose_name="Жанр"
    )
    year = models.PositiveSmallIntegerField("Рік", null=True, blank=True)
    cover_url = models.URLField("Посилання на обкладинку", blank=True, max_length=500)
    isbn = models.CharField("ISBN", max_length=20, blank=True)
    google_books_id = models.CharField(max_length=50, unique=True, null=True, blank=True, editable=False)
    creator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_books", verbose_name="Додав"
    )
    verified_author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_books",
        verbose_name="Підтверджений автор",
    )
    is_approved = models.BooleanField("Схвалено", default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    search_key = models.CharField(max_length=600, editable=False, default="")
    title_key = models.CharField(max_length=255, editable=False, default="", db_index=True)

    objects = BookQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Книга"
        verbose_name_plural = "Книги"
        indexes = [models.Index(fields=["is_approved", "-created_at"], name="book_approved_created_idx")]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = generate_unique_slug(Book, self.title, self)
        self.search_key = self.build_search_key()
        self.title_key = search_form(self.title)[:255]
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "title" in update_fields:
            kwargs["update_fields"] = {*update_fields, "search_key", "title_key"}
        super().save(*args, **kwargs)

    def build_search_key(self) -> str:
        author_name = self.author.name if self.author_id else ""
        return search_form(f"{self.title} {author_name}")[:600]

    def get_absolute_url(self) -> str:
        return reverse("core:book_detail", kwargs={"slug": self.slug})

    def is_visible_to(self, user) -> bool:
        if self.is_approved:
            return True
        return user.is_authenticated and (user.is_staff or user == self.creator)

    def can_manage(self, user) -> bool:
        return user.is_authenticated and (user.is_staff or user == self.creator)


class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    number = models.PositiveIntegerField("Номер")
    title = models.CharField("Назва", max_length=255, blank=True)

    class Meta:
        ordering = ["number"]
        constraints = [models.UniqueConstraint(fields=["book", "number"], name="unique_chapter_number_per_book")]
        verbose_name = "Розділ"
        verbose_name_plural = "Розділи"

    def __str__(self) -> str:
        return f"{self.book.title}: {self.display_title}"

    @property
    def display_title(self) -> str:
        return self.title or f"Розділ {self.number}"

    def get_absolute_url(self) -> str:
        return reverse("core:chapter_detail", kwargs={"slug": self.book.slug, "number": self.number})
