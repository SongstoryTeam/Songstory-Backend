from django.conf import settings
from django.core.paginator import Page

from core.utils.pagination import paginate as paginate_page

PAGE_PARAM = "page"


def paginate(request, queryset) -> tuple[Page, list]:
    return paginate_page(queryset, request.GET.get(PAGE_PARAM), settings.STAFF_PAGE_SIZE)
