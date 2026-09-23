"""Bounded media import and read-only host sensors."""
import math
import warnings
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageSequence, ImageOps, ImageColor
from .i18n import _

Image.MAX_IMAGE_PIXELS = 16_000_000


def sensors(root=Path("/sys/class/hwmon")):
    result = {}
    for hw in sorted(root.glob("hwmon*")):
        try:
            name = (hw / "name").read_text().strip()
            category = "CPU" if name in ("k10temp", "coretemp", "zenpower") else (
                "GPU" if name in ("amdgpu", "nouveau", "nvidia") else None)
            if not category:
                continue
            values = []
            for sensor in hw.glob("temp*_input"):
                try:
                    value = float(sensor.read_text()) / 1000
                    if math.isfinite(value) and 0 < value < 130:
                        values.append(value)
                except (OSError, ValueError):
                    pass
            if values:
                result[category] = round(max(values), 1)
        except OSError:
            pass
    return result


def fit_image(image, size, options=None):
    options = options or {}
    fit = options.get('fit', 'contain')
    if fit not in ('contain', 'cover'):
        raise ValueError(_('Einpassen oder Zuschneiden wählen'))
    zoom = float(options.get('zoom', 1))
    x, y = float(options.get('x', .5)), float(options.get('y', .5))
    if not 1 <= zoom <= 3 or not 0 <= x <= 1 or not 0 <= y <= 1:
        raise ValueError(_('Ungültiger Bildausschnitt'))
    background = ImageColor.getrgb(options.get('background', '#101d29'))
    image = ImageOps.exif_transpose(image).convert('RGBA')
    scale = (max if fit == 'cover' else min)(size / image.width, size / image.height) * zoom
    image = image.resize((max(1, round(image.width*scale)), max(1, round(image.height*scale))), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (size, size), background)
    canvas.alpha_composite(image, (round((size-image.width)*x), round((size-image.height)*y)))
    return canvas.convert('RGB')


def prepare_media(path, mode, size, destination, options=None):
    source = Path(path)
    if not source.is_file() or source.stat().st_size > 10 * 1024 * 1024:
        raise ValueError(_("Bitte eine Bilddatei bis 10 MiB auswählen"))
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(source) as im:
            if im.format not in ("PNG", "JPEG", "GIF", "WEBP"):
                raise ValueError(_("Erlaubt: PNG, JPEG, GIF, WebP"))
            if mode == "gif" and im.format != "GIF":
                raise ValueError(_("GIF-Modus benötigt eine GIF-Datei"))
            if mode == "static":
                fit_image(im, size, options).save(destination, "PNG")
            else:
                count = getattr(im, "n_frames", 1)
                if count > 120 or count * max(size * size, im.width * im.height) > 24_000_000:
                    raise ValueError(_("GIF ist zu lang (max. 120 Frames / 24 Mio. Ausgabepixel)"))
                frames, durations = [], []
                for frame in ImageSequence.Iterator(im):
                    frames.append(fit_image(frame, size, options))
                    durations.append(max(40, min(10000, frame.info.get("duration", 100))))
                frames[0].save(destination, "GIF", save_all=True, append_images=frames[1:],
                               duration=durations, loop=0)
    return str(destination)


def stats_image(size, status, host, destination, options=None):
    options = options or {}
    template = options.get('template', 'overview')
    if template not in ('single', 'dual', 'overview'):
        raise ValueError(_('Unbekannte LCD-Vorlage'))
    scale = float(options.get('font_scale', 1))
    if not .7 <= scale <= 1.5:
        raise ValueError(_('Schriftgröße außerhalb des Bereichs'))
    background = options.get('background', '#101d29')
    accent = options.get('accent', '#6ce5c0')
    ImageColor.getrgb(background); ImageColor.getrgb(accent)
    im = Image.new("RGB", (size, size), background)
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", round(size / 14 * scale))
        title = ImageFont.truetype("DejaVuSans.ttf", size // 10)
    except OSError:
        font = title = ImageFont.load_default()
    draw.ellipse((8, 8, size - 8, size - 8), outline=accent, width=max(2, size // 100))
    draw.text((size // 2, size * .22), "BOREAL", anchor="mm", font=title, fill=accent)
    liquid = status.get("Liquid temperature", {}).get("value")
    available = {'liquid': (_('Wasser'), liquid), 'CPU': ('CPU', host.get('CPU')), 'GPU': ('GPU', host.get('GPU'))}
    for sensor in host.get('_sensors', []):
        available[sensor['id']] = (sensor['label'], sensor['value'])
    selection = options.get('sensors', ['liquid', 'CPU', 'GPU'])
    if not isinstance(selection, list) or not 1 <= len(selection) <= 3:
        raise ValueError(_('Ein bis drei Sensoren auswählen'))
    rows = [available.get(key, (_('Sensor fehlt'), None)) for key in selection]
    rows = rows[:{'single': 1, 'dual': 2, 'overview': 3}[template]]
    for i, (label, value) in enumerate(rows):
        unit = options.get('unit', 'C')
        if unit not in ('C', 'F'):
            raise ValueError(_('Ungültige Temperatureinheit'))
        if value is not None and unit == 'F': value = value * 1.8 + 32
        text = f"{label[:16]}  {value:.1f} °{unit}" if value is not None else f"{label[:16]}  —"
        draw.text((size // 2, size * (.43 + i * .14)), text, anchor="mm", font=font, fill="white")
    im.save(destination, "PNG")
    return str(destination)


def sensor_records(root=Path('/sys/class/hwmon')):
    import hashlib
    import time
    result = []
    for hw in sorted(root.glob('hwmon*')):
        try:
            driver = (hw/'name').read_text().strip()
            category = 'CPU' if driver in ('k10temp','coretemp','zenpower') else ('GPU' if driver in ('amdgpu','nouveau','nvidia') else None)
            if not category: continue
            for sensor in sorted(hw.glob('temp*_input')):
                try:
                    value = float(sensor.read_text()) / 1000
                    if not math.isfinite(value) or not 0 < value < 130: continue
                    name = sensor.name.replace('_input','_label')
                    label = (hw/name).read_text().strip() if (hw/name).exists() else sensor.stem
                    stable = str((hw/'device').resolve()) + ':' + driver + ':' + sensor.name
                    key = hashlib.sha256(stable.encode()).hexdigest()[:16]
                    result.append(dict(id=key, category=category, label=f'{category} {label}', driver=driver,
                                       value=round(value,1), unit='°C', timestamp=time.time()))
                except (OSError,ValueError): pass
        except OSError: pass
    return result
