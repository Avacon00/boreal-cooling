"""Media decoding happens only in a bounded subprocess, never on GTK/USB threads."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from .core import atomic_json
from .i18n import _


def directory():
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'boreal/media'


def media_call(op, **args):
    try:
        if op == 'import':
            directory().mkdir(mode=0o700, parents=True, exist_ok=True)
        workspace = tempfile.TemporaryDirectory(prefix='.import-', dir=directory()) if op == 'import' else nullcontext(None)
        with workspace as tmp:
            if tmp is not None:
                args = dict(args, workspace=tmp)
            proc = subprocess.run([sys.executable, '-m', 'boreal.media_worker'],
                input=json.dumps(dict(op=op, **args)), text=True, capture_output=True, timeout=15)
    except subprocess.TimeoutExpired:
        raise ValueError(_('Bildverarbeitung dauerte zu lange; bitte kleineres Medium wählen')) from None
    if proc.returncode:
        raise ValueError(_('Bildverarbeitung wurde wegen eines Fehlers oder Ressourcenlimits beendet'))
    result = json.loads(proc.stdout)
    if not result['ok']:
        raise ValueError(result['error'])
    return result['result']


def records():
    root = directory()
    if not root.exists():
        return []
    result = []
    for path in sorted(root.glob('*.json')):
        try:
            if path.stat().st_size > 8192:
                continue
            result.append(json.loads(path.read_text()))
        except (ValueError, OSError):
            continue
    return result[-100:]


def asset(key):
    if not isinstance(key, str) or len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
        raise ValueError(_('Ungültiges Medium'))
    path = directory() / f'{key}.json'
    if not path.exists():
        raise ValueError(_('Medium nicht mehr in der Bibliothek'))
    record = json.loads(path.read_text())
    if record.get('format') not in ('png', 'gif'):
        raise ValueError(_('Ungültiges Medienformat in der Bibliothek'))
    # Paths come from our directory, never from serialized user-supplied metadata.
    return directory() / f"{key}.{record['format']}", record
