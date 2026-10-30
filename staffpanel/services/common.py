from collections.abc import Iterable

from django.db.models import Count, IntegerField, Model, OuterRef, Subquery
from django.db.models.functions import Coalesce


def related_count(model: type[Model], link: str) -> Coalesce:
    totals = (
        model.objects.filter(**{link: OuterRef("pk")})
        .order_by()
        .values(link)
        .annotate(total=Count("pk"))
        .values("total")
    )
    return Coalesce(Subquery(totals, output_field=IntegerField()), 0)


def pks(items: Iterable[Model]) -> list[int]:
    return [item.pk for item in items]
