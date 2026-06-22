from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import (
    AuthorVerification,
    Book,
    BookRating,
    BookTranslation,
    Comment,
    Language,
    MusicRecommendation,
    Playlist,
    PlaylistTrack,
)
from .validators import validate_image_url


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-checkbox"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing} form-input".strip()


class BookForm(StyledFormMixin, forms.ModelForm):
    title = forms.CharField(max_length=255)
    description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-textarea"}),
        required=False,
    )

    class Meta:
        model = Book
        fields = ["author", "year", "genre", "cover_image", "cover_url"]
        widgets = {"cover_url": forms.URLInput(attrs={"placeholder": "https://..."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            translation = self.instance.translations.first()
            if translation:
                self.fields["title"].initial = translation.title
                self.fields["description"].initial = translation.description

    def clean_cover_url(self):
        url = self.cleaned_data.get("cover_url", "")
        if url:
            validate_image_url(url)
        return url

    def save(self, commit=True):
        book = super().save(commit=commit)
        if commit:
            language = Language.objects.filter(is_active=True).first()
            if language:
                BookTranslation.objects.update_or_create(
                    book=book,
                    language=language,
                    defaults={
                        "title": self.cleaned_data.get("title", ""),
                        "description": self.cleaned_data.get("description", ""),
                    },
                )
        return book


class SignUpForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "example@mail.com"}),
    )
    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "+380..."}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            user.profile.phone = self.cleaned_data.get("phone", "")
            user.profile.save(update_fields=["phone"])
        return user


class UserUpdateForm(StyledFormMixin, forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]


class MusicRecommendationForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = MusicRecommendation
        fields = ["track_title", "artist", "link_type", "link_url", "embed_code", "comment", "mood"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"}),
            "embed_code": forms.TextInput(attrs={"readonly": "readonly"}),
        }


class PlaylistForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Playlist
        fields = ["title", "description", "mood", "external_link", "is_public"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"})}


class PlaylistTrackForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PlaylistTrack
        fields = ["track_title", "artist", "link_url"]


class CommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 3, "class": "form-textarea"})}


class BulkChaptersForm(StyledFormMixin, forms.Form):
    number_of_chapters = forms.IntegerField(
        min_value=1,
        max_value=100,
        label="Number of chapters",
        widget=forms.NumberInput(attrs={"placeholder": "10"}),
    )


class AuthorVerificationForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = AuthorVerification
        fields = ["proof_document", "proof_authorship", "publisher_url", "additional_notes"]
        widgets = {
            "additional_notes": forms.Textarea(attrs={"rows": 4, "class": "form-textarea"}),
            "publisher_url": forms.URLInput(attrs={"placeholder": "https://publisher.com/book/..."}),
        }


class BookRatingForm(forms.ModelForm):
    class Meta:
        model = BookRating
        fields = ["score"]
        widgets = {"score": forms.HiddenInput()}
