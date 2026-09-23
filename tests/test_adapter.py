import importlib.util
import unittest
from unittest.mock import Mock, patch


@unittest.skipUnless(importlib.util.find_spec('liquidctl'), 'liquidctl not installed')
class AdapterTests(unittest.TestCase):
    def test_bulk_guard_refuses_kernel_owned_interface(self):
        from boreal.hardware import guarded_bulk_open
        from liquidctl.driver.usb import PyUsbDevice
        device = Mock()
        device._select_interface.return_value = 1
        device.usbdev.is_kernel_driver_active.return_value = True
        with guarded_bulk_open(), self.assertRaisesRegex(RuntimeError, 'Kernel'):
            PyUsbDevice.open(device)
        device.usbdev.detach_kernel_driver.assert_not_called()
        device.usbdev.set_configuration.assert_not_called()

    def test_bulk_guard_refuses_unconfigured_device(self):
        from boreal.hardware import guarded_bulk_open
        from liquidctl.driver.usb import PyUsbDevice
        device = Mock()
        device.usbdev.get_active_configuration.side_effect = OSError('Unconfigured')
        with guarded_bulk_open(), self.assertRaises(OSError):
            PyUsbDevice.open(device)
        device.usbdev.set_configuration.assert_not_called()

    def test_contract_against_pinned_driver(self):
        import importlib.metadata
        if importlib.metadata.version('liquidctl') != '1.16.0':
            self.skipTest('Pinned 1.16.0 required for contract check')
        from boreal.hardware import MODELS
        from liquidctl.driver.kraken3 import KrakenX3, KrakenZ3
        for cls in (KrakenX3, KrakenZ3):
            for vendor, pid, name, options in cls._MATCHES:
                if pid not in MODELS:
                    continue
                self.assertEqual(MODELS[pid][1], cls.__name__)
                if cls is KrakenZ3:
                    self.assertEqual(options['lcd_resolution'], (MODELS[pid][2],) * 2)
                if pid in (0x300c, 0x300e, 0x3012, 0x3014):
                    self.assertFalse(options['color_channels'])

    def test_fallback_attempts_fan_even_if_pump_fails(self):
        from boreal.hardware import LiquidHardware
        hw = LiquidHardware.__new__(LiquidHardware)
        dev = Mock()
        dev.set_speed_profile.side_effect = [OSError('pump failed'), None]
        hw.devices = {'key': dev}
        hw.info = lambda key: {'channels': ['pump', 'fan']}
        with self.assertRaises(RuntimeError):
            hw.fallback('key')
        self.assertEqual(dev.set_speed_profile.call_count, 2)
        self.assertEqual(dev.set_speed_profile.call_args_list[-1].args[0], 'fan')

    def test_elite_status_ignores_non_status_packet(self):
        from boreal.hardware import LiquidHardware
        hw = LiquidHardware.__new__(LiquidHardware)
        dev = Mock(product_id=0x3012)
        good = [0x75, 0x01] + [0] * 62
        dev._read.side_effect = [[0xff, 1] + [0] * 62, good]
        def status():
            packet = dev._read()
            return [('Pump speed', packet[17] + 256 * packet[18], 'rpm')]
        dev.get_status.side_effect = status
        hw.devices = {'key': dev}
        self.assertEqual(hw.status('key')['Pump speed']['value'], 0)
        self.assertEqual(dev._read.call_count, 2)

    def test_elite_status_missing_valid_packet_fails_bounded(self):
        from boreal.hardware import LiquidHardware
        hw = LiquidHardware.__new__(LiquidHardware)
        dev = Mock(product_id=0x3012)
        dev._read.return_value = [0xff, 1] + [0] * 62
        dev.get_status.side_effect = lambda: dev._read()
        hw.devices = {'key': dev}
        with self.assertRaisesRegex(RuntimeError, '75:01'):
            hw.status('key')
        self.assertEqual(dev._read.call_count, 12)
