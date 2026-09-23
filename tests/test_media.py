import tempfile
import unittest
from pathlib import Path
from PIL import Image
from boreal.media import prepare_media, stats_image, sensors


class MediaTests(unittest.TestCase):
    def test_resize_and_stats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (800, 400), 'green').save(root / 'in.png')
            prepare_media(root / 'in.png', 'static', 320, root / 'out.png')
            with Image.open(root / 'out.png') as image:
                self.assertEqual(image.size, (320, 320))
            stats_image(240, {}, {}, root / 'stats.png')
            self.assertTrue((root / 'stats.png').is_file())

    def test_rejects_wrong_gif_and_oversize(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (10, 10)).save(root / 'in.png')
            with self.assertRaises(ValueError):
                prepare_media(root / 'in.png', 'gif', 320, root / 'out.gif')
            with (root / 'big').open('wb') as stream:
                stream.truncate(11 * 1024 * 1024)
            with self.assertRaises(ValueError):
                prepare_media(root / 'big', 'static', 320, root / 'out.png')

    def test_animated_gif(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = Image.new('RGB', (10, 10), 'red'), Image.new('RGB', (10, 10), 'blue')
            a.save(root / 'in.gif', save_all=True, append_images=[b], duration=100)
            prepare_media(root / 'in.gif', 'gif', 240, root / 'out.gif')
            with Image.open(root / 'out.gif') as image:
                self.assertEqual(image.n_frames, 2)

    def test_sensor_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hw = root / 'hwmon0'
            hw.mkdir()
            (hw / 'name').write_text('k10temp')
            (hw / 'temp1_input').write_text('65000')
            (hw / 'temp2_input').write_text('NaN')
            self.assertEqual(sensors(root), {'CPU': 65})
