import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from boreal.autostart import autostart_path, set_ui_autostart


class AutostartTests(unittest.TestCase):
    def test_enable_and_disable_managed_entry(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_CONFIG_HOME': tmp}):
            set_ui_autostart(True, '/usr/bin/boreal')
            path = autostart_path()
            self.assertIn('Exec="/usr/bin/boreal" --hardware', path.read_text())
            self.assertIn('X-Boreal-Managed=true', path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            set_ui_autostart(False)
            self.assertFalse(path.exists())

    def test_disable_preserves_foreign_entry(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_CONFIG_HOME': tmp}):
            path = autostart_path(); path.parent.mkdir(parents=True)
            path.write_text('[Desktop Entry]\nName=Other\n')
            with self.assertRaises(ValueError):
                set_ui_autostart(False)
            self.assertTrue(path.exists())
