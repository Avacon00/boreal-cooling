# Boreal

**Native Linux-Steuerung für NZXT-Kraken-Kühlungen – mit GTK4, Libadwaita und liquidctl.**

[English README](README.en.md) · [Fehler melden](https://github.com/Avacon00/boreal-cooling/issues/new/choose) · [Version 0.2.5 herunterladen](https://github.com/Avacon00/boreal-cooling/releases/tag/v0.2.5)

![Version](https://img.shields.io/badge/version-0.2.5-35c99a)
![Python](https://img.shields.io/badge/Python-%E2%89%A53.12-3776ab)
![GTK](https://img.shields.io/badge/GTK-4-4a86cf)
![Lizenz](https://img.shields.io/badge/Lizenz-GPL--3.0--or--later-blue)

> [!IMPORTANT]
> Die reale Kraken-Steuerung wurde bisher auf **Pop!_OS 24.04**, einer
> Ubuntu-basierten Distribution, mit einer **NZXT Kraken Elite 360 RGB V2**
> (`1e71:3012`, Firmware `1.2.0`) geprüft. Das Arch-Paket wurde in einer
> sauberen Arch-Umgebung gebaut und im Demo-Modus unter X11 und Wayland
> getestet, aber noch nicht mit echter Kraken-Hardware auf Arch oder CachyOS.

Boreal ist eine eigenständige Open-Source-Anwendung. NZXT CAM dient nur als
Maßstab für eine verständliche Bedienung. Boreal verwendet keinen
proprietären CAM-Code und übernimmt weder dessen Branding noch dessen UI.

## Funktionen

### Übersicht und Telemetrie

- Kühlmittel-, CPU- und GPU-Temperaturen
- Pumpen- und Lüfterdrehzahl
- aktives Kühlprofil und Verbindungsstatus
- frei wählbares Messintervall: 0,5 / 1 / 2 / 3 / 5 Sekunden
- Zeitstempel und Kennzeichnung veralteter Messwerte
- kompakter Temperaturverlauf

### Kühlung

- native, auf der Kraken gespeicherte Wassertemperaturkurven
- getrennte Pumpen- und Lüfterkurven
- Profile **Leise**, **Ausgewogen** und **Leistung**
- zusätzliche, klar markierte Testprofile
- grafischer Kurveneditor und Tastaturtabelle
- eigene Profile speichern, duplizieren, umbenennen, importieren und exportieren
- Änderungen werden erst über **Anwenden** an die Hardware übertragen
- dauerhaft erreichbare Sicherheitsaktion **Volle Kühlleistung**

Sicherheitsgrenzen: Pumpe mindestens 60 %, Lüfter mindestens 30 % und beide
Kanäle spätestens bei 50 °C mit 100 %. Kritische Sensordaten oder echter
Pumpenstillstand verriegeln die Steuerung und lösen einen Fallbackversuch aus.

### Kraken-LCD

- statische Bilder und animierte GIFs
- lokale Medienbibliothek
- Zuschneiden, Einpassen, Skalierung und Hintergrundfarbe
- Helligkeit und Ausrichtung in vier Schritten
- runde, maßstabsgetreue Vorschau
- drei Statistikvorlagen für Temperaturen und Drehzahlen
- wählbare Sensoren, Farben, Schriftgrößen und Einheiten
- pausierbare Live-Statistiken; identische Bilder werden nicht erneut übertragen

### RGB-Beleuchtung

- HSV-Farbkreis, Farbfelder und HEX-Eingabe
- getrennte Helligkeitssteuerung
- feste Farbe und Ausschalten
- Wiederherstellung der zuletzt erfolgreich übertragenen Beleuchtung
- Pumpenring und erkannte Lüfterbeleuchtung
- Zubehörerkennung statt Annahmen anhand der Radiatorgröße

### Alltag und Linux-Integration

- native GTK4-/Libadwaita-Oberfläche
- Deutsch, Englisch und automatische Systemsprache
- helles, dunkles oder systemweites Erscheinungsbild
- StatusNotifier-Tray mit Profilwahl und Schnellaktionen
- Schließen in den Tray, ohne den Hardwaredienst zu beenden
- optionaler Autostart von Dienst, Oberfläche und Tray
- automatische Wiederherstellung nach ausdrücklicher Aktivierung
- systemd-Benutzerdienste für Hardware- und Demo-Modus
- udev-Regel für USB-/hidraw-Zugriff
- rotierende Logs und bereinigter Diagnoseexport
- Demo-Modus ohne angeschlossene Hardware

## Unterstützungsstatus

| System | Paket | Demo/UI | Echte Kraken-Hardware |
|---|---|---|---|
| Pop!_OS 24.04 / COSMIC | DEB | geprüft | **geprüft** |
| Ubuntu 24.04 | DEB | vorgesehen | noch nicht separat hardwaregeprüft |
| Arch Linux | Pacman | X11 und Wayland geprüft | noch nicht hardwaregeprüft |
| CachyOS, EndeavourOS, Garuda | Pacman | Arch-kompatibles Paket | noch nicht hardwaregeprüft |
| Debian | derzeit kein freigegebenes Paket | nicht abgenommen | nicht geprüft |
| Fedora / openSUSE | RPM geplant | nicht abgenommen | nicht geprüft |

Hardwareseitig ist derzeit die Kraken Elite RGB 2024/V2 mit USB-ID
`1e71:3012` und Firmware `1.2.0` der primäre Teststand. Andere von liquidctl
unterstützte Kraken können erkannt werden, gelten aber bis zu einem bestätigten
Testbericht nicht als von Boreal freigegeben.

## Installation

Pakete und Prüfsummen stehen unter
[Releases](https://github.com/Avacon00/boreal-cooling/releases/tag/v0.2.5).

### Pop!_OS 24.04 / Ubuntu 24.04

```bash
sudo apt install ./boreal-cooling_0.2.5.preview1_all.deb
systemctl --user daemon-reload
```

### Arch Linux / CachyOS / EndeavourOS / Garuda

```bash
sudo pacman -U ./boreal-cooling-0.2.5-1-any.pkg.tar.zst
```

Nach der Installation die Kraken neu anstecken oder Linux neu starten, damit
die udev-Regel sicher greift. Der Installer aktiviert weder Autostart noch
Geräteübernahme. Beides wird bewusst in Boreal eingeschaltet.

Ausführliche Hinweise: [Arch Linux und CachyOS](docs/ARCH-CACHYOS.md) ·
[Paketprüfung 0.2.5](docs/PACKAGING-0.2.5.md)

## Erste Einrichtung

1. Andere Programme beenden, die dieselbe Kraken steuern.
2. Boreal über das Programmmenü starten.
3. Erkanntes Modell und Firmware prüfen.
4. **Einrichten** wählen. Boreal setzt zunächst sichere Ausgangswerte und lädt
   anschließend das ausgewogene Profil.
5. Display und Beleuchtung konfigurieren.
6. Autostart und automatische Wiederherstellung nur bei Bedarf aktivieren.

Das Schließen des Fensters beendet den Hardwaredienst nicht. Ohne verfügbaren
Tray-Host bleibt Boreal über den Programmstarter erreichbar.

## Fehler und Hardwaretests melden

Tests auf weiteren Distributionen und Kraken-Modellen sind ausdrücklich
willkommen. Bitte dafür ein
[GitHub-Issue](https://github.com/Avacon00/boreal-cooling/issues/new/choose)
öffnen. Die Vorlagen fragen gezielt nach:

- Distribution, Version und Desktop-Sitzung
- Boreal-Paket und Version
- Kraken-Modell, USB-ID und Firmware
- genauen Schritten und beobachtetem Verhalten
- relevanten, zuvor geprüften Diagnoseinformationen

Seriennummern, Benutzernamen und persönliche Dateipfade bitte vor dem
Veröffentlichen entfernen. Fehlerberichte und Hardwaretests werden gemeinsam
ausgewertet; unbestätigte Geräte werden nicht automatisch als unterstützt
markiert.

## Entwicklung

```bash
sudo apt install python3-venv python3-pip python3-gi python3-gi-cairo \
  gir1.2-gtk-4.0 gir1.2-adw-1 python3-pil python3-packaging
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install "liquidctl>=1.16,<1.17"
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m boreal --demo
```

Arch-Quellen und Paketbau:

```bash
python3 tools/build-arch-release.py --output ../packages/arch
cd ../packages/arch
makepkg -si
```

## Architektur

- `ui.py`, `widgets.py`: GTK-Oberfläche
- `runtime.py`, `transport.py`: RPC v2, Aufträge und Unix-Sockets
- `service.py`: Gerätezustände, Prioritäten und Sicherheitslogik
- `hardware.py`, `rgb.py`: liquidctl- und Elite-V2-Adapter
- `worker.py`: begrenzte USB-Prozesse
- `library.py`, `media_worker.py`: Medienprüfung und Aufbereitung
- `settings.py`: versionierte Konfiguration und Wiederherstellung
- `tray.py`, `tray_model.py`: StatusNotifier und Schnellaktionen

UI und Hardwaredienst sind getrennt. Pro Gerät gibt es einen geordneten
Hardwarezugriffspfad; Kühlungs- und Sicherheitsaufträge haben Vorrang vor neuen
Display- und RGB-Aufträgen.

## Daten und Datenschutz

Boreal arbeitet lokal, benötigt kein Konto und nutzt keine Cloud. Konfiguration,
Medien und Logs liegen im Home-Verzeichnis:

- `~/.config/boreal`
- `~/.local/share/boreal`
- `~/.local/state/boreal`

Diagnoseexporte entfernen bekannte Seriennummern, Gerätekennungen und
persönliche Pfade. Vor dem Hochladen sollte der Export trotzdem geprüft werden.

## Aktuelle Grenzen

- Preview-Software; noch keine stabile 1.0-Freigabe
- reale Hardwareprüfung bisher nur auf Pop!_OS mit der genannten Elite V2
- kein integriertes Firmwareupdate
- CPU-/GPU-Werte dienen zunächst der Anzeige, nicht als Regelquelle
- kein freier LCD-Layouteditor
- animierte RGB-Effekte und weitere Hersteller folgen später
- Standby-, Neustart- und Langzeittests werden weiter ausgebaut

## Mitarbeit

Siehe [CONTRIBUTING.md](CONTRIBUTING.md). Pull Requests sollten Hardwarezugriff,
UI und Paketierung getrennt halten und die bestehenden Sicherheitsgrenzen nicht
abschwächen.

## Lizenz und Marken

GPL-3.0-or-later, siehe [LICENSE](LICENSE). Boreal ist kein Produkt von NZXT und
wird von NZXT weder unterstützt noch bestätigt. NZXT, Kraken und CAM sind Marken
ihrer jeweiligen Rechteinhaber.
