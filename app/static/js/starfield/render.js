/**
 * render.js — drawing helpers shared by the map and the levels: glyphs,
 * glowing shapes, the parallax star background, the world nebulas and
 * planets, the network grid of open sectors, rocks and the ships.
 */
import { W, H, TAU, FA } from './data.js';
import { tr } from './i18n.js';

const FA_FONT = "'Font Awesome 7 Free'";   // the family name of fontawesome-7.3.1/css/solid.css
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
    if (!(r > 0) || !Number.isFinite(x) || !Number.isFinite(y)) return;
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
    return `rgba(${n[0]},${n[1]},${n[2]},${Math.max(0, Math.min(1, a))})`;
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

// ── Background: 4 parallax star layers + nebulas + the world's planet ──
export function makeStars(seed = 1) {
    let s = seed;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    return [0.08, 0.15, 0.35, 0.7].map((speed, li) => Array.from({ length: 90 - li * 18 }, () => ({
        x: rnd() * W, y: rnd() * H, r: 0.4 + rnd() * (0.5 + li * 0.6), tw: rnd() * TAU, speed,
        tint: rnd() < 0.15 ? (rnd() < 0.5 ? '#9fc4ff' : '#ffd9a8') : null,
    })));
}

// one planet per world, far away (it barely moves with the camera)
const PLANETS = {
    ocean: { x: 0.82, y: 0.2, r: 120, ring: false, bands: 3 },
    gas: { x: 0.15, y: 0.78, r: 150, ring: true, bands: 6 },
    lava: { x: 0.85, y: 0.8, r: 110, ring: false, bands: 2, cracks: true },
    ice: { x: 0.12, y: 0.18, r: 100, ring: false, bands: 2 },
    core: { x: 0.5, y: 0.12, r: 90, ring: true, bands: 0, pulse: true },
    desert: { x: 0.86, y: 0.22, r: 130, ring: false, bands: 4 },
    neon: { x: 0.12, y: 0.8, r: 110, ring: true, bands: 0, grid: true },
    ringed: { x: 0.82, y: 0.78, r: 120, ring: true, bands: 3 },
    station: { x: 0.85, y: 0.2, r: 90, ring: true, bands: 0, station: true },
    asteroid: { x: 0.15, y: 0.2, r: 80, ring: false, bands: 0, cracks: true },
    crystal: { x: 0.82, y: 0.25, r: 110, ring: false, bands: 0, facets: true },
    canyon: { x: 0.18, y: 0.82, r: 140, ring: false, bands: 5 },
    shattered: { x: 0.8, y: 0.2, r: 110, ring: false, bands: 0, broken: true },
    bio: { x: 0.5, y: 0.85, r: 150, ring: false, bands: 0, spots: true },
};

export function drawPlanet(ctx, theme, t, px = 0, py = 0, at = null) {
    const pl = PLANETS[theme.planet];
    if (!pl) return;
    const x = at ? at.x : pl.x * W - px, y = at ? at.y : pl.y * H - py, r = at ? at.r : pl.r;
    ctx.save();
    glow(ctx, x, y, r * 1.9, theme.hue, 0.18);
    const g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.35, r * 0.1, x, y, r);
    g.addColorStop(0, hexA(theme.hue, 0.95)); g.addColorStop(0.55, hexA(theme.hue2, 0.95)); g.addColorStop(1, 'rgba(2,3,10,0.98)');
    if (pl.ring) {           // the back half of the ring, behind the planet
        ctx.save(); ctx.translate(x, y); ctx.rotate(-0.35); ctx.scale(1, 0.28);
        ctx.beginPath(); ctx.arc(0, 0, r * 1.75, Math.PI, TAU); ctx.strokeStyle = hexA(theme.hue, 0.3); ctx.lineWidth = r * 0.08; ctx.stroke();
        ctx.restore();
    }
    if (pl.broken) {
        for (let i = 0; i < 6; i++) {
            const a = i * TAU / 6 + t * 0.00005, off = r * 0.08 + Math.sin(t * 0.0004 + i) * r * 0.05;
            const cx = x + Math.cos(a + TAU / 12) * off, cy = y + Math.sin(a + TAU / 12) * off;
            ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, r * 0.92, a, a + TAU / 6 - 0.06); ctx.closePath();
            ctx.fillStyle = g; ctx.fill();
        }
    } else {
        ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fillStyle = g; ctx.fill();
        ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.clip();
        for (let i = 0; i < pl.bands; i++) {
            // soft cloud bands: a vertical gradient, no hard edge
            const by = y - r + (i + 0.5) * (2 * r / pl.bands) + Math.sin(t * 0.0005 + i) * 4, bh = r / (pl.bands * 0.9);
            const bg = ctx.createLinearGradient(0, by - bh / 2, 0, by + bh / 2);
            const c = i % 2 ? theme.hue : '#ffffff';
            bg.addColorStop(0, hexA(c, 0)); bg.addColorStop(0.5, hexA(c, 0.07)); bg.addColorStop(1, hexA(c, 0));
            ctx.fillStyle = bg; ctx.fillRect(x - r, by - bh / 2, 2 * r, bh);
        }
        if (pl.cracks) for (let i = 0; i < 5; i++) {
            ctx.beginPath(); const a = i * 1.3; ctx.moveTo(x + Math.cos(a) * r * 0.2, y + Math.sin(a) * r * 0.2);
            ctx.lineTo(x + Math.cos(a + 0.3) * r * 0.7, y + Math.sin(a + 0.3) * r * 0.7); ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r);
            ctx.strokeStyle = hexA('#ffd166', 0.35 + 0.15 * Math.sin(t * 0.003 + i)); ctx.lineWidth = 2; ctx.stroke();
        }
        if (pl.grid) {
            ctx.strokeStyle = hexA(theme.hue, 0.22); ctx.lineWidth = 1;
            for (let i = -4; i <= 4; i++) { ctx.beginPath(); ctx.moveTo(x - r, y + i * r / 4); ctx.lineTo(x + r, y + i * r / 4); ctx.moveTo(x + i * r / 4, y - r); ctx.lineTo(x + i * r / 4, y + r); ctx.stroke(); }
        }
        if (pl.facets) for (let i = 0; i < 6; i++) { ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(i * TAU / 6) * r, y + Math.sin(i * TAU / 6) * r); ctx.strokeStyle = hexA('#ffffff', 0.12); ctx.lineWidth = 2; ctx.stroke(); }
        if (pl.spots) for (let i = 0; i < 9; i++) { const a = i * 2.1, d = r * (0.2 + (i % 4) * 0.18); circle(ctx, x + Math.cos(a) * d, y + Math.sin(a) * d, r * 0.09, hexA('#f0c8ff', 0.25)); }
        if (pl.station) { ctx.strokeStyle = hexA('#ffffff', 0.3); ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(x, y, r * 0.6, 0, TAU); ctx.stroke(); }
        // the night side
        const sh = ctx.createLinearGradient(x - r, y - r, x + r, y + r);
        sh.addColorStop(0.45, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(0,0,0,0.55)');
        ctx.fillStyle = sh; ctx.fillRect(x - r, y - r, 2 * r, 2 * r);
        ctx.restore();
        if (pl.pulse) circle(ctx, x, y, r + 8 + Math.sin(t * 0.004) * 4, null, hexA(theme.hue, 0.4), 2);
    }
    if (pl.ring) {           // the front half of the ring
        ctx.save(); ctx.translate(x, y); ctx.rotate(-0.35); ctx.scale(1, 0.28);
        ctx.beginPath(); ctx.arc(0, 0, r * 1.75, 0, Math.PI); ctx.strokeStyle = hexA(theme.hue, 0.45); ctx.lineWidth = r * 0.08; ctx.stroke();
        ctx.restore();
    }
    ctx.restore();
}

export function drawBackground(ctx, stars, t, theme, drift = { x: 0, y: 0 }, image = null, dim = false) {
    ctx.fillStyle = theme.bg;
    ctx.fillRect(0, 0, W, H);
    if (image && image.complete && image.naturalWidth) {
        ctx.save(); ctx.globalAlpha = 0.24; ctx.drawImage(image, 0, 0, W, H); ctx.restore();
    }
    // nebula clouds in the world's colours
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const clouds = [[0.2, 0.3, 420], [0.75, 0.65, 380], [0.55, 0.15, 300], [0.4, 0.85, 260]];
    clouds.forEach(([cx, cy, r], i) => {
        const span = W + 600, spanY = H + 600;
        const x = ((cx * W - drift.x * 0.05 + Math.sin(t * 0.0003 + i) * 40) % span + span) % span - 300;
        const y = ((cy * H - drift.y * 0.05 + Math.cos(t * 0.00025 + i * 2) * 30) % spanY + spanY) % spanY - 300;
        glow(ctx, x, y, r, i % 2 ? theme.hue2 : theme.hue, 0.12);
    });
    ctx.restore();
    // in a level the planet stays in the back: dimmed, so the fight reads well
    ctx.save(); if (dim) ctx.globalAlpha = 0.45;
    drawPlanet(ctx, theme, t, (drift.x * 0.02) % 200, (drift.y * 0.02) % 120);
    ctx.restore();
    stars.forEach(layer => layer.forEach(st => {
        const x = ((st.x - drift.x * st.speed) % W + W) % W;
        const y = ((st.y - drift.y * st.speed) % H + H) % H;
        const a = 0.45 + 0.55 * Math.abs(Math.sin(st.tw + t * 0.002));
        ctx.fillStyle = st.tint ? hexA(st.tint, a * (0.4 + st.speed)) : `rgba(255,255,255,${a * (0.4 + st.speed)})`;
        ctx.fillRect(x, y, st.r, st.r);
    }));
}

/** Open sectors: a faint network grid in world space, so you feel the ship move */
export function drawGrid(ctx, cam, aw, ah, hue, t) {
    const step = 160;
    ctx.save();
    ctx.strokeStyle = hexA(hue, 0.07); ctx.lineWidth = 1;
    const x0 = Math.floor(cam.x / step) * step, y0 = Math.floor(cam.y / step) * step;
    ctx.beginPath();
    for (let x = x0; x < cam.x + W + step; x += step) { if (x < 0 || x > aw) continue; ctx.moveTo(x, Math.max(0, cam.y)); ctx.lineTo(x, Math.min(ah, cam.y + H)); }
    for (let y = y0; y < cam.y + H + step; y += step) { if (y < 0 || y > ah) continue; ctx.moveTo(Math.max(0, cam.x), y); ctx.lineTo(Math.min(aw, cam.x + W), y); }
    ctx.stroke();
    // nodes at the crossings, some of them blinking like live hosts
    for (let x = x0; x < cam.x + W + step; x += step) for (let y = y0; y < cam.y + H + step; y += step) {
        if (x < 0 || y < 0 || x > aw || y > ah) continue;
        const h = ((x * 73856093) ^ (y * 19349663)) >>> 0;
        if (h % 7 === 0) { ctx.fillStyle = hexA(hue, 0.25 + 0.2 * Math.sin(t * 0.05 + h)); ctx.fillRect(x - 2, y - 2, 4, 4); }
    }
    ctx.restore();
}

/** A drifting rock of corrupted data: blocks ships and bullets */
export function drawRock(ctx, k, theme) {
    ctx.save();
    ctx.beginPath();
    k.verts.forEach((v, i) => {
        const a = k.rot + i / k.verts.length * TAU;
        const x = k.x + Math.cos(a) * k.r * v, y = k.y + Math.sin(a) * k.r * v;
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    });
    ctx.closePath();
    const g = ctx.createRadialGradient(k.x - k.r * 0.4, k.y - k.r * 0.4, k.r * 0.1, k.x, k.y, k.r);
    g.addColorStop(0, '#3a4258'); g.addColorStop(1, '#0b0e18');
    ctx.fillStyle = g; ctx.fill();
    ctx.strokeStyle = hexA(theme.hue, 0.45); ctx.lineWidth = 2; ctx.stroke();
    ctx.clip();
    for (let i = 0; i < 3; i++) {
        const a = k.rot * 2 + i * 2.1, d = k.r * 0.45;
        circle(ctx, k.x + Math.cos(a) * d, k.y + Math.sin(a) * d, k.r * 0.16, 'rgba(0,0,0,0.35)', 'rgba(255,255,255,0.06)', 1);
    }
    ctx.fillStyle = hexA(theme.hue, 0.25);
    ctx.fillRect(k.x - k.r * 0.6, k.y + Math.sin(k.rot * 3) * k.r * 0.3, k.r * 1.2, 1.5);
    ctx.restore();
}

// ── Player ship — a detection rule; every engine has its own silhouette ──
const HULLS = {
    dart:   [[20, 0], [-12, -13], [-6, 0], [-12, 13]],
    wing:   [[18, 0], [2, -6], [-10, -17], [-6, -4], [-12, 0], [-6, 4], [-10, 17], [2, 6]],
    arrow:  [[24, 0], [-4, -9], [-14, -9], [-8, 0], [-14, 9], [-4, 9]],
    ring:   [[20, 0], [-10, -11], [-5, 0], [-10, 11]],
    scroll: [[22, 0], [8, -7], [-14, -7], [-10, 0], [-14, 7], [8, 7]],
    shield: [[18, 0], [10, -12], [-10, -14], [-14, 0], [-10, 14], [10, 12]],
    dish:   [[16, 0], [6, -16], [-2, -8], [-12, -10], [-8, 0], [-12, 10], [-2, 8], [6, 16]],
    star:   [[22, 0], [2, -5], [-6, -16], [-6, -4], [-14, 0], [-6, 4], [-6, 16], [2, 5]],
    hex:    [[18, 0], [9, -14], [-9, -14], [-15, 0], [-9, 14], [9, 14]],
    heavy:  [[20, -4], [20, 4], [4, 15], [-14, 15], [-10, 0], [-14, -15], [4, -15]],
    lance:  [[28, 0], [0, -6], [-12, -12], [-8, 0], [-12, 12], [0, 6]],
    split:  [[20, -6], [-10, -16], [-6, -2], [-12, 0], [-6, 2], [-10, 16], [20, 6], [4, 0]],
    orb:    null,
    blade:  [[24, 0], [-2, -4], [-14, -14], [-8, -2], [-14, 0], [-8, 2], [-14, 14], [-2, 4]],
    cross:  [[18, -4], [18, 4], [4, 4], [4, 16], [-4, 16], [-4, 4], [-14, 4], [-14, -4], [-4, -4], [-4, -16], [4, -16], [4, -4]],
};

export function drawShip(ctx, x, y, angle, skin, { thrust = 0, alpha = 1, t = 0, scale = 1 } = {}) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.scale(scale, scale);
    ctx.globalAlpha *= alpha;
    glow(ctx, 0, 0, 36, skin.glow, 0.35);
    if (thrust > 0) {
        const fl = 10 + thrust * 16 + Math.sin(t * 0.6) * 4;
        ctx.save(); ctx.globalCompositeOperation = 'lighter';
        ctx.beginPath(); ctx.moveTo(-11, -6); ctx.lineTo(-11 - fl, 0); ctx.lineTo(-11, 6); ctx.closePath();
        ctx.fillStyle = skin.flame; ctx.fill();
        ctx.beginPath(); ctx.moveTo(-11, -3); ctx.lineTo(-11 - fl * 0.55, 0); ctx.lineTo(-11, 3); ctx.closePath();
        ctx.fillStyle = '#ffffff'; ctx.fill();
        ctx.restore();
    }
    const hull = HULLS[skin.shape || 'dart'];
    ctx.beginPath();
    if (hull) hull.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
    else ctx.arc(0, 0, 13, 0, TAU);
    ctx.closePath();
    const g = ctx.createLinearGradient(-14, -14, 14, 14);
    g.addColorStop(0, skin.hull); g.addColorStop(1, hexA(skin.glow, 0.85));
    ctx.fillStyle = g; ctx.fill();
    ctx.strokeStyle = skin.glow; ctx.lineWidth = 2; ctx.stroke();
    if (skin.shape === 'ring') { ctx.beginPath(); ctx.arc(-2, 0, 18, -1.1, 1.1); ctx.strokeStyle = hexA(skin.glow, 0.8); ctx.lineWidth = 2.5; ctx.stroke(); }
    if (skin.shape === 'orb') { ctx.beginPath(); ctx.arc(0, 0, 19, t * 0.05, t * 0.05 + 4); ctx.strokeStyle = hexA(skin.glow, 0.7); ctx.lineWidth = 2; ctx.stroke(); }
    // cockpit
    ctx.beginPath(); ctx.arc(4, 0, 3.5, 0, TAU); ctx.fillStyle = '#ffffff'; ctx.fill();
    ctx.beginPath(); ctx.arc(4, 0, 2, 0, TAU); ctx.fillStyle = skin.glow; ctx.fill();
    ctx.restore();
}
