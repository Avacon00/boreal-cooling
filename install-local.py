#!/usr/bin/env python3
"""User-run install: no sudo, no device writes, no automatic service enable."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

source = Path(__file__).resolve().parent
target = Path.home() / ".local/share/boreal"
if source != target:
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".venv", "__pycache__", ".git", "*.zip"))
venv = target / ".venv"
subprocess.run(["/usr/bin/python3", "-m", "venv", "--system-site-packages", str(venv)], check=True)
python = venv / "bin/python"
subprocess.run([str(python), "-m", "pip", "install", str(target)], check=True)
runner = Path.home() / ".local/bin/boreal"
runner.parent.mkdir(parents=True, exist_ok=True)
# Python launcher avoids shell interpolation even if home has spaces or quotes.
runner.write_text("#!/usr/bin/python3\nimport os, sys\nos.execv(" + repr(str(python)) +
                  ", [" + repr(str(python)) + ", '-m', 'boreal', *sys.argv[1:]])\n")
runner.chmod(0o755)
applications = Path.home() / ".local/share/applications"
applications.mkdir(parents=True, exist_ok=True)
escaped = str(runner).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%")
for name, mode in (("io.boreal.Cooling", "hardware"), ("io.boreal.Cooling.Demo", "demo")):
    (applications / f"{name}.desktop").write_text(
        f'[Desktop Entry]\nType=Application\nName=Boreal{" Demo" if mode == "demo" else ""}\n'
        f'Comment=Kraken-Kühlung unter Linux\nExec="{escaped}" --{mode}\n'
        'Icon=sensors-temperature-symbolic\nTerminal=false\nCategories=System;Settings;\n')
unitdir = Path.home() / ".config/systemd/user"
unitdir.mkdir(parents=True, exist_ok=True)
(unitdir / "boreal.service").write_text((target / "integration/boreal.service").read_text())
print(f"Installiert: {runner}\nProgrammstarter: Boreal / Boreal Demo\nAutostart und Dienst wurden NICHT aktiviert.")
