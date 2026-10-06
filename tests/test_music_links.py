from unittest import mock

from django.test import SimpleTestCase

from core.services.http import ExternalServiceError
from core.services.music_links import canonical_url, embed_url, fetch_metadata, parse_link

YOUTUBE_ID = "dQw4w9WgXcQ"
SPOTIFY_ID = "4cOdK2wGLETKBW3PvgPWqT"


class ParseLinkTests(SimpleTestCase):
    def test_youtube_variants_resolve_to_same_id(self):
        urls = [
            f"https://www.youtube.com/watch?v={YOUTUBE_ID}",
            f"https://youtu.be/{YOUTUBE_ID}",
            f"https://m.youtube.com/watch?feature=share&v={YOUTUBE_ID}",
            f"https://www.youtube.com/embed/{YOUTUBE_ID}",
            f"https://music.youtube.com/watch?v={YOUTUBE_ID}",
        ]
        for url in urls:
            with self.subTest(url=url):
                link = parse_link(url)
                self.assertEqual((link.platform, link.external_id), ("youtube", YOUTUBE_ID))

    def test_spotify_variants(self):
        for url in (f"https://open.spotify.com/track/{SPOTIFY_ID}?si=abc", f"spotify:track:{SPOTIFY_ID}"):
            with self.subTest(url=url):
                link = parse_link(url)
                self.assertEqual((link.platform, link.external_id), ("spotify", SPOTIFY_ID))

    def test_rejects_unsupported_links(self):
        for url in ("https://example.com/watch?v=dQw4w9WgXcQ", "https://open.spotify.com/album/abc", "not a url", ""):
            with self.subTest(url=url):
                self.assertIsNone(parse_link(url))

    def test_url_builders(self):
        self.assertEqual(canonical_url("youtube", YOUTUBE_ID), f"https://www.youtube.com/watch?v={YOUTUBE_ID}")
        self.assertIn(YOUTUBE_ID, embed_url("youtube", YOUTUBE_ID))
        self.assertEqual(embed_url("spotify", SPOTIFY_ID), f"https://open.spotify.com/embed/track/{SPOTIFY_ID}")


class MetadataTests(SimpleTestCase):
    def test_reads_title_and_strips_topic_suffix(self):
        link = parse_link(f"https://youtu.be/{YOUTUBE_ID}")
        payload = {"title": "Пісня", "author_name": "Гурт - Topic"}
        with mock.patch("core.services.music_links.get_json", return_value=payload):
            metadata = fetch_metadata(link)
        self.assertEqual((metadata.title, metadata.artist), ("Пісня", "Гурт"))

    def test_returns_none_when_service_fails(self):
        link = parse_link(f"https://youtu.be/{YOUTUBE_ID}")
        with mock.patch("core.services.music_links.get_json", side_effect=ExternalServiceError("down")):
            self.assertIsNone(fetch_metadata(link))

    def test_returns_none_without_title(self):
        link = parse_link(f"https://youtu.be/{YOUTUBE_ID}")
        with mock.patch("core.services.music_links.get_json", return_value={}):
            self.assertIsNone(fetch_metadata(link))
