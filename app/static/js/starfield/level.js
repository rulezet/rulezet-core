/**
 * level.js — one running level: the player, weapons, ship powers, enemies,
 * boss, hazards, pickups, objectives, scoring and stars. Pure game logic +
 * canvas drawing; the DOM side (HUD, menus) lives in main.js and gets data
 * through the callbacks.
 *
 * Arena: one screen (W × H), or an "open" sector (def.size) bigger than the
 * screen, seen through a camera that follows the ship — fly anywhere, the
 * radar (bottom right) and the arrows on the screen edges show the way.
 *
 * Kinds: waves | survive | beacons | protect | boss | honeypot | endless
 *        keys | escort | capture | pursuit | dark | purge | gauntlet | triage | defend
 * Mods (def.mods): rocks (n), storm, dark, mines (n)
 */
import { W, H, TAU, WEAPONS, ENEMIES, PICKUPS, WORLDS, BOSSES } from './data.js';
import { makeEnemy, updateEnemy, drawEnemy, onEnemyDeath, hittable, deflects, CLOUD_R } from './enemies.js';
import { makeBoss } from './bosses.js';
import { circle, poly, glyph, glow, hexA, text, drawShip, drawRock, drawGrid } from './render.js';
import { Sfx } from './audio.js';
import { tr } from './i18n.js';

const IPS_R = 150;                     // Suricata's IPS Drop field radius
const PARANOIA_R = 135;                // OWASP CRS reflect field radius

const rand = (a, b) => a + Math.random() * (b - a);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const dist2 = (ax, ay, bx, by) => (ax - bx) ** 2 + (ay - by) ** 2;

function segDist(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1;
    const l2 = dx * dx + dy * dy || 1;
    const t = clamp(((px - x1) * dx + (py - y1) * dy) / l2, 0, 1);
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}

/**
 * @param def      level definition (data.levelDef) or { kind: 'endless' }
 * @param env      { skin, upgrades, weapons (ids), diff, settings, callbacks: { onEnd, onBoss } }
 */
export function createLevel(def, env) {
    const world = def.world ?? 0;
    const theme = WORLDS[world];
    const up = env.upgrades || {};
    const lv = id => up[id] || 0;
    const mods = def.mods || {};
    const open = !!def.size;
    const kind = def.kind;

    const L = {
        def, world, tier: def.tier ?? world * 4, diff: env.diff, theme,
        pool: def.pool || theme.pool,
        aw: open ? def.size[0] : W, ah: open ? def.size[1] : H, open,
        cam: { x: 0, y: 0 },
        t: 0, score: 0, kills: 0, combo: 0, comboT: 0, maxCombo: 0,
        levelBytes: 0, hits: 0, finished: false, result: null,
        bullets: [], ebullets: [], enemies: [], pickups: [], particles: [], floaters: [],
        beams: [], zones: [], messages: [], boss: null,
        rocks: [], hazards: [], sensors: [], gates: [], keys: [], relays: [], exit: null,
        allies: [], marks: [], wells: [], nets: [], bolts: [], radioQ: [], radioMsg: null,
        shakeT: 0, shakeMag: 0, slow: false, hurtT: 0,
        invertT: 0, gravity: null, wind: null, lightT: 0, pulse: null,
        dark: !!mods.dark || kind === 'dark',
        objective: { label: '', progress: 0 }, phaseLabel: '',
        wave: 0, waveQueue: [], waveDelay: 0,
        timer: def.duration || 0,
        endingT: 0, fp: 0, malicious: 0, serversLost: 0, ping: null,
        skinShape: env.skin.shape || 'dart',
        // What the player did during the run — sent with the result (admin score tracking).
        stats: { shots: {}, dashes: 0, bombs: 0, specials: 0, pickups: {}, killsBy: {}, weaponSwitches: 0, falsePositives: 0 },
    };

    const weapons = WEAPONS.filter(w => (env.weapons || ['pulse']).includes(w.id));
    const scheme = env.settings?.controls === 'twin' ? 'twin' : 'classic';
    let mouseUsed = false;
    let lastMove = [0, -1];
    const P = L.player = {
        x: L.aw / 2, y: L.ah - 140, vx: 0, vy: 0, angle: -Math.PI / 2, r: 12,
        maxHp: 3 + lv('hp'), hp: 3 + lv('hp'), inv: 120, dashCd: 0, dashT: 0,
        bombs: 2 + lv('bombs'), maxBombs: 2 + lv('bombs'),
        weapon: 0, cool: 0, buffs: { rapid: 0, shield: 0, overclock: 0 },
        disarmed: 0, pulled: null, thrust: 0, slowT: 0,
        speed: 4.3 * (1 + 0.06 * lv('speed')), dmgMul: 1 + 0.15 * lv('damage'),
        rateMul: 1 - 0.08 * lv('rate'), dashMax: Math.round(75 * (1 - 0.12 * lv('dash'))),
        magnet: 80 + 55 * lv('magnet'), armor: 0.08 * lv('armor'),
        // ship super power: starts charged, then recharges on its own
        specialCd: 0, specialMax: Math.round((env.skin.special?.cd || 15) * 60 * (1 - 0.1 * lv('power'))), specialT: 0,
        history: [],
    };

    // ── API used by enemies.js / bosses*.js ────────────────────────────
    L.pick = arr => arr[Math.floor(Math.random() * arr.length)];
    L.enemyBullet = (x, y, vx, vy, o = {}) => {
        const s = L.diff.bullet;
        L.ebullets.push({ x, y, vx: vx * s, vy: vy * s, r: o.r || 6, color: o.color || '#ff5d73', life: o.life || 420, kind: o.kind || 'shot', dmg: o.dmg || 1 });
    };
    L.spawnEnemy = (type, x, y, extra = {}) => {
        const e = makeEnemy(type, clamp(x, 30, L.aw - 30), clamp(y, 30, L.ah - 30), L, extra);
        L.enemies.push(e);
        return e;
    };
    L.addBeam = b => { L.beams.push({ x: 0, y: 0, rot: 0, ...b, t: 0 }); };
    L.addZone = z => { L.zones.push({ ...z, t: 0 }); };
    L.addHazard = h => { const z = { t: 0, arm: 60, dmg: 1, ...h }; L.hazards.push(z); return z; };
    L.addRock = (x, y, r) => { const k = { x, y, r, rot: rand(0, TAU), spin: rand(-0.004, 0.004), verts: Array.from({ length: 11 }, () => rand(0.82, 1.08)) }; L.rocks.push(k); return k; };
    L.removeRock = k => { L.rocks = L.rocks.filter(o => o !== k); };
    L.blocked = (x1, y1, x2, y2) => L.rocks.some(k => segDist(k.x, k.y, x1, y1, x2, y2) < k.r * 0.9);
    L.shake = m => { if (env.settings?.shake !== false) { L.shakeT = 14; L.shakeMag = Math.max(L.shakeMag, m); } };
    L.announce = (str, color = '#fff', sub = '') => { L.messages.push({ kind: 'big', str, sub, color, t: 0, life: 110 }); };
    L.say = (str, color = '#fff') => { if (str) L.messages.push({ kind: 'line', str, color, t: 0, life: 200 }); };
    L.radio = (str) => { if (str) L.radioQ.push({ str, t: 0, life: 330 }); };
    L.float = (x, y, str, color = '#fff') => { L.floaters.push({ x, y, str, color, t: 0, life: 50 }); };
    L.addScore = n => { L.score += n; };
    L.hurtPlayer = () => hurt();
    L.damageEnemy = (e, d) => damageEnemy(e, d, 'ally');
    L.removeEnemy = e => { e.dead = true; e.removed = true; };
    /** End of a round (wave cleared, boss phase, beacon down, swarm survived): every heart back */
    L.restoreHearts = () => {
        const full = Math.max(3, P.maxHp);
        if (P.hp >= full || L.finished) return;
        P.hp = full;
        L.float(P.x, P.y - 30, tr('HEARTS RESTORED'), '#ff5b8a');
        Sfx.powerup();
    };
    L.drainBytes = (e, n) => {
        if (L.levelBytes <= 0) return;
        L.levelBytes = Math.max(0, L.levelBytes - n);
        L.float(e.x, e.y - 20, tr('-{n} byte', { n }), '#ffd166');
    };
    L.explosion = (x, y, radius, color, hurtsPlayer) => {
        burst(x, y, 26, color, 6);
        L.particles.push({ kind: 'ring', x, y, r: 10, max: radius, life: 22, t: 0, color });
        L.particles.push({ kind: 'flash', x, y, r: radius * 0.9, life: 10, t: 0, color });
        Sfx.explode(true); L.shake(8);
        if (hurtsPlayer && dist2(x, y, P.x, P.y) < (radius + P.r) ** 2) hurt();
        if (hurtsPlayer) for (const s of L.sensors) if (s.hp > 0 && dist2(x, y, s.x, s.y) < (radius + s.r) ** 2) damageSensor(s, 3);
    };

    function burst(x, y, n, color, speed = 4) {
        if (L.particles.length > 600) n = Math.ceil(n / 3);
        for (let i = 0; i < n; i++) {
            const a = rand(0, TAU), s = rand(0.5, speed);
            L.particles.push({ kind: 'spark', x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: rand(18, 40), t: 0, color, size: rand(1.5, 3.5) });
        }
    }
    const inRock = (x, y, pad = 0) => L.rocks.some(k => dist2(x, y, k.x, k.y) < (k.r + pad) ** 2);
    const onScreen = (x, y, m = 60) => x > L.cam.x - m && x < L.cam.x + W + m && y > L.cam.y - m && y < L.cam.y + H + m;

    // ── Spawning helpers ──────────────────────────────────────────────
    function spawnPoint(minDist = 220) {
        if (open) {
            // just off-screen, around the ship: malware comes from the dark
            for (let i = 0; i < 24; i++) {
                const a = rand(0, TAU), d = rand(640, 900);
                const x = P.x + Math.cos(a) * d, y = P.y + Math.sin(a) * d;
                if (x > 60 && x < L.aw - 60 && y > 60 && y < L.ah - 60 && !inRock(x, y, 30)) return [x, y];
            }
            return [clamp(P.x + rand(-700, 700), 60, L.aw - 60), clamp(P.y + (Math.random() < 0.5 ? -600 : 600), 60, L.ah - 60)];
        }
        for (let i = 0; i < 20; i++) {
            const x = rand(60, L.aw - 60), y = rand(60, L.ah - 60);
            if (dist2(x, y, P.x, P.y) > minDist * minDist && !inRock(x, y, 25) && L.sensors.every(s => dist2(x, y, s.x, s.y) > 160 * 160)) return [x, y];
        }
        return [Math.random() < 0.5 ? 60 : L.aw - 60, rand(60, L.ah - 60)];
    }
    function pickType(allowStatic = false) {
        const pool = L.pool.filter(k => allowStatic || !ENEMIES[k].static);
        // earlier entries of the pool are the world's "common" malware
        const weights = pool.map((_, i) => 1 / (1 + i * 0.35));
        let r = Math.random() * weights.reduce((a, b) => a + b, 0);
        for (let i = 0; i < pool.length; i++) { r -= weights[i]; if (r <= 0) return pool[i]; }
        return pool[0];
    }
    function spawnOne(type, extra) {
        const [x, y] = spawnPoint();
        return L.spawnEnemy(type || pickType(), x, y, extra);
    }
    function spawnNear(cx, cy, dmin, dmax, type) {
        for (let i = 0; i < 16; i++) {
            const a = rand(0, TAU), d = rand(dmin, dmax);
            const x = cx + Math.cos(a) * d, y = cy + Math.sin(a) * d;
            if (x > 50 && x < L.aw - 50 && y > 50 && y < L.ah - 50 && !inRock(x, y, 25) && (!open || !onScreen(x, y, 20))) return L.spawnEnemy(type || pickType(), x, y);
        }
        return spawnOne(type);
    }

    function buildWave(n) {
        const count = Math.min(Math.round(24 * L.diff.spawn), Math.round((5 + L.tier * 0.55 + n * 2) * L.diff.spawn));
        const q = [];
        for (let i = 0; i < count; i++) q.push(pickType(false));
        if (L.pool.includes('botnet') && n >= 2) q.push('botnet');
        return q;
    }
    const alive = () => L.enemies.filter(e => !e.dead && !e.def.benign && !e.ally);

    /** Spread points over a big sector: far from each other, from the start and out of rocks */
    function scatter(n, minGap, fromStart, avoid = []) {
        const pts = [];
        for (let i = 0; i < n; i++) {
            let best = null, bestScore = -1;
            for (let k = 0; k < 60; k++) {
                const x = rand(140, L.aw - 140), y = rand(140, L.ah - 140);
                if (inRock(x, y, 60)) continue;
                const dStart = Math.sqrt(dist2(x, y, P.x, P.y));
                const dOthers = [...pts, ...avoid].reduce((m, p) => Math.min(m, Math.sqrt(dist2(x, y, p.x, p.y))), 1e9);
                const score = Math.min(dOthers / minGap, dStart / fromStart, 1.5) + Math.random() * 0.05;
                if (score > bestScore) { bestScore = score; best = { x, y }; }
            }
            pts.push(best || { x: rand(140, L.aw - 140), y: rand(140, L.ah - 140) });
        }
        return pts;
    }
    function placeRocks(n) {
        for (let i = 0; i < n; i++) {
            for (let k = 0; k < 30; k++) {
                const r = open ? rand(34, 95) : rand(28, 52);
                const x = rand(r + 20, L.aw - r - 20), y = rand(r + 20, L.ah - r - 20);
                if (dist2(x, y, P.x, P.y) < (r + 200) ** 2) continue;
                if (L.rocks.some(o => dist2(x, y, o.x, o.y) < (o.r + r + 70) ** 2)) continue;
                if (L.sensors.some(s => dist2(x, y, s.x, s.y) < (r + 150) ** 2)) continue;
                const path = L.sensors[0] && L.sensors[0].path;
                if (path && path.some((p, j) => j && segDist(x, y, path[j - 1].x, path[j - 1].y, p.x, p.y) < r + 110)) continue;
                L.addRock(x, y, r); break;
            }
        }
    }

    // ── Setup per kind ───────────────────────────────────────────────
    if (open) { P.x = L.aw / 2; P.y = L.ah / 2; }
    if (kind === 'escort' || kind === 'gauntlet') { P.x = 220; P.y = L.ah / 2; P.angle = 0; }

    if (kind === 'protect') {
        const hp = 26 + Math.min(world, 8) * 3;
        L.sensors.push({ x: W / 2, y: H / 2, r: 30, hp, maxHp: hp, flash: 0, label: tr('SENSOR'), glyph: 'eye' });
        P.y = H / 2 + 120;
    }
    if (kind === 'defend') {
        const pts = scatter(def.servers || 3, 900, 500);
        const hp = 30 + Math.min(world, 15);
        pts.forEach(p => L.sensors.push({ x: p.x, y: p.y, r: 32, hp, maxHp: hp, flash: 0, label: tr('SERVER'), glyph: 'server', hitT: 0, turret: true }));
    }
    if (kind === 'escort') {
        const n = 9, path = [];
        for (let i = 0; i <= n; i++) path.push({ x: 300 + (L.aw - 600) * i / n, y: L.ah / 2 + (i === 0 ? 0 : Math.sin(i * 1.7) * (L.ah * 0.3)) });
        const hp = def.convoyHp || 34;
        L.sensors.push({ x: path[0].x, y: path[0].y, r: 34, hp, maxHp: hp, flash: 0, label: tr('CONVOY'), glyph: 'database', path, wpi: 1, moving: true, travelled: 0 });
        L.pathLen = path.reduce((s, p, i) => (i ? s + Math.hypot(p.x - path[i - 1].x, p.y - path[i - 1].y) : 0), 0);
        P.x = path[0].x - 80; P.y = path[0].y;
        L.exit = { x: path[n].x + 150, y: path[n].y, r: 80, open: true, deco: true };
    }
    if (mods.rocks) placeRocks(mods.rocks);
    if (kind === 'beacons') {
        if (open) {
            scatter(def.beacons, 700, 600).forEach((p, i) => L.spawnEnemy('beacon', p.x, p.y, { spawnT: 40 + i * 15, isTarget: true }));
        } else {
            const placed = [];
            for (let i = 0; i < def.beacons; i++) {
                let x, y, ok = false;
                for (let k = 0; k < 40 && !ok; k++) {
                    x = rand(120, W - 120); y = rand(100, H - 260);
                    ok = placed.every(([px, py]) => dist2(x, y, px, py) > 230 * 230) && !inRock(x, y, 40);
                }
                placed.push([x, y]);
                L.spawnEnemy('beacon', x, y, { spawnT: 40 + i * 15, isTarget: true });
            }
        }
    }
    if (kind === 'keys') {
        const pts = scatter(def.keys || 6, 750, 700);
        L.keys = pts.map((p, i) => ({ x: p.x, y: p.y, got: false, seen: false, t: rand(0, 100), i }));
        // each key sits in a vault watched by a few sleeping malware
        for (const k of L.keys) {
            for (let g = 0; g < 2 + Math.floor(L.tier / 16); g++) {
                const a = rand(0, TAU);
                L.spawnEnemy(pickType(false), k.x + Math.cos(a) * 110, k.y + Math.sin(a) * 110, { guard: true, home: { x: k.x, y: k.y }, spawnT: 0 });
            }
        }
        L.exit = { x: P.x, y: P.y, r: 80, open: false };
    }
    if (kind === 'capture') {
        const pts = scatter(def.nodes || 4, 750, 650);
        L.relays = pts.map(p => ({ x: p.x, y: p.y, r: 125, prog: 0, done: false, t: 0 }));
    }
    if (kind === 'pursuit') {
        // the courier runs from near the start to the exit gate at the far side, zig-zagging
        const sx = L.aw * 0.5 + 300, sy = L.ah * 0.5;
        const ex = Math.random() < 0.5 ? L.aw - 200 : 200, ey = Math.random() < 0.5 ? 200 : L.ah - 200;
        const path = [];
        const n = 9;
        for (let i = 1; i <= n; i++) {
            const k = i / n;
            let x = sx + (ex - sx) * k + (i < n ? rand(-700, 700) : 0), y = sy + (ey - sy) * k + (i < n ? rand(-600, 600) : 0);
            x = clamp(x, 150, L.aw - 150); y = clamp(y, 150, L.ah - 150);
            path.push({ x, y });
        }
        L.courierPath = path;
        const hp = Math.round((def.courierHp || 70) * L.diff.hp * (1 + L.tier * 0.02));
        L.courier = L.spawnEnemy('courier', sx, sy, { hp, cool: 360, spawnT: 40 });
        L.courier.maxHp = hp;
        L.exit = { x: ex, y: ey, r: 90, open: true, enemy: true };
    }
    if (kind === 'dark') {
        scatter(def.targets || 6, 600, 550).forEach(p => L.spawnEnemy('implant', p.x, p.y, { isTarget: true, spawnT: 0 }));
    }
    if (kind === 'gauntlet') {
        const n = def.gates || 10, x0 = 750, x1 = L.aw - 650;
        for (let i = 0; i < n; i++) {
            const x = x0 + (x1 - x0) * i / Math.max(1, n - 1);
            const type = ['blink', 'gap', 'sweep', 'blink', 'gap'][i % 5];
            L.gates.push({ type, x, i, phase: rand(0, 200), on: false, gapY: L.ah / 2, gapW: 230, a: rand(0, TAU), spin: (i % 2 ? 1 : -1) * (0.012 + L.tier * 0.0002), arm: 380 });
            if (i % 3 === 1) L.spawnEnemy(L.pool.includes('scanner') ? 'scanner' : pickType(false), x + 260, rand(150, L.ah - 150), { guard: true, home: { x: x + 260, y: L.ah / 2 }, spawnT: 0 });
        }
        L.exit = { x: L.aw - 180, y: L.ah / 2, r: 110, open: true };
    }
    if (kind === 'purge') { L.wave = 0; }
    if (mods.mines) {
        for (let i = 0; i < mods.mines; i++) {
            const x = rand(600, L.aw - 300), y = rand(80, L.ah - 80);
            if (!inRock(x, y, 30)) L.spawnEnemy('mine', x, y, { spawnT: 0 });
        }
    }
    if (mods.storm) L.wind = { a: rand(0, TAU), k: 0.085 };
    if (kind === 'boss') {
        L.boss = makeBoss(def.boss, L);
        L.bossIntroT = 150;
        L.bossPhase = 1;
        Sfx.warning();
    }
    if (open) { L.cam.x = clamp(P.x - W / 2, 0, L.aw - W); L.cam.y = clamp(P.y - H / 2, 0, L.ah - H); }
    if (def.radio && def.radio[0]) L.radioStart = def.radio[0];

    // ── Player actions ───────────────────────────────────────────────
    function currentWeapon() { return weapons[P.weapon] || weapons[0]; }
    const pdmg = () => P.dmgMul * (P.buffs.overclock > 0 ? 2 : 1);

    function pushBullet(o) {
        L.bullets.push({ r: 3.5, life: 90, pierce: false, homing: false, hitIds: null, age: 0, ...o });
    }

    function fire() {
        const wp = currentWeapon();
        if (P.cool > 0 || P.disarmed > 0) return;
        if (wp.id === 'beam') {
            L.beamT = 3;
            if (L.t % 10 === 0) { L.stats.shots.beam = (L.stats.shots.beam || 0) + 1; Sfx.shoot('rail'); }
            return;
        }
        const rapid = P.buffs.rapid > 0 ? 0.5 : 1;
        P.cool = Math.max(3, Math.round(wp.rate * P.rateMul * rapid));
        L.stats.shots[wp.id] = (L.stats.shots[wp.id] || 0) + 1;
        const dmg = wp.dmg * pdmg();
        for (let i = 0; i < wp.count; i++) {
            const off = wp.count > 1 ? (i - (wp.count - 1) / 2) * wp.spread : 0;
            const a = P.angle + off;
            pushBullet({
                x: P.x + Math.cos(P.angle) * 18, y: P.y + Math.sin(P.angle) * 18,
                vx: Math.cos(a) * wp.speed + P.vx * 0.3, vy: Math.sin(a) * wp.speed + P.vy * 0.3,
                r: wp.id === 'rail' || wp.id === 'seeker' ? 5 : wp.id === 'flak' ? 7 : wp.id === 'blade' ? 7 : 3.5, dmg, life: wp.life || 90,
                pierce: !!wp.pierce, homing: !!wp.homing, color: wp.color, hitIds: wp.pierce ? new Set() : null, id: wp.id,
                blast: wp.blast || 0, chain: wp.chain || 0, boomerang: !!wp.boomerang,
            });
        }
        Sfx.shoot(wp.id === 'flak' || wp.id === 'blade' ? 'spread' : wp.id === 'arc' ? 'seeker' : wp.id);
    }

    function dash(mx, my) {
        if (P.dashCd > 0) return;
        let [dx, dy] = [mx, my];
        if (!dx && !dy) { dx = Math.cos(P.angle); dy = Math.sin(P.angle); }
        const l = Math.hypot(dx, dy) || 1;
        P.vx = dx / l * 15; P.vy = dy / l * 15;
        P.dashT = 12; P.inv = Math.max(P.inv, 16); P.dashCd = P.dashMax;
        L.stats.dashes++;
        burst(P.x, P.y, 12, env.skin.glow, 3);
        // a dash tears the kprobe hooks off
        for (const e of L.enemies) if (e.latched && !e.dead) { e.latched = false; killEnemy(e); }
        Sfx.dash();
    }

    /** Area damage from the player (bombs, ship powers): never hits clean traffic */
    function areaDamage(x, y, radius, d, bossD = d) {
        for (const e of L.enemies) if (!e.dead && hittable(e) && !e.def.benign && dist2(x, y, e.x, e.y) < (radius + e.r) ** 2) damageEnemy(e, d, 'area');
        if (L.boss && !L.boss.entering && L.boss.hp > 0) for (const tg of L.boss.targets()) if (!tg.shielded && dist2(x, y, tg.x, tg.y) < (radius + tg.r) ** 2) tg.hit(bossD);
    }

    function bomb() {
        if (P.bombs <= 0) { Sfx.deny(); return; }
        P.bombs--;
        L.stats.bombs++;
        L.ebullets.length = 0;
        L.beams.forEach(b => { if (b.t < b.tele) b.cancel = true; });
        L.hazards.forEach(h => { if (dist2(h.x, h.y, P.x, P.y) < 420 * 420) h.life = Math.min(h.life, 20); });
        L.particles.push({ kind: 'ring', x: P.x, y: P.y, r: 20, max: 900, life: 40, t: 0, color: '#ffffff' });
        L.particles.push({ kind: 'flash', x: P.x, y: P.y, r: 500, life: 14, t: 0, color: '#ffffff' });
        const reach = open ? 900 : 2000;
        for (const e of L.enemies) if (!e.dead && hittable(e) && !e.def.benign && dist2(e.x, e.y, P.x, P.y) < reach * reach) damageEnemy(e, 6 * P.dmgMul, 'area');
        if (L.boss && !L.boss.entering) for (const tg of L.boss.targets()) if (!tg.shielded) tg.hit(18 * P.dmgMul);
        for (const e of L.enemies) if (e.latched) { e.latched = false; killEnemy(e); }
        P.inv = Math.max(P.inv, 60);
        L.shake(20); Sfx.bomb();
        L.announce('QUARANTINE', '#ffffff');
    }

    function nearestTargets(x, y, range, n, exclude = new Set()) {
        const c = [];
        for (const e of L.enemies) if (!e.dead && hittable(e) && !e.def.benign && !e.disguised && !exclude.has(e) && dist2(x, y, e.x, e.y) < range * range) c.push(e);
        c.sort((a, b) => dist2(x, y, a.x, a.y) - dist2(x, y, b.x, b.y));
        return c.slice(0, n);
    }
    function bolt(x1, y1, x2, y2, color) {
        const pts = [[x1, y1]];
        for (let i = 1; i < 6; i++) { const k = i / 6; pts.push([x1 + (x2 - x1) * k + rand(-12, 12), y1 + (y2 - y1) * k + rand(-12, 12)]); }
        pts.push([x2, y2]);
        L.bolts.push({ pts, color, t: 0, life: 16 });
    }

    function special() {
        const sp = env.skin.special;
        if (!sp || P.specialCd > 0) { if (sp) Sfx.deny(); return; }
        P.specialCd = P.specialMax;
        L.stats.specials++;
        const c = env.skin.glow;
        const dmg = pdmg();
        const ax = Math.cos(P.angle), ay = Math.sin(P.angle);
        switch (sp.id) {
            case 'sweep':
                for (let i = 0; i < 24; i++) {
                    const a = P.angle + i * TAU / 24;
                    pushBullet({ x: P.x, y: P.y, vx: Math.cos(a) * 12, vy: Math.sin(a) * 12, r: 5, dmg: 3 * dmg, life: 80, pierce: true, color: c, hitIds: new Set(), id: 'rail' });
                }
                L.particles.push({ kind: 'ring', x: P.x, y: P.y, r: 10, max: 260, life: 24, t: 0, color: c });
                break;
            case 'inspect':
                for (let i = 0; i < 10; i++) {
                    const a = P.angle + (i - 4.5) * 0.35;
                    pushBullet({ x: P.x, y: P.y, vx: Math.cos(a) * 6, vy: Math.sin(a) * 6, r: 5, dmg: 2.5 * dmg, life: 160, homing: true, color: c, id: 'seeker' });
                }
                break;
            case 'threshold': {
                const marked = nearestTargets(P.x, P.y, 760, 40);
                marked.forEach((e, i) => L.marks.push({ e, t: 50 + i * 2, dmg: 7 * dmg }));
                if (L.boss && !L.boss.entering && L.boss.hp > 0) L.marks.push({ boss: true, t: 60, dmg: 26 * dmg });
                L.particles.push({ kind: 'ring', x: P.x, y: P.y, r: 10, max: 760, life: 30, t: 0, color: c });
                break;
            }
            case 'paranoia': P.specialT = Math.round((sp.dur || 5) * 60); break;
            case 'portscan': scanPulse(900, true); break;
            case 'inject': {
                const cand = L.enemies.filter(e => !e.dead && hittable(e) && !e.def.static && !e.def.benign && e.type !== 'courier' && !e.ally && dist2(e.x, e.y, P.x, P.y) < 650 * 650)
                    .sort((a, b) => dist2(a.x, a.y, P.x, P.y) - dist2(b.x, b.y, P.x, P.y)).slice(0, 5);
                cand.forEach(e => { e.ally = true; e.allyT = Math.round((sp.dur || 8) * 60); e.latched = false; e.disguised = false; L.float(e.x, e.y - 24, 'INJECTED', c); });
                if (!cand.length) L.float(P.x, P.y - 30, tr('No target in range'), '#aaa');
                break;
            }
            case 'agents':
                L.allies = [0, 1, 2].map(i => ({ a: i * TAU / 3, life: Math.round((sp.dur || 10) * 60), cd: 10 + i * 5, x: P.x, y: P.y }));
                break;
            case 'response': {
                const ox = P.x, oy = P.y;
                let d = 270, nx, ny;
                do { nx = clamp(P.x + ax * d, 20, L.aw - 20); ny = clamp(P.y + ay * d, 20, L.ah - 20); d -= 30; } while (inRock(nx, ny, P.r) && d > 0);
                P.x = nx; P.y = ny;
                for (const [x, y] of [[ox, oy], [nx, ny]]) {
                    L.particles.push({ kind: 'ring', x, y, r: 10, max: 130, life: 20, t: 0, color: c });
                    L.particles.push({ kind: 'flash', x, y, r: 120, life: 10, t: 0, color: c });
                    burst(x, y, 18, c, 6);
                    areaDamage(x, y, 125, 8 * dmg, 12 * dmg);
                }
                for (let i = 0; i < 10; i++) { const k = i / 10; L.particles.push({ kind: 'spark', x: ox + (nx - ox) * k, y: oy + (ny - oy) * k, vx: 0, vy: 0, life: 20, t: 0, color: c, size: 4 }); }
                P.inv = Math.max(P.inv, 40);
                L.shake(8);
                break;
            }
            case 'join': {
                let from = { x: P.x, y: P.y };
                const hit = new Set();
                for (let i = 0; i < 10; i++) {
                    const [e] = nearestTargets(from.x, from.y, i === 0 ? 460 : 300, 1, hit);
                    if (!e) break;
                    bolt(from.x, from.y, e.x, e.y, c);
                    hit.add(e);
                    damageEnemy(e, 5 * dmg, 'area');
                    from = e;
                }
                if (L.boss && !L.boss.entering && L.boss.hp > 0) {
                    const tg = L.boss.targets().find(t => !t.shielded);
                    if (tg && dist2(tg.x, tg.y, from.x, from.y) < 600 * 600) { bolt(from.x, from.y, tg.x, tg.y, c); tg.hit(16 * dmg); }
                }
                break;
            }
            case 'rewind': {
                const h = P.history[0];
                if (h) {
                    for (let i = 0; i < P.history.length; i += 8) L.particles.push({ kind: 'spark', x: P.history[i].x, y: P.history[i].y, vx: 0, vy: 0, life: 30, t: 0, color: c, size: 3 });
                    P.x = h.x; P.y = h.y; P.hp = Math.max(P.hp, h.hp); P.vx = P.vy = 0;
                    L.ebullets = L.ebullets.filter(b => dist2(b.x, b.y, P.x, P.y) > 240 * 240);
                    L.particles.push({ kind: 'ring', x: P.x, y: P.y, r: 240, max: 10, life: 24, t: 0, color: c });
                }
                P.inv = Math.max(P.inv, 50);
                break;
            }
            case 'gravity':
                L.wells.push({ x: clamp(P.x + ax * 240, 40, L.aw - 40), y: clamp(P.y + ay * 240, 40, L.ah - 40), t: 0, life: 160, dmg: 10 * dmg, color: c });
                break;
            case 'volley':
                for (let i = 0; i < 10; i++) {
                    const a = P.angle + (i - 4.5) * 0.26;
                    pushBullet({ x: P.x, y: P.y, vx: Math.cos(a) * 12, vy: Math.sin(a) * 12, r: 7, dmg: 3 * dmg, life: 110, pierce: true, hitIds: new Set(), color: c, id: 'blade', boomerang: true });
                }
                break;
            case 'net':
                L.nets.push({ x: clamp(P.x + ax * 220, 40, L.aw - 40), y: clamp(P.y + ay * 220, 40, L.ah - 40), r: 175, t: 0, life: Math.round((sp.dur || 4) * 60), color: c });
                break;
            default:
                P.specialT = Math.round((sp.dur || 5) * 60);
                if (sp.id === 'correlate') L.slow = true;
        }
        P.inv = Math.max(P.inv, 30);
        burst(P.x, P.y, 24, c, 5);
        L.announce(sp.name.toUpperCase(), c);
        Sfx.powerup();
    }

    /** A scan pulse: lights up, reveals what hides (keys, implants, rootkits); stun = Nmap's Port Sweep */
    function scanPulse(range, stun) {
        L.pulse = { x: P.x, y: P.y, r: 0, max: range, t: 0, stun };
        if (stun) {
            L.lightT = 240;
            for (const k of L.keys) k.seen = true;
            for (const e of L.enemies) {
                if (e.dead || dist2(e.x, e.y, P.x, P.y) > range * range) continue;
                e.seen = true;
                if (!e.ally && !e.def.benign) e.stun = Math.max(e.stun, 120);
                if (e.type === 'rootkit' && e.state === 'burrowed') { e.state = 'emerging'; e.stateT = 10; }
                if (e.type === 'keylogger') e.alpha = 1;
                e.disguised = false;
            }
        }
        Sfx.telegraph();
    }

    function hurt() {
        if (P.inv > 0 || L.finished) return;
        if (P.buffs.shield > 0) { P.buffs.shield = 0; P.inv = 60; Sfx.shieldBreak(); burst(P.x, P.y, 20, '#6ea8ff'); return; }
        if (P.armor > 0 && Math.random() < P.armor) { P.inv = 50; L.float(P.x, P.y - 26, tr('BLOCKED'), '#c0c0ff'); Sfx.shieldBreak(); return; }
        P.hp--; L.hits++; P.inv = 100; L.combo = 0; L.comboT = 0; L.hurtT = 22;
        L.shake(16); Sfx.hurt(); burst(P.x, P.y, 30, '#ff5d73', 5);
        if (P.hp <= 0) lose(tr('Rule disabled'));
    }

    function damageSensor(s, n) {
        if (!s || s.hp <= 0 || L.finished) return;
        s.hp -= n; s.flash = 6; s.hitT = 90;
        if (s.hp <= 0) {
            L.explosion(s.x, s.y, 120, '#5be7ff', false);
            if (kind === 'defend') {
                L.serversLost++;
                const limit = (def.servers || 3) > 1 ? 2 : 1;
                if (L.serversLost >= limit) lose(tr('Servers lost'));
                else { L.announce(tr('SERVER LOST'), '#ff5d73'); L.say(tr('One server down — do not lose another!'), '#ff5d73'); }
            } else lose(kind === 'escort' ? tr('Convoy lost') : tr('Sensor lost'));
        }
    }

    // ── Enemies dying, drops ─────────────────────────────────────────
    function damageEnemy(e, d, src = 'shot') {
        if (e.dead) return;
        if (e.def.benign && src !== 'shot') return;
        e.hp -= d; e.flash = 4; e.lastHitT = L.t;
        if (e.hp <= 0) killEnemy(e, src);
        else {
            Sfx.hit();
            if (e.def.benign && !e.warned) { e.warned = true; L.float(e.x, e.y - 22, tr('CLEAN TRAFFIC — HOLD FIRE!'), '#4be08a'); }
        }
    }

    function killEnemy(e, src = 'shot') {
        if (e.dead) return;
        e.dead = true;
        if (e.def.benign) {
            // a false positive: the SOC hates those
            L.fp++; L.stats.falsePositives++;
            L.score = Math.max(0, L.score - 300);
            L.float(e.x, e.y, tr('FALSE POSITIVE'), '#ff5d73');
            burst(e.x, e.y, 14, '#4be08a', 3);
            L.shake(6); Sfx.deny();
            if (kind === 'triage' && L.fp > (def.maxFp ?? 5)) lose(tr('Too many false positives'));
            return;
        }
        L.kills++;
        if (kind === 'triage') L.malicious++;
        L.stats.killsBy[e.type] = (L.stats.killsBy[e.type] || 0) + 1;
        L.comboT = 150; L.combo++;
        L.maxCombo = Math.max(L.maxCombo, L.combo);
        const mult = Math.min(8, 1 + Math.floor(L.combo / 5));
        const pts = e.def.score * mult;
        L.score += pts;
        L.float(e.x, e.y, `+${pts}`, mult > 1 ? '#ffd166' : '#ffffff');
        burst(e.x, e.y, e.def.static ? 30 : 14, e.def.color, e.def.static ? 6 : 4);
        L.particles.push({ kind: 'flash', x: e.x, y: e.y, r: e.r * 2.6, life: 8, t: 0, color: e.def.color });
        Sfx.explode(!!e.def.static || e.type === 'courier');
        if (e.def.static || e.type === 'courier') L.shake(8);
        const byteMul = kind === 'honeypot' ? 3 : 1;
        const n = Math.round(e.def.bytes * byteMul * (e.type === 'shard' ? e.size / 3 : 1));
        for (let i = 0; i < n; i++) dropPickup('byte', e.x + rand(-12, 12), e.y + rand(-12, 12));
        const chance = kind === 'honeypot' ? 0.1 : (e.def.static || e.type === 'courier') ? 0.6 : 0.055;
        if (Math.random() < chance) {
            const r = Math.random();
            dropPickup(r < 0.28 ? 'heal' : r < 0.52 ? 'rapid' : r < 0.72 ? 'shield' : r < 0.86 ? 'overclock' : 'bomb', e.x, e.y);
        }
        if (e.type === 'beacon' && kind === 'beacons') L.restoreHearts();
        if (e.type === 'implant' && kind === 'dark') { L.restoreHearts(); L.announce(tr('IMPLANT REMOVED'), '#ff4d6d'); }
        if (!e.silent) onEnemyDeath(e, L);
    }

    function dropPickup(type, x, y) {
        const a = rand(0, TAU), s = type === 'byte' ? rand(1, 3) : 1;
        L.pickups.push({ type, x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, t: 0, life: type === 'byte' ? 600 : 720 });
    }

    function collect(pk) {
        const d = PICKUPS[pk.type];
        L.stats.pickups[pk.type] = (L.stats.pickups[pk.type] || 0) + 1;
        if (pk.type === 'byte') { L.levelBytes++; Sfx.pickup(); return; }
        if (pk.type === 'heal') { if (P.hp < P.maxHp) P.hp++; else L.score += 250; }
        else if (pk.type === 'bomb') { P.bombs = Math.min(P.maxBombs + 1, P.bombs + 1); }
        else P.buffs[pk.type] = d.frames;
        L.float(pk.x, pk.y - 14, d.label, d.color);
        Sfx.powerup();
    }

    // ── Objectives ───────────────────────────────────────────────────
    function startWave(n) {
        L.wave = n; L.waveQueue = buildWave(n); L.waveSpawnT = 0;
        L.announce(kind === 'endless' ? tr('WAVE {n}', { n }) : tr('WAVE {n} / {m}', { n, m: def.waves }), theme.hue);
        Sfx.levelUp();
    }
    /** Background pressure in open sectors: malware keeps coming from the dark */
    function trickle(every, cap) {
        if (L.t > 120 && L.t % Math.max(20, Math.round(every / L.diff.spawn)) === 0 && alive().filter(e => !e.guard || e.alerted).length < cap) spawnOne();
    }
    const secs = () => Math.ceil(Math.max(0, L.timer) / 60);

    function updateObjective() {
        const live = alive();
        switch (kind) {
            case 'waves':
            case 'endless': {
                if (L.wave === 0 && L.t === 90) startWave(1);
                if (L.wave > 0 && L.waveQueue.length && --L.waveSpawnT <= 0) {
                    spawnOne(L.waveQueue.shift());
                    L.waveSpawnT = Math.max(10, 28 - L.tier) / L.diff.spawn;
                }
                const bossAlive = L.boss && L.boss.hp > 0;
                if (L.wave > 0 && !L.waveQueue.length && !live.length && !bossAlive) {
                    if (L.waveDelay === 0) {
                        L.waveDelay = 100;
                        L.restoreHearts();
                    }
                    if (--L.waveDelay === 0) {
                        if (kind === 'waves' && L.wave >= def.waves) return win();
                        const next = L.wave + 1;
                        if (kind === 'endless' && next % 5 === 0) {
                            L.wave = next;
                            const bi = ((next / 5) - 1) % BOSSES.length;
                            L.boss = makeBoss(bi, L, 0.45 + next * 0.03);
                            L.announce(tr('WAVE {n} — {name}', { n: next, name: BOSSES[bi].name }), BOSSES[bi].color);
                            Sfx.warning();
                        } else startWave(next);
                    }
                }
                L.objective = kind === 'waves'
                    ? { label: tr('Wave {n} / {m}', { n: Math.max(1, L.wave), m: def.waves }), progress: (Math.max(0, L.wave - 1) + (L.waveQueue.length || live.length ? 0 : 1)) / def.waves }
                    : { label: tr('Wave {n}', { n: Math.max(1, L.wave) }), progress: null };
                if (kind === 'endless') { L.tier = Math.min(30, L.wave * 0.8); }
                break;
            }
            case 'survive':
            case 'protect':
            case 'honeypot':
            case 'defend': {
                L.timer--;
                const every = kind === 'honeypot' ? 14 : kind === 'defend' ? Math.max(48, 95 - L.tier * 1.5) / L.diff.spawn : Math.max(26, 85 - L.tier * 2.6) / L.diff.spawn;
                const cap = kind === 'honeypot' ? 26 : kind === 'defend' ? Math.round(Math.min(16, 8 + L.tier * 0.25) * L.diff.spawn) : Math.round(Math.min(26, 9 + L.tier * 0.5) * L.diff.spawn);
                if (L.t > 90 && L.t % Math.max(1, Math.round(every)) === 0 && live.length < cap) {
                    if (kind === 'honeypot') spawnOne(L.pick(['wormlet', 'drone', 'trojan', 'worm', 'miner']));
                    else if (kind === 'defend') { const s = L.pick(L.sensors.filter(x => x.hp > 0)); if (s) { const e = spawnNear(s.x, s.y, 460, 760); e.huntsSensor = Math.random() < 0.5; e.sensorRef = s; } }
                    else spawnOne();
                }
                if (kind !== 'honeypot' && L.t % 900 === 450) {          // a swarm every 15 s
                    L.restoreHearts();                                 // the previous 15 s were a round
                    L.say(tr('Incoming swarm!'), theme.hue);
                    const swarm = L.pool.includes('drone') ? 'drone' : L.pool.includes('scanbot') ? 'scanbot' : L.pool.includes('toolcall') ? 'toolcall' : 'wormlet';
                    for (let i = 0; i < 4 + Math.min(world, 8); i++) spawnOne(swarm);
                }
                const total = def.duration;
                const s0 = L.sensors[0];
                L.objective = {
                    label: kind === 'protect' ? tr('Scan {n}% — sensor {hp}/{max}', { n: Math.round(100 * (1 - L.timer / total)), hp: Math.max(0, Math.ceil(s0.hp)), max: s0.maxHp })
                         : kind === 'defend' ? tr('Hold {n}s — servers {a}/{m}', { n: secs(), a: L.sensors.filter(x => x.hp > 0).length, m: L.sensors.length })
                         : kind === 'honeypot' ? tr('Honeypot — {n}s — {b} bytes', { n: secs(), b: L.levelBytes }) : tr('Survive — {n}s', { n: secs() }),
                    progress: 1 - L.timer / total,
                };
                if (L.timer <= 0) {
                    for (const e of L.enemies) if (!e.dead && !e.def.static) { burst(e.x, e.y, 10, e.def.color); e.dead = true; }
                    win();
                }
                break;
            }
            case 'beacons': {
                if (L.t > 120 && L.t % Math.round(Math.max(60, 150 - L.tier * 4) / L.diff.spawn) === 0 && live.length < 6 + L.tier * 0.4) spawnOne();
                const left = live.filter(e => e.type === 'beacon').length;
                L.objective = { label: tr('C2 beacons — {n} / {m} down', { n: def.beacons - left, m: def.beacons }), progress: (def.beacons - left) / def.beacons };
                if (L.t > 120 && left === 0) win();
                break;
            }
            case 'boss': {
                const b = L.boss;
                L.objective = { label: b.name, progress: null };
                if (b.phase !== L.bossPhase) { L.bossPhase = b.phase; if (b.phase === 2 && def.radio && def.radio[1]) L.radio(def.radio[1]); }
                if (b.hp <= 0 && !L.endingT) {
                    L.endingT = 150; L.ebullets.length = 0; L.beams.length = 0; L.zones.length = 0;
                    L.hazards.forEach(h => { h.life = Math.min(h.life, 30); });
                    for (const e of L.enemies) e.dead = true;
                    L.announce(tr('{name} NEUTRALIZED', { name: b.name }), b.def.color);
                    Sfx.bossRoar();
                }
                if (L.endingT) {
                    if (L.endingT % 12 === 0) L.explosion(b.x + rand(-60, 60), b.y + rand(-60, 60), 70, L.pick([b.def.color, '#fff', '#ffd166']), false);
                    if (--L.endingT === 1) { for (let i = 0; i < 25; i++) dropPickup('byte', b.x, b.y); b.cleanup(); L.boss = null; win(); }
                }
                break;
            }
            case 'keys': {
                trickle(Math.max(80, 170 - L.tier * 2), 8 + L.tier * 0.25);
                let got = 0;
                for (const k of L.keys) {
                    k.t++;
                    if (k.got) { got++; continue; }
                    if (dist2(k.x, k.y, P.x, P.y) < 650 * 650) k.seen = true;
                    if (dist2(k.x, k.y, P.x, P.y) < 44 * 44) {
                        k.got = true; got++;
                        L.announce(tr('KEY {n} / {m}', { n: got, m: L.keys.length }), '#ffd166');
                        burst(k.x, k.y, 30, '#ffd166', 5); Sfx.powerup();
                        L.particles.push({ kind: 'ring', x: k.x, y: k.y, r: 10, max: 160, life: 26, t: 0, color: '#ffd166' });
                        if (got % 2 === 0) L.restoreHearts();
                        if (got === L.keys.length) { L.exit.open = true; L.say(tr('All keys found — the exit gate is open!'), '#ffd166'); L.announce(tr('EXIT OPEN'), '#4be08a'); Sfx.levelUp(); }
                    }
                }
                // a ping towards the nearest key nobody has seen yet
                if (L.t % 540 === 200) {
                    const left = L.keys.filter(k => !k.got).sort((a, b) => dist2(a.x, a.y, P.x, P.y) - dist2(b.x, b.y, P.x, P.y));
                    if (left.length) { L.ping = { x: left[0].x, y: left[0].y, t: 0 }; Sfx.telegraph(); }
                }
                const all = got === L.keys.length;
                L.objective = all ? { label: tr('Reach the exit gate'), progress: 1 } : { label: tr('Keys {n} / {m}', { n: got, m: L.keys.length }), progress: got / L.keys.length };
                if (all && dist2(L.exit.x, L.exit.y, P.x, P.y) < L.exit.r ** 2) win();
                break;
            }
            case 'escort': {
                const c = L.sensors[0];
                if (c.hp > 0) {
                    const near = dist2(c.x, c.y, P.x, P.y) < 380 * 380;
                    c.waiting = !near;
                    const wp = c.path[c.wpi];
                    if (wp && near) {
                        const a = Math.atan2(wp.y - c.y, wp.x - c.x), sp = 1.15;
                        c.x += Math.cos(a) * sp; c.y += Math.sin(a) * sp; c.travelled += sp;
                        if (dist2(c.x, c.y, wp.x, wp.y) < 9) c.wpi++;
                    }
                    if (!wp) return win();
                }
                if (L.t > 120 && L.t % Math.max(30, Math.round((110 - L.tier * 1.5) / L.diff.spawn)) === 0 && alive().length < 8 + L.tier * 0.3) {
                    const e = spawnNear(c.x + 300, c.y, 520, 820);
                    e.huntsSensor = Math.random() < 0.55; e.sensorRef = c;
                }
                const prog = Math.min(1, c.travelled / L.pathLen);
                if (!L.radioMid && prog > 0.5 && def.radio && def.radio[1]) { L.radioMid = true; L.radio(def.radio[1]); }
                L.objective = { label: tr('Convoy {n}% — integrity {hp}/{max}', { n: Math.round(prog * 100), hp: Math.max(0, Math.ceil(c.hp)), max: c.maxHp }) + (c.waiting ? tr(' — WAITING FOR YOU') : ''), progress: prog };
                break;
            }
            case 'capture': {
                trickle(Math.max(70, 150 - L.tier * 2), 9 + L.tier * 0.3);
                let done = 0;
                for (const r of L.relays) {
                    r.t++;
                    if (r.done) { done++; continue; }
                    const inside = dist2(r.x, r.y, P.x, P.y) < r.r * r.r;
                    r.active = inside;
                    if (inside) {
                        r.prog = Math.min(1, r.prog + 1 / ((def.capTime || 5) * 60));
                        if (L.t % 75 === 0 && alive().length < 14) spawnNear(r.x, r.y, 520, 760);
                        if (r.prog >= 1) {
                            r.done = true; done++;
                            L.announce(tr('RELAY {n} / {m} CAPTURED', { n: done, m: L.relays.length }), theme.hue);
                            L.particles.push({ kind: 'ring', x: r.x, y: r.y, r: 20, max: 260, life: 30, t: 0, color: theme.hue });
                            L.restoreHearts(); Sfx.levelUp();
                        }
                    }
                }
                const cur = L.relays.find(r => r.active && !r.done);
                L.objective = { label: tr('Relays {n} / {m}', { n: done, m: L.relays.length }) + (cur ? tr(' — capturing {p}%', { p: Math.round(cur.prog * 100) }) : ''), progress: (done + (cur ? cur.prog : 0)) / L.relays.length };
                if (done === L.relays.length) win();
                break;
            }
            case 'pursuit': {
                trickle(Math.max(90, 180 - L.tier * 2), 7 + L.tier * 0.25);
                const c = L.courier;
                if (c.escaped && !c.dead) { L.removeEnemy(c); return lose(tr('Data exfiltrated')); }
                if (c.dead && !c.removed) return win();
                const leftWp = Math.max(0, L.courierPath.length - (c.wpi || 0));
                if (!L.radioMid && c.hp < c.maxHp * 0.5 && def.radio && def.radio[1]) { L.radioMid = true; L.radio(def.radio[1]); }
                L.objective = { label: tr('Courier {hp}% — {n} hops to the exit', { hp: Math.max(0, Math.round(100 * c.hp / c.maxHp)), n: leftWp }), progress: 1 - c.hp / c.maxHp };
                break;
            }
            case 'dark': {
                trickle(Math.max(80, 160 - L.tier * 2), 8 + L.tier * 0.25);
                const targets = L.enemies.filter(e => e.isTarget && !e.dead);
                const total = def.targets || 6;
                L.objective = { label: tr('Implants {n} / {m}', { n: total - targets.length, m: total }), progress: (total - targets.length) / total };
                if (L.t > 60 && !targets.length) win();
                break;
            }
            case 'purge': {
                const shards = L.enemies.filter(e => e.type === 'shard' && !e.dead);
                if (L.wave === 0 && L.t === 80) startPurge(1);
                if (L.wave > 0 && !shards.length && !L.waveDelay) {
                    L.waveDelay = 90; L.restoreHearts();
                }
                if (L.waveDelay > 0 && --L.waveDelay === 0) {
                    if (L.wave >= def.waves) return win();
                    startPurge(L.wave + 1);
                }
                if (L.wave > 0 && L.t % Math.max(60, Math.round(160 / L.diff.spawn)) === 0 && alive().length - shards.length < 4 + L.wave) spawnOne(L.pick(L.pool.filter(k => k !== 'shard' && !ENEMIES[k].static)));
                L.objective = { label: tr('Shard wave {n} / {m} — {s} left', { n: Math.max(1, L.wave), m: def.waves, s: shards.length }), progress: (Math.max(0, L.wave - 1) + (shards.length ? 0 : 1)) / def.waves };
                break;
            }
            case 'gauntlet': {
                if (L.t > 150 && L.t % Math.max(40, Math.round((120 - L.tier) / L.diff.spawn)) === 0 && alive().length < 8 + L.tier * 0.2) {
                    const x = clamp(P.x + rand(650, 900), 60, L.aw - 60), y = rand(80, L.ah - 80);
                    if (!inRock(x, y, 30)) L.spawnEnemy(pickType(false), x, y);
                }
                const prog = clamp((P.x - 220) / (L.exit.x - 220), 0, 1);
                if (!L.radioMid && prog > 0.5 && def.radio && def.radio[1]) { L.radioMid = true; L.radio(def.radio[1]); }
                L.objective = { label: tr('Corridor {n}%', { n: Math.round(prog * 100) }), progress: prog };
                if (dist2(L.exit.x, L.exit.y, P.x, P.y) < L.exit.r ** 2) win();
                break;
            }
            case 'triage': {
                if (L.t > 60 && L.t % 42 === 0 && L.enemies.filter(e => e.def.benign && !e.dead).length < 8) {
                    const left = Math.random() < 0.5;
                    L.spawnEnemy('benign', left ? 20 : W - 20, rand(70, H - 70), { spawnT: 0 });
                }
                const every = Math.max(28, Math.round((70 - L.tier) / L.diff.spawn));
                if (L.t > 90 && L.t % every === 0 && alive().length < 7 + L.tier * 0.2) {
                    const type = pickType(false);
                    const fromSide = Math.random() < 0.6;
                    const y = rand(70, H - 70), x = fromSide ? (Math.random() < 0.5 ? 30 : W - 30) : rand(80, W - 80);
                    const e = L.spawnEnemy(type, x, fromSide ? y : (Math.random() < 0.5 ? 30 : H - 30));
                    if (Math.random() < 0.3 && !ENEMIES[type].static) e.disguised = true;
                }
                const quota = def.quota || 25;
                if (!L.radioMid && L.malicious >= quota / 2 && def.radio && def.radio[1]) { L.radioMid = true; L.radio(def.radio[1]); }
                L.objective = { label: tr('Malicious {n} / {m} — false positives {f} / {x}', { n: Math.min(L.malicious, quota), m: quota, f: L.fp, x: def.maxFp ?? 5 }), progress: Math.min(1, L.malicious / quota) };
                if (L.malicious >= quota) {
                    for (const e of L.enemies) if (!e.dead && !e.def.benign) { burst(e.x, e.y, 10, e.def.color); e.dead = true; }
                    win();
                }
                break;
            }
        }
        // mid-level radio for the timed kinds
        if (!L.radioMid && def.radio && def.radio[1] && L.objective.progress !== null && L.objective.progress >= 0.5 && kind !== 'boss') {
            L.radioMid = true; L.radio(def.radio[1]);
        }
    }

    function startPurge(n) {
        L.wave = n;
        const count = Math.round((2 + n) * (L.diff.spawn > 1 ? 1.2 : 1));
        for (let i = 0; i < count; i++) {
            const edge = i % 4, x = edge === 0 ? 40 : edge === 1 ? W - 40 : rand(80, W - 80), y = edge >= 2 ? (edge === 2 ? 40 : H - 40) : rand(80, H - 80);
            const a = Math.atan2(H / 2 - y, W / 2 - x) + rand(-0.6, 0.6), s = rand(0.8, 1.4);
            L.spawnEnemy('shard', x, y, { size: 3, vx: Math.cos(a) * s, vy: Math.sin(a) * s });
        }
        L.announce(tr('SHARD WAVE {n} / {m}', { n, m: def.waves }), theme.hue);
        Sfx.levelUp();
    }

    function stars() {
        const crit = [{ label: tr('Complete the level'), ok: true }];
        const s = L.t / 60;
        const maxHits = kind === 'boss' ? 3 : 2;
        crit.push({ label: tr('Take {n} hits or fewer', { n: maxHits }), ok: L.hits <= maxHits });
        if (kind === 'survive') crit.push({ label: tr('Take no hit at all'), ok: L.hits === 0 });
        else if (kind === 'protect') crit.push({ label: tr('Sensor above 70%'), ok: L.sensors[0].hp >= L.sensors[0].maxHp * 0.7 });
        else if (kind === 'escort') crit.push({ label: tr('Convoy above 70%'), ok: L.sensors[0].hp >= L.sensors[0].maxHp * 0.7 });
        else if (kind === 'defend') crit.push({ label: tr('Lose no server'), ok: L.serversLost === 0 });
        else if (kind === 'triage') crit.push({ label: tr('No false positive'), ok: L.fp === 0 });
        else if (kind === 'honeypot') { const goal = 120 + Math.min(world, 8) * 30; crit.push({ label: tr('Collect {n} bytes', { n: goal }), ok: L.levelBytes >= goal }); }
        else crit.push({ label: tr('Finish under {n}s', { n: def.par }), ok: s <= def.par });
        return { crit, stars: crit.filter(c => c.ok).length };
    }

    function finishResult(won, reason) {
        const s = won ? stars() : { crit: [], stars: 0 };
        const bytes = Math.round(L.levelBytes * L.diff.bytes * (won ? 1 : 0.5));
        L.result = {
            won, reason, stars: s.stars, crit: s.crit, score: L.score + (won ? Math.round(P.hp * 300 + L.levelBytes * 5) : 0),
            bytes, time: Math.round(L.t / 60), hits: L.hits, kills: L.kills, maxCombo: L.maxCombo, wave: L.wave,
            hpLeft: P.hp, maxHp: P.maxHp, bombsLeft: P.bombs, stats: L.stats,
            bossName: L.boss ? (L.boss.name || null) : null,
        };
        L.finished = true;
        L.finishT = 70;
    }
    function win() { if (L.finished) return; Sfx.victory(); finishResult(true); }
    function lose(reason) { if (L.finished) return; Sfx.gameOver(); finishResult(false, reason); }

    // ── Collisions with the world ────────────────────────────────────
    function collideRocks(o, bounce = 0.5) {
        for (const k of L.rocks) {
            const dx = o.x - k.x, dy = o.y - k.y, min = k.r + o.r;
            const d2 = dx * dx + dy * dy;
            if (d2 < min * min && d2 > 0.01) {
                const d = Math.sqrt(d2), nx = dx / d, ny = dy / d;
                o.x = k.x + nx * min; o.y = k.y + ny * min;
                const dot = o.vx * nx + o.vy * ny;
                if (dot < 0) { o.vx -= (1 + bounce) * dot * nx; o.vy -= (1 + bounce) * dot * ny; }
            }
        }
    }
    function gateHits(g) {
        // returns true if the gate is deadly at the player's position
        const top = 0, bot = L.ah;
        if (g.type === 'blink') return g.on && Math.abs(P.x - g.x) < P.r + 8;
        if (g.type === 'gap') return Math.abs(P.x - g.x) < P.r + 8 && Math.abs(P.y - g.gapY) > g.gapW / 2 - P.r;
        if (g.type === 'sweep') {
            for (let k = 0; k < 2; k++) {
                const a = g.a + k * Math.PI;
                if (segDist(P.x, P.y, g.x, L.ah / 2, g.x + Math.cos(a) * g.arm, L.ah / 2 + Math.sin(a) * g.arm) < P.r + 6) return true;
            }
            return false;
        }
        return top > bot;
    }
    function updateGates() {
        for (const g of L.gates) {
            if (g.type === 'blink') { const c = (L.t + g.phase) % 160; g.on = c < 75; g.warn = c >= 140; }
            else if (g.type === 'gap') g.gapY = L.ah / 2 + Math.sin(L.t * 0.012 + g.phase) * (L.ah / 2 - 170);
            else g.a += g.spin;
            if (gateHits(g) && P.inv <= 0) {
                hurt();
                P.vx = (P.x < g.x ? -1 : 1) * 7;
                L.float(P.x, P.y - 26, tr('FIREWALL!'), '#ff5d73');
            }
        }
    }

    // ── Per-frame update ─────────────────────────────────────────────
    L.update = (input) => {
        L.t++;
        if (L.finished) {
            updateParticles();
            if (--L.finishT === 0) env.callbacks.onEnd(L.result);
            return;
        }
        if (L.boss && L.bossIntroT > 0) { L.bossIntroT--; L.boss.update(); updateParticles(); updateCamera(); return; }
        if (!L.radioSaid && L.t > 40) { L.radioSaid = true; if (L.radioStart) L.radio(L.radioStart); }

        // ── controls: "classic" (turn + thrust, like the original
        // Starfield) or "twin" (move with WASD, aim with the mouse) ──
        const st = input.state;
        const inv = L.invertT > 0 ? -1 : 1;
        const padAim = st.pad && (Math.abs(st.pad.rx) > 0.2 || Math.abs(st.pad.ry) > 0.2);
        let mx = 0, my = 0;
        if (scheme === 'classic') {
            const turn = ((input.act('left') ? -1 : 0) + (input.act('right') ? 1 : 0) + (st.pad ? st.pad.lx : 0)) * inv;
            P.angle += clamp(turn, -1, 1) * 0.075;
            if (padAim) P.angle = Math.atan2(st.pad.ry * inv, st.pad.rx * inv);
            let thrust = (input.act('up') || (st.pad && st.pad.ly < -0.4)) ? 1 : 0;
            let brake = input.act('down') || (st.pad && st.pad.ly > 0.4);
            if (inv < 0) { const t0 = thrust; thrust = brake ? 1 : 0; brake = !!t0; }
            if (P.dashT > 0) P.dashT--;
            else {
                P.vx += Math.cos(P.angle) * thrust * 0.36;
                P.vy += Math.sin(P.angle) * thrust * 0.36;
                const fr = brake ? 0.9 : 0.985;
                P.vx *= fr; P.vy *= fr;
                const sp = Math.hypot(P.vx, P.vy), max = P.speed * 1.3;
                if (sp > max) { P.vx *= max / sp; P.vy *= max / sp; }
            }
            P.thrust = thrust;
            mx = Math.cos(P.angle); my = Math.sin(P.angle);          // dash goes forward
        } else {
            if (st.mouseActive < 2) mouseUsed = true;                 // once the mouse moved, it aims
            [mx, my] = input.move();
            mx *= inv; my *= inv;
            if (mx || my) lastMove = [mx, my];
            const wmx = st.mx + L.cam.x, wmy = st.my + L.cam.y;      // the mouse, in the sector
            if (padAim) P.angle = Math.atan2(st.pad.ry, st.pad.rx);
            else if (mouseUsed) P.angle = Math.atan2(wmy - P.y, wmx - P.x);
            else {
                let target = null;
                if (env.settings?.assist === true) {
                    let bd = Infinity;
                    const cands = L.enemies.filter(e => !e.dead && hittable(e) && e.alpha > 0.3 && !e.def.benign && !e.disguised && onScreen(e.x, e.y, 0));
                    if (L.boss && !L.boss.entering) L.boss.targets().filter(t => !t.shielded).forEach(t => cands.push(t));
                    for (const e of cands) { const d = dist2(e.x, e.y, P.x, P.y); if (d < bd) { bd = d; target = e; } }
                }
                P.angle = target ? Math.atan2(target.y - P.y, target.x - P.x) : Math.atan2(lastMove[1], lastMove[0]);
            }
            if (P.dashT > 0) P.dashT--;
            else {
                P.vx += (mx * P.speed - P.vx) * 0.18;
                P.vy += (my * P.speed - P.vy) * 0.18;
            }
            P.thrust = Math.min(1, Math.hypot(mx, my));
        }
        if (P.pulled) {
            const src = P.pulled;
            const a = Math.atan2(src.y - P.y, src.x - P.x);
            P.vx += Math.cos(a) * 0.9; P.vy += Math.sin(a) * 0.9;
            if (--src.frames <= 0) P.pulled = null;
        }
        if (L.wind) {
            L.wind.a += Math.sin(L.t * 0.004) * 0.006;
            if (P.dashT === 0) { P.vx += Math.cos(L.wind.a) * L.wind.k; P.vy += Math.sin(L.wind.a) * L.wind.k; }
        }
        if (L.gravity) {
            const g = L.gravity, a = Math.atan2(g.y - P.y, g.x - P.x);
            if (P.dashT === 0) { P.vx += Math.cos(a) * g.k; P.vy += Math.sin(a) * g.k; }
            L.gravity = null;
        }
        if (P.slowT > 0) { P.slowT--; P.vx *= 0.9; P.vy *= 0.9; }
        P.x = clamp(P.x + P.vx, 16, L.aw - 16);
        P.y = clamp(P.y + P.vy, 16, L.ah - 16);
        if (L.rocks.length) collideRocks(P, 0.4);
        P.history.push({ x: P.x, y: P.y, hp: P.hp });
        if (P.history.length > 180) P.history.shift();
        if (P.thrust > 0 && L.t % 2 === 0) {
            const a = P.angle + Math.PI + rand(-0.3, 0.3);
            L.particles.push({ kind: 'spark', x: P.x + Math.cos(P.angle + Math.PI) * 14, y: P.y + Math.sin(P.angle + Math.PI) * 14, vx: Math.cos(a) * 2 + P.vx * 0.5, vy: Math.sin(a) * 2 + P.vy * 0.5, life: 16, t: 0, color: env.skin.flame, size: 2.5 });
        }
        updateCamera();

        // actions
        const wantFire = (scheme === 'twin' && st.mouseDown) || input.act('fire') || (st.pad && st.pad.fire);
        if (wantFire) fire();
        if (input.actHit('dash') || (scheme === 'twin' && input.hit('Mouse2')) || (st.pad && st.pad.dash)) dash(mx, my);
        if (input.actHit('bomb') || (st.pad && st.pad.bomb)) bomb();
        if (input.actHit('special') || (st.pad && st.pad.special)) special();
        const prevWeapon = P.weapon;
        weapons.forEach((wp, i) => { if (input.hit(`Digit${WEAPONS.indexOf(wp) + 1}`)) P.weapon = i; });
        if (input.actHit('weapon') || st.wheel > 0 || (st.pad && st.pad.next)) P.weapon = (P.weapon + 1) % weapons.length;
        if (st.wheel < 0 || (st.pad && st.pad.prev)) P.weapon = (P.weapon - 1 + weapons.length) % weapons.length;
        if (P.weapon !== prevWeapon) L.stats.weaponSwitches++;

        if (P.cool > 0) P.cool--;
        if (P.inv > 0) P.inv--;
        if (P.dashCd > 0) P.dashCd--;
        if (P.specialCd > 0) P.specialCd--;
        if (P.specialT > 0 && --P.specialT === 0) L.slow = false;
        if (P.disarmed > 0) P.disarmed--;
        for (const k in P.buffs) if (P.buffs[k] > 0) P.buffs[k]--;
        if (L.comboT > 0 && --L.comboT === 0) L.combo = 0;
        if (L.invertT > 0) L.invertT--;
        if (L.lightT > 0) L.lightT--;
        if (L.hurtT > 0) L.hurtT--;

        // the scanner pulse of dark levels, every few seconds
        if (L.dark && L.t % 320 === 100) scanPulse(700, false);
        if (L.pulse) {
            const pu = L.pulse;
            pu.t++; pu.r = pu.max * Math.min(1, pu.t / 50);
            for (const e of L.enemies) if (!e.seen && dist2(e.x, e.y, pu.x, pu.y) < pu.r * pu.r) { e.seen = true; e.revealT = 200; }
            for (const k of L.keys) if (dist2(k.x, k.y, pu.x, pu.y) < pu.r * pu.r) k.seen = true;
            for (const e of L.enemies) if (dist2(e.x, e.y, pu.x, pu.y) < pu.r * pu.r && dist2(e.x, e.y, pu.x, pu.y) > (pu.r - 60) ** 2) e.revealT = 200;
            if (pu.t > 70) L.pulse = null;
        }

        updateObjective();
        if (L.finished) { updateParticles(); return; }
        if (L.gates.length) updateGates();

        // ── the CRS Beam (continuous laser) ──
        if (L.beamT > 0) {
            L.beamT--;
            const wp = WEAPONS.find(w => w.id === 'beam');
            let len = wp.range;
            const ex = Math.cos(P.angle), ey = Math.sin(P.angle);
            for (const k of L.rocks) {             // the beam stops on the first rock
                const fx = k.x - P.x, fy = k.y - P.y, tproj = fx * ex + fy * ey;
                if (tproj > 0 && tproj < len) { const dd = Math.hypot(fx - ex * tproj, fy - ey * tproj); if (dd < k.r) len = Math.min(len, tproj - Math.sqrt(k.r * k.r - dd * dd)); }
            }
            const x2 = P.x + ex * len, y2 = P.y + ey * len;
            L.beamLine = { x1: P.x + ex * 16, y1: P.y + ey * 16, x2, y2 };
            const d = wp.dmg * pdmg();
            for (const e of L.enemies) if (!e.dead && hittable(e) && segDist(e.x, e.y, P.x, P.y, x2, y2) < e.r + 6) { if (!deflects(e, { x: P.x, y: P.y, pierce: false })) damageEnemy(e, d, 'shot'); }
            if (L.boss && !L.boss.entering && L.boss.hp > 0) for (const tg of L.boss.targets()) if (!tg.shielded && segDist(tg.x, tg.y, P.x, P.y, x2, y2) < tg.r + 4) tg.hit(d);
            if (L.t % 3 === 0) L.particles.push({ kind: 'spark', x: x2, y: y2, vx: rand(-2, 2), vy: rand(-2, 2), life: 12, t: 0, color: wp.color, size: 3 });
        } else L.beamLine = null;

        // player bullets
        const clouds = L.enemies.filter(e => e.type === 'obfusc' && !e.dead && e.spawnT <= 0);
        for (const b of L.bullets) {
            b.age++;
            if (b.homing) {
                let best = null, bd = 380 * 380;
                for (const e of L.enemies) if (!e.dead && hittable(e) && !e.def.benign && !e.disguised) { const d = dist2(e.x, e.y, b.x, b.y); if (d < bd) { bd = d; best = e; } }
                if (!best && L.boss && !L.boss.entering) for (const t of L.boss.targets()) { if (t.shielded) continue; const d = dist2(t.x, t.y, b.x, b.y); if (d < bd) { bd = d; best = t; } }
                if (best) {
                    const a = Math.atan2(best.y - b.y, best.x - b.x), sp = Math.hypot(b.vx, b.vy) + 0.12;
                    const cur = Math.atan2(b.vy, b.vx);
                    let d = ((a - cur + Math.PI * 3) % TAU) - Math.PI;
                    const na = cur + clamp(d, -0.12, 0.12);
                    b.vx = Math.cos(na) * Math.min(sp, 11); b.vy = Math.sin(na) * Math.min(sp, 11);
                }
                if (L.t % 2 === 0) L.particles.push({ kind: 'spark', x: b.x, y: b.y, vx: 0, vy: 0, life: 14, t: 0, color: b.color, size: 2 });
            }
            if (b.boomerang && b.age > 28) {
                const a = Math.atan2(P.y - b.y, P.x - b.x), sp = Math.min(16, Math.hypot(b.vx, b.vy) + 0.6);
                b.vx += (Math.cos(a) * sp - b.vx) * 0.15; b.vy += (Math.sin(a) * sp - b.vy) * 0.15;
                if (dist2(b.x, b.y, P.x, P.y) < 26 * 26) { b.life = 0; continue; }
            }
            b.x += b.vx; b.y += b.vy; b.life--;
            if (b.x < -20 || b.x > L.aw + 20 || b.y < -20 || b.y > L.ah + 20) b.life = 0;
            if (b.life > 0 && L.rocks.length && inRock(b.x, b.y, b.r)) { b.life = 0; burst(b.x, b.y, 3, '#bbb', 2); }
            if (b.life > 0 && clouds.length) {
                for (const c of clouds) if (dist2(b.x, b.y, c.x, c.y) < CLOUD_R * CLOUD_R && dist2(b.x, b.y, c.x, c.y) > (c.r + 8) ** 2 && Math.random() < 0.07) { b.life = 0; L.particles.push({ kind: 'spark', x: b.x, y: b.y, vx: 0, vy: 0, life: 18, t: 0, color: '#b0c4ff', size: 4 }); break; }
            }
            if (b.life <= 0) { if (b.blast) flakBurst(b); continue; }
            for (const e of L.enemies) {
                if (e.dead || !hittable(e) || (b.hitIds && b.hitIds.has(e))) continue;
                if (dist2(b.x, b.y, e.x, e.y) < (b.r + e.r) ** 2) {
                    if (deflects(e, b)) { b.life = 0; burst(b.x, b.y, 4, '#ffd166', 2); Sfx.hit(); break; }
                    damageEnemy(e, b.dmg, 'shot');
                    if (b.chain) chainFrom(e, b);
                    if (b.blast) { b.life = 0; flakBurst(b); break; }
                    if (b.hitIds) b.hitIds.add(e); else { b.life = 0; break; }
                }
            }
            if (b.life > 0 && L.boss && !L.boss.entering && L.boss.hp > 0) {
                for (const tg of L.boss.targets()) {
                    if (dist2(b.x, b.y, tg.x, tg.y) < (b.r + tg.r) ** 2) {
                        if (tg.shielded) { burst(b.x, b.y, 3, '#c08bff', 2); b.life = 0; break; }
                        tg.hit(b.dmg); Sfx.hit();
                        if (b.blast) { b.life = 0; flakBurst(b); break; }
                        if (!b.pierce) { b.life = 0; break; }
                    }
                }
            }
        }
        L.bullets = L.bullets.filter(b => b.life > 0);

        // enemies
        const ips = P.specialT > 0 && env.skin.special?.id === 'ips';
        for (const e of L.enemies) {
            if (e.dead) continue;
            updateEnemy(e, L);
            if (e.dead) continue;
            if (e.hp <= 0) { killEnemy(e, e.ally ? 'area' : 'shot'); continue; }
            if (e.spawnT > 0 || e.alpha < 0.3 || e.ally || e.def.benign || e.frozen > 0) continue;
            if (dist2(e.x, e.y, P.x, P.y) < (e.r + P.r) ** 2 && e.type !== 'decoy') {
                if (e.type === 'latch') {
                    if (!e.latched && P.inv <= 0 && P.dashT === 0) { e.latched = true; e.latchT = 0; e.latchA = Math.atan2(e.y - P.y, e.x - P.x); L.float(P.x, P.y - 24, tr('HOOKED — DASH!'), '#c0ff5b'); Sfx.telegraph(); }
                    continue;
                }
                if (e.type === 'locker' && P.inv <= 0) { P.disarmed = 120; L.float(P.x, P.y - 24, 'ENCRYPTED!', '#ff7a3c'); }
                hurt();
                if (!e.def.static && e.type !== 'locker' && e.type !== 'courier') damageEnemy(e, 2, 'area');
            }
            for (const s of L.sensors) {
                if (s.hp <= 0 || e.def.static) continue;
                if (dist2(e.x, e.y, s.x, s.y) < (e.r + s.r) ** 2) {
                    if (e.t % 30 === 0) damageSensor(s, 1);
                    e.vx -= (s.x - e.x) * 0.01; e.vy -= (s.y - e.y) * 0.01;
                }
            }
        }
        if (ips && L.t % 10 === 0) {
            for (const e of L.enemies) if (!e.dead && hittable(e) && !e.def.benign && dist2(e.x, e.y, P.x, P.y) < (IPS_R + e.r) ** 2) damageEnemy(e, 0.8 * P.dmgMul, 'area');
        }
        L.enemies = L.enemies.filter(e => !e.dead);

        // ship powers still running
        updatePowers();

        // boss
        if (L.boss && L.boss.hp > 0) {
            L.boss.update();
            if (!L.boss.entering) {
                for (const tg of L.boss.targets()) {
                    if (dist2(tg.x, tg.y, P.x, P.y) < (tg.r * 0.8 + P.r) ** 2 && (L.boss.alpha ?? 1) > 0.3) hurt();
                }
                if (L.boss.tethers) for (const [x1, y1, x2, y2] of L.boss.tethers()) if (segDist(P.x, P.y, x1, y1, x2, y2) < P.r + 4) hurt();
            }
            if (env.callbacks.onBoss) env.callbacks.onBoss(L.boss);
        } else if (L.boss && kind !== 'boss') {
            // endless: a boss between waves just blows up and pays out
            const b = L.boss;
            for (let i = 0; i < 4; i++) L.explosion(b.x + rand(-50, 50), b.y + rand(-50, 50), 80, b.def.color, false);
            for (let i = 0; i < 20; i++) dropPickup('byte', b.x, b.y);
            L.score += 5000; L.float(b.x, b.y, '+5000', '#ffd166');
            L.ebullets.length = 0; L.beams.length = 0; L.zones.length = 0;
            b.cleanup();
            L.hazards.forEach(h => { h.life = Math.min(h.life, 20); });
            for (const e of L.enemies) if (e.fromBoss) e.fromBoss = false;
            L.boss = null;
            if (env.callbacks.onBoss) env.callbacks.onBoss(null);
        } else if (L.boss && env.callbacks.onBoss) env.callbacks.onBoss(L.boss);

        // enemy bullets (half speed under Sigma's Correlation, dropped in Suricata's IPS field,
        // reflected by OWASP CRS's Paranoia, frozen in Plum Island's net, swallowed by Elastic's well)
        const bs = L.slow ? 0.5 : 1;
        const paranoia = P.specialT > 0 && env.skin.special?.id === 'paranoia';
        for (const b of L.ebullets) {
            let frozen = false;
            for (const n of L.nets) if (dist2(b.x, b.y, n.x, n.y) < n.r * n.r) { frozen = true; break; }
            if (!frozen) { b.x += b.vx * bs; b.y += b.vy * bs; b.life--; }
            if (b.x < -40 || b.x > L.aw + 40 || b.y < -40 || b.y > L.ah + 40) b.life = 0;
            if (b.life > 0 && L.rocks.length && inRock(b.x, b.y, b.r * 0.5)) b.life = 0;
            if (ips && dist2(b.x, b.y, P.x, P.y) < IPS_R * IPS_R) { b.life = 0; if (Math.random() < 0.3) burst(b.x, b.y, 2, env.skin.glow, 1); }
            if (b.life > 0 && paranoia && dist2(b.x, b.y, P.x, P.y) < PARANOIA_R * PARANOIA_R) {
                b.life = 0;
                const a = Math.atan2(b.y - P.y, b.x - P.x);
                pushBullet({ x: b.x, y: b.y, vx: Math.cos(a) * 9, vy: Math.sin(a) * 9, r: 5, dmg: 1.4 * P.dmgMul, life: 80, color: env.skin.glow, id: 'pulse' });
            }
            if (b.life <= 0 || frozen) continue;
            if (dist2(b.x, b.y, P.x, P.y) < (b.r + P.r - 3) ** 2) {
                b.life = 0;
                if (b.kind === 'hook' && P.inv <= 0) { P.pulled = { x: b.x - b.vx * 30, y: b.y - b.vy * 30, frames: 50 }; L.float(P.x, P.y - 24, 'HOOKED!', '#3ee0c8'); }
                hurt();
            } else {
                for (const s of L.sensors) {
                    if (s.hp > 0 && dist2(b.x, b.y, s.x, s.y) < (b.r + s.r) ** 2) { b.life = 0; damageSensor(s, b.dmg); break; }
                }
            }
        }
        L.ebullets = L.ebullets.filter(b => b.life > 0);
        if (L.ebullets.length > 700) L.ebullets.splice(0, L.ebullets.length - 700);

        // hazards
        for (const bm of L.beams) {
            bm.t++;
            if (bm.owner && bm.owner.dead && bm.t <= bm.tele) bm.cancel = true;
            if (bm.follow) { bm.x = bm.follow.x; bm.y = bm.follow.y; }
            if (bm.t > bm.tele) bm.angle += bm.rot;
            if (bm.t === bm.tele && bm.active) Sfx.beam();
            if (!bm.cancel && bm.t > bm.tele && bm.t <= bm.tele + bm.active) {
                const x2 = bm.x + Math.cos(bm.angle) * bm.len, y2 = bm.y + Math.sin(bm.angle) * bm.len;
                if (segDist(P.x, P.y, bm.x, bm.y, x2, y2) < bm.width / 2 + P.r - 2) hurt();
            }
        }
        L.beams = L.beams.filter(bm => !bm.cancel && bm.t <= bm.tele + bm.active + 10);
        for (const z of L.zones) {
            z.t++;
            if (z.t > z.tele && z.t <= z.tele + z.active && P.x > z.x && P.x < z.x + z.w && P.y > z.y && P.y < z.y + z.h) hurt();
        }
        L.zones = L.zones.filter(z => z.t <= z.tele + z.active);
        for (const h of L.hazards) {
            h.t++; h.life--;
            if (h.t > h.arm && h.life > 0 && dist2(h.x, h.y, P.x, P.y) < (h.r * 0.85 + P.r) ** 2) hurt();
        }
        L.hazards = L.hazards.filter(h => h.life > 0);

        // pickups
        for (const pk of L.pickups) {
            pk.t++; pk.life--;
            const d2 = dist2(pk.x, pk.y, P.x, P.y);
            const mag = pk.type === 'byte' ? P.magnet : 40;
            if (d2 < mag * mag) {
                const a = Math.atan2(P.y - pk.y, P.x - pk.x);
                pk.vx += Math.cos(a) * 0.9; pk.vy += Math.sin(a) * 0.9;
            }
            pk.vx *= 0.92; pk.vy *= 0.92;
            pk.x = clamp(pk.x + pk.vx, 10, L.aw - 10); pk.y = clamp(pk.y + pk.vy, 10, L.ah - 10);
            if (d2 < (P.r + 14) ** 2) { collect(pk); pk.life = 0; }
        }
        L.pickups = L.pickups.filter(pk => pk.life > 0);
        for (const s of L.sensors) {
            if (s.flash > 0) s.flash--; if (s.hitT > 0) s.hitT--;
            // the servers defend themselves a little: one shot at the closest malware
            if (s.turret && s.hp > 0 && L.t % 40 === 0) {
                const [e] = nearestTargets(s.x, s.y, 320, 1);
                if (e) { const a = Math.atan2(e.y - s.y, e.x - s.x); pushBullet({ x: s.x, y: s.y, vx: Math.cos(a) * 10, vy: Math.sin(a) * 10, r: 4, dmg: 1.2, life: 40, color: '#5be7ff', id: 'pulse' }); }
            }
        }
        for (const k of L.rocks) k.rot += k.spin;
        if (L.ping && ++L.ping.t > 150) L.ping = null;

        updateParticles();
    };

    function flakBurst(b) {
        L.particles.push({ kind: 'ring', x: b.x, y: b.y, r: 8, max: b.blast, life: 16, t: 0, color: b.color });
        L.particles.push({ kind: 'flash', x: b.x, y: b.y, r: b.blast, life: 8, t: 0, color: b.color });
        burst(b.x, b.y, 10, b.color, 4);
        for (const e of L.enemies) if (!e.dead && hittable(e) && dist2(b.x, b.y, e.x, e.y) < (b.blast + e.r) ** 2) damageEnemy(e, b.dmg * 0.8, 'shot');
        if (L.boss && !L.boss.entering && L.boss.hp > 0) for (const tg of L.boss.targets()) if (!tg.shielded && dist2(b.x, b.y, tg.x, tg.y) < (b.blast + tg.r) ** 2) tg.hit(b.dmg * 0.5);
        Sfx.explode(false);
        b.blast = 0;
    }
    function chainFrom(e, b) {
        let from = e;
        const hit = new Set([e]);
        for (let i = 0; i < b.chain; i++) {
            const [n] = nearestTargets(from.x, from.y, 210, 1, hit);
            if (!n) break;
            bolt(from.x, from.y, n.x, n.y, b.color);
            hit.add(n);
            damageEnemy(n, b.dmg * 0.7, 'shot');
            from = n;
        }
    }

    function updatePowers() {
        for (const m of L.marks) {
            if (--m.t > 0) continue;
            if (m.boss) { if (L.boss && L.boss.hp > 0) { const tg = L.boss.targets().find(t => !t.shielded); if (tg) { tg.hit(m.dmg); L.particles.push({ kind: 'flash', x: tg.x, y: tg.y, r: 90, life: 10, t: 0, color: env.skin.glow }); } } }
            else if (!m.e.dead) { L.particles.push({ kind: 'flash', x: m.e.x, y: m.e.y, r: 50, life: 10, t: 0, color: env.skin.glow }); burst(m.e.x, m.e.y, 8, env.skin.glow, 3); damageEnemy(m.e, m.dmg, 'area'); }
        }
        if (L.marks.some(m => m.t <= 0)) Sfx.explode(false);
        L.marks = L.marks.filter(m => m.t > 0);
        for (const a of L.allies) {
            a.life--; a.a += 0.05;
            a.x = P.x + Math.cos(a.a) * 62; a.y = P.y + Math.sin(a.a) * 62;
            if (--a.cd <= 0) {
                const [e] = nearestTargets(a.x, a.y, 520, 1);
                let tx = null, ty = null;
                if (e) { tx = e.x; ty = e.y; }
                else if (L.boss && !L.boss.entering && L.boss.hp > 0) { const tg = L.boss.targets().find(t => !t.shielded); if (tg && dist2(tg.x, tg.y, a.x, a.y) < 700 * 700) { tx = tg.x; ty = tg.y; } }
                if (tx !== null) {
                    const ang = Math.atan2(ty - a.y, tx - a.x);
                    pushBullet({ x: a.x, y: a.y, vx: Math.cos(ang) * 12, vy: Math.sin(ang) * 12, r: 4, dmg: 1 * P.dmgMul, life: 70, color: env.skin.glow, id: 'pulse' });
                }
                a.cd = 14;
            }
        }
        L.allies = L.allies.filter(a => a.life > 0);
        for (const w of L.wells) {
            w.t++;
            const R = 330;
            for (const e of L.enemies) {
                if (e.dead || e.def.static || e.def.benign || e.ally) continue;
                const d2 = dist2(e.x, e.y, w.x, w.y);
                if (d2 < R * R) { const a = Math.atan2(w.y - e.y, w.x - e.x); e.vx += Math.cos(a) * 0.55; e.vy += Math.sin(a) * 0.55; e.x += Math.cos(a) * 1.2; e.y += Math.sin(a) * 1.2; }
            }
            for (const b of L.ebullets) {
                const d2 = dist2(b.x, b.y, w.x, w.y);
                if (d2 < R * R) { const a = Math.atan2(w.y - b.y, w.x - b.x); b.vx += Math.cos(a) * 0.5; b.vy += Math.sin(a) * 0.5; if (d2 < 40 * 40) b.life = 0; }
            }
            if (w.t >= w.life) {
                L.particles.push({ kind: 'ring', x: w.x, y: w.y, r: 10, max: 190, life: 22, t: 0, color: w.color });
                L.particles.push({ kind: 'flash', x: w.x, y: w.y, r: 180, life: 12, t: 0, color: w.color });
                burst(w.x, w.y, 30, w.color, 6);
                areaDamage(w.x, w.y, 180, w.dmg, w.dmg * 1.5);
                L.shake(12); Sfx.explode(true);
            }
        }
        L.wells = L.wells.filter(w => w.t < w.life);
        for (const n of L.nets) {
            n.t++;
            for (const e of L.enemies) if (!e.dead && !e.ally && !e.def.benign && dist2(e.x, e.y, n.x, n.y) < (n.r + e.r) ** 2) e.frozen = Math.max(e.frozen, 2);
        }
        L.nets = L.nets.filter(n => n.t < n.life);
        for (const b of L.bolts) b.t++;
        L.bolts = L.bolts.filter(b => b.t < b.life);
    }

    function updateCamera() {
        if (!open) return;
        const tx = P.x - W / 2 + P.vx * 18, ty = P.y - H / 2 + P.vy * 18;
        L.cam.x += (tx - L.cam.x) * 0.1; L.cam.y += (ty - L.cam.y) * 0.1;
        L.cam.x = clamp(L.cam.x, 0, L.aw - W); L.cam.y = clamp(L.cam.y, 0, L.ah - H);
    }

    function updateParticles() {
        for (const p of L.particles) {
            p.t++;
            if (p.kind === 'spark') { p.x += p.vx; p.y += p.vy; p.vx *= 0.95; p.vy *= 0.95; }
            else if (p.kind === 'ring') p.r += (p.max - p.r) * 0.15;
        }
        L.particles = L.particles.filter(p => p.t < p.life);
        if (L.particles.length > 800) L.particles.splice(0, L.particles.length - 800);
        for (const f of L.floaters) { f.t++; f.y -= 0.6; }
        L.floaters = L.floaters.filter(f => f.t < f.life);
        for (const m of L.messages) m.t++;
        L.messages = L.messages.filter(m => m.t < m.life);
        if (!L.radioMsg && L.radioQ.length) L.radioMsg = L.radioQ.shift();
        if (L.radioMsg && ++L.radioMsg.t >= L.radioMsg.life) L.radioMsg = null;
        if (L.shakeT > 0) { L.shakeT--; if (!L.shakeT) L.shakeMag = 0; }
    }

    // ── Drawing ──────────────────────────────────────────────────────
    function drawSensor(ctx, s) {
        if (s.hp <= 0) {
            circle(ctx, s.x, s.y, s.r, '#111', '#333', 2);
            glyph(ctx, 'skull', s.x, s.y, 20, '#555');
            return;
        }
        const col = s.hitT > 0 && L.t % 10 < 5 ? '#ff5d73' : '#5be7ff';
        glow(ctx, s.x, s.y, 90, col, 0.25);
        circle(ctx, s.x, s.y, s.r + 12, null, hexA(col, 0.4), 2);
        const prog = kind === 'protect' || kind === 'defend' ? 1 - L.timer / def.duration : s.hp / s.maxHp;
        ctx.beginPath(); ctx.arc(s.x, s.y, s.r + 12, -Math.PI / 2, -Math.PI / 2 + prog * TAU);
        ctx.strokeStyle = col; ctx.lineWidth = 4; ctx.stroke();
        circle(ctx, s.x, s.y, s.r, s.flash ? '#fff' : '#06202a', col, 3);
        glyph(ctx, s.glyph || 'eye', s.x, s.y, 22, col);
        ctx.save(); ctx.globalAlpha = 0.25;
        ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.arc(s.x, s.y, 160, L.t * 0.03, L.t * 0.03 + 0.5); ctx.closePath();
        ctx.fillStyle = col; ctx.fill(); ctx.restore();
        if (kind !== 'protect') {
            const w = 60; ctx.fillStyle = 'rgba(0,0,0,.55)'; ctx.fillRect(s.x - w / 2, s.y + s.r + 20, w, 5);
            ctx.fillStyle = s.hp / s.maxHp > 0.5 ? '#4be08a' : s.hp / s.maxHp > 0.25 ? '#ffd166' : '#ff5d73';
            ctx.fillRect(s.x - w / 2, s.y + s.r + 20, w * s.hp / s.maxHp, 5);
            text(ctx, s.label + (s.waiting ? ' · ' + tr('WAITING') : ''), s.x, s.y - s.r - 22, { size: 11, color: col, weight: 800 });
        }
    }
    function drawPath(ctx, s) {
        ctx.save(); ctx.setLineDash([3, 14]); ctx.lineDashOffset = -L.t * 0.5;
        ctx.beginPath(); ctx.moveTo(s.x, s.y);
        for (let i = s.wpi; i < s.path.length; i++) ctx.lineTo(s.path[i].x, s.path[i].y);
        ctx.strokeStyle = hexA('#5be7ff', 0.35); ctx.lineWidth = 3; ctx.stroke(); ctx.restore();
    }
    function drawGate(ctx, g) {
        const col = '#ff5d73';
        if (g.type === 'blink') {
            const a = g.on ? 1 : g.warn ? (L.t % 8 < 4 ? 0.5 : 0.15) : 0.12;
            ctx.save();
            if (g.on) { ctx.fillStyle = hexA(col, 0.18); ctx.fillRect(g.x - 18, 0, 36, L.ah); }
            ctx.globalAlpha = a; ctx.beginPath(); ctx.moveTo(g.x, 0); ctx.lineTo(g.x, L.ah);
            ctx.strokeStyle = g.on ? '#ffffff' : col; ctx.lineWidth = g.on ? 5 : 2; ctx.setLineDash(g.on ? [] : [10, 10]); ctx.stroke();
            ctx.restore();
        } else if (g.type === 'gap') {
            const y1 = g.gapY - g.gapW / 2, y2 = g.gapY + g.gapW / 2;
            ctx.fillStyle = hexA(col, 0.16); ctx.fillRect(g.x - 16, 0, 32, y1); ctx.fillRect(g.x - 16, y2, 32, L.ah - y2);
            ctx.beginPath(); ctx.moveTo(g.x, 0); ctx.lineTo(g.x, y1); ctx.moveTo(g.x, y2); ctx.lineTo(g.x, L.ah);
            ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 4; ctx.stroke();
            circle(ctx, g.x, y1, 7, col); circle(ctx, g.x, y2, 7, col);
        } else {
            const cy = L.ah / 2;
            for (let k = 0; k < 2; k++) {
                const a = g.a + k * Math.PI;
                ctx.beginPath(); ctx.moveTo(g.x, cy); ctx.lineTo(g.x + Math.cos(a) * g.arm, cy + Math.sin(a) * g.arm);
                ctx.strokeStyle = hexA(col, 0.3); ctx.lineWidth = 14; ctx.stroke();
                ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 3; ctx.stroke();
            }
            poly(ctx, g.x, cy, 22, 6, L.t * 0.03, '#2a0a10', col, 3);
        }
        // pylons top and bottom
        poly(ctx, g.x, 10, 14, 4, Math.PI / 4, '#1a0a10', col, 2);
        poly(ctx, g.x, L.ah - 10, 14, 4, Math.PI / 4, '#1a0a10', col, 2);
    }
    function drawExit(ctx, x) {
        const open2 = x.open;
        const col = x.enemy ? '#ff5d73' : open2 ? '#4be08a' : '#666';
        if (open2) glow(ctx, x.x, x.y, x.r * 2.2, col, 0.35);
        for (let i = 0; i < 3; i++) poly(ctx, x.x, x.y, x.r * (0.5 + i * 0.25), 6, L.t * 0.01 * (i % 2 ? 1 : -1), null, hexA(col, open2 ? 0.8 - i * 0.2 : 0.3), 3 - i);
        glyph(ctx, x.enemy ? 'fileExport' : open2 ? 'door' : 'lock', x.x, x.y, 30, col);
        text(ctx, x.enemy ? tr('EXFIL GATE') : open2 ? tr('EXIT') : tr('LOCKED'), x.x, x.y + x.r + 18, { size: 12, color: col });
    }
    function drawKey(ctx, k) {
        if (k.got) return;
        const bob = Math.sin(k.t * 0.06) * 5;
        glow(ctx, k.x, k.y + bob, 70, '#ffd166', 0.45);
        circle(ctx, k.x, k.y + bob, 26 + Math.sin(k.t * 0.1) * 3, null, hexA('#ffd166', 0.6), 2);
        poly(ctx, k.x, k.y + bob, 20, 4, k.t * 0.02, '#2a2202', '#ffd166', 3);
        glyph(ctx, 'key', k.x, k.y + bob, 18, '#ffd166');
    }
    function drawRelay(ctx, r) {
        const col = r.done ? '#4be08a' : theme.hue;
        ctx.save(); ctx.globalAlpha = r.active ? 0.18 : 0.08; circle(ctx, r.x, r.y, r.r, col); ctx.restore();
        circle(ctx, r.x, r.y, r.r, null, hexA(col, r.active ? 0.9 : 0.5), 2);
        if (!r.done && r.prog > 0) { ctx.beginPath(); ctx.arc(r.x, r.y, r.r, -Math.PI / 2, -Math.PI / 2 + r.prog * TAU); ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 6; ctx.stroke(); }
        poly(ctx, r.x, r.y, 30, 6, r.t * 0.01, '#06101a', col, 3);
        glyph(ctx, r.done ? 'flag' : 'tower', r.x, r.y, 20, col);
    }

    L.draw = (ctx) => {
        ctx.save();
        if (L.shakeT > 0) ctx.translate(rand(-1, 1) * L.shakeMag * L.shakeT / 14, rand(-1, 1) * L.shakeMag * L.shakeT / 14);
        ctx.translate(-Math.round(L.cam.x), -Math.round(L.cam.y));

        if (open) drawGrid(ctx, L.cam, L.aw, L.ah, theme.hue, L.t);
        if (L.wind) {
            ctx.save(); ctx.globalAlpha = 0.18; ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1;
            const wx = Math.cos(L.wind.a), wy = Math.sin(L.wind.a);
            for (let i = 0; i < 26; i++) {
                const sx = L.cam.x + ((i * 197 + L.t * 9 * wx) % W + W) % W, sy = L.cam.y + ((i * 113 + L.t * 9 * wy) % H + H) % H;
                ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(sx - wx * 40, sy - wy * 40); ctx.stroke();
            }
            ctx.restore();
        }

        for (const h of L.hazards) {
            if (!onScreen(h.x, h.y, h.r)) continue;
            const armed = h.t > h.arm;
            const fade = Math.min(1, h.life / 30);
            ctx.save(); ctx.globalAlpha = fade * (armed ? 0.32 : (L.t % 10 < 5 ? 0.18 : 0.08));
            circle(ctx, h.x, h.y, h.r, h.color); ctx.restore();
            circle(ctx, h.x, h.y, h.r, null, hexA(h.color, armed ? 0.8 * fade : 0.4), armed ? 2 : 1);
            if (armed) glyph(ctx, 'biohazard', h.x, h.y, 20, hexA(h.color, 0.5 * fade));
        }
        for (const z of L.zones) {
            const active = z.t > z.tele;
            const blink = !active && Math.floor(z.t / 8) % 2;
            ctx.fillStyle = hexA(z.color, active ? 0.28 : blink ? 0.14 : 0.06);
            ctx.fillRect(z.x, z.y, z.w, z.h);
            ctx.strokeStyle = hexA(z.color, 0.8); ctx.lineWidth = 2; ctx.setLineDash(active ? [] : [12, 8]);
            ctx.strokeRect(z.x + 2, z.y + 2, z.w - 4, z.h - 4); ctx.setLineDash([]);
            if (active) glyph(ctx, 'lock', z.x + z.w / 2, z.y + z.h / 2, 60, hexA(z.color, 0.35));
        }
        for (const r of L.relays) if (onScreen(r.x, r.y, r.r)) drawRelay(ctx, r);
        if (L.exit && onScreen(L.exit.x, L.exit.y, L.exit.r * 2)) drawExit(ctx, L.exit);
        if (kind === 'escort' && L.sensors[0]) drawPath(ctx, L.sensors[0]);
        if (kind === 'pursuit' && L.courier && !L.courier.dead) {
            ctx.save(); ctx.setLineDash([2, 16]); ctx.beginPath(); ctx.moveTo(L.courier.x, L.courier.y);
            for (let i = L.courier.wpi || 0; i < L.courierPath.length; i++) ctx.lineTo(L.courierPath[i].x, L.courierPath[i].y);
            ctx.strokeStyle = hexA('#ff5d73', 0.3); ctx.lineWidth = 2; ctx.stroke(); ctx.restore();
        }
        for (const k of L.keys) if (onScreen(k.x, k.y, 80)) drawKey(ctx, k);
        for (const s of L.sensors) if (onScreen(s.x, s.y, 200)) drawSensor(ctx, s);
        for (const k of L.rocks) if (onScreen(k.x, k.y, k.r + 20)) drawRock(ctx, k, theme);
        for (const g of L.gates) if (g.x > L.cam.x - g.arm - 40 && g.x < L.cam.x + W + g.arm + 40) drawGate(ctx, g);
        for (const n of L.nets) {
            const fade = Math.min(1, (n.life - n.t) / 30, n.t / 8);
            ctx.save(); ctx.globalAlpha = 0.16 * fade; circle(ctx, n.x, n.y, n.r, '#bfe9ff'); ctx.restore();
            ctx.save(); ctx.globalAlpha = 0.7 * fade; ctx.strokeStyle = '#bfe9ff'; ctx.lineWidth = 1;
            for (let i = -4; i <= 4; i++) {
                const o = i * n.r / 4.5, h2 = Math.sqrt(Math.max(0, n.r * n.r - o * o));
                ctx.beginPath(); ctx.moveTo(n.x + o, n.y - h2); ctx.lineTo(n.x + o, n.y + h2); ctx.moveTo(n.x - h2, n.y + o); ctx.lineTo(n.x + h2, n.y + o); ctx.stroke();
            }
            ctx.restore();
            circle(ctx, n.x, n.y, n.r, null, hexA('#bfe9ff', 0.9 * fade), 2);
        }
        for (const w of L.wells) {
            const k = w.t / w.life;
            for (let i = 0; i < 4; i++) { const rr = 330 * (1 - ((w.t * 3 + i * 80) % 330) / 330); circle(ctx, w.x, w.y, rr, null, hexA(w.color, 0.35 * (1 - rr / 330)), 2); }
            glow(ctx, w.x, w.y, 80 + k * 40, w.color, 0.6);
            circle(ctx, w.x, w.y, 18 + k * 12, '#000', w.color, 3);
        }

        for (const pk of L.pickups) {
            if (!onScreen(pk.x, pk.y)) continue;
            const pd = PICKUPS[pk.type];
            const fading = pk.life < 120 && Math.floor(pk.life / 6) % 2;
            if (fading) continue;
            if (pk.type === 'byte') {
                poly(ctx, pk.x, pk.y, 6, 4, pk.t * 0.08, pd.color);
            } else {
                const bob = Math.sin(pk.t * 0.1) * 3;
                glow(ctx, pk.x, pk.y + bob, 32, pd.color, 0.4);
                circle(ctx, pk.x, pk.y + bob, pd.r, '#0b1020', pd.color, 2);
                glyph(ctx, pd.glyph, pk.x, pk.y + bob, 14, pd.color);
            }
        }

        for (const e of L.enemies) if (onScreen(e.x, e.y, e.type === 'scanner' ? 430 : e.type === 'jailbreak' ? 240 : 80)) drawEnemy(ctx, e, L);
        if (L.boss && L.boss.hp > 0 || (L.boss && L.endingT)) L.boss.draw(ctx, L);

        for (const bm of L.beams) {
            if (bm.cancel) continue;
            const x2 = bm.x + Math.cos(bm.angle) * bm.len, y2 = bm.y + Math.sin(bm.angle) * bm.len;
            const active = bm.t > bm.tele && bm.t <= bm.tele + bm.active;
            ctx.save();
            ctx.beginPath(); ctx.moveTo(bm.x, bm.y); ctx.lineTo(x2, y2);
            if (active) {
                ctx.strokeStyle = hexA(bm.color, 0.35); ctx.lineWidth = bm.width * 1.8; ctx.stroke();
                ctx.strokeStyle = '#ffffff'; ctx.lineWidth = bm.width * 0.45; ctx.stroke();
            } else if (bm.t <= bm.tele) {
                ctx.strokeStyle = hexA(bm.color, 0.25 + 0.35 * (bm.t / bm.tele));
                ctx.setLineDash([14, 10]); ctx.lineWidth = Math.max(2, bm.width * 0.3); ctx.stroke();
            }
            ctx.restore();
        }

        // ── everything that glows: additive blending ──
        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        if (L.beamLine) {
            const b = L.beamLine, c = WEAPONS.find(w => w.id === 'beam').color;
            ctx.beginPath(); ctx.moveTo(b.x1, b.y1); ctx.lineTo(b.x2, b.y2);
            ctx.strokeStyle = hexA(c, 0.35); ctx.lineWidth = 14 + Math.sin(L.t * 0.8) * 3; ctx.stroke();
            ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 3; ctx.stroke();
            glow(ctx, b.x2, b.y2, 26, c, 0.6);
        }
        for (const b of L.bullets) {
            if (!onScreen(b.x, b.y)) continue;
            if (b.id === 'rail') {
                ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(b.x - b.vx * 2.2, b.y - b.vy * 2.2);
                ctx.strokeStyle = b.color; ctx.lineWidth = 5; ctx.stroke();
                ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.5; ctx.stroke();
            } else if (b.id === 'seeker') {
                poly(ctx, b.x, b.y, 6, 3, Math.atan2(b.vy, b.vx), b.color);
            } else if (b.id === 'blade') {
                const a = b.age * 0.5;
                for (let k = 0; k < 2; k++) { ctx.beginPath(); ctx.moveTo(b.x + Math.cos(a + k * Math.PI / 2) * 10, b.y + Math.sin(a + k * Math.PI / 2) * 10); ctx.lineTo(b.x - Math.cos(a + k * Math.PI / 2) * 10, b.y - Math.sin(a + k * Math.PI / 2) * 10); ctx.strokeStyle = b.color; ctx.lineWidth = 3; ctx.stroke(); }
            } else if (b.id === 'flak') {
                glow(ctx, b.x, b.y, 18, b.color, 0.5);
                circle(ctx, b.x, b.y, b.r, b.color);
            } else {
                ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(b.x - b.vx * 1.2, b.y - b.vy * 1.2);
                ctx.strokeStyle = hexA(b.color, 0.5); ctx.lineWidth = b.r * 1.6; ctx.stroke();
                circle(ctx, b.x, b.y, b.r, b.color);
            }
        }
        for (const bl of L.bolts) {
            ctx.globalAlpha = 1 - bl.t / bl.life;
            ctx.beginPath(); bl.pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
            ctx.strokeStyle = bl.color; ctx.lineWidth = 4; ctx.stroke();
            ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.5; ctx.stroke();
        }
        ctx.globalAlpha = 1;
        ctx.restore();

        for (const b of L.ebullets) {
            if (!onScreen(b.x, b.y)) continue;
            if (b.kind === 'hook') {
                circle(ctx, b.x, b.y, b.r + 3, null, b.color, 2);
                glyph(ctx, 'key', b.x, b.y, 10, b.color);
            } else if (b.kind === 'log') {
                ctx.fillStyle = hexA(b.color, 0.35); ctx.fillRect(b.x - b.r * 1.8, b.y - b.r * 0.7, b.r * 3.6, b.r * 1.4);
                ctx.fillStyle = '#fff4dd'; ctx.fillRect(b.x - b.r * 1.3, b.y - 1, b.r * 2.6, 2);
            } else {
                circle(ctx, b.x, b.y, b.r + 2, hexA(b.color, 0.35));
                circle(ctx, b.x, b.y, b.r * 0.6, '#ffffff');
            }
        }

        // marks of Sagan's Threshold Alert
        for (const m of L.marks) {
            const tg = m.boss ? (L.boss && L.boss.targets()[0]) : m.e;
            if (!tg || tg.dead) continue;
            const k = m.t / 60;
            circle(ctx, tg.x, tg.y, (tg.r || 20) + 8 + k * 20, null, hexA(env.skin.glow, 0.9), 2);
            glyph(ctx, 'bullseye', tg.x, tg.y - (tg.r || 20) - 14, 14, env.skin.glow);
        }
        // ATR's guardian agents
        for (const a of L.allies) {
            glow(ctx, a.x, a.y, 24, env.skin.glow, 0.5);
            poly(ctx, a.x, a.y, 9, 6, L.t * 0.1, '#04201a', env.skin.glow, 2);
        }

        // player
        if (!(L.finished && !L.result.won)) {
            const blink = P.inv > 0 && P.inv % 8 < 4 && P.dashT === 0;
            if (P.pulled) {
                ctx.beginPath(); ctx.moveTo(P.x, P.y); ctx.lineTo(P.pulled.x, P.pulled.y);
                ctx.strokeStyle = hexA('#3ee0c8', 0.6); ctx.lineWidth = 2; ctx.stroke();
            }
            if (P.dashT > 0) for (let i = 1; i <= 3; i++) drawShip(ctx, P.x - P.vx * i * 1.5, P.y - P.vy * i * 1.5, P.angle, env.skin, { alpha: 0.25 / i, t: L.t });
            drawShip(ctx, P.x, P.y, P.angle, env.skin, { thrust: P.thrust, alpha: blink ? 0.35 : 1, t: L.t });
            if (P.buffs.shield > 0) circle(ctx, P.x, P.y, 26 + Math.sin(L.t * 0.2) * 2, hexA('#6ea8ff', 0.12), hexA('#6ea8ff', 0.8), 2);
            if (P.disarmed > 0) glyph(ctx, 'lock', P.x, P.y - 28, 14, '#ff7a3c');
            if (P.buffs.overclock > 0) glow(ctx, P.x, P.y, 40, '#ff6bd8', 0.3);
            const spId = env.skin.special?.id;
            if (P.specialT > 0 && (spId === 'ips' || spId === 'paranoia')) {
                const fade = Math.min(1, P.specialT / 30), R = spId === 'ips' ? IPS_R : PARANOIA_R;
                circle(ctx, P.x, P.y, R + Math.sin(L.t * 0.15) * 4, hexA(env.skin.glow, 0.08 * fade), hexA(env.skin.glow, 0.7 * fade), 2);
                if (spId === 'paranoia') poly(ctx, P.x, P.y, R - 10, 6, L.t * 0.02, null, hexA(env.skin.glow, 0.4 * fade), 1.5);
            }
        }

        for (const p of L.particles) {
            if (!onScreen(p.x, p.y, p.kind === 'spark' ? 10 : (p.max || p.r) + 10)) continue;
            const k = 1 - p.t / p.life;
            if (p.kind === 'spark') { ctx.globalAlpha = k; ctx.fillStyle = p.color; ctx.fillRect(p.x, p.y, p.size, p.size); }
            else if (p.kind === 'flash') { ctx.globalAlpha = 1; glow(ctx, p.x, p.y, p.r * (0.6 + 0.4 * (1 - k)), p.color, 0.5 * k); }
            else { ctx.globalAlpha = k * 0.8; circle(ctx, p.x, p.y, p.r, null, p.color, 3); }
        }
        ctx.globalAlpha = 1;
        if (L.pulse) { const pu = L.pulse; circle(ctx, pu.x, pu.y, pu.r, null, hexA(pu.stun ? env.skin.glow : '#9fe8ff', 0.7 * (1 - pu.t / 70)), 3); }
        for (const f of L.floaters) text(ctx, f.str, f.x, f.y, { size: 14, color: f.color, alpha: 1 - f.t / f.life });
        if (open) {
            // the edge of the sector: a firewall
            ctx.strokeStyle = hexA(theme.hue, 0.5 + 0.2 * Math.sin(L.t * 0.05)); ctx.lineWidth = 4; ctx.setLineDash([24, 12]);
            ctx.strokeRect(2, 2, L.aw - 4, L.ah - 4); ctx.setLineDash([]);
        }
        ctx.restore();

        // ── screen space ─────────────────────────────────────────────
        const sx = P.x - L.cam.x, sy = P.y - L.cam.y;
        if (L.slow) { ctx.fillStyle = hexA(env.skin.glow, 0.05); ctx.fillRect(0, 0, W, H); }
        if (L.invertT > 0) { ctx.fillStyle = hexA('#c9a7ff', L.t % 20 < 10 ? 0.1 : 0.05); ctx.fillRect(0, 0, W, H); }
        if (L.dark) {
            const lightR = L.lightT > 0 ? 620 : 230;
            const g = ctx.createRadialGradient(sx, sy, lightR * 0.45, sx, sy, lightR * 1.15);
            g.addColorStop(0, 'rgba(1,2,8,0)'); g.addColorStop(1, 'rgba(1,2,8,0.95)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
            // what the pulses revealed shows through the dark
            for (const e of L.enemies) {
                if (!(e.revealT > 0) && !(e.isTarget && e.seen)) continue;
                if (e.revealT > 0) e.revealT--;
                const ex = e.x - L.cam.x, ey = e.y - L.cam.y;
                if (ex < -20 || ex > W + 20 || ey < -20 || ey > H + 20) continue;
                const a = e.isTarget ? 0.9 : Math.min(1, e.revealT / 60) * 0.8;
                ctx.save(); ctx.globalAlpha = a;
                poly(ctx, ex, ey, e.r + 6, 4, Math.PI / 4, null, e.isTarget ? '#ff4d6d' : e.def.color, 2);
                if (e.isTarget) glyph(ctx, 'spider', ex, ey, 16, '#ff4d6d');
                ctx.restore();
            }
            for (const k of L.keys) {
                if (k.got || !k.seen) continue;
                const kx = k.x - L.cam.x, ky = k.y - L.cam.y;
                if (kx > -30 && kx < W + 30 && ky > -30 && ky < H + 30) glyph(ctx, 'key', kx, ky, 20, '#ffd166');
            }
        }
        if (open) drawPointers(ctx);
        if (open) drawRadar(ctx);
        if (L.hurtT > 0) {
            const g = ctx.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 0.9);
            g.addColorStop(0, 'rgba(255,40,60,0)'); g.addColorStop(1, `rgba(255,40,60,${0.35 * L.hurtT / 22})`);
            ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
        }

        // radio: Rulezy on the comms
        if (L.radioMsg) {
            const m = L.radioMsg, a = Math.min(1, m.t / 12, (m.life - m.t) / 20);
            const words = m.str.split(' '), lines = [];
            let cur = '';
            ctx.save(); ctx.font = '600 14px system-ui, sans-serif';
            for (const w2 of words) { const tt = cur ? cur + ' ' + w2 : w2; if (ctx.measureText(tt).width > 400) { lines.push(cur); cur = w2; } else cur = tt; }
            if (cur) lines.push(cur);
            const bh = 34 + lines.length * 18, bx = 16, by = H - 70 - bh;
            ctx.globalAlpha = a * 0.78; ctx.fillStyle = '#050a18'; ctx.fillRect(bx, by, 470, bh);
            ctx.globalAlpha = a; ctx.fillStyle = theme.hue; ctx.fillRect(bx, by, 3, bh);
            ctx.restore();
            circle(ctx, bx + 30, by + bh / 2, 17, '#0b1530', theme.hue, 2);
            glyph(ctx, 'robot', bx + 30, by + bh / 2, 16, theme.hue, a);
            text(ctx, 'RULEZY', bx + 58, by + 14, { size: 11, color: theme.hue, align: 'left', alpha: a });
            lines.forEach((ln, i) => text(ctx, ln, bx + 58, by + 32 + i * 18, { size: 14, color: '#e8eeff', align: 'left', weight: 600, alpha: a }));
        }

        // announcements (not shaken)
        const big = L.messages.filter(m => m.kind === 'big').slice(-1)[0];
        if (big) {
            const a = Math.min(1, big.t / 10, (big.life - big.t) / 20);
            const s = 1 + Math.max(0, 1 - big.t / 8) * 0.3;
            text(ctx, big.str, W / 2 + 2, H / 2 - 78, { size: 46 * s, color: '#000', alpha: a * 0.5 });
            text(ctx, big.str, W / 2, H / 2 - 80, { size: 46 * s, color: big.color, alpha: a });
        }
        const line = L.messages.filter(m => m.kind === 'line').slice(-1)[0];
        if (line) {
            const a = Math.min(1, line.t / 10, (line.life - line.t) / 20);
            ctx.save(); ctx.globalAlpha = a * 0.6; ctx.fillStyle = '#000'; ctx.fillRect(W / 2 - 360, H - 70, 720, 40); ctx.restore();
            text(ctx, line.str, W / 2, H - 50, { size: 17, color: line.color, alpha: a, weight: 600 });
        }
        if (L.boss && L.bossIntroT > 0) {
            const a = Math.min(1, (150 - L.bossIntroT) / 20, L.bossIntroT / 20);
            const bar = 70 * a;
            ctx.save(); ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, bar); ctx.fillRect(0, H - bar, W, bar); ctx.restore();
            ctx.save(); ctx.globalAlpha = a * 0.55; ctx.fillStyle = '#000'; ctx.fillRect(0, H / 2 - 90, W, 180); ctx.restore();
            text(ctx, 'WARNING', W / 2, H / 2 - 45, { size: 22, color: '#ff5d73', alpha: a * (L.t % 20 < 12 ? 1 : 0.4) });
            text(ctx, L.boss.name, W / 2, H / 2 + 5, { size: 54, color: L.boss.def.color, alpha: a });
            text(ctx, L.boss.def.intro, W / 2, H / 2 + 55, { size: 16, color: '#ddd', alpha: a, weight: 500 });
        }
    };

    /** Arrows on the screen edge towards what matters and is off-screen */
    function pointerTargets() {
        const out = [];
        for (const k of L.keys) if (!k.got && k.seen) out.push({ x: k.x, y: k.y, color: '#ffd166', glyph: 'key' });
        if (L.ping && L.ping.t < 150) out.push({ x: L.ping.x, y: L.ping.y, color: '#ffd166', glyph: 'key', ping: true });
        for (const r of L.relays) if (!r.done) out.push({ x: r.x, y: r.y, color: theme.hue, glyph: 'tower' });
        for (const s of L.sensors) if (s.hp > 0) out.push({ x: s.x, y: s.y, color: s.hitT > 0 ? '#ff5d73' : '#5be7ff', glyph: s.glyph || 'eye' });
        for (const e of L.enemies) if (e.isTarget && !e.dead && (e.type === 'beacon' || e.seen)) out.push({ x: e.x, y: e.y, color: e.def.color, glyph: e.def.glyph });
        if (L.courier && !L.courier.dead) out.push({ x: L.courier.x, y: L.courier.y, color: '#ffd84f', glyph: 'fileExport' });
        if (L.exit && L.exit.open && !L.exit.deco && (kind !== 'keys' || L.keys.every(k => k.got))) out.push({ x: L.exit.x, y: L.exit.y, color: L.exit.enemy ? '#ff5d73' : '#4be08a', glyph: L.exit.enemy ? 'fileExport' : 'door' });
        return out;
    }
    function drawPointers(ctx) {
        for (const p of pointerTargets()) {
            const sx = p.x - L.cam.x, sy = p.y - L.cam.y;
            if (sx > 0 && sx < W && sy > 0 && sy < H) continue;
            const cx = W / 2, cy = H / 2, a = Math.atan2(sy - cy, sx - cx);
            const m = 34;
            const k = Math.min((W / 2 - m) / Math.abs(Math.cos(a) || 1e-6), (H / 2 - m) / Math.abs(Math.sin(a) || 1e-6));
            const x = cx + Math.cos(a) * k, y = cy + Math.sin(a) * k;
            const pulse = p.ping ? 1 + Math.sin(L.t * 0.3) * 0.25 : 1;
            ctx.save(); ctx.translate(x, y); ctx.rotate(a);
            ctx.beginPath(); ctx.moveTo(16 * pulse, 0); ctx.lineTo(-6, -10 * pulse); ctx.lineTo(-6, 10 * pulse); ctx.closePath();
            ctx.fillStyle = p.color; ctx.globalAlpha = 0.9; ctx.fill(); ctx.restore();
            glyph(ctx, p.glyph, x - Math.cos(a) * 22, y - Math.sin(a) * 22, 13, p.color);
            const d = Math.round(Math.hypot(p.x - P.x, p.y - P.y) / 10);
            text(ctx, `${d}m`, x - Math.cos(a) * 22, y - Math.sin(a) * 22 + 16, { size: 10, color: p.color, weight: 700 });
        }
    }
    function drawRadar(ctx) {
        const rw = 200, rh = Math.round(rw * L.ah / L.aw), rx = W - rw - 14, ry = H - rh - 76;
        const sc = rw / L.aw;
        ctx.save();
        ctx.globalAlpha = 0.72; ctx.fillStyle = '#030814'; ctx.fillRect(rx, ry, rw, rh);
        ctx.globalAlpha = 1; ctx.strokeStyle = hexA(theme.hue, 0.6); ctx.lineWidth = 1.5; ctx.strokeRect(rx, ry, rw, rh);
        // the camera's view
        ctx.strokeStyle = 'rgba(255,255,255,0.25)'; ctx.strokeRect(rx + L.cam.x * sc, ry + L.cam.y * sc, W * sc, H * sc);
        ctx.fillStyle = 'rgba(160,170,190,0.35)';
        for (const k of L.rocks) { ctx.beginPath(); ctx.arc(rx + k.x * sc, ry + k.y * sc, Math.max(1, k.r * sc), 0, TAU); ctx.fill(); }
        for (const g of L.gates) { ctx.fillStyle = 'rgba(255,93,115,0.6)'; ctx.fillRect(rx + g.x * sc - 0.5, ry, 1.5, rh); }
        const dot = (x, y, c, r = 2) => { ctx.fillStyle = c; ctx.fillRect(rx + x * sc - r, ry + y * sc - r, r * 2, r * 2); };
        if (!L.dark || L.lightT > 0) for (const e of L.enemies) if (!e.dead && !e.isTarget && (onScreen(e.x, e.y, 300) || e.revealT > 0)) dot(e.x, e.y, e.def.benign ? '#4be08a' : e.ally ? '#6fffd2' : '#ff5d73', 1.2);
        for (const e of L.enemies) if (e.isTarget && !e.dead && (e.type === 'beacon' || e.seen)) dot(e.x, e.y, e.def.color, 3);
        for (const r of L.relays) dot(r.x, r.y, r.done ? '#4be08a' : theme.hue, 3);
        for (const s of L.sensors) if (s.hp > 0) dot(s.x, s.y, s.hitT > 0 && L.t % 10 < 5 ? '#ff5d73' : '#5be7ff', 3);
        for (const k of L.keys) if (!k.got && k.seen) dot(k.x, k.y, '#ffd166', 3);
        if (L.courier && !L.courier.dead) dot(L.courier.x, L.courier.y, '#ffd84f', 3.5);
        if (L.exit && L.exit.open && !L.exit.deco) dot(L.exit.x, L.exit.y, L.exit.enemy ? '#ff5d73' : '#4be08a', 3.5);
        if (L.ping) { ctx.strokeStyle = hexA('#ffd166', 1 - L.ping.t / 150); ctx.beginPath(); ctx.arc(rx + L.ping.x * sc, ry + L.ping.y * sc, 4 + L.ping.t * 0.08, 0, TAU); ctx.stroke(); }
        // you
        ctx.save(); ctx.translate(rx + P.x * sc, ry + P.y * sc); ctx.rotate(P.angle);
        ctx.beginPath(); ctx.moveTo(5, 0); ctx.lineTo(-3, -3.5); ctx.lineTo(-3, 3.5); ctx.closePath(); ctx.fillStyle = '#ffffff'; ctx.fill(); ctx.restore();
        ctx.restore();
        text(ctx, tr('RADAR'), rx + 4, ry - 8, { size: 10, color: hexA(theme.hue, 0.9), align: 'left', weight: 800 });
    }

    /** Data for the HTML HUD */
    L.hud = () => ({
        hp: P.hp, maxHp: P.maxHp, bombs: P.bombs, score: L.score, bytes: L.levelBytes,
        combo: L.combo >= 5 ? Math.min(8, 1 + Math.floor(L.combo / 5)) : 1, comboT: L.comboT,
        weapon: currentWeapon().id, weapons: weapons.map(w => w.id), dash: 1 - P.dashCd / P.dashMax,
        special: 1 - P.specialCd / P.specialMax, specialActive: P.specialT > 0 || L.allies.length > 0 || L.nets.length > 0 || L.wells.length > 0,
        buffs: { ...P.buffs }, disarmed: P.disarmed, objective: L.objective, inverted: L.invertT > 0,
    });

    return L;
}
