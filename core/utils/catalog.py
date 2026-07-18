from __future__ import annotations

from core.models.author import Author, AuthorTranslation
from core.models.genre import Genre, GenreTranslation
from core.models.language import Language
from core.utils.slugs import generate_unique_slug


def get_or_create_author(name: str, language: Language | None) -> Author:
    """Resolve free-text author input to an Author record, reusing an
    existing one (case-insensitive match on any translated name) or
    creating a new Author with a translation in the given language."""
    name = name.strip()
    existing = AuthorTranslation.objects.filter(name__iexact=name).select_related("author").first()
    if existing:
        return existing.author

    author = Author.objects.create(slug=generate_unique_slug(Author, name))
    if language:
        AuthorTranslation.objects.create(author=author, language=language, name=name)
    return author


def get_or_create_genre(name: str, language: Language | None) -> Genre:
    """Resolve free-text genre input to a Genre record, reusing an
    existing one (case-insensitive match on any translated name) or
    creating a new Genre with a translation in the given language."""
    name = name.strip()
    existing = GenreTranslation.objects.filter(name__iexact=name).select_related("genre").first()
    if existing:
        return existing.genre

    genre = Genre.objects.create(slug=generate_unique_slug(Genre, name))
    if language:
        GenreTranslation.objects.create(genre=genre, language=language, name=name)
    return genre
