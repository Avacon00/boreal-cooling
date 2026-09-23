import hashlib
import json
import resource
import os
import stat
import sys
from contextlib import nullcontext
from pathlib import Path
from PIL import Image
from .core import atomic_json
from .library import directory
from .media import prepare_media, stats_image


def copy_source(source, destination):
    """Validate the opened object, then enforce the limit even if it grows."""
    limit = 10 * 1024**2
    fd = os.open(source, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('Bitte eine reguläre Bilddatei bis 10 MiB auswählen')
        with open(destination, 'xb') as output:
            remaining = limit
            while True:
                block = stream.read(min(65536, remaining + 1))
                if not block:
                    break
                if len(block) > remaining:
                    raise ValueError('Quelldatei ist während des Imports zu groß geworden')
                output.write(block)
                remaining -= len(block)


def main():
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (12, 12))
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024**2, 128 * 1024**2))
    try:
        req = json.loads(sys.stdin.read(65537))
        if req['op'] == 'stats':
            result = stats_image(req['size'], req['status'], req['host'], Path(req['destination']), req.get('options'))
        elif req['op'] == 'import':
            root = directory()
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            if len(list(root.glob('*.json'))) >= 100:
                raise ValueError('Medienbibliothek voll (maximal 100 Medien)')
            fmt = 'gif' if req['mode'] == 'gif' else 'png'
            # The parent owns this workspace and removes it even after SIGKILL.
            with nullcontext(req['workspace']) as tmp:
                out = Path(tmp) / f'asset.{fmt}'
                source = Path(req['path'])
                preserved = Path(tmp) / 'source'
                copy_source(source, preserved)
                prepare_media(preserved, req['mode'], req['size'], out, req.get('options'))
                key = hashlib.sha256(out.read_bytes()).hexdigest()
                target = root / f'{key}.{fmt}'
                out.replace(target)
                preserved.replace(root / f'{key}.source')
            with Image.open(target) as im:
                im.seek(0)
                im.convert('RGB').save(root / f'{key}-preview.png')
                count = getattr(im, 'n_frames', 1)
            record = dict(id=key, name=Path(req['path']).name[:100], format=fmt,
                          width=req['size'], height=req['size'], frames=count,
                          bytes=target.stat().st_size, preview=str(root / f'{key}-preview.png'),
                          path=str(target), source=str(root / f'{key}.source'), options=req.get('options', {}))
            atomic_json(root / f'{key}.json', record)
            result = record
        else:
            raise ValueError('Unbekannte Medienaktion')
        print(json.dumps(dict(ok=True, result=result), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps(dict(ok=False, error=str(exc)), ensure_ascii=False))


if __name__ == '__main__':
    main()
