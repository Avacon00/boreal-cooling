# Kraken Elite V2 – Test am echten Gerät

14.09.2026, Benutzergerät: Kraken Elite 360 RGB. Ausgelesen: NZXT Kraken Elite V2,
USB 1e71:3012, Firmware 1.2.0, liquidctl 1.16.0, LCD 640 × 640.

## Nachgewiesen

- USB-Zugriff nach Einrichten der udev-Regeln erfolgreich.
- Ausgangsmessung: Wasser 28,2 °C, Pumpe ca. 1465 U/min bei 20%, Lüfter ca. 505 U/min bei 20%.
- Native Kurve mit 100%: Pumpe 2884 U/min, Lüfter 2419 U/min.
- Native Kurve mit 70% Pumpe / 50% Lüfter: Pumpe 2464 U/min, Lüfter 1209 U/min.
- Wasser während des kurzen Stufentests 28,2 °C. Dies ist kein thermischer Last-/Dauertest.
- Anschließend Profil Ausgewogen gesetzt. Unter späteren Messbedingungen ca. 73% Pumpe / 44% Lüfter,
  Pumpe ca. 2520 U/min, Lüfter ca. 1070 U/min, Wasser 27,6 °C.
- LCD-Statistikbild erfolgreich übertragen und vom Benutzer ausdrücklich als korrekt sichtbar bestätigt.
- Echter Boreal-Dienst und native Hardware-UI gestartet. Wiederholte Telemetrie und LCD-Stats-Uploads
  im 10-Sekunden-Takt ohne Verbindungsfehler beobachtet.
- GIF-Testdatei übertragen, API-Aufruf erfolgreich; der Benutzer bestätigte die korrekt laufende Animation.
- Zum Abschluss LCD wieder auf laufende Statistiken gestellt und verbundenen, fehlerfreien Zustand geprüft.

## Gefundener und korrigierter Fehler

Direkt nach einem Kurven-Schreibzugriff lieferte eine Statusabfrage zunächst ein Paket
mit Kennung ff:01 statt der regulären Sensorantwort 75:01. liquidctl 1.16.0 interpretierte
das Paket trotzdem als Sensorwerte: 1 °C, 0 U/min und 0% auf beiden Kanälen.
Boreals Schutzprüfung reagierte korrekt auf die vermeintlich stillstehende Pumpe und
verriegelte die Verbindung mit gesendetem 100%-Fallback.

Der Adapter prüft nun für PID 3012 die Antwortkennung und Mindestlänge. Maximal zwölf
Nicht-Sensorpakete werden innerhalb des bestehenden Prozess-Zeitlimits verworfen;
es werden keine zusätzlichen Steuerbefehle gesendet. Ein echtes 75:01-Paket mit
0 U/min bleibt ein Sensorfehler. Die Bedeutung des ff:01-Pakets wurde nicht abschließend
bestimmt; es wird ausdrücklich nicht als bestätigter Sensorwert oder bestätigte
Steuerquittung behandelt. Andere Modellpfade wurden nicht verändert.

Regression: 32 Tests einschließlich Socket-Integration bestanden. Neue Tests decken
die Paketunterscheidung, erhaltene Null-RPM-Werte und die begrenzte Fehlersuche ab.

## Noch offen

- RGB: liquidctl 1.16.0 meldet keine Farbkanäle für diese Variante. Keine Roh-RGB-Pakete getestet.
- Helligkeit, Drehung, Suspend/Resume, Hotplug, Kaltstart und thermischer Dauertest noch nicht abgenommen.
- Kein absichtlicher physischer Pumpen-/Sensorausfall auf dem produktiven Rechner.
- Kein Nachweis für andere Elite-Firmware oder andere Kraken-Modelle.

## Aktiver Zustand

Das ausgewogene Profil ist absichtlich aktiv. Es entspricht nicht den unbekannten
ursprünglichen Firmwarekurven; die anfänglichen 20%-Werte waren nur ein Messpunkt.
Boreal läuft als normaler Benutzer. Bei Dienstende versucht es 100%-Kurven zu setzen.
Die native Oberfläche zeigt echte Messwerte, keine Demo-Kraken.
