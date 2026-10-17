"""Єдині правила очищення даних книги. Їх застосовують модель, форма додавання та імпорт, тож записи в базі однакові
незалежно від того, звідки прийшли."""

import re
import unicodedata
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from .external import strip_html

TITLE_MAX = 255
NAME_MAX = 255
GENRE_MAX = 100
DESCRIPTION_MAX = 5000
COVER_URL_MAX = 500
EXTERNAL_ID_MAX = 50
MIN_YEAR = 1
ISBN_INPUT_MAX = 20
ISBN_10_LENGTH = 10
ISBN_13_LENGTH = 13
TYPOGRAPHIC_APOSTROPHE = "’"

_INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad"), None)
# NUL та інші керівні символи Postgres не приймає зовсім; \n і \t лишаємо для обробки пробілів.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACES = re.compile(r"[^\S\n]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_WHITESPACE = re.compile(r"\s+")
_APOSTROPHE = re.compile(r"(?<=\w)['ʼ‘’`´′](?=\w)")
_LETTERS = re.compile(r"[^\W\d_]+")
_COMMA_SPACING = re.compile(r"\s*[,;]\s*")
_URL_VALIDATOR = URLValidator(schemes=["https"])


def _base(value) -> str:
    text = unicodedata.normalize("NFC", str(value or "")).translate(_INVISIBLE)
    return _CONTROL.sub("", text).replace("\r\n", "\n").replace("\r", "\n")


def clean_text(value, max_length: int | None = None) -> str:
    """Один рядок: без невидимих символів, з одним пробілом між словами та єдиним апострофом у словах."""
    text = _APOSTROPHE.sub(TYPOGRAPHIC_APOSTROPHE, _WHITESPACE.sub(" ", _base(value)).strip())
    return text[:max_length].rstrip() if max_length else text


def clean_title(value) -> str:
    return clean_text(value, TITLE_MAX)


def clean_person_name(value) -> str:
    """«тарас  шевченко» і «ТАРАС ШЕВЧЕНКО» стають «Тарас Шевченко». Змішаний регістр не чіпаємо: «ван Гог» лишається."""
    name = _COMMA_SPACING.sub(", ", clean_text(value)).strip(", ")
    if name and (name == name.lower() or name == name.upper()):
        name = _LETTERS.sub(lambda match: match.group().capitalize(), name.lower())
    return name[:NAME_MAX].rstrip()


def clean_genre_name(value) -> str:
    name = clean_text(value, GENRE_MAX)
    return name[:1].upper() + name[1:]


def clean_description(value) -> str:
    text = strip_html_keep_lines(value)
    if len(text) > DESCRIPTION_MAX:
        text = text[:DESCRIPTION_MAX].rsplit(" ", 1)[0].rstrip()
    return text


def strip_html_keep_lines(value) -> str:
    lines = [_APOSTROPHE.sub(TYPOGRAPHIC_APOSTROPHE, _SPACES.sub(" ", line).strip()) for line in _base(value).split("\n")]
    text = _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()
    return strip_html(text) if "<" in text and ">" in text else text


def clean_year(value) -> int | None:
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    return year if MIN_YEAR <= year <= date.today().year + 1 else None


def clean_cover_url(value) -> str:
    url = clean_text(value)
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    if not url or len(url) > COVER_URL_MAX:
        return ""
    try:
        _URL_VALIDATOR(url)
    except ValidationError:
        return ""
    return url


def clean_isbn(value) -> str:
    code = re.sub(r"[^0-9Xx]", "", str(value or "")).upper()
    if len(code) == ISBN_13_LENGTH:
        return code if code.isdigit() else ""
    if len(code) == ISBN_10_LENGTH:
        return code if code[:-1].isdigit() else ""
    return ""


def clean_external_id(value) -> str | None:
    identifier = clean_text(value)
    return identifier if identifier and len(identifier) <= EXTERNAL_ID_MAX else None
