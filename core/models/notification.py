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
        (TYPE_LIKE_MUSIC, "Music liked"),
        (TYPE_COMMENT_REPLY, "Comment reply"),
        (TYPE_VERIFICATION_APPROVED, "Verification approved"),
        (TYPE_VERIFICATION_REJECTED, "Verification rejected"),
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
