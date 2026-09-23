import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from boreal.diagnostics import export, log_excerpt, sanitize


class DiagnosticsTests(unittest.TestCase):
    def test_sanitize_state_and_strings(self):
        value = sanitize({
            'id': 'hidden',
            'message': '/home/alice/private.png device=abcdef0123456789abcdef01 serial=SECRET123',
        })
        self.assertNotIn('id', value)
        self.assertNotIn('alice', value['message'])
        self.assertNotIn('abcdef0123456789abcdef01', value['message'])
        self.assertNotIn('SECRET123', value['message'])

    def test_export_includes_only_bounded_redacted_log_tails(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_STATE_HOME': tmp}):
            root = Path(tmp) / 'boreal'
            root.mkdir()
            secret = '/home/alice/private.gif serial_number=MY-SERIAL device=abcdef0123456789abcdef01'
            (root / 'ui.log').write_text(('old\n' * 250) + secret + '\nlast useful line\n')
            (root / 'unrelated.log').write_text('must not be exported')
            destination = Path(export({'devices': [{'id': 'private'}]}))
            with zipfile.ZipFile(destination) as archive:
                expected = {'status.json', 'README.txt', 'logs/ui.log'}
                self.assertEqual(set(archive.namelist()), expected)
                log = archive.read('logs/ui.log').decode()
                self.assertNotIn('alice', log)
                self.assertNotIn('MY-SERIAL', log)
                self.assertNotIn('abcdef0123456789abcdef01', log)
                self.assertIn('last useful line', log)
                self.assertLessEqual(len(log.splitlines()), 200)
                state = json.loads(archive.read('status.json'))
                self.assertNotIn('id', state['snapshot']['devices'][0])

    def test_missing_log_has_no_excerpt(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(log_excerpt(Path(tmp) / 'missing.log'))
