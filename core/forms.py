from datetime import date

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.functional import cached_property

from . import limits
from .models import AuthorVerification, Genre, Platform, Track, UserProfile
from .services import suggestions as suggestion_service
from .services.books import find_duplicate, pending_books_left
from .services.normalize import (
    ISBN_INPUT_MAX,
    MIN_YEAR,
    clean_cover_url,
    clean_description,
    clean_genre_name,
    clean_isbn,
    clean_person_name,
    clean_title,
)
from .services.music_links import parse_link


USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = User._meta.get_field("username").max_length
PERSON_NAME_MAX_LENGTH = User._meta.get_field("first_name").max_length
TEXTAREA_ROWS_COMPACT = 2
TEXTAREA_ROWS_SHORT = 3
TEXTAREA_ROWS_DEFAULT = 4
TEXTAREA_ROWS_LONG = 5


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
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
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
        max_length=PERSON_NAME_MAX_LENGTH,
        label="Ім'я",
        widget=forms.TextInput(attrs={"placeholder": "Олена", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        required=False,
        max_length=PERSON_NAME_MAX_LENGTH,
        label="Прізвище",
        widget=forms.TextInput(attrs={"placeholder": "Коваленко", "autocomplete": "family-name"}),
    )
    phone = forms.CharField(
        required=False,
        max_length=limits.PHONE_MAX_LENGTH,
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
            profile = UserProfile.objects.for_user(user)
            profile.phone = self.cleaned_data.get("phone", "")
            profile.save(update_fields=["phone"])
        return user


class ProfileForm(StyledFormMixin, forms.ModelForm):
    bio = forms.CharField(label="Про себе", required=False, widget=forms.Textarea(attrs={"rows": TEXTAREA_ROWS_DEFAULT}))

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {"first_name": "Ім'я", "last_name": "Прізвище", "email": "Пошта"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["bio"].initial = UserProfile.objects.for_user(self.instance).bio

    def clean_email(self) -> str:
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Цю пошту вже використано.")
        return email

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=commit)
        if commit:
            profile = UserProfile.objects.for_user(user)
            profile.bio = self.cleaned_data["bio"]
            profile.save(update_fields=["bio"])
        return user


class AccentForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["accent"]
        widgets = {"accent": forms.RadioSelect(attrs={"class": "accent-option__input", "data-accent-option": ""})}


class BookFieldsForm(StyledFormMixin, forms.Form):
    GENRE_DATALIST_ID = "genre-options"

    title = forms.CharField(
        label="Назва",
        max_length=limits.TEXT_MAX_LENGTH,
        widget=forms.TextInput(
            attrs={"placeholder": "Наприклад, Тіні забутих предків", "autocomplete": "off", "autofocus": "autofocus"}
        ),
    )
    author_name = forms.CharField(
        label="Автор",
        max_length=limits.TEXT_MAX_LENGTH,
        widget=forms.TextInput(attrs={"placeholder": "Ім'я та прізвище", "autocomplete": "off"}),
    )
    year = forms.IntegerField(
        label="Рік видання",
        required=False,
        min_value=MIN_YEAR,
        widget=forms.NumberInput(attrs={"placeholder": "2020", "inputmode": "numeric"}),
    )
    genre_name = forms.CharField(
        label="Жанр",
        max_length=limits.GENRE_NAME_MAX_LENGTH,
        required=False,
        widget=forms.TextInput(
            attrs={
                "list": GENRE_DATALIST_ID,
                "autocomplete": "off",
                "placeholder": "Оберіть зі списку або введіть свій",
            }
        ),
    )
    isbn = forms.CharField(
        label="ISBN",
        max_length=ISBN_INPUT_MAX,
        required=False,
        help_text="Знайдіть його на звороті обкладинки. Допомагає виявити дублікати.",
        widget=forms.TextInput(attrs={"placeholder": "978-966-917-170-6", "inputmode": "numeric"}),
    )
    description = forms.CharField(
        label="Опис",
        required=False,
        max_length=limits.DESCRIPTION_MAX_LENGTH,
        widget=forms.Textarea(attrs={"rows": TEXTAREA_ROWS_LONG, "placeholder": "Кілька речень про сюжет або настрій книги"}),
    )
    cover_url = forms.URLField(
        label="Посилання на обкладинку",
        required=False,
        max_length=limits.URL_MAX_LENGTH,
        help_text="Пряме https-посилання на зображення (.jpg, .png, .webp).",
        widget=forms.URLInput(attrs={"placeholder": "https://…", "autocomplete": "off"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["year"].widget.attrs["max"] = date.today().year + 1

    @cached_property
    def genre_names(self) -> list[str]:
        return list(Genre.objects.values_list("name", flat=True))

    def clean_title(self):
        title = clean_title(self.cleaned_data["title"])
        if not title:
            raise forms.ValidationError("Вкажіть назву книги.")
        return title

    def clean_author_name(self):
        author = clean_person_name(self.cleaned_data["author_name"])
        if not author and self.fields["author_name"].required:
            raise forms.ValidationError("Вкажіть автора.")
        return author

    def clean_genre_name(self):
        return clean_genre_name(self.cleaned_data["genre_name"])

    def clean_isbn(self):
        raw = self.cleaned_data["isbn"]
        code = clean_isbn(raw)
        if raw.strip() and not code:
            raise forms.ValidationError("ISBN має містити 10 або 13 цифр.")
        return code

    def clean_description(self):
        return clean_description(self.cleaned_data["description"])

    def clean_cover_url(self):
        url = self.cleaned_data["cover_url"]
        cleaned = clean_cover_url(url)
        if url and not cleaned:
            raise forms.ValidationError("Потрібне коректне https-посилання на зображення.")
        return cleaned

    def clean_year(self):
        year = self.cleaned_data["year"]
        if year and year > date.today().year + 1:
            raise forms.ValidationError("Рік не може бути у далекому майбутньому.")
        return year


class BookCreateForm(BookFieldsForm):
    STEPS = (
        {
            "id": "book",
            "title": "Книга",
            "description": "За назвою й автором ми перевіримо, чи цієї книги ще немає в каталозі",
            "icon": "search",
            "fields": ("title", "author_name"),
        },
        {
            "id": "details",
            "title": "Подробиці",
            "description": "Необов'язково, але з ними книгу легше знайти й не сплутати з іншим виданням",
            "icon": "list-plus",
            "fields": ("year", "genre_name", "isbn", "description"),
        },
        {
            "id": "cover",
            "title": "Обкладинка",
            "description": "Вставте посилання на зображення, і ми покажемо, як книга виглядатиме в каталозі",
            "icon": "book-open",
            "fields": ("cover_url",),
        },
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.duplicate = None

    def steps_with_fields(self):
        for step in self.STEPS:
            yield {**step, "bound_fields": [self[name] for name in step["fields"]]}

    def clean(self):
        cleaned = super().clean()
        if pending_books_left(self.user) == 0:
            raise forms.ValidationError(
                f"На перевірці вже {settings.PENDING_BOOKS_LIMIT} ваших книг. "
                "Дочекайтесь рішення модератора, щоб додати нові."
            )
        title, author = cleaned.get("title"), cleaned.get("author_name")
        if title and author:
            duplicate = find_duplicate(title, author, cleaned.get("isbn", ""))
            if duplicate:
                self.duplicate = duplicate
                raise forms.ValidationError("Така книга вже є в каталозі або очікує на перевірку.")
        return cleaned


class BookEditSuggestionForm(BookFieldsForm):
    reason = forms.CharField(
        label="Чому ви пропонуєте ці зміни (необов'язково)",
        required=False,
        max_length=limits.SUGGESTION_REASON_MAX_LENGTH,
        widget=forms.Textarea(
            attrs={"rows": TEXTAREA_ROWS_SHORT, "placeholder": "Наприклад, виправлено помилку в назві видання"}
        ),
    )

    def __init__(self, *args, book, user, **kwargs):
        kwargs.setdefault("initial", suggestion_service.book_snapshot(book))
        super().__init__(*args, **kwargs)
        self.book = book
        self.user = user
        self.changes: dict = {}
        self.fields["author_name"].required = bool(book.author_id)

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        if suggestion_service.pending_suggestions_left(self.user) == 0:
            raise forms.ValidationError(
                f"На розгляді вже {settings.PENDING_SUGGESTIONS_LIMIT} ваших пропозицій. "
                "Дочекайтесь рішення модератора, щоб надіслати нові."
            )
        self.changes = suggestion_service.compute_changes(self.book, cleaned)
        if not self.changes:
            raise forms.ValidationError("Ви нічого не змінили.")
        if suggestion_service.touches_identity(self.changes) and suggestion_service.find_conflicting_book(
            self.book, cleaned
        ):
            raise forms.ValidationError("Така книга вже є в каталозі або очікує на перевірку.")
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
            max_length=limits.RECOMMENDATION_NOTE_MAX_LENGTH,
            label="Чому цей трек підходить (необов'язково)",
            widget=forms.Textarea(attrs={"rows": TEXTAREA_ROWS_COMPACT}),
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
    external_id = forms.CharField(max_length=limits.EXTERNAL_ID_MAX_LENGTH, widget=forms.HiddenInput)
    title = forms.CharField(label="Назва треку", max_length=limits.TEXT_MAX_LENGTH)
    artist = forms.CharField(label="Виконавець", max_length=limits.TEXT_MAX_LENGTH, required=False)
    comment = CommentField()


class PlaylistForm(StyledFormMixin, forms.Form):
    title = forms.CharField(label="Назва", max_length=limits.TEXT_MAX_LENGTH)
    description = forms.CharField(label="Опис", required=False, widget=forms.Textarea(attrs={"rows": TEXTAREA_ROWS_SHORT}))
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
            "additional_notes": forms.Textarea(attrs={"rows": TEXTAREA_ROWS_DEFAULT}),
            "publisher_url": forms.URLInput(attrs={"placeholder": "https://publisher.com/book/…"}),
        }
