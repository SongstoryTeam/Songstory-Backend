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
