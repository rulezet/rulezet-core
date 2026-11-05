/**
 * color.js — the text colour readable on a background chosen by a user (organisation badges…).
 * Same rule as app/core/utils/colors.py (keep both in step): '#000' on a light colour, '#fff' on a dark one.
 */
export function readableTextColor(background, dark = '#000', light = '#fff') {
    const m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec((background || '').trim());
    if (!m) return light;
    let h = m[1];
    if (h.length === 3) h = h.split('').map(c => c + c).join('');
    const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
    const [r, g, b] = [0, 2, 4].map(i => lin(parseInt(h.slice(i, i + 2), 16)));
    const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    return lum > 0.4 ? dark : light;   // white kept on mid tones, black only on really light colours
}
