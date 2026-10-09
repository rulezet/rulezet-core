/**
 * worldmap.js — the campaign map, one world at a time: levels as nodes on
 * a path, the ship travelling between them (Mario-world style), stars,
 * locks, the boss node, the secret honeypot branch and the gates to the
 * neighbouring worlds.
 */
import { W, H, TAU, WORLDS, ENEMIES, levelDef } from './data.js';
import { circle, poly, glyph, glow, hexA, text, drawShip } from './render.js';
import * as Save from './save.js';
import { Sfx } from './audio.js';

// Walking order on a world's path; 5 = the secret honeypot (branch off node 2)
const ORDER = [0, 1, 2, 5, 3, 4];

export function createMap() {
    const M = {
        world: 0, node: 0, t: 0,
        ship: { x: 0, y: 0 }, moving: null, hover: null,
        drifters: [],
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

    /** Mouse: hover + click a node (returns 'play' on a second click on the current node) */
    M.pointer = (mx, my, click) => {
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
    M.canPlay = () => !M.moving && reachable(M.world, M.node);

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
            text(ctx, open ? WORLDS[M.world + 1].name.toUpperCase() : 'LOCKED', W - 70, H / 2 + 44, { size: 11, color: open ? '#fff' : '#888', align: 'right', weight: 700 });
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
            else text(ctx, String(i + 1), x, y + 1, { size: 22, color: '#fff' });
            for (let s = 0; s < 3; s++) {
                glyph(ctx, 'star', x + (s - 1) * 18, y + r + 16, 13, s < stars ? '#ffd166' : 'rgba(255,255,255,0.18)');
            }
            if (i === M.hover && i !== M.node) circle(ctx, x, y, r + 10, null, hexA('#ffffff', 0.5), 1.5);
        }

        // the ship
        const bob = M.moving ? 0 : Math.sin(M.t * 0.08) * 4;
        drawShip(ctx, M.ship.x, M.ship.y - 52 + bob, -Math.PI / 2, skin, { thrust: M.moving ? 1 : 0.3, t: M.t, scale: 1.1 });
    };

    return M;
}
