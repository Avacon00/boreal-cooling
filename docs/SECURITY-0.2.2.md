# Sicherheitsprüfung und Korrekturen in 0.2.2

Der vollständige statische Scan des Boreal-Quellstands 0.2.1 bestätigte zwei
lokale Befunde niedriger Schwere. Es wurden keine direkt aus dem Netzwerk
erreichbaren Schwachstellen gefunden.

## Medienimport

Vor 0.2.2 wurde ein ausgewählter Pfad nach einer Größenabfrage vollständig
kopiert. Ein als Bild angebotenes Spezialgerät oder eine während des Kopierens
wachsende Datei konnte dadurch mehr als die vorgesehenen 10 MiB schreiben.

0.2.2 öffnet die Quelle genau einmal, prüft den geöffneten Deskriptor als
reguläre Datei und erzwingt die Grenze während des Kopierens. Der Elternprozess
besitzt das temporäre Arbeitsverzeichnis und entfernt Teildaten auch nach einem
Timeout des Medienprozesses. Normale Dateien und symbolische Links auf reguläre
Dateien bleiben nutzbar; die gespeicherte Quelle für erneutes Zuschneiden bleibt
erhalten.

## Lokaler Laufzeitpfad

Der Ersatzpfad ohne XDG_RUNTIME_DIR prüfte früher nur den letzten Unterordner.
Ein anderer lokaler Benutzer konnte unter engen Race-Bedingungen einen zuvor
angelegten Elternordner austauschen. Außerdem folgte die Lockdatei symbolischen
Links und der Client prüfte die Identität des Socket-Servers nicht.

0.2.2 prüft den privaten Basisordner und seinen direkten Schutzkontext, öffnet
Lockdateien ohne Linkverfolgung und ohne Kürzung, validiert Typ, Eigentümer und
Linkanzahl und prüft die Server-UID vor dem ersten RPC-Schreibzugriff. Alte,
benutzereigene 0755-Fallbackordner und 0644-Lockdateien werden nach erfolgreicher
Typ-/Eigentümerprüfung sicher verschärft; fremde oder verlinkte Pfade werden
abgelehnt.

## Verifikation

Die Regressionstests decken Spezialdateien, wachsende Quellen, Timeout-Bereinigung,
normale Importe und erneutes Zuschneiden, fremde/verlinkte Laufzeitpfade,
Lock-Symlinks/Hardlinks, Altversionsmigration und eine fremde Socket-Server-UID
ab. Der vollständige Testlauf schließt die bestehende Socket-Integration und
Gerätesimulation ein. Die physische Kraken wurde für diese lokalen Dateisystem-
und IPC-Korrekturen nicht neu beschrieben.
