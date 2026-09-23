# Bedienungsupdate – 15.09.2026

Implementiert: medienabhängige LCD-Aktion und Übertragungszustand; HSV-Farbkreis,
Farbfelder, HEX, Tastaturregler; fünf Messwertkarten und wählbare 0,5/1/2/3/5 Sekunden;
zusätzliche Testprofile. Gewünschtes Intervall ist global gespeichert, Standard 1 Sekunde.
Sicherheitsabtastung erfolgt spätestens nach 3 Sekunden außerhalb laufender USB-Aufrufe.
Die Historie umfasst zwölf Minuten anhand echter Zeitstempel. LCD-Stats bleiben bei 10 Sekunden.
Zwei erkannte Telemetrie-Zeitüberschreitungen bei 0,5 Sekunden stellen auf 1 Sekunde zurück;
der Verbindungsfehler wird dadurch nicht aufgehoben und keine Wiederverbindung erzwungen.

RPC v2 erweitert um `set_refresh_interval` mit `value` (500/1000/2000/3000/5000).
Snapshots enthalten `refresh_interval_ms`, `refresh_notice` und Geräte-`measured_at`.
Bestehende gespeicherte eigene Profile und bereits aktive Hardwarekurven bleiben erhalten.

Testprofile „Leise – Test“, „Ausgewogen – Test“ und „Leistung – Test“ sind Boreal-Kandidaten,
keine universell optimierten oder vom Hersteller zertifizierten Werte. Native Wasserquelle,
Pumpe mindestens 60%, Lüfter mindestens 30%, 100% spätestens bei 50°C.

Recherchegrundlagen:
- https://www.reddit.com/r/NZXT/comments/1kf86zm/help_with_fan_settings/
- https://support.nzxt.com/hc/en-us/articles/4411717735067-Controlling-your-PC-fans-in-CAM

44 automatisierte Tests einschließlich Socket-Integration bestanden. Wayland-Demo:
alle Seiten bei 800×600 einschließlich 200%-Skalierung, vier GIF-Vorschauausrichtungen und Dateidialogabbruch bestanden.
GVFS-Warnungen der isolierten Laufzeitumgebung, keine UI-Ausnahme dabei.

Noch nicht abgenommen: reale Abtastraten/CPU-Last während Uploads, RGB-Farben/Helligkeiten,
Geräusch- und Temperaturvergleich der Testprofile, vollständige Tastaturprüfung sowie Hell-/Dunkelvergleich. Der ursprüngliche Rotationsabsturz bleibt offen. Laufende Hardwareprozesse
wurden nicht ersetzt; zum Nutzen der neuen Intervallfunktion müssen UI und Dienst gemeinsam
neu gestartet werden. Kein automatisches Überschreiben der laufenden Kühlung beim Update.
