# Zu Boreal beitragen

Danke für Tests, Fehlerberichte und Verbesserungen. Boreal steuert reale
Kühlhardware; nachvollziehbare Tests und vorsichtige Änderungen sind deshalb
besonders wichtig.

## Fehler und Hardwareberichte

Bitte zuerst eine passende GitHub-Issue-Vorlage verwenden. Für neue
Hardwaretests sind Distribution, Desktop-Sitzung, Kraken-Modell, USB-ID,
Firmware und getestete Funktionen erforderlich.

Vor dem Hochladen von Diagnoseinformationen entfernen:

- Seriennummern und eindeutige Gerätekennungen
- Benutzernamen und persönliche Pfade
- private Medien und nicht für die Öffentlichkeit bestimmte Logs

## Änderungen entwickeln

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install "liquidctl>=1.16,<1.17"
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m boreal --demo
```

Pull Requests sollten einen klaren Auslöser, das neue Verhalten und die
durchgeführten Tests beschreiben. Änderungen an USB-Protokollen, Grenzwerten,
udev-Regeln oder Wiederherstellung benötigen eine eigene Begründung.

## Grundregeln

- keine proprietären CAM-Dateien, Grafiken oder Code übernehmen
- Hardwarezugriff und UI getrennt halten
- keine USB-Schreibzugriffe aus UI-Callbacks
- vorhandene Kühlungsgrenzen nicht stillschweigend abschwächen
- unbekannte Modelle und Firmwarestände nicht automatisch freigeben
- keine persönlichen Diagnose- oder Konfigurationsdaten einchecken

Der Demo-Modus ist der bevorzugte Einstieg für UI- und Paketänderungen. Reale
Hardwaretests nie unbeaufsichtigt durchführen.
