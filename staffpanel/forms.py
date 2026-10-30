from dataclasses import dataclass

from django import forms

from core import limits
from core.forms import StyledFormMixin
from core.text import MAX_QUERY_LENGTH
from staffpanel.services.verifications import Decision

NOTE_REQUIRED_ERROR = "Вкажіть причину відмови: користувач отримає її листом."
NOTE_ROWS = 4


class FilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        max_length=MAX_QUERY_LENGTH,
        strip=True,
        widget=forms.TextInput(attrs={"type": "search", "autocomplete": "off", "spellcheck": "false"}),
    )
    state = forms.CharField(required=False, max_length=limits.CODE_MAX_LENGTH)


@dataclass(frozen=True)
class Filters:
    form: FilterForm
    query: str
    state: str


def read_filters(request, placeholder: str) -> Filters:
    form = FilterForm(request.GET)
    form.fields["q"].widget.attrs["placeholder"] = placeholder
    form.is_valid()
    return Filters(form, form.cleaned_data.get("q", ""), form.cleaned_data.get("state", ""))


class VerificationReviewForm(StyledFormMixin, forms.Form):
    decision = forms.ChoiceField(choices=Decision.choices, widget=forms.HiddenInput)
    note = forms.CharField(
        label="Коментар для користувача",
        required=False,
        max_length=limits.DESCRIPTION_MAX_LENGTH,
        widget=forms.Textarea(attrs={"rows": NOTE_ROWS}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == Decision.REJECT and not cleaned.get("note"):
            self.add_error("note", NOTE_REQUIRED_ERROR)
        return cleaned
