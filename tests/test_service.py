import copy
import tempfile
import unittest
from pathlib import Path
from boreal.core import PRESETS, Profiles
from boreal.hardware import DemoHardware, identity
from boreal.service import Controller


class FakeWorker:
    def __init__(self):
        self.hardware = DemoHardware()
        self.process = object()
        self.calls = []
        self.fail = None

    def close(self):
        self.process = None

    def call(self, op, *args):
        if self.process is None:
            self.process = object()
        self.calls.append(op)
        if self.fail == op:
            self.fail = None
            raise OSError('USB write failed')
        return getattr(self.hardware, op)(*args)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.worker = FakeWorker()
        self.controller = Controller(self.worker, Profiles(Path(self.temp.name) / 'p.json'))
        self.call('discover')

    def tearDown(self):
        self.temp.cleanup()

    def call(self, op, **kw):
        return self.controller.dispatch(dict(v=1, op=op, device='demo-z3', **kw))

    def test_discover_never_changes_speed(self):
        self.assertEqual(self.worker.calls, ['discover'])

    def test_attach_starts_at_100(self):
        state = self.call('attach')['devices'][0]
        self.assertTrue(state['connected'])
        self.assertEqual(self.worker.hardware.profiles['demo-z3']['pump'][0][1], 100)
        self.assertEqual(self.worker.calls[1:], ['attach', 'fallback', 'status'])

    def test_apply_requires_connection(self):
        from boreal.errors import BorealError
        with self.assertRaises(BorealError):
            self.call('apply', profile=PRESETS['Leise'])

    def test_validation_happens_before_writes(self):
        self.call('attach')
        before = len(self.worker.calls)
        bad = copy.deepcopy(PRESETS['Leise'])
        bad['fan'][0][1] = 0
        with self.assertRaises(ValueError):
            self.call('apply', profile=bad)
        self.assertEqual(before, len(self.worker.calls))

    def test_partial_write_fault_sets_fallback_and_latches(self):
        self.call('attach')
        self.worker.fail = 'curves'
        with self.assertRaises(RuntimeError):
            self.call('apply', profile=PRESETS['Leise'])
        state = self.controller.snapshot()['devices'][0]
        self.assertFalse(state['connected'])
        self.assertIn('Fallback gesendet', state['error'])
        self.assertEqual(state['status'], {})
        self.assertEqual(self.worker.calls[-2:], ['fallback', 'detach'])

    def test_invalid_telemetry_faults(self):
        for status in ({}, {'Liquid temperature': {'value': float('nan'), 'unit': '°C'}},
                       {'Liquid temperature': {'value': 51, 'unit': '°C'}, 'Pump speed': {'value': 1800, 'unit': 'rpm'}},
                       {'Liquid temperature': {'value': 32, 'unit': '°C'}, 'Pump speed': {'value': 0, 'unit': 'rpm'}},
                       {'Liquid temperature': {'value': 32, 'unit': 'F'}, 'Pump speed': {'value': 1800, 'unit': 'rpm'}}):
            with self.subTest(status=status), self.assertRaises(RuntimeError):
                Controller.check_status(status)

    def test_polling_error_clears_telemetry(self):
        self.call('attach')
        self.worker.fail = 'status'
        self.controller.tick()
        state = self.controller.snapshot()['devices'][0]
        self.assertFalse(state['connected'])
        self.assertFalse(state['status'])

    def test_dead_worker_does_not_guess_identity_for_fallback(self):
        self.call('attach')
        self.worker.process = None
        before = len(self.worker.calls)
        self.controller.fault(self.controller.devices['demo-z3'], 'timeout')
        self.assertEqual(len(self.worker.calls), before)
        self.assertIn('unbestätigt', self.controller.devices['demo-z3']['error'])

    def test_capability_gates(self):
        self.call('attach')
        item = self.controller.devices['demo-z3']
        item['colors'] = []
        with self.assertRaises(ValueError):
            self.call('color', channel='ring', mode='fixed', hex='ff00ff')
        item['gif'] = False
        with self.assertRaises(ValueError):
            self.call('screen', mode='gif', value='/tmp/nonexistent.gif')
        item['lcd'] = 0
        with self.assertRaises(ValueError):
            self.call('screen', mode='liquid')

    def test_rgb_screen_and_detach(self):
        self.call('attach')
        self.call('color', channel='external', mode='fixed', hex='74dbbb')
        self.call('screen', mode='liquid')
        result = self.call('detach')['devices'][0]
        self.assertFalse(result['connected'])
        self.assertEqual(self.worker.calls[-2:], ['fallback', 'detach'])

    def test_unknown_protocol_and_identity(self):
        with self.assertRaises(ValueError):
            self.controller.dispatch(dict(v=99, op='discover'))
        with self.assertRaises(ValueError):
            self.controller.dispatch(dict(v=1, op='attach', device='missing'))

    def test_identity_follows_serial_not_usb_order(self):
        class Device:
            vendor_id, product_id, serial_number, bus, address = 0x1e71, 0x3008, 'ABC', 'hid', '1'
        d = Device()
        key = identity(d)
        d.address = '2'
        self.assertEqual(key, identity(d))
        d.serial_number = 'OTHER'
        self.assertNotEqual(key, identity(d))
