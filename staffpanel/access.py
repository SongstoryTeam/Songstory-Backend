from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.db import models
from django.http import Http404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from core.ratelimits import rate_limited

RATE_LIMIT_GROUP = "staff_action"


class Permission(models.TextChoices):
    BOOKS_VIEW = "core.view_book"
    BOOKS_CHANGE = "core.change_book"
    BOOKS_DELETE = "core.delete_book"
    VERIFICATIONS_VIEW = "core.view_authorverification"
    VERIFICATIONS_REVIEW = "core.change_authorverification"
    COMMENTS_VIEW = "core.view_comment"
    COMMENTS_DELETE = "core.delete_comment"
    USERS_VIEW = "auth.view_user"
    USERS_CHANGE = "auth.change_user"
    ACTIVITY_VIEW = "admin.view_logentry"


def is_staff_member(user) -> bool:
    return bool(user and user.is_authenticated and user.is_active and user.is_staff)


def has_access(user, *permissions: str) -> bool:
    return is_staff_member(user) and all(user.has_perm(str(permission)) for permission in permissions)


def staff_required(*permissions: str):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not has_access(request.user, *permissions):
                raise Http404
            return view(request, *args, **kwargs)

        return never_cache(wrapper)

    return decorator


def staff_view(*permissions: str):
    def decorator(view):
        return staff_required(*permissions)(rate_limited(RATE_LIMIT_GROUP)(view))

    return decorator


def staff_action(*permissions: str):
    def decorator(view):
        return staff_required(*permissions)(require_POST(rate_limited(RATE_LIMIT_GROUP)(view)))

    return decorator
