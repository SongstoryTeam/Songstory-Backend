from django.db import models
from slugify import slugify

DEFAULT_SLUG = "item"


def generate_unique_slug(model: type[models.Model], text: str, instance: models.Model | None = None) -> str:
    field = model._meta.get_field("slug")
    base = (slugify(text) or DEFAULT_SLUG)[: field.max_length - 6].strip("-") or DEFAULT_SLUG
    queryset = model._default_manager.all()
    if instance is not None and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    slug = base
    counter = 2
    while queryset.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug
