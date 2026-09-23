"""Only this module knows liquidctl. No raw USB packets or kernel overrides."""
import hashlib
import importlib.metadata
import math
import logging
import os
from pathlib import Path
import time
from contextlib import contextmanager
from unittest.mock import patch
from .core import interpolate, PRESETS
from .i18n import _

MODELS = {
    0x170e: ("Kraken X42/X52/X62/X72", "Kraken2", 0),
    0x2007: ("Kraken X53/X63/X73", "KrakenX3", 0),
    0x2014: ("Kraken X53/X63/X73", "KrakenX3", 0),
    0x3008: ("Kraken Z53/Z63/Z73", "KrakenZ3", 320),
    0x300c: ("Kraken Elite 2023", "KrakenZ3", 640),
    0x300e: ("Kraken 2023", "KrakenZ3", 240),
    0x3012: ("Kraken Elite RGB 2024", "KrakenZ3", 640),
    0x3014: ("Kraken Plus 2024", "KrakenZ3", 240),
}


def check_device_access(usb_root=Path("/sys/bus/usb/devices"),
                        hid_root=Path("/sys/class/hidraw"), dev_root=Path("/dev")):
    """Check permissions without opening devices or changing their state."""
    denied = []
    for usb in usb_root.iterdir():
        try:
            vendor = (usb / "idVendor").read_text().strip()
            product = int((usb / "idProduct").read_text().strip(), 16)
            if vendor != "1e71" or product not in MODELS:
                continue
            bus = int((usb / "busnum").read_text())
            address = int((usb / "devnum").read_text())
        except (OSError, ValueError):
            continue
        nodes = [dev_root / "bus/usb" / f"{bus:03}" / f"{address:03}"]
        nodes.extend(dev_root / hid.name for hid in hid_root.glob("hidraw*")
                     if hid.resolve().is_relative_to(usb.resolve()))
        for node in nodes:
            if not os.access(node, os.R_OK | os.W_OK):
                denied.append(str(node))
    if denied:
        raise PermissionError(
            _("Kein Lese-/Schreibzugriff auf Kraken: {devices}. Bitte die mitgelieferten udev-Regeln wie im README einrichten; Boreal anschließend als normalen Benutzer starten.").format(devices=", ".join(denied)))


@contextmanager
def guarded_bulk_open():
    # liquidctl opens LCD bulk interfaces during discovery. Refuse its optional
    # kernel detach/configuration path: the app does not own those decisions.
    from liquidctl.driver.usb import PyUsbDevice
    original = PyUsbDevice.open

    def checked(device, *args, **kwargs):
        cfg = device.usbdev.get_active_configuration()
        interface = device._select_interface(cfg)
        if device.usbdev.is_kernel_driver_active(interface):
            raise RuntimeError(_("LCD-USB-Interface durch Kernel belegt; kein automatisches Ablösen"))
        return original(device, *args, **kwargs)

    with patch.object(PyUsbDevice, "open", checked):
        yield


def identity(device):
    serial = device.serial_number
    token = f"{device.vendor_id:04x}:{device.product_id:04x}:" + (
        f"serial:{serial}" if serial else f"session:{device.bus}:{device.address}")
    return hashlib.sha256(token.encode()).hexdigest()[:24]


class LiquidHardware:
    def __init__(self):
        self.version = importlib.metadata.version("liquidctl")
        # Limit the adapter contract to the documented release family.
        from packaging.version import Version
        if not Version("1.16.0") <= Version(self.version) < Version("1.17"):
            raise RuntimeError(_("liquidctl 1.16.x erforderlich (installiert: {version})").format(version=self.version))
        self.devices = {}
        self.opened = set()
        self.rgb = {}
        self.rgb_errors = {}

    def discover(self, target=None):
        if self.opened:
            raise ValueError(_("Vor erneutem Suchen alle Geräte trennen"))
        check_device_access()
        from liquidctl import find_liquidctl_devices
        self.devices.clear()
        result = []
        with guarded_bulk_open():
            filters = {'vendor': 0x1e71}
            if target:
                filters['product'] = int(target['pid'], 16)
                if target.get('serial'): filters['serial'] = target['serial']
                else: filters['address'] = target['address']
            discovered = list(find_liquidctl_devices(**filters))
        for dev in discovered:
            if dev.product_id not in MODELS:
                continue
            key = identity(dev)
            if key in self.devices:
                raise ValueError(_("Mehrdeutige Geräteidentität; keine automatische Auswahl"))
            expected = MODELS[dev.product_id][1]
            if type(dev).__name__ != expected:
                continue
            self.devices[key] = dev
            result.append(self.info(key))
        return result

    def info(self, key):
        dev = self.devices[key]
        pid = dev.product_id
        x2 = pid == 0x170e
        channels = ["pump", "fan"] if x2 else list(getattr(dev, "_speed_channels", {}))
        colors = ["ring", "logo", "sync"] if x2 else list(getattr(dev, "_color_channels", {}))
        if key in self.rgb:
            colors = list(self.rgb[key].zones)
        fw = getattr(dev, "_firmware_version", None) if x2 else getattr(dev, "_fw", None)
        lcd = MODELS[pid][2]
        return {"id": key, "name": MODELS[pid][0], "pid": f"{pid:04x}",
                "identity": "Seriennummer" if dev.serial_number else "Nur diese Sitzung",
                "channels": channels, "colors": colors, "lcd": lcd,
                "gif": bool(lcd and fw and not (pid in (0x300c, 0x300e) and fw[0] >= 2)),
                "firmware": ".".join(map(str, fw)) if fw else "unbekannt",
                "blocked": _("Upstream markiert Elite 2023 als fehlerhaft") if pid == 0x300c else "",
                "warning": _("LCD-Uploads können firmwarebedingt fehlschlagen") if pid == 0x3014 else "",
                "driver_version": self.version,
                "brightness": getattr(dev, 'brightness', None),
                "orientation": getattr(dev, 'orientation', 0) * 90 if lcd else None,
                "rgb_reason": self.rgb_errors.get(key, _('Nach Verbindung prüfen') if pid == 0x3012 else ''),
                "rgb_zones": self.rgb[key].zones if key in self.rgb else {},
                "tested": pid == 0x3012 and fw == (1, 2, 0)}

    def attach(self, key):
        dev = self.devices[key]
        if self.info(key)["blocked"]:
            raise ValueError(self.info(key)["blocked"])
        if key not in self.opened:
            dev.connect()
            bulk = getattr(dev, 'bulk_device', None)
            if bulk:
                with guarded_bulk_open(): bulk.open()
            self.opened.add(key)
        dev.initialize()
        if dev.product_id == 0x170e:
            fw = getattr(dev, "_firmware_version", None)
            # Kraken2 exposes firmware_version as a property in liquidctl.
            fw = getattr(dev, "firmware_version", fw)
            if not fw or int(fw[0]) < 4:
                raise ValueError(_("X2 benötigt bestätigte Firmware >=4 für native Kurven"))
        if dev.product_id == 0x3012:
            if getattr(dev, '_fw', None) == (1, 2, 0):
                from .rgb import EliteRGB
                adapter = EliteRGB(dev)
                try:
                    adapter.probe()
                    self.rgb[key] = adapter
                    self.rgb_errors[key] = '' if adapter.zones else _('Zubehör nicht eindeutig erkannt')
                except Exception as exc:
                    self.rgb_errors[key] = _('Zubehörerkennung fehlgeschlagen: {error}').format(error=exc)
            else:
                self.rgb_errors[key] = _('RGB nur für geprüfte Firmware 1.2.0 freigegeben')
        return self.info(key)

    def display_info(self, key):
        dev = self.devices[key]
        if not MODELS[dev.product_id][2]:
            raise ValueError(_('Kein LCD'))
        dev.device.clear_enqueued_reports()
        dev._write([0x30, 0x01])
        for attempt in range(12):
            report = dev._read()
            if len(report) >= 27 and bytes(report[:2]) == b'\x31\x01':
                dev.brightness, dev.orientation = report[24], report[26]
                return dict(brightness=dev.brightness, orientation=dev.orientation * 90)
        raise RuntimeError(_('LCD-Einstellungen konnten nicht bestätigt werden'))

    def status(self, key):
        dev = self.devices[key]
        def collect():
            return {str(k): {"value": v, "unit": str(u)}
                    for k, v, u in dev.get_status()}
        if dev.product_id != 0x3012:
            return collect()
        # On Elite V2 FW 1.2.0 an ff:01 report can arrive after a curve
        # write. liquidctl 1.16 reads it as telemetry without checking its
        # header. Accept only the observed 75:01 status response; never
        # suppress an actual zero-RPM status packet or issue write retries.
        original_read = dev._read
        def read_status():
            for attempt in range(12):
                data = original_read()
                if len(data) >= 26 and bytes(data[:2]) == b"\x75\x01":
                    return data
                logging.getLogger(__name__).warning(
                    "Nicht-Sensorantwort bei Elite-V2-Status verworfen: %s", bytes(data[:2]).hex())
            raise RuntimeError(_("Keine gültige Elite-V2-Sensorantwort (75:01) empfangen"))
        with patch.object(dev, "_read", read_status):
            return collect()

    def curves(self, key, value):
        for channel in self.info(key)["channels"]:
            self.devices[key].set_speed_profile(channel, value[channel])

    def fallback(self, key):
        errors = []
        for channel in self.info(key)["channels"]:
            try:
                self.devices[key].set_speed_profile(channel, [(20, 100), (50, 100)])
            except Exception as exc:
                errors.append(f"{channel}: {exc}")
        if errors:
            raise RuntimeError("; ".join(errors))

    def screen(self, key, mode, value=None):
        self.devices[key].set_screen("lcd", mode, value)

    def color(self, key, channel, mode, colors, brightness=100):
        if self.devices[key].product_id == 0x3012:
            if key not in self.rgb or mode not in ('fixed', 'off'):
                raise ValueError(_('RGB-Modus für diese Firmware nicht freigegeben'))
            self.rgb[key].set(channel, [0,0,0] if mode == 'off' else colors[0], brightness)
        else:
            self.devices[key].set_color(channel, mode, colors)

    def detach(self, key):
        if key in self.opened:
            try:
                self.devices[key].disconnect()
                bulk = getattr(self.devices[key], 'bulk_device', None)
                if bulk: bulk.close()
            finally:
                self.opened.discard(key)

    def close(self):
        for key in list(self.opened):
            self.detach(key)


class DemoHardware:
    version = "Demo"

    def __init__(self):
        self.opened = set()
        self.profiles = {}
        self.commands = []

    def info(self, key):
        return {"id": "demo-z3", "name": _("Kraken Z63 · simuliert"), "pid": "3008",
                "identity": "Demo", "channels": ["pump", "fan"], "colors": ["external"],
                "lcd": 320, "gif": True, "firmware": "Demo 1.0", "blocked": "",
                "warning": _("Keine Hardwarezugriffe"), "driver_version": "Demo", "tested": True,
                "brightness": getattr(self, 'brightness', 70), "orientation": getattr(self, 'orientation', 0),
                "rgb_reason": "", "rgb_zones": {"external": {"leds":24}}}

    def discover(self, target=None):
        return [self.info("demo-z3")]

    def attach(self, key):
        if key != "demo-z3":
            raise ValueError(_("Unbekanntes Demogerät"))
        self.opened.add(key)
        return self.info(key)

    def status(self, key):
        t = 32 + math.sin(time.monotonic() / 12) * 2
        p = self.profiles.get(key, PRESETS["Ausgewogen"])
        pump, fan = (interpolate(p[c], t) for c in ("pump", "fan"))
        return {"Liquid temperature": {"value": round(t, 1), "unit": "°C"},
                "Pump speed": {"value": round(pump * 28), "unit": "rpm"},
                "Fan speed": {"value": round(fan * 18), "unit": "rpm"},
                "Pump duty": {"value": round(pump), "unit": "%"},
                "Fan duty": {"value": round(fan), "unit": "%"}}

    def curves(self, key, value):
        self.profiles[key] = value
        self.commands.append(("curves", key, value))

    def fallback(self, key):
        self.curves(key, {c: [[20, 100], [50, 100]] for c in ("pump", "fan")})

    def screen(self, key, mode, value=None):
        self.commands.append(("screen", key, mode))
        if mode in ('brightness','orientation'): setattr(self, mode, value)

    def display_info(self, key):
        return dict(brightness=getattr(self,'brightness',70), orientation=getattr(self,'orientation',0))

    def color(self, key, channel, mode, colors, brightness=100):
        self.commands.append(("color", key, channel, mode, colors))

    def detach(self, key):
        self.opened.discard(key)

    def close(self):
        self.opened.clear()


def catalog(demo=False):
    """Read-only sysfs discovery; does not construct USB drivers or steal handles."""
    if demo: return [dict(DemoHardware().info('demo-z3'), selector=None)]
    result = []
    for usb in Path('/sys/bus/usb/devices').iterdir():
        try:
            if (usb/'idVendor').read_text().strip() != '1e71': continue
            pid = int((usb/'idProduct').read_text().strip(),16)
            if pid not in MODELS: continue
            serial = (usb/'serial').read_text().strip() if (usb/'serial').exists() else None
            hids = [h for h in Path('/sys/class/hidraw').glob('*') if h.resolve().is_relative_to(usb.resolve())]
            if not hids: continue
            address = '/dev/' + hids[0].name
            from types import SimpleNamespace
            key = identity(SimpleNamespace(vendor_id=0x1e71,product_id=pid,serial_number=serial,bus='hid',address=address))
            name, driver, lcd = MODELS[pid]
            result.append(dict(id=key,name=name,pid=f'{pid:04x}',lcd=lcd,channels=['pump'] if driver=='KrakenX3' else ['pump','fan'],
                               colors=[],gif=False,firmware='unbekannt',blocked=_('Elite 2023 ist nicht freigegeben') if pid==0x300c else '',
                               identity='Seriennummer' if serial else 'Nur diese Sitzung',warning='',driver_version='1.16.0',
                               selector={'pid':f'{pid:04x}','serial':serial,'address':address}))
        except (OSError, ValueError): continue
    return result
