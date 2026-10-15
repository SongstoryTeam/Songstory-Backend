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
    # «ґ» зводимо до «г»: читачі часто набирають «Бардуго», а в книзі написано «Бардуґо».
    folded = unicodedata.normalize("NFC", value).casefold().translate(_STRIP_APOSTROPHES).replace("ґ", "г")
    return " ".join(_NON_WORD.sub(" ", folded).split())


def name_key(value: str) -> str:
    """Ключ автора, нечутливий до регістру, порядку слів і ґ/г: «Шевченко Тарас» = «тарас шевченко»."""
    return " ".join(sorted(search_form(value).split()))[:255]


def search_terms(query: str) -> list[str]:
    return search_form(query).split()


def clean_query(raw: str) -> str:
    """Обрізає надто довгі пошукові запити, щоб не навантажувати БД."""
    return " ".join(raw.split())[:MAX_QUERY_LENGTH]
