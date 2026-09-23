"""Manage the opt-in desktop autostart entry for the Boreal UI and tray."""
import os
from pathlib import Path
import tempfile


MARKER = "X-Boreal-Managed=true"


def autostart_path():
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config / "autostart/io.boreal.Cooling.desktop"


def executable_path():
    for candidate in (Path("/usr/bin/boreal"), Path.home() / ".local/bin/boreal"):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError("Boreal ist noch nicht installiert")


def _desktop_quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$") + '"'


def set_ui_autostart(enabled, executable=None):
    path = autostart_path()
    if not enabled:
        if not path.exists() and not path.is_symlink():
            return
        if path.is_symlink() or MARKER not in path.read_text()[:4096]:
            raise ValueError("Vorhandener Autostart-Eintrag gehört nicht zu Boreal")
        path.unlink()
        return

    executable = Path(executable) if executable else executable_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Boreal\n"
        "Comment=Kraken-Steuerung und Tray starten\n"
        f"Exec={_desktop_quote(executable)} --hardware\n"
        "Icon=io.boreal.Cooling\n"
        "Terminal=false\n"
        "Categories=System;Settings;\n"
        "X-GNOME-Autostart-enabled=true\n"
        f"{MARKER}\n"
    )
    fd, temporary = tempfile.mkstemp(prefix=".boreal-autostart-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
