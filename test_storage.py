import tempfile

from django.test import SimpleTestCase, override_settings

from core.storage import TolerantManifestStaticFilesStorage


class TolerantStaticStorageTests(SimpleTestCase):
    def test_missing_file_returns_unhashed_url_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as root, override_settings(STATIC_ROOT=root, DEBUG=False):
            storage = TolerantManifestStaticFilesStorage()
            with self.assertLogs("core.storage", level="WARNING"):
                url = storage.url("images/og-default.png")
        self.assertTrue(url.endswith("/static/images/og-default.png"))
