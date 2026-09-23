import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from boreal.hardware import check_device_access


class AccessTests(unittest.TestCase):
    def test_permission_error_identifies_usb_and_hid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            usb = root / 'usb/device'
            hid = root / 'hid'
            usb.mkdir(parents=True)
            hid.mkdir()
            for name, value in {'idVendor': '1e71', 'idProduct': '3012', 'busnum': '1', 'devnum': '8'}.items():
                (usb / name).write_text(value)
            (usb / 'interface/hidraw11').mkdir(parents=True)
            (hid / 'hidraw11').symlink_to(usb / 'interface/hidraw11')
            with patch('boreal.hardware.os.access', return_value=False):
                with self.assertRaises(PermissionError) as error:
                    check_device_access(root / 'usb', hid, root / 'dev')
                self.assertIn('bus/usb/001/008', str(error.exception))
                self.assertIn('hidraw11', str(error.exception))
            with patch('boreal.hardware.os.access', return_value=True):
                check_device_access(root / 'usb', hid, root / 'dev')

    def test_other_vendors_are_not_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            usb = root / 'device'
            usb.mkdir()
            (usb / 'idVendor').write_text('1234')
            (usb / 'idProduct').write_text('3012')
            with patch('boreal.hardware.os.access') as access:
                check_device_access(root, root / 'hid', root / 'dev')
                access.assert_not_called()
