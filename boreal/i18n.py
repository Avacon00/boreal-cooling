"""Small gettext front end with a predictable German/English locale policy."""
from __future__ import annotations

import gettext as _gettext
import os
from pathlib import Path


SUPPORTED = ("de", "en")
_override = "system"
_language = "en"
_translation: _gettext.NullTranslations = _gettext.NullTranslations()


def system_language(environ=None):
    """Return German only for a German locale; English is the safe fallback."""
    environ = os.environ if environ is None else environ
    for key in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        raw = str(environ.get(key, "")).strip()
        if not raw:
            continue
        # LANGUAGE may contain a preference list such as de_DE:en_US.
        value = raw.split(":", 1)[0].split(".", 1)[0].split("@", 1)[0]
        code = value.split("_", 1)[0].lower()
        return "de" if code == "de" else "en"
    return "en"


def resolve_language(value="system", environ=None):
    if value not in ("system", *SUPPORTED):
        raise ValueError("Unbekannte Sprache")
    return system_language(environ) if value == "system" else value


def configure(value="system", environ=None):
    """Select the process translation. Existing widgets update after restart."""
    global _override, _language, _translation
    if value == "system" and environ is None:
        value = os.environ.get("BOREAL_LANGUAGE", value)
    language = resolve_language(value, environ)
    _override, _language = value, language
    os.environ["BOREAL_LANGUAGE"] = value
    localedir = Path(__file__).with_name("locale")
    try:
        _translation = _gettext.translation(
            "boreal", localedir=str(localedir), languages=[language]
        )
    except OSError:
        _translation = _gettext.NullTranslations()
    return language


def gettext(message):
    return _translation.gettext(message)


def current_language():
    return _language


def current_override():
    return _override


def profile_label(name):
    """Translate built-in names without changing stable persisted profile keys."""
    return gettext(name) if name in {
        "Leise", "Ausgewogen", "Leistung",
        "Leise – Test", "Ausgewogen – Test", "Leistung – Test",
    } else name


_ = gettext
configure()
