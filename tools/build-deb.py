#!/usr/bin/env python3
"""Build offline from an environment containing liquidctl 1.16.0."""
import argparse
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import tempfile

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
source=Path(__file__).resolve().parents[1]
dist=importlib.metadata.distribution('liquidctl')
if dist.version != '1.16.0': raise SystemExit('Build requires liquidctl 1.16.0')
args.output.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='boreal-deb-') as tmp:
    root=Path(tmp)
    def write(path,text,mode=0o644):
        dest=root/path;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(text) if isinstance(text,bytes) else dest.write_text(text)
        dest.chmod(mode)
    app=root/'usr/lib/boreal';app.mkdir(parents=True)
    shutil.copytree(source/'boreal',app/'boreal',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for f in dist.files:
        if f.parts[0]=='liquidctl' or f.parts[0].endswith('.dist-info'):
            if '__pycache__' in f.parts or str(f).endswith('.pyc'):continue
            dest=app/f;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(dist.locate_file(f),dest)
    write('usr/bin/boreal',"#!/usr/bin/python3\nimport os,sys\nsys.path.insert(0,'/usr/lib/boreal')\nos.environ['PYTHONPATH']='/usr/lib/boreal'\nfrom boreal.__main__ import main\nmain()\n",0o755)
    write('usr/share/icons/hicolor/scalable/apps/io.boreal.Cooling.svg',(source/'boreal/assets/io.boreal.Cooling.svg').read_text())
    write('usr/share/locale/en/LC_MESSAGES/boreal.mo',(source/'boreal/locale/en/LC_MESSAGES/boreal.mo').read_bytes())
    hardware_unit=(source/'integration/boreal.service').read_text().replace('%h/.local/bin/boreal','/usr/bin/boreal').replace('TimeoutStopSec=30','TimeoutStopSec=60')
    write('usr/lib/systemd/user/boreal.service',hardware_unit)
    write('usr/lib/systemd/user/boreal-demo.service',(source/'integration/boreal-demo.service').read_text())
    for desktop in ('io.boreal.Cooling.desktop','io.boreal.Cooling.Demo.desktop'):
        write('usr/share/applications/'+desktop,(source/'integration'/desktop).read_text())
    for name in ('71-boreal-kraken.rules',):
        write('usr/lib/udev/rules.d/'+name,(source/'integration'/name).read_text())
    write('usr/share/doc/boreal-cooling/copyright',(source/'LICENSE').read_text())
    shutil.copytree(source/'docs',root/'usr/share/doc/boreal-cooling/docs')
    write('usr/share/doc/boreal-cooling/README.md',(source/'README.md').read_text())
    write('usr/share/doc/boreal-cooling/README.en.md',(source/'README.en.md').read_text())
    write('usr/share/doc/boreal-cooling/CHANGELOG.md',(source/'CHANGELOG.md').read_text())
    write('usr/share/doc/boreal-cooling/CONTRIBUTING.md',(source/'CONTRIBUTING.md').read_text())
    write('usr/share/doc/boreal-cooling/SECURITY.md',(source/'SECURITY.md').read_text())
    write('DEBIAN/control','''Package: boreal-cooling
Version: 0.2.5~preview1
Section: utils
Priority: optional
Architecture: all
Maintainer: Boreal contributors <noreply@localhost>
Depends: python3 (>= 3.12), python3-gi, python3-gi-cairo, gir1.2-gtk-4.0 (>= 4.10), gir1.2-adw-1 (>= 1.4), python3-pil (>= 10.2), python3-packaging, python3-hid, python3-usb, python3-smbus, python3-docopt, python3-crcmod, python3-colorlog
Description: Native Linux Kraken cooling control (preview)
 Separate user service, native GTK UI and bounded hardware workers.
 Includes liquidctl 1.16.0; no pip or network installer scripts.
''')
    # Do not carry a developer's umask or group-write bits into the package.
    root.chmod(0o755)
    for entry in root.rglob('*'):
        if entry.is_symlink():
            continue
        entry.chmod(0o755 if entry.is_dir() else 0o644)
    (root/'usr/bin/boreal').chmod(0o755)
    target=args.output.resolve()/'boreal-cooling_0.2.5~preview1_all.deb'
    subprocess.run(['dpkg-deb','--root-owner-group','--build',str(root),str(target)],check=True)
    print(target)
