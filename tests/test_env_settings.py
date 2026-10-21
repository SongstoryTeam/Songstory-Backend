import os
from unittest import mock

from django.test import SimpleTestCase

from songstery.settings import env_value


class EnvValueTests(SimpleTestCase):
    def test_missing_and_empty_values_fall_back_to_default(self):
        with mock.patch.dict(os.environ, {"EMPTY_VAR": "", "BLANK_VAR": "   "}):
            self.assertEqual(env_value("EMPTY_VAR", "fallback"), "fallback")
            self.assertEqual(env_value("BLANK_VAR", "fallback"), "fallback")
            self.assertEqual(env_value("UNSET_VAR_FOR_TEST", "fallback"), "fallback")

    def test_real_value_is_trimmed_and_returned(self):
        with mock.patch.dict(os.environ, {"REAL_VAR": "  value "}):
            self.assertEqual(env_value("REAL_VAR", "fallback"), "value")
