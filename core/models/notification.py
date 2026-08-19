from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Notification(models.Model):
    TYPE_LIKE_MUSIC = "like_music"
    TYPE_COMMENT_REPLY = "comment_reply"
    TYPE_VERIFICATION_APPROVED = "verification_approved"
    TYPE_VERIFICATION_REJECTED = "verification_rejected"

    TYPE_CHOICES = [
        (TYPE_LIKE_MUSIC, "Вподобання треку"),
        (TYPE_COMMENT_REPLY, "Відповідь на коментар"),
        (TYPE_VERIFICATION_APPROVED, "Заявку на верифікацію схвалено"),
        (TYPE_VERIFICATION_REJECTED, "Заявку на верифікацію відхилено"),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"], name="core_notif_recip_read_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.get_type_display()}] → {self.recipient.username}"

    @classmethod
    def mark_all_read(cls, user: User) -> int:
        return cls.objects.filter(recipient=user, is_read=False).update(is_read=True)

    @classmethod
    def unread_count(cls, user: User) -> int:
        return cls.objects.filter(recipient=user, is_read=False).count()

    def get_message(self) -> str:
        """Human-readable summary shown in the notification feed and page."""
        obj = self.content_object
        if self.type == self.TYPE_LIKE_MUSIC:
            if obj is not None:
                return f"Хтось вподобав ваш трек «{obj.track_title}»"
            return "Хтось вподобав ваш трек"
        if self.type == self.TYPE_COMMENT_REPLY:
            return "Хтось відповів на ваш коментар"
        if self.type == self.TYPE_VERIFICATION_APPROVED:
            return "Вашу заявку на верифікацію автора схвалено"
        if self.type == self.TYPE_VERIFICATION_REJECTED:
            return "Вашу заявку на верифікацію автора відхилено"
        return self.get_type_display()

    def get_absolute_url(self) -> str | None:
        """Where clicking this notification should take the user, if the
        underlying object (or the object it belongs to) still exists."""
        obj = self.content_object
        if obj is None:
            return None
        if self.type == self.TYPE_LIKE_MUSIC:
            return obj.chapter.get_absolute_url()
        if self.type == self.TYPE_COMMENT_REPLY:
            return self._comment_url(obj)
        if self.type in (self.TYPE_VERIFICATION_APPROVED, self.TYPE_VERIFICATION_REJECTED):
            return obj.book.get_absolute_url()
        return None

    @staticmethod
    def _comment_url(comment) -> str | None:
        if comment.chapter_id:
            return comment.chapter.get_absolute_url()
        if comment.book_id:
            return comment.book.get_absolute_url()
        if comment.playlist_id:
            return comment.playlist.get_absolute_url()
        return None
