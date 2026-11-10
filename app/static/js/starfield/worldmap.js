/**
 * worldmap.js — the campaign map, one world at a time: levels as nodes on
 * a path, the ship travelling between them (Mario-world style), stars,
 * locks, the boss node, the secret honeypot branch and the gates to the
 * neighbouring worlds. The galaxy view (G) shows all sixteen worlds and
 * warps the ship to any world already open.
 */
import { W, H, TAU, WORLDS, ENEMIES, ACT2_FIRST_WORLD, levelDef } from './data.js';
import { circle, poly, glyph, glow, hexA, text, drawShip, drawPlanet } from './render.js';
import * as Save from './save.js';
import { Sfx } from './audio.js';
import { tr } from './i18n.js';

// Walking order on a world's path; 5 = the secret honeypot (branch off node 2)
const ORDER = [0, 1, 2, 5, 3, 4];

// Galaxy view: where each world sits (Act I on the first arc, Act II winding down)
const GALAXY = [
    [130, 200], [290, 150], [450, 205], [610, 155], [770, 210],
    [960, 175], [1130, 290], [980, 395], [800, 350], [620, 405], [440, 360], [260, 410],
    [140, 535], [330, 580], [540, 555], [790, 570],
];

export function createMap() {
    const M = {
        world: 0, node: 0, t: 0,
        ship: { x: 0, y: 0 }, moving: null, hover: null,
        drifters: [], galaxy: false, gSel: 0, gHover: null,
    };

    const nodePos = (w, i) => (i === 5 ? WORLDS[w].secret : WORLDS[w].nodes[i]);
    const reachable = (w, i) => (i === 5 ? Save.secretUnlocked(w) && Save.isUnlocked(w, 5) : Save.isUnlocked(w, i));

    function placeShip() { const [x, y] = nodePos(M.world, M.node); M.ship.x = x; M.ship.y = y; }

    function makeDrifters() {
        const pool = WORLDS[M.world].pool;
        M.drifters = Array.from({ length: 9 }, () => ({
            type: pool[Math.floor(Math.random() * pool.length)],
            x: Math.random() * W, y: Math.random() * H, a: Math.random() * TAU, s: 0.2 + Math.random() * 0.4,
        }));
    }

    M.enter = (world, node) => {
        M.world = world; M.node = node;
        if (!reachable(world, node)) M.node = 0;
        placeShip(); makeDrifters(); M.moving = null;
    };

    function travelTo(i) {
        if (i === M.node || !reachable(M.world, i)) { if (!reachable(M.world, i)) Sfx.deny(); return false; }
        const [x, y] = nodePos(M.world, i);
        M.moving = { from: { ...M.ship }, to: { x, y }, t: 0, dur: 26, node: i };
        Sfx.move();
        return true;
    }

    M.step = (dir) => {
        if (M.moving) return;
        let idx = ORDER.indexOf(M.node);
        for (let k = 0; k < ORDER.length; k++) {
            idx += dir;
            if (idx < 0 || idx >= ORDER.length) break;
            const cand = ORDER[idx];
            if (cand === 5 && !Save.secretUnlocked(M.world)) continue;
            if (travelTo(cand)) return;
            Sfx.deny(); return;
        }
        // walked off the end of the path → neighbouring world
        if (dir > 0 && M.node === 4 && M.world + 1 < WORLDS.length && Save.worldUnlocked(M.world + 1)) { M.changeWorld(M.world + 1, 0); return; }
        if (dir < 0 && M.node === 0 && M.world > 0) { M.changeWorld(M.world - 1, 4); return; }
        Sfx.deny();
    };

    M.changeWorld = (w, node) => {
        if (w < 0 || w >= WORLDS.length || !Save.worldUnlocked(w)) { Sfx.deny(); return; }
        M.enter(w, node ?? 0);
        M.onWorldChange && M.onWorldChange(w);
        Sfx.levelUp();
    };

    // ── Galaxy view ──
    M.openGalaxy = (v = !M.galaxy) => { M.galaxy = v; M.gSel = M.world; Sfx.move(); };
    M.galaxyStep = (dir) => {
        let s = M.gSel;
        for (let k = 0; k < WORLDS.length; k++) {
            s += dir;
            if (s < 0 || s >= WORLDS.length) { Sfx.deny(); return; }
            if (Save.worldUnlocked(s)) { M.gSel = s; Sfx.move(); return; }
        }
    };
    M.galaxyWarp = () => {
        const w = M.gSel;
        if (!Save.worldUnlocked(w)) { Sfx.deny(); return; }
        M.galaxy = false;
        if (w !== M.world) M.changeWorld(w, 0);
    };

    /** Mouse: hover + click a node (returns 'play' on a second click on the current node) */
    M.pointer = (mx, my, click) => {
        if (M.galaxy) {
            M.gHover = null;
            GALAXY.forEach(([x, y], i) => { if ((mx - x) ** 2 + (my - y) ** 2 < 36 ** 2) M.gHover = i; });
            if (click) {
                if (M.gHover !== null) { if (Save.worldUnlocked(M.gHover)) { M.gSel = M.gHover; M.galaxyWarp(); } else Sfx.deny(); }
            }
            return null;
        }
        M.hover = null;
        const list = [0, 1, 2, 3, 4, 5];
        for (const i of list) {
            if (i === 5 && !Save.secretUnlocked(M.world)) continue;
            const [x, y] = nodePos(M.world, i);
            if ((mx - x) ** 2 + (my - y) ** 2 < 38 ** 2) { M.hover = i; break; }
        }
        // world gates
        const gateR = M.world + 1 < WORLDS.length && (mx > W - 90 && my > H / 2 - 60 && my < H / 2 + 60);
        const gateL = M.world > 0 && (mx < 90 && my > H / 2 - 60 && my < H / 2 + 60);
        if (click) {
            if (M.hover !== null) {
                if (M.hover === M.node && !M.moving) return 'play';
                travelTo(M.hover);
            } else if (gateR) M.changeWorld(M.world + 1, 0);
            else if (gateL) M.changeWorld(M.world - 1, 4);
        }
        return null;
    };

    M.selected = () => ({ world: M.world, index: M.node, def: levelDef(M.world, M.node) });
    M.canPlay = () => !M.galaxy && !M.moving && reachable(M.world, M.node);

    M.update = () => {
        M.t++;
        if (M.moving) {
            const m = M.moving; m.t++;
            const k = Math.min(1, m.t / m.dur), e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
            M.ship.x = m.from.x + (m.to.x - m.from.x) * e;
            M.ship.y = m.from.y + (m.to.y - m.from.y) * e - Math.sin(k * Math.PI) * 30;
            if (k >= 1) { M.node = m.node; M.moving = null; M.onArrive && M.onArrive(M.node); }
        }
        for (const d of M.drifters) {
            d.x += Math.cos(d.a) * d.s; d.y += Math.sin(d.a) * d.s; d.a += Math.sin(M.t * 0.01 + d.x) * 0.01;
            if (d.x < -30) d.x = W + 30; if (d.x > W + 30) d.x = -30; if (d.y < -30) d.y = H + 30; if (d.y > H + 30) d.y = -30;
        }
    };

    function pathLine(ctx, a, b, open, color) {
        ctx.save();
        ctx.beginPath();
        const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2 - 40;
        ctx.moveTo(a[0], a[1]); ctx.quadraticCurveTo(mx, my, b[0], b[1]);
        ctx.lineWidth = open ? 6 : 3;
        ctx.strokeStyle = open ? hexA(color, 0.75) : 'rgba(255,255,255,0.18)';
        ctx.setLineDash(open ? [2, 12] : [6, 10]);
        ctx.lineCap = 'round';
        ctx.lineDashOffset = open ? -M.t * 0.6 : 0;
        ctx.stroke();
        ctx.restore();
    }

    const KIND_GLYPH = { keys: 'key', escort: 'database', capture: 'tower', pursuit: 'fileExport', dark: 'eyeSlash', purge: 'cube', gauntlet: 'shield', triage: 'filter', defend: 'server' };

    function drawGalaxy(ctx, skin) {
        ctx.save(); ctx.globalAlpha = 0.93; ctx.fillStyle = '#02030a'; ctx.fillRect(0, 0, W, H); ctx.restore();
        text(ctx, tr('GALAXY MAP'), W / 2, 40, { size: 26, color: '#fff' });
        text(ctx, tr('Click an open world or use the arrows and Enter to warp · G or Esc to close'), W / 2, 66, { size: 13, color: '#9fb0d8', weight: 600 });
        text(ctx, tr('ACT I'), 130, 110, { size: 12, color: '#ff6bd8', align: 'left' });
        text(ctx, tr('ACT II — THE DEEP GRAPH'), 960, 110, { size: 12, color: '#d77bff' });
        for (let i = 0; i + 1 < GALAXY.length; i++) {
            const open = Save.worldUnlocked(i + 1);
            ctx.save(); ctx.beginPath(); ctx.moveTo(...GALAXY[i]); ctx.lineTo(...GALAXY[i + 1]);
            ctx.setLineDash(open ? [3, 9] : [6, 10]); ctx.lineDashOffset = -M.t * 0.4;
            ctx.strokeStyle = open ? hexA(WORLDS[i + 1].hue, 0.7) : 'rgba(255,255,255,0.12)'; ctx.lineWidth = open ? 3 : 2; ctx.stroke(); ctx.restore();
        }
        GALAXY.forEach(([x, y], i) => {
            const w = WORLDS[i], open = Save.worldUnlocked(i);
            const r = i === WORLDS.length - 1 ? 34 : 26;
            const sel = i === M.gSel, hov = i === M.gHover;
            if (open) drawPlanet(ctx, w, M.t * 16, 0, 0, { x, y, r });
            else { circle(ctx, x, y, r, '#0b0e18', '#333', 2); glyph(ctx, 'lock', x, y, 16, '#555'); }
            if (sel || hov) circle(ctx, x, y, r + 9 + Math.sin(M.t * 0.12) * 2, null, sel ? '#ffffff' : hexA('#ffffff', 0.5), 2);
            if (Save.get().bosses.includes(i)) glyph(ctx, 'flag', x + r * 0.8, y - r * 0.8, 13, '#4be08a');
            text(ctx, open ? w.name : '???', x, y + r + 16, { size: 11, color: open ? '#fff' : '#666', weight: 700 });
            if (open) text(ctx, `★ ${Save.worldStars(i)}/15`, x, y + r + 30, { size: 10, color: '#ffd166', weight: 700 });
            if (i === M.world) drawShip(ctx, x, y - r - 18, -Math.PI / 2, skin, { thrust: 0.4, t: M.t, scale: 0.7 });
        });
        const w = WORLDS[M.gSel];
        if (w) {
            ctx.save(); ctx.globalAlpha = 0.7; ctx.fillStyle = '#000'; ctx.fillRect(W / 2 - 330, H - 64, 660, 50); ctx.restore();
            text(ctx, `${w.sub} — ${w.name}`, W / 2, H - 48, { size: 15, color: w.hue });
            text(ctx, w.story, W / 2, H - 28, { size: 12, color: '#cfd8f0', weight: 500 });
        }
    }

    M.draw = (ctx, skin) => {
        const w = WORLDS[M.world];
        // drifting malware in the background
        for (const d of M.drifters) {
            const def = ENEMIES[d.type];
            ctx.save(); ctx.globalAlpha = 0.18;
            circle(ctx, d.x, d.y, def.r, null, def.color, 1.5);
            glyph(ctx, def.glyph, d.x, d.y, def.r, def.color);
            ctx.restore();
        }
        // paths
        for (let i = 0; i < 4; i++) pathLine(ctx, w.nodes[i], w.nodes[i + 1], Save.isUnlocked(M.world, i + 1), w.hue);
        if (Save.secretUnlocked(M.world)) pathLine(ctx, w.nodes[2], w.secret, true, '#ffd166');

        // gates
        if (M.world + 1 < WORLDS.length) {
            const open = Save.worldUnlocked(M.world + 1);
            pathLine(ctx, w.nodes[4], [W - 40, H / 2], open, w.hue);
            poly(ctx, W - 40, H / 2, 26, 3, 0, open ? hexA(WORLDS[M.world + 1].hue, 0.9) : 'rgba(255,255,255,0.15)');
            text(ctx, open ? WORLDS[M.world + 1].name.toUpperCase() : tr('LOCKED'), W - 70, H / 2 + 44, { size: 11, color: open ? '#fff' : '#888', align: 'right', weight: 700 });
            if (M.world + 1 === ACT2_FIRST_WORLD && !open) text(ctx, tr('ACT II — beat the Zero-Day'), W - 70, H / 2 + 60, { size: 10, color: '#ff6bd8', align: 'right', weight: 700 });
        }
        if (M.world > 0) {
            poly(ctx, 40, H / 2, 26, 3, Math.PI, hexA(WORLDS[M.world - 1].hue, 0.9));
            text(ctx, WORLDS[M.world - 1].name.toUpperCase(), 70, H / 2 + 44, { size: 11, color: '#fff', align: 'left', weight: 700 });
        }

        // nodes
        const nodes = [0, 1, 2, 3, 4].concat(Save.secretUnlocked(M.world) ? [5] : []);
        for (const i of nodes) {
            const [x, y] = nodePos(M.world, i);
            const open = reachable(M.world, i);
            const boss = i === 4, secret = i === 5;
            const r = boss ? 40 : 28;
            const stars = Save.starsOf(M.world, i);
            const col = secret ? '#ffd166' : boss ? '#ff5d73' : w.hue;
            const pulse = (i === M.node || i === M.hover) ? 1 + Math.sin(M.t * 0.1) * 0.06 : 1;
            if (open) glow(ctx, x, y, r * 2.6, col, i === M.node ? 0.45 : 0.25);
            poly(ctx, x, y, r * pulse, boss ? 8 : secret ? 4 : 6, M.t * (boss ? 0.004 : 0.002), open ? '#0b1020' : '#111', open ? col : '#444', boss ? 4 : 3);
            if (!open) glyph(ctx, 'lock', x, y, 18, '#666');
            else if (boss) glyph(ctx, Save.get().bosses.includes(M.world) ? 'flag' : 'skull', x, y, 26, col);
            else if (secret) glyph(ctx, 'gem', x, y, 20, col);
            else {
                text(ctx, String(i + 1), x, y + 1, { size: 22, color: '#fff' });
                // the kind of the level, as a little badge
                const k = KIND_GLYPH[levelDef(M.world, i).kind];
                if (k) { circle(ctx, x + r * 0.8, y - r * 0.8, 11, '#0b1020', col, 1.5); glyph(ctx, k, x + r * 0.8, y - r * 0.8, 11, col); }
            }
            for (let s = 0; s < 3; s++) {
                glyph(ctx, 'star', x + (s - 1) * 18, y + r + 16, 13, s < stars ? '#ffd166' : 'rgba(255,255,255,0.18)');
            }
            if (i === M.hover && i !== M.node) circle(ctx, x, y, r + 10, null, hexA('#ffffff', 0.5), 1.5);
        }

        // the ship
        const bob = M.moving ? 0 : Math.sin(M.t * 0.08) * 4;
        drawShip(ctx, M.ship.x, M.ship.y - 52 + bob, -Math.PI / 2, skin, { thrust: M.moving ? 1 : 0.3, t: M.t, scale: 1.1 });

        if (M.galaxy) drawGalaxy(ctx, skin);
    };

    return M;
}
