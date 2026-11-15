import json

from django.conf import settings
from django.urls import reverse
from django.utils.text import Truncator

from core.templatetags.core_extras import uk_plural

ESCAPES = {"<": "\\u003c", ">": "\\u003e", "&": "\\u0026"}
SCHEMA_CONTEXT = "https://schema.org"
DESCRIPTION_MAX_LENGTH = 158
DESCRIPTION_TRACK_SAMPLE = 3
LANGUAGE = "uk"


def json_ld(payload: dict) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    for char, escaped in ESCAPES.items():
        text = text.replace(char, escaped)
    return text


def absolute_url(path: str) -> str:
    return f"{settings.SITE_URL.rstrip('/')}{path}"


def graph(*nodes: dict) -> str:
    return json_ld({"@context": SCHEMA_CONTEXT, "@graph": [node for node in nodes if node]})


def shorten(text: str, limit: int = DESCRIPTION_MAX_LENGTH) -> str:
    return Truncator(" ".join(text.split())).chars(limit)


def breadcrumbs_ld(*crumbs: tuple[str, str]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": index, "name": name, "item": absolute_url(path)}
            for index, (name, path) in enumerate(crumbs, start=1)
        ],
    }


def track_label(track) -> str:
    return f"{track.artist} — {track.title}" if track.artist else track.title


def book_description(book, tracks_total: int, sample_tracks) -> str:
    author = f" ({book.author.name})" if book.author else ""
    if not tracks_total:
        return shorten(f"Музика до книги «{book.title}»{author}: додайте першу пісню до цієї книги чи розділів.")
    sample = ", ".join(track_label(track) for track in list(sample_tracks)[:DESCRIPTION_TRACK_SAMPLE])
    return shorten(
        f"Яку музику слухати під час читання «{book.title}»{author}? "
        f"Читачі радять {tracks_total} {uk_plural(tracks_total, 'трек,треки,треків')}: {sample}. Слухайте онлайн."
    )


def chapter_description(book, chapter, tracks_total: int, sample_tracks) -> str:
    if not tracks_total:
        return shorten(f"Музика до розділу «{chapter.display_title}» книги «{book.title}»: поки що без рекомендацій.")
    sample = ", ".join(track_label(track) for track in list(sample_tracks)[:DESCRIPTION_TRACK_SAMPLE])
    return shorten(
        f"Музика для читання: {chapter.display_title} з книги «{book.title}». "
        f"Читачі радять {sample}. Слухайте онлайн."
    )


def playlist_description(playlist, tracks_total: int) -> str:
    if playlist.description:
        return shorten(playlist.description)
    return shorten(
        f"Плейлист «{playlist.title}» до книги «{playlist.book.title}»: "
        f"{tracks_total} {uk_plural(tracks_total, 'трек,треки,треків')} для читання. Слухайте онлайн."
    )


def recording_nodes(tracks) -> list[dict]:
    nodes = []
    for track in tracks:
        node = {"@type": "MusicRecording", "name": track.title, "url": track.url}
        if track.artist:
            node["byArtist"] = {"@type": "MusicGroup", "name": track.artist}
        nodes.append(node)
    return nodes


def tracklist_ld(name: str, tracks) -> dict | None:
    nodes = recording_nodes(tracks)
    if not nodes:
        return None
    return {
        "@type": "ItemList",
        "name": name,
        "numberOfItems": len(nodes),
        "itemListElement": [
            {"@type": "ListItem", "position": index, "item": node} for index, node in enumerate(nodes, start=1)
        ],
    }


def book_node(book) -> dict:
    node = {
        "@type": "Book",
        "name": book.title,
        "url": absolute_url(book.get_absolute_url()),
        "inLanguage": LANGUAGE,
    }
    if book.author:
        node["author"] = {"@type": "Person", "name": book.author.name}
    if book.cover_url:
        node["image"] = book.cover_url
    if book.isbn:
        node["isbn"] = book.isbn
    if book.year:
        node["datePublished"] = str(book.year)
    if book.genre:
        node["genre"] = book.genre.name
    if book.description:
        node["description"] = shorten(book.description, 300)
    return node


def book_json_ld(book, tracks=()) -> str:
    crumbs = [("Каталог", reverse("core:book_list"))]
    if book.genre and book.genre.slug:
        crumbs.append((book.genre.name, book.genre.get_absolute_url()))
    crumbs.append((book.title, book.get_absolute_url()))
    return graph(
        book_node(book),
        breadcrumbs_ld(("Головна", reverse("core:home")), *crumbs),
        tracklist_ld(f"Музика до книги «{book.title}»", tracks),
    )


def chapter_json_ld(book, chapter, tracks=()) -> str:
    return graph(
        breadcrumbs_ld(
            ("Головна", reverse("core:home")),
            ("Каталог", reverse("core:book_list")),
            (book.title, book.get_absolute_url()),
            (chapter.display_title, chapter.get_absolute_url()),
        ),
        tracklist_ld(f"Музика до розділу «{chapter.display_title}»", tracks),
    )


def playlist_json_ld(playlist, tracks=()) -> str:
    book = playlist.book
    nodes = recording_nodes(tracks)
    playlist_node = {
        "@type": "MusicPlaylist",
        "name": playlist.title,
        "url": absolute_url(playlist.get_absolute_url()),
        "inLanguage": LANGUAGE,
        "numTracks": len(nodes),
        "track": nodes,
    }
    if playlist.description:
        playlist_node["description"] = shorten(playlist.description, 300)
    return graph(
        playlist_node,
        breadcrumbs_ld(
            ("Головна", reverse("core:home")),
            (book.title, book.get_absolute_url()),
            (playlist.title, playlist.get_absolute_url()),
        ),
    )


def website_json_ld() -> str:
    return graph(
        {
            "@type": "WebSite",
            "name": settings.SITE_NAME,
            "url": absolute_url(reverse("core:home")),
            "inLanguage": LANGUAGE,
            "description": settings.SITE_DESCRIPTION,
        },
        {
            "@type": "Organization",
            "name": settings.SITE_NAME,
            "url": absolute_url(reverse("core:home")),
        },
    )


def genre_json_ld(genre, path: str) -> str:
    return graph(
        {
            "@type": "CollectionPage",
            "name": genre.page_title,
            "url": absolute_url(path),
            "inLanguage": LANGUAGE,
        },
        breadcrumbs_ld(("Головна", reverse("core:home")), ("Каталог", reverse("core:book_list")), (genre.name, path)),
    )


READING_GUIDE_TITLE = "Музика для читання: що слухати, коли читаєш книгу"


def reading_guide_json_ld() -> str:
    path = reverse("core:reading_music")
    return graph(
        {
            "@type": "WebPage",
            "name": READING_GUIDE_TITLE,
            "url": absolute_url(path),
            "inLanguage": LANGUAGE,
            "isPartOf": {"@type": "WebSite", "name": settings.SITE_NAME, "url": absolute_url(reverse("core:home"))},
        },
        breadcrumbs_ld(("Головна", reverse("core:home")), ("Музика для читання", path)),
    )
