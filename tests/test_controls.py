import tempfile
import unittest
from pathlib import Path
from boreal.colors import parse_hex,hsv_hex
from boreal.settings import Settings,ProfileLibrary
from boreal.core import PRESETS,TEST_PRESETS,profile

class ControlsTests(unittest.TestCase):
    def test_colors(self):
        self.assertEqual(parse_hex('#FF0000'),(1,0,0))
        self.assertEqual(hsv_hex(0,1),'FF0000')
        self.assertEqual(hsv_hex(1/3,1),'00FF00')
        self.assertEqual(hsv_hex(.5,0),'FFFFFF')
        for value in ('red','#123','GG0000','1234567'):
            with self.assertRaises(ValueError):parse_hex(value)

    def test_intervals_persist_and_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings=Settings(Path(tmp))
            for value in (500,1000,2000,3000,5000):
                settings.refresh_interval(value)
                self.assertEqual(Settings(Path(tmp)).read()['refresh_interval_ms'],value)
            for value in (True,0,1,500.0,'500',600):
                with self.assertRaises(ValueError):settings.refresh_interval(value)

    def test_test_profiles_are_additive(self):
        with tempfile.TemporaryDirectory() as tmp:
            library=ProfileLibrary(Path(tmp));library.save('Mein Profil',PRESETS['Leise'])
            values=library.read()
            for key,value in {**PRESETS,**TEST_PRESETS}.items():self.assertEqual(values[key],profile(value))
            self.assertEqual(values['Mein Profil'],PRESETS['Leise'])
            library.save('Zweites Profil',PRESETS['Leistung'])
            self.assertEqual(library.read()['Mein Profil'],PRESETS['Leise'])
