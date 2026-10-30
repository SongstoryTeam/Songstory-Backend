from django import template
from django.urls import reverse

from core.models import AuthorVerification
from staffpanel.access import Permission, has_access, is_staff_member
from staffpanel.actions import available
from staffpanel.services.books import BOOK_ACTIONS

register = template.Library()


@register.inclusion_tag("staffpanel/_book_toolbar.html", takes_context=True)
def staff_book_toolbar(context, book) -> dict:
    request = context["request"]
    user = request.user
    if not is_staff_member(user):
        return {}
    pending = list(
        AuthorVerification.objects.filter(book=book, status=AuthorVerification.Status.PENDING).values_list(
            "pk", flat=True
        )[:2]
    )
    verification_url = ""
    if pending and has_access(user, Permission.VERIFICATIONS_VIEW):
        verification_url = (
            reverse("staff:verification_detail", args=[pending[0]])
            if len(pending) == 1
            else reverse("staff:verifications")
        )
    return {
        "request": request,
        "book": book,
        "actions": available(BOOK_ACTIONS, user, book),
        "can_edit": has_access(user, Permission.BOOKS_CHANGE),
        "can_open": has_access(user, Permission.BOOKS_VIEW),
        "verification_url": verification_url,
    }
