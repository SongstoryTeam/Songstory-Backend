from django.shortcuts import render

from staffpanel.access import Permission, staff_view
from staffpanel.forms import read_filters
from staffpanel.pagination import paginate
from staffpanel.services.activity import DEFAULT_KIND, ActivityKind, activity_queryset


@staff_view(Permission.ACTIVITY_VIEW)
def activity_list(request):
    filters = read_filters(request, "Об'єкт або виконавець")
    kind = filters.state if filters.state in ActivityKind.values else DEFAULT_KIND.value
    page, page_range = paginate(request, activity_queryset(kind=kind, query=filters.query))
    return render(
        request,
        "staffpanel/activity.html",
        {
            "page": page,
            "page_range": page_range,
            "filters": filters,
            "current_state": kind,
            "states": ActivityKind.choices,
        },
    )
