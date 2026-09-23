# Tray-Update – 16.09.2026

- X und „In den Tray“ blenden das Fenster bei registriertem Tray-Host aus.
- Ohne Tray-Host beendet X nur die Oberfläche. Ein verlorener Host bringt ein
  verborgenes Fenster zurück; spätere Host-Registrierung meldet Boreal erneut an.
- Menü: Öffnen, Status, Geräteauswahl bei mehreren Geräten, Kühlprofile einschließlich
  eigener/Testprofile, volle Kühlleistung, Display, Beleuchtung, Einstellungen,
  Oberfläche beenden. Das Beenden des Hardwarediensts bleibt in Einstellungen.
- Profilmarkierung basiert auf der bestätigten Kurve. Schnellzugriffe verwenden
  gespeicherte Profile und halten die Gerätekennung beim Klick fest.
- Display-Stats können pausiert/fortgesetzt werden; Beleuchtung behält die zuletzt
  erfolgreiche eingeschaltete Konfiguration auch nach Ausschalten.
- Eigenes skalierbares Icon und StatusNotifier-Bitmap-Fallback; Demo trägt eigenen Titel.

Neue RPC-v2-Aktionen: pause_stats, resume_stats, lights_off, restore_lights (mit device).
Optionaler Gerätezustand rgb_last_on enthält erfolgreiche Beleuchtung pro Zone.

Geprüft: 49 Tests inklusive Socket-Integration. Echte COSMIC-Tray-Registrierung,
20 Ausblend-/Öffnungszyklen, simulierter Hostverlust und Wiederanzeige. D-Bus-Menü
mit Untermenüs ausgelesen und ein Profil-Event mit genau einem gebundenen Auftrag
bestätigt (Testdaten, keine Hardwareänderung).

Noch visuell zu bestätigen: Öffnen des Menüs durch physischen Klick auf das Icon,
RGB-/Display-Schnellaktionen am Gerät. Vollständige Hell-/Dunkel-/Tastaturabnahme
und echter Neustart des COSMIC-Panels stehen noch aus. Keine stabile Freigabe
für den weiterhin nicht abschließend geklärten ursprünglichen Rotationsabsturz.
