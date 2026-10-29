from typing import NamedTuple

from django.conf import settings
from django.core.paginator import Page, Paginator


class Pagination(NamedTuple):
    page: Page
    page_range: list


def paginate(queryset, page_number, per_page: int) -> Pagination:
    paginator = Paginator(queryset, per_page)
    page = paginator.get_page(page_number)
    page_range = list(
        paginator.get_elided_page_range(
            page.number, on_each_side=settings.PAGINATION_WINDOW, on_ends=settings.PAGINATION_EDGE
        )
    )
    return Pagination(page=page, page_range=page_range)
