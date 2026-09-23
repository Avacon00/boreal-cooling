#!/usr/bin/env bash
# Run in the normal Pop!_OS terminal. Installs USB ACL rules, no cooling writes.
set -euo pipefail
boreal_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
sudo install -o root -g root -m 0644 \
  "$boreal_dir/integration/71-boreal-kraken.rules" \
  /etc/udev/rules.d/71-boreal-kraken.rules
sudo udevadm control --reload-rules
while IFS= read -r boreal_device; do
  sudo udevadm trigger --action=change "$boreal_device"
  sudo udevadm trigger --action=change --subsystem-match=hidraw --parent-match="$boreal_device"
done < <(python3 - <<'PY'
from pathlib import Path
for device in Path('/sys/bus/usb/devices').iterdir():
    try:
        if ((device/'idVendor').read_text().strip() == '1e71' and
            (device/'idProduct').read_text().strip() in
                {'170e','2007','2014','3008','300c','300e','3012','3014'}):
            print(device.resolve())
    except OSError:
        continue
PY
)
sudo udevadm settle --timeout=10
printf '%s\n' 'USB-Regeln eingerichtet. Boreal-Zugriff kann jetzt erneut geprüft werden.'
