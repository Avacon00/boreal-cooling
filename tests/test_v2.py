import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path
from boreal.rgb import frames, parse_accessories
from boreal.settings import restore_allowed, Settings
from boreal.errors import BorealError
from test_service import FakeWorker
from boreal.service import Controller
from boreal.core import Profiles


class V2RegressionTests(unittest.TestCase):
    def test_ui_builders_do_not_shadow_gettext(self):
        source = (Path(__file__).resolve().parents[1] / "boreal/ui.py").read_text()
        self.assertNotIn("content,_=self.page", source)

    def test_ui_fields_do_not_shadow_methods(self):
        tree = ast.parse((Path(__file__).parents[1] / 'boreal/ui.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        methods = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
        assigned = {n.attr for n in ast.walk(cls) if isinstance(n, ast.Attribute)
                    and isinstance(n.ctx, ast.Store) and isinstance(n.value, ast.Name)
                    and n.value.id == 'self'}
        self.assertFalse(methods & assigned)

    def test_rgb_only_detected_accessories(self):
        report = bytearray(64); report[:2] = b'\x21\x03'; report[14] = 2
        report[15] = 0x1e; report[21:24] = bytes([0x17]*3)
        self.assertEqual(parse_accessories(report), {'ring': {'mask': 1, 'leds': 24}, 'fans': {'mask': 2, 'leds': 24}})
        report[22] = 0xff
        self.assertEqual(list(parse_accessories(report)), ['ring'])
        with self.assertRaises(ValueError): parse_accessories(bytes(64))

    def test_rgb_grb_chunk_and_brightness(self):
        packets = frames(1, 24, (200, 100, 50), 50)
        self.assertEqual(len(packets), 3)
        self.assertTrue(all(len(p) == 64 for p in packets))
        self.assertEqual(packets[0][:7], bytes([0x22, 0x10, 1, 0, 50, 100, 25]))
        self.assertEqual(packets[1][:7], bytes([0x22, 0x11, 1, 0, 50, 100, 25]))
        self.assertEqual(packets[2][:3], bytes([0x22, 0xa0, 1]))
        for mask, count in ((3,24), (1,41), (1,0)):
            with self.assertRaises(ValueError): frames(mask,count,(0,0,0))

    def test_restore_requires_every_guard(self):
        saved = dict(enabled=True, firmware='1.2.0')
        device = dict(identity='Seriennummer', pid='3012', firmware='1.2.0')
        self.assertTrue(restore_allowed(saved, device))
        for change in ({'enabled':False}, {'latched':True}, {'firmware':'1.3.0'}):
            self.assertFalse(restore_allowed({**saved, **change}, device))
        for change in ({'identity':'USB-Adresse'}, {'pid':'3008'}, {'firmware':'1.3.0'}):
            self.assertFalse(restore_allowed(saved, {**device, **change}))

    def test_corrupt_settings_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'settings-v2.json'; path.write_text('{broken')
            with self.assertRaises(ValueError): Settings(Path(tmp))
            self.assertEqual(path.read_text(), '{broken')

    def test_display_error_keeps_healthy_cooling(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker=FakeWorker(); ctl=Controller(worker, Profiles(Path(tmp)/'profiles.json'))
            def call(op, **args): return ctl.dispatch(dict(v=2,op=op,device='demo-z3',**args))
            call('discover'); call('attach'); worker.fail='screen'
            with self.assertRaises(BorealError): call('screen',mode='orientation',value=90)
            item=ctl.snapshot()['devices'][0]
            self.assertTrue(item['connected']); self.assertFalse(item['latched'])
            self.assertTrue(item['display']['error'])
            self.assertNotIn('detach',worker.calls)

    def test_fifty_rotation_commands_preserve_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker=FakeWorker(); ctl=Controller(worker, Profiles(Path(tmp)/'profiles.json'))
            def call(op, **args): return ctl.dispatch(dict(v=2,op=op,device='demo-z3',**args))
            call('discover'); call('attach')
            for i in range(50):
                call('screen',mode='orientation',value=(i%4)*90)
                self.assertTrue(ctl.snapshot()['devices'][0]['connected'])
            self.assertEqual(worker.calls.count('screen'),50)

class MediaLibraryTests(unittest.TestCase):
    def test_recrop_after_original_removed(self):
        import os
        from unittest.mock import patch
        from PIL import Image
        from boreal.library import media_call
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_DATA_HOME':tmp}):
            path=Path(tmp)/'original.png'
            Image.new('RGB',(160,80),'red').save(path)
            record=media_call('import',path=str(path),mode='static',size=64)
            path.unlink()
            self.assertTrue(Path(record['source']).is_file())
            recropped=media_call('import',path=record['source'],mode='static',size=64,options={'fit':'cover'})
            with Image.open(recropped['path']) as im:
                self.assertEqual(im.getpixel((0,0)), (255,0,0))

    def test_asset_rejects_unexpected_format(self):
        import os
        from unittest.mock import patch
        from boreal.library import directory, asset
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_DATA_HOME':tmp}):
            directory().mkdir(parents=True)
            key='a'*64
            (directory()/f'{key}.json').write_text(json.dumps({'format':'../../outside'}))
            with self.assertRaises(ValueError):asset(key)
