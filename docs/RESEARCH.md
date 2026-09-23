# Kraken unter Linux – Recherche vor Implementierung
Stand: 14.09.2026. Angaben sind Treiberfähigkeiten, keine Hardware-Freigabe dieser App.

| Familie | USB PID (VID 1e71) | liquidctl | Schnittstellen / Grenze |
|---|---|---|---|
| X42/X52/X62/X72 | 170e | Kraken2 | USB HID, hwmon; Wasser/Pumpe/Lüfter/RGB; native Kurven ab Firmware 4 |
| X53/X63/X73 | 2007, 2014 | KrakenX3 | HID/hwmon; Wasser/Pumpe/RGB, **kein Lüfterkanal**, kein LCD |
| Z53/Z63/Z73 | 3008 | KrakenZ3 | HID/hwmon, USB-Bulk für LCD (320²), Lüfter, externes RGB |
| Kraken Standard 2023 | 300e | KrakenZ3, ab 1.14 | LCD 240²; GIF mit Firmware 2.x eingeschränkt |
| Kraken Elite 2023 | 300c | KrakenZ3, ab 1.14 | LCD 640²; Upstream beschreibt Gerät als broken: im MVP gesperrt |
| Elite RGB 2024 | 3012 | KrakenZ3, ab 1.15 | LCD 640²; RGB-Kanäle im geprüften Upstream leer |
| Plus 2024 (teils 2025 vermarktet) | 3014 | KrakenZ3, ab 1.16 | LCD 240²; offene Berichte über Upload-Timeouts |
| Core 2025 | kein eigener USB-Endpunkt | kein Kraken-Treiber | Mainboard DC/PWM/ARGB; kein LCD. Pumpe laut NZXT immer 100%. |
| M22 / 120 / ältere X | außerhalb MVP | teils separate Treiber | Nicht mit X3/Z3-Kühlfunktionen gleichsetzen |

Primärquellen:
- [liquidctl Modell-/Versionsübersicht](https://github.com/liquidctl/liquidctl)
- [X3/Z3/2023/2024 Anleitung](https://github.com/liquidctl/liquidctl/blob/main/docs/kraken-x3-z3-guide.md)
- [Treiber und PID-/Kanaldefinitionen](https://github.com/liquidctl/liquidctl/blob/main/liquidctl/driver/kraken3.py)
- [X2/M22](https://github.com/liquidctl/liquidctl/blob/main/docs/kraken-x2-m2-guide.md)
- [Linux hwmon nzxt-kraken3](https://docs.kernel.org/hwmon/nzxt-kraken3.html)
- [OpenKraken](https://github.com/davidboulay/OpenKraken) und [RGB-Protokollnotizen](https://github.com/davidboulay/OpenKraken/blob/main/PROTOCOL.md)
- [2023 Firmwareproblem #631](https://github.com/liquidctl/liquidctl/issues/631)
- [Plus LCD-Timeout #908](https://github.com/liquidctl/liquidctl/issues/908)
- [NZXT Core-Anschlüsse](https://support.nzxt.com/hc/en-us/articles/41097959681435-Is-the-Kraken-Core-compatible-with-NZXT-CAM)
- [NZXT Core Pumpeneinstellung](https://support.nzxt.com/hc/en-us/articles/41139760146587-Installing-the-Kraken-Core-BIOS-Setup-and-Control)

Folgerungen: Fähigkeiten werden zusätzlich gegen den installierten Treiber geprüft. Keine pauschale Elite/Plus-RGB-Zusage und keine unbekannten USB-Pakete. OpenKraken dient als Referenz; sein zusätzlicher RGB-Pfad wird nicht übernommen. Kein erzwungener Direct-Access und kein Ablösen von Kernel-Treibern. Fehlende hwmon-Schreibrechte werden als Fehler gemeldet. USB-Bulk benötigt neben hidraw eigene Rechte. Keine parallele Steuerung durch CAM, CoolerControl, OpenRGB oder OpenKraken.
