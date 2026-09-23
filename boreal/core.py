"""Pure policy, validation and atomic configuration; no hardware/UI imports."""
import json
import math
import os
import tempfile
from pathlib import Path
from .i18n import _

PRESETS = {
    "Leise": {"pump": [[20, 60], [35, 70], [42, 90], [50, 100]],
              "fan": [[20, 30], [35, 45], [42, 75], [50, 100]]},
    "Ausgewogen": {"pump": [[20, 70], [32, 75], [40, 95], [50, 100]],
                    "fan": [[20, 35], [32, 50], [40, 80], [50, 100]]},
    "Leistung": {"pump": [[20, 85], [32, 90], [40, 100], [50, 100]],
                 "fan": [[20, 50], [32, 65], [40, 95], [50, 100]]},
}


TEST_PRESETS = {
    name + ' – Test': {'pump': list(map(list, zip((20,30,35,40,45,50), pump))),
                      'fan': list(map(list, zip((20,30,35,40,45,50), fan)))}
    for name,pump,fan in (
        ('Leise',(70,70,70,80,95,100),(30,30,40,60,85,100)),
        ('Ausgewogen',(80,80,80,90,100,100),(35,40,55,75,95,100)),
        ('Leistung',(100,100,100,100,100,100),(50,60,75,90,100,100)))
}


def number(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(_("Zahl zwischen {low} und {high} erwartet").format(low=low,high=high))
    return value


def curve(points, channel):
    if channel not in ("pump", "fan"):
        raise ValueError(_("Unbekannter Kühlkanal"))
    if not isinstance(points, list) or not 2 <= len(points) <= 12:
        raise ValueError(_("Eine Kurve benötigt 2–12 Punkte"))
    result = []
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(_("Kurvenpunkt muss Temperatur und Prozent enthalten"))
        temp = number(point[0], 20, 50)
        duty = number(point[1], 60 if channel == "pump" else 30, 100)
        if int(temp) != temp or int(duty) != duty:
            raise ValueError(_("Bitte ganzzahlige Kurvenpunkte verwenden"))
        if result and (temp <= result[-1][0] or duty < result[-1][1]):
            raise ValueError(_("Temperaturen müssen steigen; Leistung darf nicht fallen"))
        result.append([int(temp), int(duty)])
    if result[0][0] != 20 or result[-1] != [50, 100]:
        raise ValueError(_("Kurve muss bei 20°C beginnen und bei 50°C / 100% enden"))
    return result


def profile(value):
    if not isinstance(value, dict) or set(value) != {"pump", "fan"}:
        raise ValueError(_("Profil benötigt pump und fan"))
    return {c: curve(value[c], c) for c in ("pump", "fan")}


def interpolate(points, temp):
    for a, b in zip(points, points[1:]):
        if temp <= b[0]:
            return a[1] + max(0, temp - a[0]) / (b[0] - a[0]) * (b[1] - a[1])
    return points[-1][1]


def config_dir():
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "boreal"


def state_dir():
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "boreal"


def atomic_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Profiles:
    def __init__(self, path=None):
        self.path = path or config_dir() / "profiles.json"

    def read(self):
        values = {}
        if self.path.exists():
            if self.path.stat().st_size > 262144:
                raise ValueError(_("Profildatei ist zu groß"))
            values = json.loads(self.path.read_text())
            if not isinstance(values, dict) or len(values) > 100:
                raise ValueError(_("Ungültige Profilsammlung"))
            values = {self.name(k): profile(v) for k, v in values.items()}
        return {**PRESETS, **values}

    @staticmethod
    def name(name):
        if not isinstance(name, str) or not name.strip() or len(name) > 64:
            raise ValueError(_("Profilname muss 1–64 Zeichen enthalten"))
        return name.strip()

    def save(self, name, value):
        name = self.name(name)
        if name in PRESETS:
            raise ValueError(_("Für eigene Profile bitte einen neuen Namen verwenden"))
        values = {k: v for k, v in self.read().items() if k not in PRESETS}
        if len(values) >= 100 and name not in values:
            raise ValueError(_("Maximal 100 eigene Profile"))
        values[name] = profile(value)
        atomic_json(self.path, values)

    def delete(self, name):
        if name in PRESETS:
            raise ValueError(_("Voreinstellungen können nicht gelöscht werden"))
        values = {k: v for k, v in self.read().items() if k not in PRESETS}
        if name not in values:
            raise ValueError(_("Profil nicht gefunden"))
        del values[name]
        atomic_json(self.path, values)
