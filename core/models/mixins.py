from django.conf import settings


class TranslatableMixin:
    """Shared lookup logic for models that expose content through a
    `translations` related manager keyed by `Language.code`.

    Models using this mixin must define a `translations` related manager
    whose entries have a `language` foreign key. Looking up a field falls
    back to whichever translation exists first if the requested language
    isn't available, so pages never render blank instead of showing
    something in another language.
    """

    def get_translated_field(self, field: str, lang: str | None = None) -> str:
        lang = lang or settings.LANGUAGE_CODE
        translation = self.translations.filter(language__code=lang).first()
        value = getattr(translation, field, "") if translation else ""
        if value:
            return value

        fallback = self.translations.first()
        return getattr(fallback, field, "") if fallback else ""
