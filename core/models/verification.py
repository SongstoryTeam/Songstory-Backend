from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.storage import get_private_storage
from core.validators import validate_upload_size

from .book import Book


def proof_upload_path(instance, filename: str) -> str:
    return f"author_proofs/{instance.user_id}/{filename}"


class AuthorVerification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Очікує"
        APPROVED = "approved", "Схвалено"
        REJECTED = "rejected", "Відхилено"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="author_verifications")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="author_verifications")
    proof_document = models.FileField(
        "Документ, що посвідчує особу",
        upload_to=proof_upload_path,
        storage=get_private_storage,
        validators=[
            FileExtensionValidator(settings.VERIFICATION_ALLOWED_EXTENSIONS),
            validate_upload_size,
        ],
    )
    proof_authorship = models.FileField(
        "Підтвердження авторства",
        upload_to=proof_upload_path,
        storage=get_private_storage,
        validators=[
            FileExtensionValidator(settings.VERIFICATION_ALLOWED_EXTENSIONS),
            validate_upload_size,
        ],
    )
    publisher_url = models.URLField("Сторінка книги на сайті видавця", blank=True)
    additional_notes = models.TextField("Додаткова інформація", blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    admin_note = models.TextField("Нотатка адміністратора", blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_verifications"
    )

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"],
                condition=Q(status="pending"),
                name="single_pending_verification_per_user_book",
            )
        ]
        verbose_name = "Заявка на верифікацію автора"
        verbose_name_plural = "Заявки на верифікацію авторів"

    def __str__(self) -> str:
        return f"{self.user.username} → {self.book} ({self.get_status_display()})"

    def approve(self, reviewer: User, note: str = "") -> None:
        from core import emails

        self._close(self.Status.APPROVED, reviewer, note)
        self.book.verified_author = self.user
        self.book.save(update_fields=["verified_author"])
        profile = self.user.profile
        profile.is_verified_author = True
        profile.save(update_fields=["is_verified_author"])
        emails.send_verification_approved(self)

    def reject(self, reviewer: User, note: str = "") -> None:
        from core import emails

        self._close(self.Status.REJECTED, reviewer, note)
        emails.send_verification_rejected(self)

    def _close(self, status: str, reviewer: User, note: str) -> None:
        self.status = status
        self.admin_note = note
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save(update_fields=["status", "admin_note", "reviewed_at", "reviewed_by"])
