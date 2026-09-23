# Aktueller Nachtrag

32 Tests einschließlich Socket-Integration nach Elite-V2-Korrektur bestanden. Zusätzlich echte Hardwaretests: siehe [Kraken Elite V2](HARDWARE-ELITE-V2.md). Der folgende ursprüngliche Bericht beschreibt den Stand vor diesen Hardwaretests.

# Prüfbericht — 14.09.2026

## Durchgeführt

- Python 3.12, GTK 4.14, Libadwaita 1.5, Pillow 10.2, liquidctl 1.16.0.
- 28 automatisierte Tests, 28 erfolgreich, einschließlich eingeschaltetem Unix-Socket-Integrationstest.
- Echte Unterprozesse: Demo-Worker, Zeitüberschreitung mit Prozessabbruch, Dienststart/-ende, privater Socket, zweite Dienstinstanz abgewiesen.
- Policy: Pumpen-/Lüftergrenzen, monoton steigende Kurven, NaN/Bool/Überlauf/fehlende Kanäle, Validierung vor Schreibzugriffen.
- Fehlerfälle: Pumpenstillstand, fehlende/falsche Sensorwerte und Einheiten, Übertemperatur, Teilschreibfehler, verlorener Worker, Versuch des zweiten Fallbackkanals trotz Fehler im ersten.
- Profile: Speichern/Lesen/Löschen, geschützte Presets, beschädigte Daten werden nicht still überschrieben, Dateimodus 0600.
- LCD-Medien: Größenänderung, animiertes GIF, unpassender Dateityp, Größenlimit, Stats ohne erfundene Sensorwerte.
- Adaptervertrag gegen installiertes liquidctl 1.16.0: PID, Klasse, LCD-Größe, fehlende Elite-/Plus-RGB-Kanäle. Sperre belegter und unkonfigurierter USB-Bulk-Interfaces ohne Konfigurationsänderung.
- Native Oberfläche unter X11 gestartet: Geräte suchen → verbinden → Profil anwenden → Messwerte anzeigen → trennen. GTK-Renderer-Aufnahme visuell geprüft.
- Nativer Wayland-Start mit sauberem Beenden erfolgreich.
- Wheel erfolgreich gebaut und in isolierter virtueller Umgebung installiert.
- install-local.py in simuliertem Benutzerordner mit Leerzeichen erfolgreich; installierter Starter ausführbar.
- Beide udev-Dateien mit `udevadm verify` erfolgreich geprüft.
- systemd-Benutzereinheit syntaktisch erfolgreich geprüft; der noch nicht systemweit installierte Starter wurde hierfür in einer Prüfkopie durch `/usr/bin/true` ersetzt.

## Nicht nachgewiesen

- Keine reale Kraken angeschlossen/gesteuert: keine verifizierten RPM-Reaktionen, thermischen Lasttests, LCD-Uploads, RGB-Effekte oder Firmware-Persistenz.
- Keine vollständige Pop!_OS-Neuinstallation durchlaufen; Prüfung in der vorhandenen Linux-Umgebung mit oben genannten GTK-Versionen.
- Die udev-Regeln/Helfer wurden nicht an echten USB-/hwmon-Geräten aktiviert. Reale Rechtevergabe bleibt zu prüfen.
- Suspend/Resume- und Hotplug-Verhalten benötigt Tests am Gerät. Die Fehlerzustände wurden simuliert.
- Tray-Implementierung vorhanden; erfolgreiche Registrierung und Interaktion mit einem COSMIC-StatusNotifier-Host sind nicht als Hardware-/Desktopabnahme dokumentiert.
- Autostart-/systemd-Dateien wurden erzeugt, aber nicht im echten Benutzerprofil dauerhaft aktiviert.

## Abnahme am eigenen Gerät

Mit konservativer Ausgangskurve beginnen. Modell/PID, Firmware, liquidctl-Version und Kernel dokumentieren. Einzelne Funktionen getrennt prüfen: Messwerte, native Kurve beider vorhandenen Kanäle, UI schließen, LCD-Statik, GIF, RGB. Danach Dienstende, Suspend/Resume und kontrollierten USB-Verbindungsabbruch prüfen; Kühlleistung währenddessen unabhängig überwachen. Keine Pumpen-/Stromkabel zum Fehlertest trennen. Erst nach diesen Prüfungen ein leiseres Profil unter beaufsichtigter Last testen.

Für neue Firmware keine automatische Vollfreigabe übernehmen: bekannte 2023-/Plus-Probleme und Modellmatrix berücksichtigen.
