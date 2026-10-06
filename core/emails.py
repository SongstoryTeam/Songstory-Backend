from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def _send(subject: str, template: str, context: dict, recipient: str) -> None:
    if not recipient:
        return
    send_mail(
        subject=f"[{settings.SITE_NAME}] {subject}",
        message=render_to_string(template, {**context, "site_url": settings.SITE_URL, "site_name": settings.SITE_NAME}),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=True,
    )


def notify_admin_new_verification(verification) -> None:
    _send(
        "Нова заявка на верифікацію автора",
        "emails/admin_new_verification.txt",
        {"verification": verification},
        settings.ADMIN_EMAIL,
    )


def send_verification_approved(verification) -> None:
    _send("Вашу заявку схвалено", "emails/author_approved.txt", {"verification": verification}, verification.user.email)


def send_verification_rejected(verification) -> None:
    _send(
        "Результат розгляду заявки",
        "emails/author_rejected.txt",
        {"verification": verification},
        verification.user.email,
    )
