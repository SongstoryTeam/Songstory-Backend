from django.test import override_settings
from django.test.runner import DiscoverRunner


class IsolatedTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._isolation = override_settings(BOOK_SOURCES=[])
        self._isolation.enable()

    def teardown_test_environment(self, **kwargs):
        self._isolation.disable()
        super().teardown_test_environment(**kwargs)
