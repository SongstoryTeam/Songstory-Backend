import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")

# В українських назвах апостроф трапляється у кількох варіантах (', ’, ʼ, ‘, `, ´).
# Зводимо їх до одного, інакше «п'ята» не знайде «п’ята».
_APOSTROPHES = str.maketrans(dict.fromkeys("’ʼ‘`´′", "'"))
_STRIP_APOSTROPHES = str.maketrans("", "", "'’ʼ‘`´′")
_NON_WORD = re.compile(r"[\W_]+")

MAX_QUERY_LENGTH = 100


def normalize(value: str) -> str:
    return _WHITESPACE.sub(" ", value.translate(_APOSTROPHES).casefold()).strip()


def search_form(value: str) -> str:
    folded = unicodedata.normalize("NFC", value).casefold().translate(_STRIP_APOSTROPHES)
    return " ".join(_NON_WORD.sub(" ", folded).split())


def search_terms(query: str) -> list[str]:
    return search_form(query).split()


def clean_query(raw: str) -> str:
    """Обрізає надто довгі пошукові запити, щоб не навантажувати БД."""
    return " ".join(raw.split())[:MAX_QUERY_LENGTH]
