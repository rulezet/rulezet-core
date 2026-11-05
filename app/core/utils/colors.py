"""Colours: the text colour readable on a given background (badges with a user-chosen colour).
Same rule as app/static/js/utils/color.js (keep both in step)."""
import re

LIGHT_LUMINANCE = 0.4   # relative luminance above which a background is "light"
_HEX = re.compile(r'^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')


def readable_text_color(background, dark='#000', light='#fff'):
    """'#000' on a light background (white, yellow, light grey…), '#fff' on a dark one.
    WCAG relative luminance above LIGHT_LUMINANCE; anything that is not a hex colour gets the light text."""
    m = _HEX.match((background or '').strip())
    if not m:
        return light
    h = m.group(1)
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)

    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(int(h[i:i + 2], 16)) for i in (0, 2, 4))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    # white kept on mid tones (Bootstrap blue, purple, green…), black only on really light colours
    return dark if lum > LIGHT_LUMINANCE else light
