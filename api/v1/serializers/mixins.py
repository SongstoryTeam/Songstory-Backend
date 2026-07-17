class LangMixin:
    def _lang(self) -> str:
        request = self.context.get("request")
        if request is not None:
            lang = request.query_params.get("lang", "").strip().lower()
            if lang in ("uk", "en"):
                return lang
        return "uk"
