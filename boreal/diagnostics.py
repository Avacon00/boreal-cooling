import atexit
import faulthandler
import json
import logging
from logging.handlers import RotatingFileHandler
import platform
import re
import sys
import threading
import zipfile
from .core import state_dir
from . import __version__


def configure(component):
    root = state_dir()
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    handler = RotatingFileHandler(root / f"{component}.log", maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()], force=True)
    crash = open(root / f"{component}-fault.log", "a")
    faulthandler.enable(crash)
    def exception(kind, value, tb):
        logging.getLogger(component).critical("Unbehandelte Ausnahme", exc_info=(kind, value, tb))
    sys.excepthook = exception
    threading.excepthook = lambda a: exception(a.exc_type, a.exc_value, a.exc_traceback)
    logging.info("Start %s version=%s python=%s", component, __version__, platform.python_version())
    atexit.register(lambda: logging.info("Prozessende %s", component))
    return crash


def sanitize(value):
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()
                if k not in {"id", "serial", "serial_number", "path", "preview", "device", "media_id"}}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"/(?:dev|home|tmp|run|media|mnt|opt|usr|var)/[^\s\"']+", "<Pfad entfernt>", value)
        value = re.sub(r"\b[0-9a-fA-F]{24,64}\b", "<Kennung entfernt>", value)
        value = re.sub(
            r'''(?i)(\bserial(?:_number)?\b\s*[:=]\s*)(?:['"]?)[^\s,}\]'"]+''',
            r"\1<Kennung entfernt>", value)
    return value


def log_excerpt(path, maximum=128 * 1024, lines=200):
    """Return a bounded, redacted tail suitable for deliberate support export."""
    try:
        with path.open('rb') as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - maximum))
            raw = stream.read(maximum)
    except OSError:
        return None
    text = raw.decode('utf-8', errors='replace')
    if path.stat().st_size > maximum:
        text = text.split('\n', 1)[-1]
    return '\n'.join(str(sanitize(line))[:1000] for line in text.splitlines()[-lines:]) + '\n'


def export(snapshot):
    """Export allowlisted state and bounded, redacted component-log tails."""
    root = state_dir()
    destination = root / "boreal-diagnose.zip"
    data = {"version": __version__, "python": platform.python_version(),
            "kernel": platform.release(), "snapshot": sanitize(snapshot)}
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("status.json", json.dumps(data, ensure_ascii=False, indent=2))
        included = []
        for name in ('ui.log', 'hardware.log', 'ui-demo.log', 'demo.log'):
            excerpt = log_excerpt(root / name)
            if excerpt:
                archive.writestr('logs/' + name, excerpt)
                included.append(name)
        archive.writestr(
            "README.txt",
            "Persönliche Pfade, Seriennummern und Gerätekennungen werden automatisch entfernt.\n"
            "Enthaltene Logauszüge sind auf die letzten 200 Zeilen je Komponente begrenzt: "
            + (", ".join(included) if included else "keine")
            + "\nBitte den Bericht vor einer Weitergabe trotzdem prüfen.\n")
    return str(destination)
