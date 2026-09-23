"""Pure color conversion shared by native controls and tests."""
import colorsys
import re
from .i18n import _


def parse_hex(value):
    value=value.strip().removeprefix('#')
    if not re.fullmatch('[0-9a-fA-F]{6}',value):
        raise ValueError(_('Bitte sechs HEX-Zeichen eingeben, zum Beispiel #6CE5C0'))
    return tuple(int(value[i:i+2],16)/255 for i in (0,2,4))


def hsv_hex(h,s,v=1):
    return ''.join(f'{round(c*255):02X}' for c in colorsys.hsv_to_rgb(h%1,s,v))
