# Nativer Live-Test von Boreal – 16.09.2026

> Dieser Bericht hält den damaligen Testlauf unverändert fest. Später behobene
> Punkte und verbleibende Abnahmen stehen in [STATUS-0.2.2.md](STATUS-0.2.2.md).

Getestet wurde die bereits geöffnete GTK4-App auf COSMIC/Wayland mit der echten
Kraken Elite V2 (PID 3012, Firmware 1.2.0). Keine zweite Hardwaresteuerung,
kein Neustart/Standby, kein Firmwareupdate und keine absichtliche Unterbrechung.
Bedienaktionen erfolgten über AT-SPI und das D-Bus-Menü der laufenden Oberfläche;
Hardware-Matrix und Eingabevalidierung zusätzlich über deren bestehenden RPC-Dienst.
Automatisierte Tests sind ausdrücklich von sichtbaren Nutzerbestätigungen getrennt.

## Bestanden

| Prüfung | Ergebnis |
|---|---|
| X → Tray-Klick → Boreal öffnen | Vom Nutzer visuell bestätigt |
| Native Dateiauswahl „Bild hinzufügen“, Abbrechen | Vom Nutzer bestätigt; App bleibt bedienbar |
| Native Navigation | Alle fünf Seiten über GTK-Accessibility ausgewählt |
| Native HEX-Eingabe + Farbe anwenden | Magenta für Pumpenring bestätigt im Dienstzustand |
| Tray-Profile Leise / Leistung / Ausgewogen | Jeweils angewandt; passende tatsächliche Drehzahlen |
| Bild / GIF / Live-Stats × vier Rotationen | 12 echte Übertragungs-/Rotationsfälle ohne Dienstfehler; Ausrichtung ausgelesen |
| Live-Stats pausieren / fortsetzen im Tray | Mehr als einen 10-Sekunden-Zyklus unverändert, danach wieder aktualisiert |
| RGB im Tray aus / wiederherstellen | Beide Zonen aus, danach Magenta 70% wiederhergestellt |
| Sichtbare LCD- und RGB-Funktion | Nutzer bestätigt anschließend: „LCD und RGB funktionieren“ |
| Ungültige Rotation, Helligkeit, HEX, Medienkennung, Intervall | Abgewiesen; Kühlung blieb verbunden |
| Automatisierte Regression | 49 Tests inklusive Socket-Integration bestanden |

Profilreaktionen bei etwa 27,5 °C Wasser, kurze Beruhigungszeit:

| Profil | Pumpe | Lüfter |
|---|---:|---:|
| Leise | 2.381 U/min | 914 U/min |
| Leistung | 2.754 U/min | 1.376 U/min |
| Ausgewogen | 2.533 U/min | 1.094 U/min |

Dies ist ein Funktionstest, keine thermische Optimierung oder Geräuschmessung.

## Zeitverhalten

Je Einstellung rund zehn Sekunden Beobachtung, neue Geräte-Zeitstempel ausgewertet:

| Gewünschtes Intervall | Mittlerer Abstand neuer Messwerte |
|---|---:|
| 0,5 s | 0,506 s |
| 1 s | 1,007 s |
| 2 s | 2,011 s |
| 3 s | 3,014 s |
| 5 s | 3,013 s (beabsichtigte Sicherheitsabtastung spätestens alle 3 s) |

Die UI wird bei 5 Sekunden seltener aktualisiert; der Dienst überwacht weiterhin
schneller. Zustandsabfragen lagen in diesen Stichproben unter 2,9 ms.
Ein kurzes Zwei-Frame-Test-GIF wurde in etwa 0,136 s übertragen; vier parallele
Zustandsabfragen blieben unter 4,5 ms. Das ersetzt keinen Test mit großen GIFs.

## Gefundene Mängel und offene Befunde

1. **Navigation inkonsistent:** Beim Öffnen von „Beleuchtung“ über das Tray bleibt
   „Einstellungen“ in der Seitenleiste ausgewählt (gemessener Auswahlindex 4).
   Tray-Navigation muss Stack, Seitentitel und Seitenleisten-Auswahl gemeinsam ändern.
2. **Fehlende zugängliche Namen:** Farbton, Sättigung, HEX und Helligkeit erscheinen
   in AT-SPI ohne Feldnamen, obwohl sichtbare Beschriftungen vorhanden sind.
   Native Beschriftungsbeziehungen bzw. Accessible-Labels ergänzen.
3. **Accessibility bei Aus-/Einblenden instabil:** Nach Cache-Erneuerung und Wartezeit
   funktionierten 19 aufeinanderfolgende native Zyklen; beim 20. fehlte zeitweise der
   Fensterbaum. Boreal antwortete weiterhin über D-Bus, die Kühlung blieb gesund und
   ein neuer Accessibility-Prozess fand das Fenster wieder. Kein bewiesener App-Absturz;
   Ursache zwischen AT-SPI-Cache, GTK und Fensterlebenszyklus noch offen.
4. **Autostart derzeit nicht betriebsbereit:** Weder System- noch Benutzer-Unit für
   boreal.service installiert. Der Quellstart funktioniert; Autostart-End-to-End kann
   in diesem Installationszustand nicht bestehen. Vorheriger UI-Logeintrag bestätigt
   „Unit file boreal.service does not exist“. In diesem Test nicht erneut aktiviert.
5. **Unklare GPU-Beschriftung:** Der Übersichtswert „GPU“ ist das Maximum einschließlich
   Speicher-/Junction-Sensoren; hier 56 °C Speicher gegenüber ungefähr 33 °C GPU edge.
   Kein erfundener Messwert, aber ohne „Maximum“ oder Sensorname leicht missverständlich.

## Noch nicht abgenommen

- Die allgemeine LCD-/RGB-Funktion wurde vom Nutzer bestätigt. Eine gesonderte
  visuelle Einzelabnahme jeder Ausrichtung und Farbkombination ist damit nicht dokumentiert.
- Vollständige Tastatur-/Screenreader-Bedienung, Farbkreis-Ziehen, alle Layouts in
  Hell/Dunkel und 200% an der geöffneten Hardware-App.
- Import/Export-/Profilumbenennung über den nativen Dateidialog; der Portal-Dialog
  war über die verfügbare AT-SPI-Anbindung nicht auslesbar und wurde manuell bestätigt.
- Große/fehlerhafte GIFs in der realen UI, 50 kombinierte Medienwechsel,
  acht Stunden Speicher-/CPU-Beobachtung, Standby/Neustart/USB-Wiederanschluss.
- Installations-/Upgrade-/Downgrade-Test und Autostart nach tatsächlicher Installation.

## Abschlusszustand

Ausgewogen, ursprüngliches Messintervall 0,5 Sekunden, LCD-Live-Temperaturübersicht
mit 180° und ursprünglicher Helligkeit 50%; Pumpenring und Lüfter auf Magenta 70%.
Kein erkannter Kühlungsfehler. Software blieb geöffnet. Produktionscode wurde für
 diesen Test nicht verändert. Testskripte und rohe Messdaten liegen im Arbeitsordner
work/native-qa (nicht für ungeprüften öffentlichen Diagnoseversand vorgesehen).

**Urteil:** Kernfunktionen an echter Hardware erfolgreich geprüft. Wegen der
aufgeführten UI-/Accessibility-Mängel und offenen Abnahmen keine vollständige
Freigabe und kein Nachweis, dass der ursprüngliche Rotationsabsturz endgültig behoben ist.
