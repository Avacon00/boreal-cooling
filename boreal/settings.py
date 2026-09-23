"""Versioned atomic settings. Failed writes never become restore targets."""
import copy
import json
import shutil
import threading
from pathlib import Path
from .core import config_dir, atomic_json, profile, PRESETS, TEST_PRESETS
from .i18n import _


class Settings:
    def __init__(self, directory=None):
        self.directory = directory or config_dir()
        self.path = self.directory / "settings-v2.json"
        self.lock = threading.RLock()
        self.value = {"schema": 2, "devices": {}, "theme": "system", "language": "system"}
        if self.path.exists():
            if self.path.stat().st_size > 1024 * 1024:
                raise ValueError(_("Konfiguration ist zu groß"))
            value = json.loads(self.path.read_text())
            if value.get("schema") != 2 or not isinstance(value.get("devices"), dict):
                raise ValueError(_("Unbekannte Konfiguration; Sicherung vor Migration erforderlich"))
            for device in value["devices"].values():
                if "profile" in device:
                    profile(device["profile"])
            interval=value.get('refresh_interval_ms',1000)
            if type(interval) is not int or interval not in (500,1000,2000,3000,5000):
                raise ValueError(_('Ungültiges Messintervall in Konfiguration'))
            if value.get("language", "system") not in ("system", "de", "en"):
                raise ValueError(_("Unbekannte Sprache in Konfiguration"))
            self.value.update(value)

    def read(self):
        with self.lock:
            return copy.deepcopy(self.value)

    def update_device(self, key, **changes):
        with self.lock:
            value = self.read()
            value["devices"].setdefault(key, {}).update(changes)
            atomic_json(self.path, value)
            self.value = value

    def refresh_interval(self, value):
        if type(value) is not int or value not in (500,1000,2000,3000,5000):
            raise ValueError(_('Aktualisierung: 500, 1000, 2000, 3000 oder 5000 ms erwartet'))
        with self.lock:
            data=self.read(); data['refresh_interval_ms']=value
            atomic_json(self.path,data); self.value=data

    def theme(self, name):
        if name not in ("system", "light", "dark"):
            raise ValueError(_("Unbekanntes Erscheinungsbild"))
        with self.lock:
            value = self.read()
            value["theme"] = name
            atomic_json(self.path, value)
            self.value = value

    def language(self, name):
        if name not in ("system", "de", "en"):
            raise ValueError(_("Unbekannte Sprache"))
        with self.lock:
            value = self.read()
            value["language"] = name
            atomic_json(self.path, value)
            self.value = value


def restore_allowed(saved, device):
    return (saved.get("enabled") is True and not saved.get("latched", False)
            and device.get("identity") == "Seriennummer"
            and device.get("pid") == "3012"
            and device.get("firmware") == saved.get("firmware") == "1.2.0")


def migrate_profiles(directory=None):
    directory = directory or config_dir()
    old, new = directory / "profiles.json", directory / "profiles-v2.json"
    if new.exists():
        value = json.loads(new.read_text())
        if value.get("schema") != 2 or not isinstance(value.get("profiles"), dict):
            raise ValueError(_("Ungültige Profilbibliothek"))
        return new
    if old.exists():
        from .core import Profiles
        # Validate before creating the migration output or touching the original.
        values = {k: v for k, v in Profiles(old).read().items() if k not in PRESETS}
        backup = directory / "profiles.v1.backup.json"
        if not backup.exists():
            shutil.copy2(old, backup)
    else:
        values = {}
    atomic_json(new, {"schema": 2, "profiles": values})
    return new


class ProfileLibrary:
    def __init__(self, directory=None):
        self.path = migrate_profiles(directory)
        self.lock = threading.RLock()

    def read(self):
        from .core import Profiles
        with self.lock:
            if self.path.stat().st_size > 262144:
                raise ValueError(_("Profilbibliothek ist zu groß"))
            data = json.loads(self.path.read_text())
            if data.get("schema") != 2 or not isinstance(data.get("profiles"), dict) or len(data['profiles']) > 100:
                raise ValueError(_("Ungültige Profilbibliothek"))
            return {**PRESETS, **TEST_PRESETS, **{Profiles.name(k): profile(v) for k, v in data["profiles"].items()}}

    def save(self, name, value):
        from .core import Profiles
        name = Profiles.name(name)
        if name in PRESETS or name in TEST_PRESETS:
            raise ValueError(_("Voreinstellung bitte unter einem eigenen Namen speichern"))
        with self.lock:
            self.read()  # Validate before preserving the stored user library.
            data = json.loads(self.path.read_text())['profiles']
            if len(data) >= 100 and name not in data:
                raise ValueError(_("Maximal 100 eigene Profile"))
            data[name] = profile(value)
            atomic_json(self.path, {"schema": 2, "profiles": data})

    def delete(self, name):
        with self.lock:
            self.read()  # Validate before preserving the stored user library.
            data = json.loads(self.path.read_text())['profiles']
            if name not in data:
                raise ValueError(_("Nur eigene Profile können gelöscht werden"))
            del data[name]
            atomic_json(self.path, {"schema": 2, "profiles": data})

    def rename(self, old, new):
        from .core import Profiles
        new = Profiles.name(new)
        with self.lock:
            self.read()  # Validate before preserving the stored user library.
            data = json.loads(self.path.read_text())['profiles']
            if old not in data or new in self.read():
                raise ValueError(_("Eigener Quellname und unbenutzter Zielname erforderlich"))
            data[new] = data.pop(old)
            atomic_json(self.path, {"schema": 2, "profiles": data})
