import unittest
import copy
from boreal.tray_model import menu
from boreal.core import PRESETS
from test_service import ControllerTests as BaseControllerTests

class MenuTests(unittest.TestCase):
    def setUp(self):
        self.device=dict(id='one',name='Kraken',connected=True,active='Falscher Name',active_profile=PRESETS['Leise'],status={},colors=['ring'],lcd=640,display={'mode':'stats'},stats=True)
    def flatten(self,nodes):
        return {n['key']:n for n in nodes}|{k:v for n in nodes for k,v in self.flatten(n['children']).items()}
    def test_profile_uses_curve_and_captures_identity(self):
        m=self.flatten(menu({'devices':[self.device]},PRESETS,'one'))
        self.assertTrue(m['profile:Leise']['checked'])
        self.assertFalse(m['profile:Leistung']['checked'])
        self.device['id']='two'
        self.assertEqual(m['profile:Leise']['command']['device'],'one')
        self.assertEqual(m['stats']['command']['op'],'pause_stats')
    def test_busy_and_disconnected(self):
        m=self.flatten(menu({'devices':[self.device]},PRESETS,'one',True))
        self.assertFalse(m['profile:Leise']['enabled']);self.assertTrue(m['emergency']['enabled'])
        self.device['connected']=False
        m=self.flatten(menu({'devices':[self.device]},PRESETS,'one'))
        self.assertFalse(m['emergency']['enabled']);self.assertTrue(m['open']['enabled'])
    def test_no_saved_lighting(self):
        m=self.flatten(menu({'devices':[self.device]},PRESETS,'one'))
        self.assertFalse(m['rgb-restore']['enabled'])

class QuickActionTests(unittest.TestCase):
    setUp=BaseControllerTests.setUp
    tearDown=BaseControllerTests.tearDown
    call=BaseControllerTests.call
    def test_lighting_off_preserves_last_on(self):
        self.call('attach');self.call('color',channel='external',mode='fixed',hex='ff0000',brightness=70)
        self.call('lights_off')
        item=self.controller.devices['demo-z3']
        self.assertEqual(item['rgb_last_on']['external']['hex'],'ff0000')
        self.assertEqual(item['rgb_settings']['external']['mode'],'off')
        self.call('restore_lights')
        self.assertEqual(item['rgb_settings']['external']['mode'],'fixed')
    def test_pause_keeps_last_display_without_usb(self):
        self.call('attach');item=self.controller.devices['demo-z3'];item['display']['mode']='stats';item['stats']=True
        before=len(self.worker.calls);self.call('pause_stats')
        self.assertFalse(item['stats']);self.assertEqual(item['display']['mode'],'stats');self.assertEqual(before,len(self.worker.calls))

del BaseControllerTests
