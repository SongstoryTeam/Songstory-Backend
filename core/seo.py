import json

from django.conf import settings

ESCAPES = {"<": "\\u003c", ">": "\\u003e", "&": "\\u0026"}


def json_ld(payload: dict) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    for char, escaped in ESCAPES.items():
        text = text.replace(char, escaped)
    return text


def book_json_ld(book) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": book.title,
        "url": f"{settings.SITE_URL}{book.get_absolute_url()}",
    }
    if book.author:
        payload["author"] = {"@type": "Person", "name": book.author.name}
    if book.cover_url:
        payload["image"] = book.cover_url
    if book.isbn:
        payload["isbn"] = book.isbn
    if book.year:
        payload["datePublished"] = str(book.year)
    return json_ld(payload)
