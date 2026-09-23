# Paketprüfung Boreal 0.2.5

Stand: 23. September 2026

## Arch Linux

Der Paketbau wurde in einem verifizierten offiziellen Arch-Bootstrap-Abbild
`2026.09.01` ausgeführt. Verwendete Kernversionen:

- Python 3.14.7
- Pillow 12.3.0
- liquidctl 1.16.0
- GTK 4.22.5
- Libadwaita 1.9.4

`makepkg` baute das Paket ohne Netzwerkzugriff während des Builds. Alle 71
Tests liefen im Arch-System; ein Unix-Socket-Test blieb in der eingeschränkten
Build-Umgebung erwartungsgemäß übersprungen. Die liquidctl-Vertragsprüfung lief
mit Archs Paket 1.16.0 erfolgreich.

`namcap` meldete keine Fehler. Die verbleibenden Hinweise betreffen von GTK4
bereits transitiv bereitgestellte Bibliotheken, die bewusst aufgeführte
PyGObject/Cairo-Laufzeit und den von `python-installer` generierten Starter.

Geprüft wurden außerdem:

- Installation und erneute Installation mit Pacman
- Entfernung und anschließende Neuinstallation
- Erhalt von Konfiguration, Medien und Logs bei Neuinstallation und Entfernung
- nicht aktivierte systemd-Benutzerdienste nach der Paketinstallation
- udev-Regel mit Modus 0644 und Boreal-Starter mit Modus 0755
- Desktop-Dateien ohne Validierungsfehler
- systemd-Units mit `systemd-analyze verify`
- Demo-Start unter X11 auf Deutsch und Englisch
- Demo-Start unter einem kopflosen Wayland-Kompositor

Beim ersten nativen Arch-Start wurde eine Kollision zwischen einer lokalen
Hilfsvariable und der Übersetzungsfunktion gefunden. Sie ist behoben und durch
einen Regressionstest abgesichert.

## Noch offene Systemabnahmen

Ein früheres Arch-Paket 0.2.4 existierte nicht; deshalb ist ein reales
Pacman-Upgrade von diesem Paketstand nicht möglich. Neuinstallation und
Reinstallation mit erhaltenen Benutzerdaten decken den Paketlebenszyklus ab.

Eine vollständig gebootete CachyOS-VM mit Desktop, Tray-Host und
systemd-Benutzersitzung stand in dieser Umgebung nicht zur Verfügung. Das Paket
verwendet ausschließlich Arch-Abhängigkeiten und wurde im aktuellen Arch-
Userspace geprüft. Demo, Tray-Host, Autostart und Spracherkennung bleiben auf
einer frischen CachyOS-Installation noch praktisch abzunehmen.

Die reale Kraken-Steuerung ist mit Boreal auf Pop!_OS hardwaregeprüft. Auf Arch
und CachyOS bleibt sie bis zu einem physischen Test ausdrücklich
„noch nicht hardwaregeprüft“.
