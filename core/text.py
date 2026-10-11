import re

_WHITESPACE = re.compile(r"\s+")

# В українських назвах апостроф трапляється у кількох варіантах (', ’, ʼ, ‘, `, ´).
# Зводимо їх до одного, інакше «п'ята» не знайде «п’ята».
_APOSTROPHES = str.maketrans(dict.fromkeys("’ʼ‘`´′", "'"))

MAX_QUERY_LENGTH = 100


def normalize(value: str) -> str:
    return _WHITESPACE.sub(" ", value.translate(_APOSTROPHES).casefold()).strip()


def search_terms(query: str) -> list[str]:
    return [term for term in normalize(query).split(" ") if term]


def clean_query(raw: str) -> str:
    """Обрізає надто довгі пошукові запити, щоб не навантажувати БД."""
    return " ".join(raw.split())[:MAX_QUERY_LENGTH]
