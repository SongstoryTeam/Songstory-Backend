from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def _send(subject: str, template: str, context: dict, to) -> None:
    if not to:
        return
    body = render_to_string(template, context)
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to] if isinstance(to, str) else to,
        fail_silently=True,
    )


def _create_in_app(recipient, notification_type: str, obj=None) -> None:
    try:
        from django.contrib.contenttypes.models import ContentType
        from core.models.notification import Notification

        kwargs: dict = {"recipient": recipient, "type": notification_type}
        if obj is not None:
            kwargs["content_type"] = ContentType.objects.get_for_model(obj)
            kwargs["object_id"] = obj.pk
        Notification.objects.create(**kwargs)
    except Exception:
        pass


def notify_admin_new_verification(verification) -> None:
    if not settings.ADMIN_EMAIL:
        return
    _send(
        subject=f"[{settings.SITE_NAME}] Нова заявка на верифікацію автора",
        template="emails/admin_new_verification.txt",
        context={"verification": verification, "site_url": settings.SITE_URL},
        to=settings.ADMIN_EMAIL,
    )


def notify_author_approved(verification) -> None:
    _send(
        subject=f"[{settings.SITE_NAME}] Вашу заявку схвалено",
        template="emails/author_approved.txt",
        context={"verification": verification, "site_url": settings.SITE_URL},
        to=verification.user.email,
    )
    _create_in_app(verification.user, "verification_approved", verification)


def notify_author_rejected(verification) -> None:
    _send(
        subject=f"[{settings.SITE_NAME}] Результат розгляду заявки",
        template="emails/author_rejected.txt",
        context={"verification": verification, "site_url": settings.SITE_URL},
        to=verification.user.email,
    )
    _create_in_app(verification.user, "verification_rejected", verification)
