"""Elite V2 HUE2 direct frames; independently encoded from published protocol.
Reference: OpenKraken PROTOCOL.md and OpenRGB NZXTHue2Controller.
Only PID 3012 / firmware 1.2.0. No hardware animation/save commands.
"""
from .i18n import _
LED_COUNTS = {0x1e: 24, 0x17: 8, 0x18: 8, 0x1d: 24}


def parse_accessories(report):
    if len(report) < 27 or bytes(report[:2]) != b"\x21\x03" or report[14] != 2:
        raise ValueError(_("Unbekannte RGB-Zubehörantwort"))
    zones = {}
    for index, name in enumerate(("ring", "fans")):
        ids = [x for x in report[15+6*index:21+6*index] if x]
        if not ids or any(x not in LED_COUNTS for x in ids):
            continue
        if name == "ring" and ids != [0x1e]:
            continue
        count = sum(LED_COUNTS[x] for x in ids)
        if 0 < count <= 40:
            zones[name] = {"mask": 1 << index, "leds": count}
    return zones


def frames(mask, count, color, brightness=100):
    if mask not in (1, 2) or not 1 <= count <= 40:
        raise ValueError(_("Ungültige RGB-Zone"))
    if type(brightness) not in (int, float) or not 0 <= brightness <= 100:
        raise ValueError(_("Helligkeit muss 0–100 sein"))
    if len(color) != 3 or any(type(v) != int or not 0 <= v <= 255 for v in color):
        raise ValueError(_("RGB erwartet drei Werte von 0–255"))
    r, g, b = [round(v * brightness / 100) for v in color]
    data = [g, r, b] * count
    result = []
    for part, offset in enumerate(range(0, len(data), 60)):
        result.append(bytes(([0x22, 0x10 + part, mask, 0] + data[offset:offset+60])).ljust(64, b'\0'))
    commit = bytearray(64)
    for offset, value in {0: 0x22, 1: 0xa0, 2: mask, 4: 1, 7: 0x28, 10: 0x80, 12: 0x32, 15: 1}.items():
        commit[offset] = value
    return result + [bytes(commit)]


class EliteRGB:
    def __init__(self, device):
        self.device = device
        self.zones = {}

    def probe(self):
        self.device.device.clear_enqueued_reports()
        self.device._write([0x20, 0x03])
        for attempt in range(12):
            report = self.device._read()
            if bytes(report[:2]) == b'\x21\x03':
                self.zones = parse_accessories(report)
                return self.zones
        raise RuntimeError(_("RGB-Zubehörerkennung ohne gültige Antwort"))

    def set(self, zone, color, brightness):
        if zone not in self.zones:
            raise ValueError(_("RGB-Zubehör nicht erkannt"))
        data = self.zones[zone]
        for frame in frames(data['mask'], data['leds'], color, brightness):
            self.device._write(list(frame))
