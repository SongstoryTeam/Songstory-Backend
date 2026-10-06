from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .book import Book, Chapter
from .music import Playlist


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    text = models.TextField("Текст")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True, related_name="comments")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True, blank=True, related_name="comments")
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, null=True, blank=True, related_name="comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(book__isnull=False, chapter__isnull=True, playlist__isnull=True)
                    | Q(book__isnull=True, chapter__isnull=False, playlist__isnull=True)
                    | Q(book__isnull=True, chapter__isnull=True, playlist__isnull=False)
                ),
                name="comment_has_exactly_one_target",
            )
        ]
        verbose_name = "Коментар"
        verbose_name_plural = "Коментарі"

    def __str__(self) -> str:
        return f"{self.user}: {self.text[:40]}"

    def clean(self) -> None:
        if self.parent_id and self.parent.parent_id:
            raise ValidationError("Відповідати можна лише на коментар верхнього рівня.")

    @property
    def target(self):
        return self.book or self.chapter or self.playlist
