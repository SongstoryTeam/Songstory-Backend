from typing import NamedTuple

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core import limits

from .book import Book

EMPTY_VALUE_LABEL = "—"


class ChangeRow(NamedTuple):
    label: str
    old: str
    new: str


class BookEditSuggestion(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Очікує"
        APPROVED = "approved", "Схвалено"
        REJECTED = "rejected", "Відхилено"

    class Field(models.TextChoices):
        TITLE = "title", "Назва"
        AUTHOR_NAME = "author_name", "Автор"
        YEAR = "year", "Рік видання"
        GENRE_NAME = "genre_name", "Жанр"
        ISBN = "isbn", "ISBN"
        DESCRIPTION = "description", "Опис"
        COVER_URL = "cover_url", "Посилання на обкладинку"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="edit_suggestions", verbose_name="Книга")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="book_edit_suggestions", verbose_name="Автор пропозиції"
    )
    changes = models.JSONField("Зміни", default=dict)
    reason = models.TextField("Пояснення", blank=True, max_length=limits.SUGGESTION_REASON_MAX_LENGTH)
    status = models.CharField(max_length=limits.CODE_MAX_LENGTH, choices=Status.choices, default=Status.PENDING)
    admin_note = models.TextField("Нотатка модератора", blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_book_edits"
    )

    class Meta:
        ordering = ["-submitted_at", "-pk"]
        indexes = [models.Index(fields=["status", "-submitted_at"], name="suggestion_status_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"],
                condition=Q(status="pending"),
                name="single_pending_suggestion_per_user_book",
            )
        ]
        verbose_name = "Пропозиція змін до книги"
        verbose_name_plural = "Пропозиції змін до книг"

    def __str__(self) -> str:
        return f"{self.user.username} → {self.book} ({self.get_status_display()})"

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def new_values(self) -> dict:
        return {name: change["new"] for name, change in self.changes.items()}

    @property
    def field_labels(self) -> list[str]:
        return [self.Field(name).label for name in self.changes]

    def change_rows(self) -> list[ChangeRow]:
        return [
            ChangeRow(self.Field(name).label, self._display(change["old"]), self._display(change["new"]))
            for name, change in self.changes.items()
        ]

    def close(self, status: str, reviewer: User, note: str = "") -> None:
        self.status = status
        self.admin_note = note
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save(update_fields=["status", "admin_note", "reviewed_at", "reviewed_by"])

    @staticmethod
    def _display(value) -> str:
        return str(value) if value not in (None, "") else EMPTY_VALUE_LABEL
