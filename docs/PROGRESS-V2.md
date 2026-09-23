# Boreal 0.2 – Implementierung und Abnahme

> Historischer Zwischenstand vom 15.09.2026. Der aktuelle, zusammengeführte
> Stand steht in [STATUS-0.2.2.md](STATUS-0.2.2.md).

Stand: 15.09.2026. **Vorschau, keine stabile Freigabe.**

## Implementiert

- RPC v2 mit strukturierten Fehlern und abfragbaren Aufträgen; pro Gerät eine
  priorisierte Warteschlange, Zustandsabfragen unabhängig von langsamen USB-Aufträgen.
- Getrennte Kühlungs-, Display- und RGB-Fehler. Medienfehler trennen ein gesundes
  Gerät nicht. Bestehende Sicherheitsgrenzen und Telemetrie-Paketfilter bleiben erhalten.
- Asynchrone GTK-Dateidialoge mit Abbruchverwaltung; Medienaufbereitung in einem
  Prozess mit Laufzeit- und Speichergrenzen.
- Fünf native Navigationsbereiche, grafischer Kurveneditor mit Tastaturtabelle,
  Apply/Discard, Profile importieren/exportieren, runde LCD-Vorschau.
- Medienbibliothek einschließlich lokaler Quelldatei für erneutes Zuschneiden;
  drei Statistikvorlagen und 10-Sekunden-Aktualisierung mit Bildvergleich.
- Zusammenhängende Rotation mit pausierten Stats, Ausrichtungsauslesung und
  erneutem Übertragen des letzten Inhalts; Fehler bleiben sichtbar.
- Firmware- und Identitätsprüfung vor ausdrücklich aktivierter Wiederherstellung,
  versionierte Einstellungen und Profilmigration mit Sicherung.
- Elite-V2-RGB-Adapter für feste Farben/Aus/Helligkeit mit Zubehörerkennung;
  noch nicht physisch abgenommen.
- Tray-Menü, systemd-Integration, redigierter Diagnoseexport und DEB-Build ohne
  pip-Aufrufe während der Installation.

## Tatsächlich geprüft

- 41 automatisierte Tests einschließlich neuer Regressionen für UI-Namenskollisionen,
  Displayfehler, 50 simulierte Drehbefehle, RGB-Pakete/Zubehör, Wiederherstellungsregeln,
  beschädigte Konfigurationen und erneutes Zuschneiden nach Löschen des Originals.
- Separater Socket-Integrationstest mit simulierter Hardware.
- Nativer Start unter COSMIC/Wayland; Übersicht und Kurveneditor gerendert.
- Alle fünf Seiten bei tatsächlich gemessenen 800×600 Pixeln gerendert, GIF-Vorschau
  in vier Ausrichtungen und Dateidialog-Abbruch geprüft. Keine Ausnahme; GVFS-Warnungen
  wegen des isolierten Test-Laufzeitverzeichnisses wurden protokolliert.
- Beim ersten neuen UI-Start gefundene Namenskollision zwischen Hintergrundfarbfeld
  und Hintergrundfunktion behoben. Dies war ein neuer Startfehler und ist **kein
  Nachweis für die Ursache des ursprünglich gemeldeten Rotationsabsturzes**.
- DEB gebaut und entpackt; gebündeltes liquidctl 1.16.0 mit System-Python importiert
  und Hardwareadapter ohne Gerätezugriff konstruiert.

## Noch offen vor stabiler Freigabe

- Vollständige Dateidialog-/Rotationsmatrix unter Wayland einschließlich Fensterende,
  schneller Folgeaktionen, aller Medienarten und 50 echter kombinierter Abläufe.
- Visuelle Abnahme aller vier Ausrichtungen und RGB-Zonen an PID 3012 / FW 1.2.0.
- Wiederanlauf an echter Hardware, zehn Standby-Zyklen, mehrere Neustarts und
  acht Stunden beaufsichtigter Normalbetrieb ohne Speicherwachstum.
- Vollständige Prüfung bei 800×600, 200% Skalierung, Hell/Dunkel, Tastatur und Screenreader.
- DEB-Installation/Upgrade/Downgrade auf sauberem Pop!_OS; zuverlässiger Umstieg von
  älteren lokalen Startern und Benutzerdiensten. Das erzeugte Paket wurde nicht installiert.
- Diagnoseexport enthält derzeit redigierten Zustand und Versionsinformationen,
  noch keinen vollständigen redigierten Logauszug.

Die früher bestätigten echten Bild-/GIF-Tests gelten für den damaligen Stand.
Die neue Implementierung wurde bisher mit Demo-Geräten geprüft; daraus folgt
keine erneute Hardwarefreigabe. Der ursprüngliche Fensterabbruch bleibt offen.
