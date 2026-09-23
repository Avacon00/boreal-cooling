import json
import tempfile
import unittest
from pathlib import Path
from boreal.core import curve, profile, Profiles, PRESETS, interpolate


class PolicyTests(unittest.TestCase):
    def test_presets_and_interpolation(self):
        for value in PRESETS.values():
            self.assertEqual(profile(value), value)
            self.assertEqual(interpolate(value['pump'], 80), 100)

    def test_rejects_unsafe_curves(self):
        for points in ([[20, 59], [50, 100]], [[20, 80], [30, 70], [50, 100]],
                       [[20, 60], [20, 90], [50, 100]], [[20, 60], [49, 100]],
                       [[20, 60], [50, float('nan')]], [[20, True], [50, 100]],
                       [[20, 60], [50, 101]], [[20, 60]], [[0, 60], [50, 100]]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                curve(points, 'pump')

    def test_requires_both_channels(self):
        with self.assertRaises(ValueError):
            profile({'pump': [[20, 60], [50, 100]]})

    def test_atomic_profile_roundtrip_and_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'profiles.json'
            store = Profiles(path)
            store.save('Sommer', PRESETS['Leistung'])
            self.assertEqual(store.read()['Sommer'], PRESETS['Leistung'])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            store.delete('Sommer')
            self.assertNotIn('Sommer', store.read())
            with self.assertRaises(ValueError):
                store.delete('Leise')

    def test_corrupted_profile_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'profiles.json'
            path.write_text('{broken')
            with self.assertRaises(json.JSONDecodeError):
                Profiles(path).save('Neu', PRESETS['Leise'])
            self.assertEqual(path.read_text(), '{broken')
