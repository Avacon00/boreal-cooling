import argparse
import json
import subprocess
import sys
import time
from .transport import request
from .i18n import _


def ensure_service(demo):
    try:
        request(demo, "snapshot")
        return
    except (FileNotFoundError, ConnectionRefusedError):
        pass
    from pathlib import Path
    unit = 'boreal-demo.service' if demo else 'boreal.service'
    installed = any((p/unit).exists() for p in (Path.home()/'.config/systemd/user',Path('/usr/lib/systemd/user')))
    if installed:
        result = subprocess.run(['systemctl','--user','start',unit],capture_output=True,text=True,timeout=10)
        if result.returncode: raise RuntimeError(_('Boreal-Dienst konnte nicht starten: ')+result.stderr[:300])
        for _ in range(50):
            try: request(demo,'snapshot'); return
            except (FileNotFoundError,ConnectionRefusedError): time.sleep(.1)
        raise RuntimeError(_('Boreal-Dienst antwortet nicht; Diagnose im Journal prüfen'))
    # Source-tree development only. Installed builds use one systemd owner.
    command = [sys.executable, "-m", "boreal", "--daemon", "--demo" if demo else "--hardware"]
    subprocess.Popen(command, start_new_session=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            request(demo, "snapshot")
            return
        except (FileNotFoundError, ConnectionRefusedError):
            time.sleep(.1)
    raise RuntimeError(_("Boreal-Dienst konnte nicht starten. Details: ~/.local/state/boreal/"))


def main():
    parser = argparse.ArgumentParser(description=_("Boreal · native Linux Kraken control"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help=_("Simulierte Hardware (Standard)"))
    mode.add_argument("--hardware", action="store_true", help=_("Echte liquidctl-Geräte"))
    parser.add_argument("--daemon", action="store_true", help=_("Nur den Benutzerdienst starten"))
    parser.add_argument("--request", help='RPC JSON, z.B. {"op":"discover"}')
    parser.add_argument("--smoke", action="store_true", help=_("UI nach drei Sekunden schließen"))
    args = parser.parse_args()
    demo = not args.hardware
    from .i18n import configure as configure_language
    from .settings import Settings
    try: configure_language(Settings().read().get("language", "system"))
    except Exception: configure_language("system")
    if args.daemon:
        from .service import run
        run(demo)
        return
    ensure_service(demo)
    if args.request:
        value = json.loads(args.request)
        op = value.pop("op")
        print(json.dumps(request(demo, op, **value), ensure_ascii=False, indent=2))
        return
    from .ui import run
    raise SystemExit(run(demo, args.smoke))


if __name__ == "__main__":
    main()
