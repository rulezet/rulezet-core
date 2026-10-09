/**
 * render.js — drawing helpers shared by the map and the levels: glyphs,
 * glowing shapes, the parallax star background and the world nebulas.
 */
import { W, H, TAU, FA } from './data.js';
import { tr } from './i18n.js';

const FA_FONT = "'Font Awesome 6 Free'";
let faReady = false;
if (typeof document !== 'undefined' && document.fonts && document.fonts.load) {
    document.fonts.load(`900 32px ${FA_FONT}`).then(() => { faReady = true; }).catch(() => {});
}

export function glyph(ctx, name, x, y, size, color, alpha = 1) {
    if (!faReady || !name || !FA[name]) return false;
    ctx.save();
    ctx.globalAlpha *= alpha;
    ctx.font = `900 ${size}px ${FA_FONT}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = color;
    ctx.fillText(FA[name], x, y + 1);
    ctx.restore();
    return true;
}

export function circle(ctx, x, y, r, fill, stroke = null, lw = 2) {
    ctx.beginPath();
    ctx.arc(x, y, Math.max(0, r), 0, TAU);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); }
}

export function poly(ctx, x, y, r, sides, rot, fill, stroke = null, lw = 2) {
    ctx.beginPath();
    for (let i = 0; i < sides; i++) {
        const a = rot + (i / sides) * TAU;
        const px = x + Math.cos(a) * r, py = y + Math.sin(a) * r;
        i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
    }
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); }
}

/** Soft radial glow (cheaper than shadowBlur) */
export function glow(ctx, x, y, r, color, alpha = 0.35) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, hexA(color, alpha));
    g.addColorStop(1, hexA(color, 0));
    ctx.fillStyle = g;
    ctx.fillRect(x - r, y - r, r * 2, r * 2);
}

export function hexA(hex, a) {
    if (!hex || hex[0] !== '#') return hex;
    const n = hex.length === 4
        ? hex.slice(1).split('').map(c => parseInt(c + c, 16))
        : [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
    return `rgba(${n[0]},${n[1]},${n[2]},${a})`;
}

export function text(ctx, str, x, y, { size = 16, color = '#fff', align = 'center', weight = 800, alpha = 1, font = 'system-ui, sans-serif', baseline = 'middle' } = {}) {
    str = tr(str);
    ctx.save();
    ctx.globalAlpha *= alpha;
    ctx.font = `${weight} ${size}px ${font}`;
    ctx.textAlign = align;
    ctx.textBaseline = baseline;
    ctx.fillStyle = color;
    ctx.fillText(str, x, y);
    ctx.restore();
}

// ── Background: 3 parallax star layers + drifting dust ─────────────────
export function makeStars(seed = 1) {
    let s = seed;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    const layers = [0.15, 0.35, 0.7].map((speed, li) => Array.from({ length: 70 - li * 15 }, () => ({
        x: rnd() * W, y: rnd() * H, r: 0.4 + rnd() * (0.6 + li * 0.7), tw: rnd() * TAU, speed,
    })));
    return layers;
}

export function drawBackground(ctx, stars, t, theme, drift = { x: 0, y: 0 }, image = null) {
    ctx.fillStyle = theme.bg;
    ctx.fillRect(0, 0, W, H);
    if (image && image.complete && image.naturalWidth) {
        ctx.save(); ctx.globalAlpha = 0.28; ctx.drawImage(image, 0, 0, W, H); ctx.restore();
    }
    // nebula clouds in the world's colours
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const clouds = [[0.2, 0.3, 420], [0.75, 0.65, 380], [0.55, 0.15, 300]];
    clouds.forEach(([cx, cy, r], i) => {
        const x = cx * W + Math.sin(t * 0.0003 + i) * 40;
        const y = cy * H + Math.cos(t * 0.00025 + i * 2) * 30;
        glow(ctx, x, y, r, i % 2 ? theme.hue2 : theme.hue, 0.13);
    });
    ctx.restore();
    stars.forEach(layer => layer.forEach(st => {
        const x = ((st.x - drift.x * st.speed) % W + W) % W;
        const y = ((st.y - drift.y * st.speed) % H + H) % H;
        const a = 0.45 + 0.55 * Math.abs(Math.sin(st.tw + t * 0.002));
        ctx.fillStyle = `rgba(255,255,255,${a * (0.4 + st.speed)})`;
        ctx.fillRect(x, y, st.r, st.r);
    }));
}

/** Player ship — a detection rule shaped like a dart */
export function drawShip(ctx, x, y, angle, skin, { thrust = 0, alpha = 1, t = 0, scale = 1 } = {}) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.scale(scale, scale);
    ctx.globalAlpha *= alpha;
    glow(ctx, 0, 0, 34, skin.glow, 0.35);
    if (thrust > 0) {
        const fl = 10 + thrust * 14 + Math.sin(t * 0.6) * 4;
        ctx.beginPath(); ctx.moveTo(-12, -6); ctx.lineTo(-12 - fl, 0); ctx.lineTo(-12, 6); ctx.closePath();
        ctx.fillStyle = skin.flame; ctx.fill();
    }
    ctx.beginPath();
    ctx.moveTo(20, 0); ctx.lineTo(-12, -13); ctx.lineTo(-6, 0); ctx.lineTo(-12, 13); ctx.closePath();
    ctx.fillStyle = skin.hull; ctx.fill();
    ctx.strokeStyle = skin.glow; ctx.lineWidth = 2; ctx.stroke();
    ctx.beginPath(); ctx.arc(4, 0, 3.5, 0, TAU); ctx.fillStyle = skin.glow; ctx.fill();
    ctx.restore();
}
