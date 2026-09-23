# Architektur und MVP – vor dem Code festgelegt

Eigenständiger Name: Boreal. Native GTK4/Libadwaita-Oberfläche mit Python/PyGObject, passend zu Wayland und COSMIC. Python wurde statt Rust gewählt, um die bestehende liquidctl-Python-API direkt und ohne eigene Protokollimplementierung zu verwenden. UI und Hardware laufen in getrennten Prozessen; die versionierte JSON-Schnittstelle erlaubt später eine Rust-UI.

GTK UI → privater Unix-Socket → serieller Benutzerdienst → isolierter liquidctl-Worker → HID / USB-Bulk / hwmon.

MVP:
1. Expliziter Demo- oder Hardwaremodus; Geräteauswahl per stabiler Seriennummer (sonst nur Sitzungsadresse). Automatische Übernahme ausschließlich nach Opt-in sowie Identitäts-, Firmware- und Verriegelungsprüfung.
2. Nach ausdrücklichem Verbinden: Initialisierung, sichere native Wasserkurven, Telemetrie. Fähigkeiten bestimmen verfügbare Aktionen.
3. Drei Presets, speicherbare eigene Pumpen-/Lüfterkurven, visualisierte Vorschau; beide Kanäle vor dem ersten Schreiben validieren.
4. LCD: Bild, GIF, native Wassertemperatur, Helligkeit, Rotation. Optional CPU/GPU/Wasser-Statistikbilder in begrenzter Frequenz. RGB nur für geprüfte Kanäle.
5. XDG-Autostart, optionaler StatusNotifier-Tray, systemd-Benutzerdienst, rotierende Logs und sichtbare Fehler.
6. Tests für Validierung, Teilfehler, Timeouts, Geräteidentität, RPC und Demoabläufe.

Sicherheitsentscheidungen:
- Kurven laufen auf dem Gerät, keine CPU-abhängige Software-PWM-Regelung im MVP. Pumpenminimum 60%, Lüfterminimum 30%, 100% spätestens bei 50°C. Diese konservativen App-Grenzen ersetzen keine thermische Prüfung am PC.
- Bei fehlender/ungültiger Telemetrie, Pumpenstillstand oder ≥50°C: 100%-Kurven best effort, Fehler verriegeln, erneutes Verbinden erforderlich. Bei verlorenem USB-Zugriff kann kein Schreib-Fallback garantiert werden.
- Worker mit Zeitlimit; Dienst und UI bleiben fehlertolerant. Ein Lock verhindert mehrere Boreal-Hardwaredienste. Andere Programme lassen sich dadurch nicht sperren.
- Ein serieller Hardwarepfad; keine automatischen Schreib-Retries für LCD. Nach Disconnect/Suspend wird nur bei aktiviertem, eindeutig zugeordnetem und unverriegeltem Gerät wiederhergestellt; zunächst entsteht der sichere Attach-Zustand.
- Kein Root-Dienst. Socket 0600 im privaten Laufzeitordner, gleicher UID, begrenzte JSON-Nachrichten, keine Shellausführung aus RPC.
- Profile atomar gespeichert, keine Gerätezuweisung automatisch angewandt. Log enthält Resultat/Fehler, kein roher USB-Dump.

Grenzen des MVP: Keine Firmwareupdates, Mainboard-PWM-/ARGB-Schreibzugriffe, 2023-Elite-Freigabe, manuell implementierten Elite-RGB-Pakete oder vollständige CAM-Parität. Hardwarekompatibilität bleibt bis zu Tests am realen Modell unbestätigt. Benutzer muss nach Dienstneustart/Reconnect bewusst verbinden; Autostart ist keine automatische Profilübernahme.

## Hardware-Nachtrag

Die erste Abnahme an einer echten Elite V2 / Firmware 1.2.0 ist im [Hardwarebericht](HARDWARE-ELITE-V2.md) dokumentiert. Die oben beschriebenen Hardwarevorbehalte gelten weiterhin für nicht getestete Funktionen und Varianten.
