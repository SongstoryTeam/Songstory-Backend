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
from .utils.catalog import get_or_create_author, get_or_create_genre
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
    author_name = forms.CharField(max_length=255, label="Author")
    genre_name = forms.CharField(max_length=100, label="Genre", required=False)

    class Meta:
        model = Book
        fields = ["year", "cover_image", "cover_url"]
        widgets = {"cover_url": forms.URLInput(attrs={"placeholder": "https://..."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            translation = self.instance.translations.first()
            if translation:
                self.fields["title"].initial = translation.title
                self.fields["description"].initial = translation.description
            if self.instance.author_id:
                self.fields["author_name"].initial = self.instance.author.get_name()
            if self.instance.genre_id:
                self.fields["genre_name"].initial = self.instance.genre.get_name()

    def clean_cover_url(self):
        url = self.cleaned_data.get("cover_url", "")
        if url:
            validate_image_url(url)
        return url

    def save(self, commit=True):
        book = super().save(commit=False)
        language = Language.objects.filter(is_active=True).first()

        author_name = self.cleaned_data.get("author_name", "").strip()
        book.author = get_or_create_author(author_name, language) if author_name else None

        genre_name = self.cleaned_data.get("genre_name", "").strip()
        book.genre = get_or_create_genre(genre_name, language) if genre_name else None

        if commit:
            book.save()
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
    """
    Multi-step signup form. `STEPS` is the single source of truth for how the
    registration wizard is laid out — the template and the JS that drives the
    stepper both read it through `steps_with_fields()` instead of hardcoding
    field groupings anywhere else.
    """

    STEPS = (
        {
            "id": "account",
            "title": "Обліковий запис",
            "description": "Ім'я користувача та пошта, під якими вас впізнаватимуть",
            "icon": "user-round",
            "fields": ("username", "email"),
        },
        {
            "id": "profile",
            "title": "Про вас",
            "description": "Необов'язково, можна заповнити пізніше в профілі",
            "icon": "id-card",
            "fields": ("first_name", "last_name", "phone"),
        },
        {
            "id": "security",
            "title": "Захист акаунту",
            "description": "Пароль довжиною від 8 символів",
            "icon": "shield-check",
            "fields": ("password1", "password2"),
        },
    )

    username = forms.CharField(
        min_length=3,
        max_length=150,
        help_text="Тільки латинські літери, цифри та символи ./+/-/_",
        widget=forms.TextInput(attrs={
            "placeholder": "cool_reader_42",
            "autocomplete": "username",
            "autofocus": "autofocus",
            "data-check": "username",
        }),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "placeholder": "example@mail.com",
            "autocomplete": "email",
            "data-check": "email",
        }),
    )
    first_name = forms.CharField(
        required=False,
        max_length=150,
        label="Ім'я",
        widget=forms.TextInput(attrs={"placeholder": "Олена", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        required=False,
        max_length=150,
        label="Прізвище",
        widget=forms.TextInput(attrs={"placeholder": "Коваленко", "autocomplete": "family-name"}),
    )
    phone = forms.CharField(
        required=False,
        max_length=20,
        label="Телефон",
        widget=forms.TextInput(attrs={"placeholder": "+380 XX XXX XX XX", "autocomplete": "tel"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Пароль"
        self.fields["password1"].widget.attrs.update({
            "placeholder": "Мінімум 8 символів",
            "autocomplete": "new-password",
            "data-role": "password",
        })
        self.fields["password2"].label = "Повторіть пароль"
        self.fields["password2"].widget.attrs.update({
            "placeholder": "Введіть пароль ще раз",
            "autocomplete": "new-password",
            "data-role": "password-confirm",
        })

    def steps_with_fields(self):
        for step in self.STEPS:
            yield {**step, "bound_fields": [self[name] for name in step["fields"]]}

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