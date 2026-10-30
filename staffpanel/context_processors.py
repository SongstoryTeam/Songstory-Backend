from django.utils.functional import SimpleLazyObject

from staffpanel.access import is_staff_member
from staffpanel.navigation import build_nav


def staff(request) -> dict:
    if not is_staff_member(getattr(request, "user", None)):
        return {}
    return {"staff_nav": SimpleLazyObject(lambda: build_nav(request))}
