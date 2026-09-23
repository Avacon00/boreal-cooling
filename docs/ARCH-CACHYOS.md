# Arch Linux und CachyOS

Boreal 0.2.5 wird als distributionsnahes Pacman-Paket für aktuelle
x86_64-Installationen von Arch Linux, CachyOS, EndeavourOS und Garuda gebaut.
Es verwendet die Python-, GTK-, Libadwaita-, Pillow- und liquidctl-Pakete der
Distribution. Während der Installation werden keine Python-Pakete aus dem
Internet geladen.

## Installation des fertigen Pakets

```bash
sudo pacman -U ./boreal-cooling-0.2.5-1-any.pkg.tar.zst
```

Nach der Installation die Kraken neu anstecken oder Linux neu starten, damit
die udev-Regel sicher greift. Anschließend **Boreal** über das Programmmenü
öffnen. Die Paketinstallation aktiviert weder den Benutzerdienst noch die
automatische Geräteübernahme. Beides bleibt eine bewusste Einstellung in Boreal.

## Upgrade und Entfernung

Ein Upgrade erfolgt mit demselben `pacman -U`-Befehl und dem neueren Paket.

```bash
sudo pacman -U ./boreal-cooling-0.2.5-1-any.pkg.tar.zst
sudo pacman -Rns boreal-cooling
```

Upgrade, Neuinstallation und Entfernung löschen keine persönlichen Profile,
Medien oder Logs in `~/.config/boreal`, `~/.local/share/boreal` und
`~/.local/state/boreal`.

## Selbst aus dem Quellpaket bauen

`PKGBUILD`, `boreal-cooling.install` und das Quellarchiv gemeinsam in einen
leeren Ordner legen und als normaler Benutzer ausführen:

```bash
makepkg -si
```

`makepkg` verwendet ausschließlich die im `PKGBUILD` genannten offiziellen
Arch-Pakete. Die SHA-256-Prüfsummen stehen in `SHA256SUMS` und zusätzlich im
`PKGBUILD` für das Quellarchiv.

## Gültigkeitsbereich

Das Paket richtet sich zunächst an aktuelle x86_64-Systeme. Die reale Kraken
Elite V2 wurde mit Boreal auf Pop!_OS geprüft. Paket, Demo-Modus und
Desktop-Integration werden in einer sauberen Arch-Umgebung geprüft; die
Hardwaresteuerung auf Arch/CachyOS bleibt bis zu einem physischen Test als noch
nicht hardwaregeprüft gekennzeichnet.
