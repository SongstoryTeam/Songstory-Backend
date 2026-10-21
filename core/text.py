import re
import unicodedata

from core import limits

_WHITESPACE = re.compile(r"\s+")

_APOSTROPHES = str.maketrans(dict.fromkeys("’ʼ‘`´′", "'"))
_STRIP_APOSTROPHES = str.maketrans("", "", "'’ʼ‘`´′")
_NON_WORD = re.compile(r"[\W_]+")

MAX_QUERY_LENGTH = 100


def normalize(value: str) -> str:
    return _WHITESPACE.sub(" ", value.translate(_APOSTROPHES).casefold()).strip()


def search_form(value: str) -> str:
    folded = unicodedata.normalize("NFC", value).casefold().translate(_STRIP_APOSTROPHES).replace("ґ", "г")
    return " ".join(_NON_WORD.sub(" ", folded).split())


def name_key(value: str) -> str:
    return " ".join(sorted(search_form(value).split()))[: limits.TEXT_MAX_LENGTH]


def search_terms(query: str) -> list[str]:
    return search_form(query).split()


def clean_query(raw: str) -> str:
    return " ".join(raw.split())[:MAX_QUERY_LENGTH]


_FIRST_VOLUME = re.compile(r"\s+(?:кн|книга|том|т|частина|ч|book|vol|volume)\s+(?:1|перша|перший|одна|one)$")


def title_identity(title: str) -> str:
    key = search_form(title)
    return _FIRST_VOLUME.sub("", key).strip() or key
