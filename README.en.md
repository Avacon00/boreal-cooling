# Boreal – NZXT Kraken Control for Linux

**A native, independent open-source NZXT CAM alternative for Linux: monitor Kraken AIOs and control pump, fans, LCD and RGB with GTK4, Libadwaita and liquidctl.**

[Deutsche README](README.md) · [Report an issue](https://github.com/Avacon00/boreal-cooling/issues/new/choose) · [Download 0.2.5](https://github.com/Avacon00/boreal-cooling/releases/tag/v0.2.5)

> [!IMPORTANT]
> Real hardware control has so far been validated on **Pop!_OS 24.04**, an
> Ubuntu-based distribution, using an **NZXT Kraken Elite 360 RGB V2**
> (`1e71:3012`, firmware `1.2.0`). The Arch package was built in a clean Arch
> environment and its demo was tested on X11 and Wayland, but real Kraken
> hardware has not yet been tested on Arch or CachyOS.

Boreal is an independent open-source project. It does not contain proprietary
NZXT CAM code and does not copy CAM branding or its exact interface.

## Features

- liquid, CPU and GPU temperatures plus pump and fan speed
- configurable 0.5 / 1 / 2 / 3 / 5 second telemetry refresh
- native liquid-temperature pump and radiator-fan curves
- Quiet, Balanced and Performance presets plus custom profiles
- graphical and keyboard-accessible curve editing
- static images, animated GIFs and live statistics on the Kraken LCD
- local media library, crop/fit controls, brightness and four rotations
- HSV color wheel, swatches, HEX input and brightness control
- detected pump-ring and fan-lighting zones
- tray menu with profile selection and safety shortcuts
- optional login start and guarded device-state restoration
- German, English and automatic system-language selection
- separate systemd user services for real hardware and demo mode
- local logs and a redacted diagnostic export

Cooling safety limits remain active: at least 60% pump, at least 30% fan and
100% on both channels by 50 °C liquid temperature. Invalid sensor data or a
confirmed pump stop latches a cooling fault and triggers a fallback attempt.

## Platform status

| Platform | Package | Demo/UI | Real Kraken hardware |
|---|---|---|---|
| Pop!_OS 24.04 / COSMIC | DEB | tested | **tested** |
| Ubuntu 24.04 | DEB | intended | not separately hardware-tested |
| Arch Linux | Pacman | tested on X11 and Wayland | not hardware-tested |
| CachyOS, EndeavourOS, Garuda | Pacman | Arch-compatible package | not hardware-tested |
| Fedora / openSUSE | RPM planned | not validated | not tested |

The primary validated device is the Kraken Elite RGB 2024/V2 with USB ID
`1e71:3012` and firmware `1.2.0`. Other liquidctl-supported Kraken devices may
be detected, but they remain unverified until a hardware report confirms them.

## Installation

Download packages and checksums from the
[v0.2.5 release](https://github.com/Avacon00/boreal-cooling/releases/tag/v0.2.5).

Pop!_OS / Ubuntu:

```bash
sudo apt install ./boreal-cooling_0.2.5.preview1_all.deb
systemctl --user daemon-reload
```

Arch Linux / CachyOS / EndeavourOS / Garuda:

```bash
sudo pacman -U ./boreal-cooling-0.2.5-1-any.pkg.tar.zst
```

Reconnect the Kraken or reboot after installation so the udev rule takes
effect. Package installation does not enable autostart or take control of the
device. Both remain explicit choices inside Boreal.

## Reporting bugs and hardware results

Testing on other distributions and Kraken models is welcome. Please open a
[GitHub issue](https://github.com/Avacon00/boreal-cooling/issues/new/choose)
and include the distribution, desktop session, Boreal package, Kraken model,
USB ID, firmware and exact reproduction steps.

Remove serial numbers, user names and personal paths before publishing logs or
diagnostic archives. Unverified devices will only be marked supported after the
report has been reviewed.

## Development

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install "liquidctl>=1.16,<1.17"
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m boreal --demo
```

The UI and hardware service are separate. Each device has one ordered hardware
access path, and cooling or safety work is prioritized ahead of new LCD and RGB
work. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Data and privacy

Boreal works locally, requires no account and uses no cloud service. User data
is stored below `~/.config/boreal`, `~/.local/share/boreal` and
`~/.local/state/boreal`.

## Current limitations

- preview software; no stable 1.0 release yet
- real hardware validation currently limited to the device and OS listed above
- no firmware updater
- CPU/GPU values are display sources, not cooling-curve inputs yet
- no free-form LCD layout editor
- wider hardware, RGB effect and long-running suspend/resume coverage is pending

## License and trademarks

GPL-3.0-or-later, see [LICENSE](LICENSE). Boreal is not an NZXT product and is
not endorsed or supported by NZXT. NZXT, Kraken and CAM belong to their
respective owners.
