# Boreal 0.2.2 – aktueller Stand

Stand: 19.09.2026. **Vorschau, noch keine stabile Freigabe.**

## Bestätigt

- Kraken Elite V2, USB 1e71:3012, Firmware 1.2.0: Telemetrie, native
  Pumpen-/Lüfterkurven, Bild, GIF, Live-Temperaturübersicht, vier
  Ausrichtungen sowie Pumpenring- und Lüfterbeleuchtung.
- COSMIC-Tray: Ausblenden über X, Menü öffnen, vorhandenes Fenster
  wiederherstellen, Profile wechseln, Live-Stats pausieren/fortsetzen und
  Beleuchtung ausschalten/wiederherstellen.
- Messintervalle 0,5/1/2/3/5 Sekunden; die Sicherheitsabtastung bleibt bei
  langsam eingestellter Anzeige spätestens alle drei Sekunden aktiv.
- Dateiauswahl und Abbruch, getrennte Display-/RGB-/Kühlungsfehler sowie
  sichere Wiederherstellungsregeln.
- Vollständiger statischer Sicherheitscheck. Zwei lokale Befunde niedriger
  Schwere wurden in 0.2.2 korrigiert und mit Regressionstests abgedeckt.
- Diagnoseexport enthält nur erlaubte Zustandsfelder und höchstens 200
  automatisch bereinigte Logzeilen je Boreal-Komponente.

## Vor stabiler Freigabe offen

- Zehn echte Standby-/Resume-Zyklen, mehrere Neustarts und USB-Wiederanschluss
  mit aktivierter Opt-in-Wiederherstellung.
- Acht Stunden beaufsichtigter Normalbetrieb mit Speicher- und CPU-Beobachtung.
- 50 kombinierte Medienwechsel-/Rotationsabläufe in der echten UI. Die bisher
  geprüften zwölf Bild/GIF/Stats-Fälle liefen ohne Fehler; die ursprüngliche
  Ursache des verschwundenen Fensters ist nicht eindeutig reproduziert.
- Vollständige Bedienung per Tastatur und Screenreader, Hell/Dunkel und 200 %
  Skalierung in der installierten Hardware-App.
- System-DEB-Upgrade und -Downgrade auf einer sauberen Pop!_OS-Installation.
  Paketbau, Entpacken und Benutzerinstallation werden getrennt geprüft.
- Geräusch- und Temperaturvergleich der drei Testprofile unter vergleichbarer
  Last. Bis dahin bleiben sie ausdrücklich Testprofile.

Unterbrechende Standby-, Neustart- und Langzeittests werden nicht automatisch
ausgeführt. Während jeder Hardware-Abnahme muss die Kühlung sichtbar überwacht
werden; Pumpen- oder Stromkabel werden nicht absichtlich getrennt.
