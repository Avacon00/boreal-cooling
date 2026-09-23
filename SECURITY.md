# Sicherheitsrichtlinie

## Unterstützte Version

Während der Preview-Phase wird nur die jeweils aktuelle veröffentlichte Version
mit Sicherheitskorrekturen versorgt.

## Schwachstellen melden

Sicherheitsprobleme bitte nicht zusammen mit sensiblen Details in einem
öffentlichen Issue veröffentlichen. Verwende nach Möglichkeit GitHubs Funktion
**Report a vulnerability** im Security-Bereich des Repositorys. Falls sie nicht
verfügbar ist, zunächst ein öffentliches Issue ohne Exploit, Seriennummern,
private Pfade oder vertrauliche Logs öffnen und um einen privaten Kontaktweg
bitten.

Normale Abstürze, Installationsprobleme und Hardwarekompatibilität gehören in
die öffentlichen Issue-Vorlagen.

## Sicherheitsgrenzen

Boreal läuft als Benutzerdienst, verwendet udev-Zugriff statt eines Root-Diensts
und begrenzt Medien- sowie USB-Arbeit. Eine AIO-Firmware und die Hardware selbst
bleiben dennoch die letzte Sicherheitsebene. Boreal ersetzt keine unabhängige
Temperaturüberwachung oder Notabschaltung.
