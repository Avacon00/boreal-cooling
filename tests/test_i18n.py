import os
import tempfile
import unittest
from pathlib import Path

from boreal.i18n import configure, gettext, profile_label, resolve_language
from boreal.settings import Settings


class LanguageTests(unittest.TestCase):
    def tearDown(self):
        configure("system", {"LANG": "de_DE.UTF-8"})

    def test_system_language_uses_german_only_for_german_locale(self):
        self.assertEqual(resolve_language("system", {"LANG": "de_DE.UTF-8"}), "de")
        self.assertEqual(resolve_language("system", {"LANG": "en_GB.UTF-8"}), "en")
        self.assertEqual(resolve_language("system", {"LANG": "fr_FR.UTF-8"}), "en")
        self.assertEqual(resolve_language("system", {"LANG": "C.UTF-8"}), "en")

    def test_english_catalog_and_stable_profile_keys(self):
        configure("en")
        self.assertEqual(gettext("Übersicht"), "Overview")
        self.assertEqual(profile_label("Ausgewogen"), "Balanced")
        self.assertEqual(profile_label("Mein Profil"), "Mein Profil")
        configure("de")
        self.assertEqual(gettext("Übersicht"), "Übersicht")

    def test_language_setting_persists_and_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(Path(tmp))
            self.assertEqual(settings.read()["language"], "system")
            settings.language("en")
            self.assertEqual(Settings(Path(tmp)).read()["language"], "en")
            with self.assertRaises(ValueError):
                settings.language("fr")


if __name__ == "__main__":
    unittest.main()
