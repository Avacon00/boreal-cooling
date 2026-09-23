#!/usr/bin/env python3
"""Install a locally built Boreal DEB in user scope; never fetch dependencies."""
import argparse,os,shutil,subprocess,tempfile,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('package',type=Path);a=p.parse_args()
# All native dependencies must already be installed. No pip/network fallback.
subprocess.run(['/usr/bin/python3','-c',"import gi,PIL,packaging,hid,usb,smbus,docopt,crcmod,colorlog;gi.require_version('Gtk','4.0');gi.require_version('Adw','1');from gi.repository import Gtk,Adw;assert (Gtk.get_major_version(),Gtk.get_minor_version()) >= (4,10);assert (Adw.get_major_version(),Adw.get_minor_version()) >= (1,4)"],check=True)
base=Path.home()/'.local/share/boreal-app';base.mkdir(parents=True,exist_ok=True)
release=base/('release-'+time.strftime('%Y%m%d-%H%M%S'))
with tempfile.TemporaryDirectory(dir=base) as tmp:
 extracted=Path(tmp)/'package';subprocess.run(['dpkg-deb','--extract',str(a.package.resolve()),str(extracted)],check=True)
 shutil.copytree(extracted/'usr/lib/boreal',release)
 icon=Path.home()/'.local/share/icons/hicolor/scalable/apps/io.boreal.Cooling.svg';icon.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(extracted/'usr/share/icons/hicolor/scalable/apps/io.boreal.Cooling.svg',icon)
link=base/'current.new';link.symlink_to(release.name);link.replace(base/'current')
launcher=Path.home()/'.local/bin/boreal';launcher.parent.mkdir(parents=True,exist_ok=True)
if launcher.exists():shutil.copy2(launcher,base/('launcher-backup-'+str(time.time_ns())))
launcher.write_text("#!/usr/bin/python3\nimport os,sys\nfrom pathlib import Path\np=str((Path.home()/'.local/share/boreal-app/current').resolve())\nsys.path.insert(0,p)\nos.environ['PYTHONPATH']=p\nfrom boreal.__main__ import main\nmain()\n");launcher.chmod(0o755)
units=Path.home()/'.config/systemd/user';units.mkdir(parents=True,exist_ok=True)
apps=Path.home()/'.local/share/applications';apps.mkdir(parents=True,exist_ok=True)
for demo in (False,True):
 name='boreal-demo' if demo else 'boreal';mode='demo' if demo else 'hardware'
 unit=units/(name+'.service')
 if unit.exists():shutil.copy2(unit,base/(name+'-unit-backup-'+str(time.time_ns())))
 unit.write_text(f'[Unit]\nDescription=Boreal Kraken user service\nAfter=graphical-session.target\nPartOf=graphical-session.target\n\n[Service]\nType=simple\nExecStart=%h/.local/bin/boreal --daemon --{mode}\nRestart=on-failure\nRestartSec=5\nTimeoutStopSec=60\nUMask=0077\nNoNewPrivileges=yes\n\n[Install]\nWantedBy=graphical-session.target\n')
 desktop_id='io.boreal.Cooling.Demo' if demo else 'io.boreal.Cooling'
 escaped=str(launcher).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')
 (apps/(desktop_id+'.desktop')).write_text(f'[Desktop Entry]\nType=Application\nName=Boreal{" Demo" if demo else ""}\nExec="{escaped}" --{mode}\nIcon=io.boreal.Cooling\nTerminal=false\nCategories=System;Settings;\n')
subprocess.run(['systemctl','--user','daemon-reload'],check=True)
print('Installed:',release,'\nAutostart is not enabled by this installer.')
