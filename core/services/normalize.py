
import re
import unicodedata
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from core import limits

from .external import strip_html

MIN_YEAR = 1
ISBN_INPUT_MAX = 20
ISBN_10_LENGTH = 10
ISBN_13_LENGTH = 13
TYPOGRAPHIC_APOSTROPHE = "’"

_INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad"), None)
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

INSECURE_SCHEME = "http://"
SECURE_SCHEME = "https://"


def clean_text(value, max_length: int | None = None) -> str:
    text = _APOSTROPHE.sub(TYPOGRAPHIC_APOSTROPHE, _WHITESPACE.sub(" ", _base(value)).strip())
    return text[:max_length].rstrip() if max_length else text


def clean_title(value) -> str:
    return clean_text(value, limits.TEXT_MAX_LENGTH)


def clean_person_name(value) -> str:
    name = _COMMA_SPACING.sub(", ", clean_text(value)).strip(", ")
    if name and (name == name.lower() or name == name.upper()):
        name = _LETTERS.sub(lambda match: match.group().capitalize(), name.lower())
    return name[: limits.TEXT_MAX_LENGTH].rstrip()


def clean_genre_name(value) -> str:
    name = clean_text(value, limits.GENRE_NAME_MAX_LENGTH)
    return name[:1].upper() + name[1:]


def clean_description(value) -> str:
    text = strip_html_keep_lines(value)
    if len(text) > limits.DESCRIPTION_MAX_LENGTH:
        text = text[: limits.DESCRIPTION_MAX_LENGTH].rsplit(" ", 1)[0].rstrip()
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
    if url.startswith(INSECURE_SCHEME):
        url = SECURE_SCHEME + url[len(INSECURE_SCHEME) :]
    if not url or len(url) > limits.URL_MAX_LENGTH:
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
    return identifier if identifier and len(identifier) <= limits.GOOGLE_BOOKS_ID_MAX_LENGTH else None
