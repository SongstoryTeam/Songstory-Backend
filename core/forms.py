from datetime import date

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import AuthorVerification, Platform, Track
from .services.books import find_duplicate
from .services.music_links import parse_link


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.HiddenInput)):
                continue
            css_class = "form-select" if isinstance(widget, forms.Select) else "form-input"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css_class}".strip()


class SignUpForm(StyledFormMixin, UserCreationForm):
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
            "icon": "contact",
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
        widget=forms.TextInput(
            attrs={
                "placeholder": "cool_reader_42",
                "autocomplete": "username",
                "autofocus": "autofocus",
                "data-check": "username",
            }
        ),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"placeholder": "example@mail.com", "autocomplete": "email", "data-check": "email"}
        )
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
        fields = ("username", "email", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Пароль"
        self.fields["password1"].widget.attrs.update(
            {"placeholder": "Мінімум 8 символів", "autocomplete": "new-password", "data-role": "password"}
        )
        self.fields["password2"].label = "Повторіть пароль"
        self.fields["password2"].widget.attrs.update(
            {"placeholder": "Введіть пароль ще раз", "autocomplete": "new-password", "data-role": "password-confirm"}
        )

    def clean_email(self) -> str:
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Цю пошту вже використано.")
        return email

    def steps_with_fields(self):
        for step in self.STEPS:
            yield {**step, "bound_fields": [self[name] for name in step["fields"]]}

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=commit)
        if commit:
            user.profile.phone = self.cleaned_data.get("phone", "")
            user.profile.save(update_fields=["phone"])
        return user


class ProfileForm(StyledFormMixin, forms.ModelForm):
    bio = forms.CharField(label="Про себе", required=False, widget=forms.Textarea(attrs={"rows": 4}))

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {"first_name": "Ім'я", "last_name": "Прізвище", "email": "Пошта"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["bio"].initial = self.instance.profile.bio

    def clean_email(self) -> str:
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Цю пошту вже використано.")
        return email

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=commit)
        if commit:
            user.profile.bio = self.cleaned_data["bio"]
            user.profile.save(update_fields=["bio"])
        return user


class BookCreateForm(StyledFormMixin, forms.Form):
    duplicate = None

    title = forms.CharField(label="Назва", max_length=255)
    author_name = forms.CharField(label="Автор", max_length=255)
    year = forms.IntegerField(label="Рік видання", required=False, min_value=1)
    genre_name = forms.CharField(label="Жанр", max_length=100, required=False)
    cover_url = forms.URLField(label="Посилання на обкладинку", required=False, max_length=500)
    description = forms.CharField(label="Опис", required=False, widget=forms.Textarea(attrs={"rows": 4}))

    def clean_year(self):
        year = self.cleaned_data["year"]
        if year and year > date.today().year + 1:
            raise forms.ValidationError("Рік не може бути у далекому майбутньому.")
        return year

    def clean(self):
        cleaned = super().clean()
        title, author = cleaned.get("title"), cleaned.get("author_name")
        if title and author:
            duplicate = find_duplicate(title, author)
            if duplicate:
                self.duplicate = duplicate
                raise forms.ValidationError("Така книга вже є в каталозі.")
        return cleaned


class ChapterCountForm(StyledFormMixin, forms.Form):
    count = forms.IntegerField(
        label="Скільки розділів додати",
        min_value=1,
        max_value=settings.BULK_CHAPTERS_MAX,
        widget=forms.NumberInput(attrs={"placeholder": "10"}),
    )


class CommentField(forms.CharField):
    def __init__(self, **kwargs):
        super().__init__(
            required=False,
            max_length=settings.RECOMMENDATION_COMMENT_MAX_LENGTH,
            label="Чому цей трек підходить (необов'язково)",
            widget=forms.Textarea(attrs={"rows": 2}),
            **kwargs,
        )


class PickTrackForm(StyledFormMixin, forms.Form):
    track = forms.ModelChoiceField(queryset=Track.objects.all(), widget=forms.HiddenInput)
    comment = CommentField()


class TrackLinkForm(StyledFormMixin, forms.Form):
    url = forms.CharField(label="Посилання на трек", widget=forms.URLInput(attrs={"placeholder": "https://…"}))
    comment = CommentField()

    def clean_url(self) -> str:
        url = self.cleaned_data["url"].strip()
        link = parse_link(url)
        if link is None:
            raise forms.ValidationError("Підтримуються посилання на треки YouTube та Spotify.")
        self.link = link
        return url


class TrackDraftForm(StyledFormMixin, forms.Form):
    platform = forms.ChoiceField(choices=Platform.choices, widget=forms.HiddenInput)
    external_id = forms.CharField(max_length=100, widget=forms.HiddenInput)
    title = forms.CharField(label="Назва треку", max_length=255)
    artist = forms.CharField(label="Виконавець", max_length=255, required=False)
    comment = CommentField()


class PlaylistForm(StyledFormMixin, forms.Form):
    title = forms.CharField(label="Назва", max_length=255)
    description = forms.CharField(label="Опис", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    tracks = forms.ModelMultipleChoiceField(
        label="Треки з рекомендацій до цієї книги",
        queryset=Track.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, track_queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tracks"].queryset = track_queryset


class PlaylistTrackForm(StyledFormMixin, forms.Form):
    track = forms.ModelChoiceField(queryset=Track.objects.none(), label="Трек")

    def __init__(self, *args, track_queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["track"].queryset = track_queryset


class CommentForm(forms.Form):
    text = forms.CharField(max_length=settings.COMMENT_MAX_LENGTH, strip=True)


class AuthorVerificationForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = AuthorVerification
        fields = ["proof_document", "proof_authorship", "publisher_url", "additional_notes"]
        widgets = {
            "additional_notes": forms.Textarea(attrs={"rows": 4}),
            "publisher_url": forms.URLInput(attrs={"placeholder": "https://publisher.com/book/…"}),
        }
