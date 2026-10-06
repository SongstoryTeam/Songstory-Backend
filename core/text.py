import re

_WHITESPACE = re.compile(r"\s+")


def normalize(value: str) -> str:
    return _WHITESPACE.sub(" ", value.casefold()).strip()


def search_terms(query: str) -> list[str]:
    return [term for term in normalize(query).split(" ") if term]
