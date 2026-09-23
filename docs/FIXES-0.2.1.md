# Korrekturen 0.2.1 – 16.09.2026

> Historischer Stand. Siehe [STATUS-0.2.2.md](STATUS-0.2.2.md) für den
> zusammengeführten aktuellen Prüfstand.

- Tray-Navigation wählt jetzt den zugehörigen Eintrag der Seitenleiste aus und
  aktualisiert Titel und Seiteninhalt gemeinsam. An installierter App bestätigt.
- Übersicht und Kurztext benennen CPU/GPU als Maximum. Keine Änderung der Sensorwerte.
- Farbton, Sättigung, HEX, Helligkeit sowie weitere Einstellungen erhalten
  explizite GTK-Accessible-Labels. Namen über die native AT-SPI-Schnittstelle bestätigt.
- Lokaler Installer für das vorab gebaute DEB, ohne Download oder pip; vorhandene
  Systemabhängigkeiten werden vor Installation geprüft. Release unter Benutzerkonto,
  Programmstarter und beide Benutzerdienste. Bestehende Releases bleiben erhalten.
- Auf diesem Rechner ist boreal.service installiert, aktiv und für die grafische
  Sitzung aktiviert. Bisherigen Kühlungs-/Display-/RGB-Zustand beim Wechsel übernommen.
  Gerätewiederherstellung bleibt ein separater Opt-in; deren Auswahl wurde nicht geändert.

Prüfung: 49 Tests inklusive Socket-Integration bestanden. Gezielter GTK-Test für
alle fünf Tray-Seiten bestanden; installierte Hardware-App auf Navigationsauswahl,
Sensorbeschriftungen und zugängliche Feldnamen geprüft. In der isolierten GTK-Prüfung
lief kein Demo-Dienst, deshalb wurden dort erwartete Socket-Fehlermeldungen protokolliert.
Der produktive installierte Dienst antwortet und meldet keinen Kühlungsfehler.

Der Wiederöffnungsbefund wird getrennt untersucht: synchroner AT-SPI-Test mit
Cache zeigte fehlende Fensterkinder, obwohl der nächste Testprozess das Fenster
wieder fand. Ereignisverarbeitung und Cache-Deaktivierung werden im Testclient
berücksichtigt; daraus wird kein unbelegter GTK-/App-Fix abgeleitet.

Weiter offen: tatsächlicher Anmeldungs-/Standby-/Neustarttest, Langzeitbetrieb,
ursprünglicher Rotationsabsturz. Keine automatische Abschaltung oder Suspend-Tests.

Nutzerbestätigung nach den neuen Tests: „Das Fenster kommt sichtbar zurück“.
Der cachefreie AT-SPI-Test überschritt ebenfalls sein Zeitlimit. Deshalb keine
Behauptung einer vollständig reparierten Accessibility-Infrastruktur; sichtbares
Wiederöffnen bestätigt, automatisierter 20-Zyklen-Nachweis weiterhin offen.
