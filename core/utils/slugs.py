from __future__ import annotations

from django.db import models
from slugify import slugify


def generate_unique_slug(
    model: type[models.Model],
    text: str,
    slug_field: str = "slug",
) -> str:
    base = slugify(text, allow_unicode=False) or "item"
    slug = base
    counter = 2
    qs = model._default_manager.all()
    while qs.filter(**{slug_field: slug}).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug
