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


# Позначка «перша книга серії» в кінці назви: «Кн. 1», «Книга перша», «Том 1». Лише першу: «Кн. 2» — вже інша книга.
_FIRST_VOLUME = re.compile(r"\s+(?:кн|книга|том|т|частина|ч|book|vol|volume)\s+(?:1|перша|перший|одна|one)$")


def title_identity(title: str) -> str:
    """Ключ «тієї самої книги»: «Тюремна цілителька» і «Тюремна цілителька. Кн. 1» збігаються, а «Кн. 2» — ні."""
    key = search_form(title)
    return _FIRST_VOLUME.sub("", key).strip() or key
