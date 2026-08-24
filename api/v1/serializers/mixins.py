from django.conf import settings

from core.models import Language


class LangMixin:
    """Resolves which translation to serve a response in.

    Priority: an explicit `?lang=` query param (validated against the
    catalog's active languages) beats Django's request-level
    `LANGUAGE_CODE`, which beats the project default. This replaces two
    previously separate, independently hardcoded implementations of the
    same concept.
    """

    def _lang(self) -> str:
        request = self.context.get("request")
        if request is None:
            return settings.LANGUAGE_CODE

        requested = request.query_params.get("lang", "").strip().lower()
        if requested and requested in self._active_language_codes():
            return requested

        return getattr(request, "LANGUAGE_CODE", settings.LANGUAGE_CODE)

    @staticmethod
    def _active_language_codes() -> set[str]:
        return set(Language.objects.filter(is_active=True).values_list("code", flat=True))