from dataclasses import dataclass

from django.conf import settings
from django.urls import reverse

from staffpanel.access import Permission, has_access
from staffpanel.services.overview import Badge, pending_counts


@dataclass(frozen=True)
class Section:
    label: str
    icon: str
    url_name: str
    permission: Permission
    badge: Badge | None = None
    nested: tuple[str, ...] = ()

    @property
    def url_names(self) -> tuple[str, ...]:
        return (self.url_name, *self.nested)


OVERVIEW_URL_NAME = "staff:dashboard"
OVERVIEW_LABEL = "Панель керування"
OVERVIEW_ICON = "layout-dashboard"

SECTIONS = (
    Section("Книги", "book-open", "staff:books", Permission.BOOKS_VIEW, Badge.BOOKS),
    Section(
        "Заявки авторів",
        "badge-check",
        "staff:verifications",
        Permission.VERIFICATIONS_VIEW,
        Badge.VERIFICATIONS,
        ("staff:verification_detail",),
    ),
    Section("Коментарі", "message-square", "staff:comments", Permission.COMMENTS_VIEW),
    Section("Користувачі", "users", "staff:users", Permission.USERS_VIEW, None, ("staff:user_detail",)),
    Section("Журнал дій", "history", "staff:activity", Permission.ACTIVITY_VIEW),
)


@dataclass(frozen=True)
class NavItem:
    label: str
    icon: str
    url: str
    is_active: bool
    badge: int = 0

    @property
    def badge_label(self) -> str:
        cap = settings.STAFF_BADGE_CAP
        return f"{cap}+" if self.badge > cap else str(self.badge or "")


@dataclass(frozen=True)
class StaffNav:
    items: tuple[NavItem, ...]
    pending_total: int
    entry_url: str

    @property
    def pending_badge(self) -> str:
        return NavItem("", "", "", False, self.pending_total).badge_label


def build_nav(request) -> StaffNav | None:
    sections = [section for section in SECTIONS if has_access(request.user, section.permission)]
    if not sections:
        return None
    counts = pending_counts() if any(section.badge for section in sections) else {}
    current = getattr(request.resolver_match, "view_name", "")
    entry_url = reverse(OVERVIEW_URL_NAME)
    items = [NavItem(OVERVIEW_LABEL, OVERVIEW_ICON, entry_url, current == OVERVIEW_URL_NAME)]
    items.extend(
        NavItem(
            section.label,
            section.icon,
            reverse(section.url_name),
            current in section.url_names,
            counts.get(section.badge.value, 0) if section.badge else 0,
        )
        for section in sections
    )
    pending_total = sum(item.badge for item in items)
    return StaffNav(tuple(items), pending_total, entry_url)
