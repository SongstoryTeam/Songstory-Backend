from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models.interaction import Comment, Like
from .models.notification import Notification


@receiver(post_save, sender=Like)
def notify_on_like(sender, instance: Like, created: bool, **kwargs) -> None:
    if not created:
        return
    if instance.music_recommendation_id:
        target = instance.music_recommendation
        recipient = target.user
        if recipient == instance.user:
            return
        Notification.objects.create(
            recipient=recipient,
            type=Notification.TYPE_LIKE_MUSIC,
            content_type=ContentType.objects.get_for_model(target),
            object_id=target.pk,
        )


@receiver(post_save, sender=Comment)
def notify_on_reply(sender, instance: Comment, created: bool, **kwargs) -> None:
    if not created or instance.parent_id is None:
        return
    recipient = instance.parent.user
    if recipient == instance.user:
        return
    Notification.objects.create(
        recipient=recipient,
        type=Notification.TYPE_COMMENT_REPLY,
        content_type=ContentType.objects.get_for_model(instance),
        object_id=instance.pk,
    )
