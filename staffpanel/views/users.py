from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core.models import AuthorVerification
from staffpanel.access import Permission, staff_action, staff_view
from staffpanel.actions import available
from staffpanel.forms import read_filters
from staffpanel.pagination import paginate
from staffpanel.services.users import USER_ACTIONS, DEFAULT_STATE, UserState, activity_summary, user_queryset
from staffpanel.views.common import run_action

RECENT_VERIFICATIONS = 5


@staff_view(Permission.USERS_VIEW)
def user_list(request):
    filters = read_filters(request, "Ім'я або пошта")
    state = filters.state if filters.state in UserState.values else DEFAULT_STATE.value
    page, page_range = paginate(request, user_queryset(state=state, query=filters.query))
    return render(
        request,
        "staffpanel/users/list.html",
        {
            "page": page,
            "page_range": page_range,
            "filters": filters,
            "current_state": state,
            "states": UserState.choices,
        },
    )


@staff_view(Permission.USERS_VIEW)
def user_detail(request, pk: int):
    subject = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    return render(
        request,
        "staffpanel/users/detail.html",
        {
            "subject": subject,
            "summary": activity_summary(subject),
            "actions": available(USER_ACTIONS, request.user, subject),
            "verifications": AuthorVerification.objects.filter(user=subject)
            .select_related("book")
            .order_by("-submitted_at")[:RECENT_VERIFICATIONS],
            "authored_books": subject.authored_books.all(),
        },
    )


@staff_action(Permission.USERS_VIEW)
def user_action(request, pk: int, action: str):
    get_object_or_404(User, pk=pk)
    queryset = User.objects.select_related("profile").filter(pk=pk)
    return run_action(request, USER_ACTIONS, action, queryset, reverse("staff:user_detail", args=[pk]))
