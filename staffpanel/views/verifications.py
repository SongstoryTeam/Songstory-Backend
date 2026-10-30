from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from core import audit
from core.models import AuthorVerification
from staffpanel.access import Permission, has_access, staff_required, staff_view
from staffpanel.forms import VerificationReviewForm, read_filters
from staffpanel.pagination import paginate
from staffpanel.services import overview
from staffpanel.services.verifications import (
    ALREADY_REVIEWED,
    DEFAULT_STATE,
    Decision,
    ReviewError,
    VerificationState,
    authorship_taken,
    review,
    verification_queryset,
)

PROOF_FIELDS = ("proof_document", "proof_authorship")
DECISION_DONE = {
    Decision.APPROVE: "Заявку схвалено. Користувач отримає лист.",
    Decision.REJECT: "Заявку відхилено. Користувач отримає лист із причиною.",
}
PROOF_LOG_PREFIX = "Переглянуто документ: "


@staff_view(Permission.VERIFICATIONS_VIEW)
def verification_list(request):
    filters = read_filters(request, "Користувач або книга")
    state = filters.state if filters.state in VerificationState.values else DEFAULT_STATE.value
    page, page_range = paginate(request, verification_queryset(state=state, query=filters.query))
    return render(
        request,
        "staffpanel/verifications/list.html",
        {
            "page": page,
            "page_range": page_range,
            "filters": filters,
            "current_state": state,
            "states": VerificationState.choices,
            "pending_state": VerificationState.PENDING.value,
            "pending_total": overview.pending_counts()[overview.Badge.VERIFICATIONS.value],
        },
    )


@staff_view(Permission.VERIFICATIONS_VIEW)
def verification_detail(request, pk: int):
    verification = get_object_or_404(
        AuthorVerification.objects.select_related("user__profile", "book__author", "reviewed_by"), pk=pk
    )
    can_review = has_access(request.user, Permission.VERIFICATIONS_REVIEW)
    pending = verification.status == AuthorVerification.Status.PENDING
    form = VerificationReviewForm(request.POST or None) if can_review and pending else None
    if request.method == "POST":
        if not can_review:
            raise Http404
        if not pending:
            messages.error(request, ALREADY_REVIEWED)
            return redirect("staff:verification_detail", pk=pk)
        if form.is_valid():
            decision = Decision(form.cleaned_data["decision"])
            try:
                review(pk, request.user, decision, form.cleaned_data["note"])
            except ReviewError as error:
                messages.error(request, str(error))
                return redirect("staff:verification_detail", pk=pk)
            messages.success(request, DECISION_DONE[decision])
            return redirect("staff:verifications")
    return render(
        request,
        "staffpanel/verifications/detail.html",
        {
            "verification": verification,
            "form": form,
            "can_review": can_review,
            "pending": pending,
            "taken": authorship_taken(verification),
            "proofs": [(field, verification._meta.get_field(field).verbose_name) for field in PROOF_FIELDS],
            "Decision": Decision,
        },
    )


@staff_required(Permission.VERIFICATIONS_REVIEW)
def proof_download(request, pk: int, field: str):
    if field not in PROOF_FIELDS:
        raise Http404
    verification = get_object_or_404(AuthorVerification, pk=pk)
    stored = getattr(verification, field)
    if not stored:
        raise Http404
    try:
        handle = stored.open("rb")
    except FileNotFoundError:
        raise Http404
    label = verification._meta.get_field(field).verbose_name
    audit.record(request.user, [verification], audit.CHANGE, f"{PROOF_LOG_PREFIX}{label}")
    return FileResponse(handle, as_attachment=True, filename=stored.name.rsplit("/", 1)[-1])
