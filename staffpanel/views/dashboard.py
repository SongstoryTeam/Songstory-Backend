from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.http import Http404
from django.shortcuts import render

from core.models import AuthorVerification, Book
from staffpanel.access import Permission, has_access, staff_required
from staffpanel.navigation import build_nav
from staffpanel.services import overview


@staff_required()
def dashboard(request):
    nav = build_nav(request)
    if nav is None:
        raise Http404
    user = request.user
    limit = settings.STAFF_RECENT_LIMIT
    counts = overview.pending_counts()
    context = {
        "metrics": [metric for metric in overview.metrics() if has_access(user, metric.permission)],
        "trend_days": settings.STAFF_TREND_DAYS,
        "pending_books": None,
        "pending_verifications": None,
        "recent_activity": None,
    }
    if has_access(user, Permission.BOOKS_VIEW):
        context["pending_books"] = {
            "total": counts[overview.Badge.BOOKS.value],
            "items": Book.objects.filter(is_approved=False)
            .select_related("author", "creator")
            .order_by("created_at")[:limit],
        }
    if has_access(user, Permission.VERIFICATIONS_VIEW):
        context["pending_verifications"] = {
            "total": counts[overview.Badge.VERIFICATIONS.value],
            "items": AuthorVerification.objects.filter(status=AuthorVerification.Status.PENDING)
            .select_related("user", "book")
            .order_by("submitted_at")[:limit],
        }
    if has_access(user, Permission.ACTIVITY_VIEW):
        context["recent_activity"] = LogEntry.objects.select_related("user", "content_type").order_by(
            "-action_time", "-pk"
        )[:limit]
    return render(request, "staffpanel/dashboard.html", context)
