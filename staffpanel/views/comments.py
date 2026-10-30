from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core.models import Comment
from staffpanel.access import Permission, staff_action, staff_view
from staffpanel.actions import permitted, rows
from staffpanel.forms import read_filters
from staffpanel.pagination import paginate
from staffpanel.services.comments import COMMENT_ACTIONS, comment_queryset, describe_target
from staffpanel.views.common import ACTION_PARAM, run_action, selected_ids


@staff_view(Permission.COMMENTS_VIEW)
def comment_list(request):
    filters = read_filters(request, "Текст або автор")
    page, page_range = paginate(request, comment_queryset(query=filters.query))
    entries = [
        {"comment": row.obj, "target": describe_target(row.obj), "actions": row.actions}
        for row in rows(COMMENT_ACTIONS, request.user, page.object_list)
    ]
    return render(
        request,
        "staffpanel/comments/list.html",
        {
            "page": page,
            "page_range": page_range,
            "entries": entries,
            "bulk_actions": permitted(COMMENT_ACTIONS, request.user),
            "filters": filters,
        },
    )


@staff_action(Permission.COMMENTS_VIEW)
def comment_action(request, pk: int, action: str):
    get_object_or_404(Comment, pk=pk)
    return run_action(request, COMMENT_ACTIONS, action, Comment.objects.filter(pk=pk), reverse("staff:comments"))


@staff_action(Permission.COMMENTS_VIEW)
def comment_bulk(request):
    queryset = Comment.objects.filter(pk__in=selected_ids(request))
    return run_action(
        request, COMMENT_ACTIONS, request.POST.get(ACTION_PARAM, ""), queryset, reverse("staff:comments")
    )
