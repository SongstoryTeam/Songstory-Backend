from django import template
from django.conf import settings
from django.utils.translation import get_language

register = template.Library()


def _active_language() -> str:
    """Current active language, falling back to the project default."""
    return get_language() or settings.LANGUAGE_CODE


@register.filter
def localized_title(obj):
    """Translated title for any object exposing get_title(lang)."""
    return obj.get_title(_active_language())


@register.filter
def localized_description(obj):
    """Translated description for any object exposing get_description(lang)."""
    return obj.get_description(_active_language())


@register.filter
def localized_mood_tags(chapter):
    """Translated mood tags for a Chapter."""
    return chapter.get_mood_tags(_active_language())


@register.filter
def localized_name(obj):
    """Translated name for any object exposing get_name(lang) (Author, Genre)."""
    return obj.get_name(_active_language())


_SEARCH_SOURCE_LABELS = {
    "catalog": "У каталозі Songstery",
    "google_books": "Google Books",
    "open_library": "Open Library",
}


@register.filter
def source_label(source_code):
    """Human-readable label for a SearchResult.source value."""
    return _SEARCH_SOURCE_LABELS.get(source_code, source_code)


@register.simple_tag(takes_context=True)
def nav_active(context, *url_names):
    """Return "active" when the current view matches one of the given
    (optionally namespaced) URL names, e.g. {% nav_active 'core:home' %}.

    Centralises navigation highlighting in one place instead of every
    template overriding a dedicated block, so adding or reordering
    sidebar/topbar links never requires touching page templates.
    """
    request = context.get("request")
    match = getattr(request, "resolver_match", None)
    if not match:
        return ""

    current = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
    return "active" if current in url_names else ""
