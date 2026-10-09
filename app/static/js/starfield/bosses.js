/**
 * bosses.js — the five world bosses. Each boss is an object with
 * update(L), draw(ctx, L) and targets() (what the player's bullets can hit:
 * the boss itself and, for some, its parts). Phases change at 66% / 33% hp.
 * Beams and encrypted zones are generic hazards owned by the Level.
 */
import { BOSSES, W, H, TAU } from './data.js';
import { circle, poly, glyph, glow, hexA, text } from './render.js';
import { Sfx } from './audio.js';

const rand = (a, b) => a + Math.random() * (b - a);
const angleTo = (a, b) => Math.atan2(b.y - a.y, b.x - a.x);

function base(def, L) {
    const hp = Math.round(def.hp * L.diff.hp);
    return {
        def, name: def.name, x: W / 2, y: -120, r: 58, hp, maxHp: hp, t: 0, phase: 1,
        flash: 0, entering: true, invulnerable: false, alpha: 1, lines: [],
    };
}

function phaseFor(b) { return b.hp > b.maxHp * 0.66 ? 1 : b.hp > b.maxHp * 0.33 ? 2 : 3; }

function enter(b, ty = 170) {
    b.y += (ty - b.y) * 0.04;
    if (Math.abs(b.y - ty) < 2) { b.entering = false; b.t = 0; }
}

function ring(b, L, n, speed, opts = {}, rot = 0) {
    for (let i = 0; i < n; i++) {
        const a = rot + (i / n) * TAU;
        L.enemyBullet(b.x, b.y, Math.cos(a) * speed, Math.sin(a) * speed, opts);
    }
}
function fan(b, L, n, spread, speed, opts = {}) {
    const a0 = angleTo(b, L.player);
    for (let i = 0; i < n; i++) {
        const a = a0 + (i - (n - 1) / 2) * spread;
        L.enemyBullet(b.x, b.y, Math.cos(a) * speed, Math.sin(a) * speed, opts);
    }
}
function checkPhase(b, L) {
    const p = phaseFor(b);
    if (p !== b.phase) {
        b.phase = p;
        L.announce(p === 2 ? 'PHASE 2' : 'FINAL PHASE', b.def.color);
        L.restoreHearts();
        L.shake(14); Sfx.bossRoar();
        if (b.lines[p - 1]) L.say(b.lines[p - 1], b.def.color);
        if (b.onPhase) b.onPhase(p);
    }
}
function drawCore(ctx, b, sides, rot, fill) {
    const c = b.flash > 0 ? '#ffffff' : b.def.color;
    glow(ctx, b.x, b.y, b.r * 2.4, b.def.color, 0.35);
    poly(ctx, b.x, b.y, b.r, sides, rot, fill, c, 4);
    poly(ctx, b.x, b.y, b.r * 0.7, sides, -rot * 1.5, null, hexA(b.def.color, 0.5), 2);
    glyph(ctx, b.def.glyph, b.x, b.y, b.r * 0.9, c);
}

// ── 1. Phish King ───────────────────────────────────────────────────────
function phishKing(L) {
    const b = base(BOSSES[0], L);
    b.r = 60;
    b.lines = ['', 'Such a nice link. Click it. CLICK IT.', 'Every inbox. Every user. Mine.'];
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b);
        checkPhase(b, L);
        b.x = W / 2 + Math.sin(b.t * 0.011) * 420;
        b.y = 190 + Math.sin(b.t * 0.022) * 90;
        if (b.t % 70 === 0) { fan(b, L, b.phase === 1 ? 5 : 7, 0.18, 3.4, { color: '#3ee0c8' }); Sfx.enemyShoot(); }
        if (b.t % 320 === 160) {          // gifts that are not gifts
            for (let i = 0; i < 2 + b.phase; i++) L.spawnEnemy('trojan', rand(150, W - 150), rand(330, H - 100));
        }
        if (b.phase >= 2 && b.t % 170 === 85) {
            for (let i = -1; i <= 1; i++) {
                const a = angleTo(b, L.player) + i * 0.4;
                L.enemyBullet(b.x, b.y, Math.cos(a) * 5, Math.sin(a) * 5, { kind: 'hook', r: 9, color: '#3ee0c8', life: 130 });
            }
        }
        if (b.phase >= 2 && b.t % 230 === 0) ring(b, L, 18, 2.6, { color: '#5be7ff' }, b.t * 0.01);
        if (b.phase === 3) {
            if (b.t % 6 === 0) ring(b, L, 2, 3, { color: '#3ee0c8', r: 5 }, b.t * 0.07);
            if (b.t % 260 === 0 && L.enemies.filter(e => e.type === 'worm').length < 4) {
                for (let i = 0; i < 3; i++) L.spawnEnemy('worm', b.x + rand(-60, 60), b.y + rand(-30, 60));
            }
        }
    };
    b.draw = (ctx) => {
        const c = b.flash > 0 ? '#fff' : b.def.color;
        glow(ctx, b.x, b.y, 150, b.def.color, 0.3);
        // the lure
        const lx = b.x + Math.sin(b.t * 0.05) * 30, ly = b.y - 95;
        ctx.beginPath(); ctx.moveTo(b.x, b.y - b.r * 0.6); ctx.quadraticCurveTo(b.x + 10, ly - 30, lx, ly);
        ctx.strokeStyle = c; ctx.lineWidth = 3; ctx.stroke();
        glow(ctx, lx, ly, 40, '#fff6a0', 0.6);
        circle(ctx, lx, ly, 9, '#fff6a0');
        ctx.beginPath(); ctx.ellipse(b.x, b.y, b.r * 1.3, b.r, 0, 0, TAU);
        ctx.fillStyle = '#062a2a'; ctx.fill(); ctx.strokeStyle = c; ctx.lineWidth = 4; ctx.stroke();
        glyph(ctx, 'fish', b.x, b.y, b.r * 0.9, c);
    };
    b.targets = () => [{ x: b.x, y: b.y, r: b.r, hit: d => { b.hp -= d; b.flash = 4; } }];
    return b;
}

// ── 2. Botnet Hive ──────────────────────────────────────────────────────
function hive(L) {
    const b = base(BOSSES[1], L);
    b.r = 56;
    b.lines = ['', 'Reroute. Reinfect. Rebuild.', 'You cannot patch ten thousand hosts.'];
    const makeNodes = (n, hp) => Array.from({ length: n }, (_, i) => ({ a: (i / n) * TAU, hp: hp * L.diff.hp, maxHp: hp * L.diff.hp, flash: 0 }));
    b.nodes = makeNodes(6, 14);
    b.exposed = 0;
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 230);
        checkPhase(b, L);
        b.x = W / 2 + Math.sin(b.t * 0.006) * 250;
        b.y = 230 + Math.cos(b.t * 0.009) * 60;
        const alive = b.nodes.filter(n => n.hp > 0);
        b.invulnerable = alive.length > 0;
        b.nodes.forEach(n => {
            n.a += 0.012 + (b.phase - 1) * 0.004; if (n.flash > 0) n.flash--;
            n.x = b.x + Math.cos(n.a) * 135; n.y = b.y + Math.sin(n.a) * 135;
            if (n.hp > 0 && (b.t + Math.round(n.a * 50)) % 150 === 0) {
                const a = angleTo(n, L.player);
                L.enemyBullet(n.x, n.y, Math.cos(a) * 3.6, Math.sin(a) * 3.6, { color: '#c08bff' });
            }
        });
        if (!alive.length) {
            if (!b.exposed) { b.exposed = 480; L.announce('CORE EXPOSED', '#ffd166'); Sfx.powerup(); }
            b.exposed--;
            if (b.exposed <= 0) { b.nodes = makeNodes(2 + b.phase, 10); L.say('Nodes respawned — the botnet heals itself.', b.def.color); }
        }
        if (b.t % 260 === 0 && L.enemies.filter(e => e.type === 'drone').length < 8) {
            for (let i = 0; i < 3 + b.phase; i++) L.spawnEnemy('drone', b.x + rand(-80, 80), b.y + rand(-40, 80));
        }
        if (b.phase >= 2 && b.t % 520 === 100) {      // sweeping C2 beams
            const n = b.phase === 3 ? 3 : 2;
            for (let i = 0; i < n; i++) L.addBeam({ follow: b, angle: (i / n) * TAU + rand(0, 1), rot: 0.011 * (Math.random() < 0.5 ? 1 : -1), len: 1500, width: 18, tele: 80, active: 260, color: '#c08bff' });
            Sfx.warning();
        }
        if (b.phase === 3 && b.t % 120 === 0) ring(b, L, 14, 2.8, { color: '#a06bff' }, b.t * 0.02);
    };
    b.draw = (ctx) => {
        b.nodes.forEach(n => {
            if (n.hp <= 0) return;
            ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(n.x, n.y);
            ctx.strokeStyle = hexA('#a06bff', 0.35); ctx.lineWidth = 2; ctx.stroke();
            poly(ctx, n.x, n.y, 20, 6, b.t * 0.03, '#140a24', n.flash ? '#fff' : '#c08bff', 2.5);
            glyph(ctx, 'robot', n.x, n.y, 16, '#c08bff');
        });
        if (b.invulnerable) circle(ctx, b.x, b.y, b.r + 16 + Math.sin(b.t * 0.1) * 3, hexA('#a06bff', 0.12), hexA('#c08bff', 0.7), 3);
        drawCore(ctx, b, 6, b.t * 0.01, '#140a24');
    };
    b.targets = () => [
        ...b.nodes.filter(n => n.hp > 0).map(n => ({ x: n.x, y: n.y, r: 20, hit: d => { n.hp -= d; n.flash = 4; if (n.hp <= 0) { L.explosion(n.x, n.y, 40, '#c08bff', false); L.addScore(200); } } })),
        { x: b.x, y: b.y, r: b.r, shielded: b.invulnerable, hit: d => { if (!b.invulnerable) { b.hp -= d; b.flash = 4; } } },
    ];
    return b;
}

// ── 3. The Locker ───────────────────────────────────────────────────────
function locker(L) {
    const b = base(BOSSES[2], L);
    b.r = 64;
    b.lines = ['', 'Your files are encrypted. Pay to continue.', 'The price just doubled.'];
    b.wp = { x: W / 2, y: 200 };
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 200);
        checkPhase(b, L);
        const speed = b.phase === 3 ? 0.035 : 0.02;
        b.x += (b.wp.x - b.x) * speed; b.y += (b.wp.y - b.y) * speed;
        if (b.t % 200 === 0) b.wp = { x: rand(200, W - 200), y: rand(130, H / 2) };
        if (b.t % (b.phase === 3 ? 240 : 330) === 60) {        // encrypt quadrants
            const quads = [[0, 0], [W / 2, 0], [0, H / 2], [W / 2, H / 2]].sort(() => Math.random() - 0.5);
            const n = b.phase === 1 ? 1 : 2;
            quads.slice(0, n).forEach(([x, y]) => L.addZone({ x, y, w: W / 2, h: H / 2, tele: 100, active: 230, color: '#ff7a3c' }));
            L.say('Encrypting sector…', b.def.color); Sfx.warning();
        }
        if (b.t % 190 === 120) {                                 // bullet wall with a gap
            const vertical = Math.random() < 0.5;
            const gap = vertical ? L.player.y : L.player.x;
            const span = vertical ? H : W, gapW = b.phase === 3 ? 110 : 150;
            for (let s = 20; s < span; s += 34) {
                if (Math.abs(s - gap) < gapW / 2) continue;
                if (vertical) L.enemyBullet(-10, s, 3.2, 0, { color: '#ff7a3c', r: 8, life: 500 });
                else L.enemyBullet(s, -10, 0, 2.8, { color: '#ff7a3c', r: 8, life: 500 });
            }
            Sfx.enemyShoot();
        }
        if (b.t % 90 === 45) fan(b, L, b.phase === 3 ? 5 : 3, 0.25, 3.6, { color: '#ffd166', r: 9 });
    };
    b.draw = (ctx) => drawCore(ctx, b, 4, b.t * (b.phase === 3 ? 0.04 : 0.015), '#2a0f05');
    b.targets = () => [{ x: b.x, y: b.y, r: b.r, hit: d => { b.hp -= d; b.flash = 4; } }];
    return b;
}

// ── 4. APT Ghost ────────────────────────────────────────────────────────
function ghost(L) {
    const b = base(BOSSES[3], L);
    b.r = 46;
    b.lines = ['', 'We have been here since before your first log line.', 'Which one of us is real?'];
    b.fade = 0;
    const teleport = () => {
        b.x = rand(150, W - 150); b.y = rand(120, H - 150);
        const decoys = b.phase === 1 ? 2 : 3;
        for (let i = 0; i < decoys; i++) L.spawnEnemy('decoy', rand(150, W - 150), rand(120, H - 150), { spawnT: 20 });
    };
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 200);
        checkPhase(b, L);
        const cycle = b.phase === 3 ? 170 : 220;
        const k = b.t % cycle;
        if (k === cycle - 30) b.fade = 30;
        if (b.fade > 0) { b.fade--; b.alpha = b.fade / 30; if (b.fade === 0) { teleport(); b.alpha = 1; } }
        else if (b.phase === 3) b.alpha = 0.55 + 0.45 * Math.sin(b.t * 0.15);
        if (k === 40) {                               // sniper beams aimed at the player
            const n = b.phase === 1 ? 1 : 3;
            const a0 = angleTo(b, L.player);
            for (let i = 0; i < n; i++) L.addBeam({ x: b.x, y: b.y, angle: a0 + (i - (n - 1) / 2) * 0.35, rot: 0, len: 1600, width: 10, tele: 60, active: 14, color: '#ff3d7f' });
            Sfx.telegraph();
        }
        if (k === 130) ring(b, L, b.phase === 1 ? 12 : 18, 3, { color: '#ff3d7f' }, rand(0, 1));
        if (b.phase >= 2 && b.t % 300 === 200) { L.spawnEnemy('keylogger', rand(100, W - 100), rand(100, H - 100)); }
    };
    b.draw = (ctx) => {
        ctx.save(); ctx.globalAlpha = b.alpha;
        drawCore(ctx, b, 5, b.t * 0.02, '#2a0012');
        ctx.restore();
    };
    b.targets = () => (b.alpha < 0.3 ? [] : [{ x: b.x, y: b.y, r: b.r, hit: d => { b.hp -= d; b.flash = 4; } }]);
    return b;
}

// ── 5. Zero-Day ─────────────────────────────────────────────────────────
function zeroDay(L) {
    const b = base(BOSSES[4], L);
    b.r = 70;
    b.lines = ['', 'Patch Tuesday is six days away.', 'You wrote a rule for me. Let us see if it holds.'];
    b.dash = null;
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, H / 2 - 40);
        checkPhase(b, L);
        const t = b.t;
        if (b.phase === 1) {
            b.x = W / 2 + Math.sin(t * 0.008) * 200; b.y = H / 2 - 60 + Math.cos(t * 0.011) * 60;
            if (t % 5 === 0) ring(b, L, 3, 2.8, { color: '#ff6bd8', r: 5 }, t * 0.045);
            if (t % 150 === 0) ring(b, L, 22, 2.2, { color: '#ffffff', r: 6 }, 0);
        } else if (b.phase === 2) {
            b.x += (W / 2 - b.x) * 0.03; b.y += (H / 2 - b.y) * 0.03;
            if (t % 360 === 30) {
                const quads = [[0, 0], [W / 2, 0], [0, H / 2], [W / 2, H / 2]].sort(() => Math.random() - 0.5);
                L.addZone({ ...{ x: quads[0][0], y: quads[0][1] }, w: W / 2, h: H / 2, tele: 90, active: 220, color: '#ff6bd8' });
            }
            if (t % 420 === 200) {
                for (let i = 0; i < 4; i++) L.addBeam({ follow: b, angle: i * TAU / 4, rot: 0.009, len: 1500, width: 16, tele: 70, active: 240, color: '#ff6bd8' });
                Sfx.warning();
            }
            if (t % 240 === 0) for (let i = 0; i < 2; i++) L.spawnEnemy('wiper', rand(80, W - 80), Math.random() < 0.5 ? 60 : H - 60);
            if (t % 40 === 0) fan(b, L, 3, 0.3, 4, { color: '#ffffff' });
        } else {
            if (!b.dash && t % 150 === 0) {
                const a = angleTo(b, L.player);
                b.dash = { a, tele: 50, run: 0 };
                L.addBeam({ x: b.x, y: b.y, angle: a, rot: 0, len: 1600, width: b.r * 1.6, tele: 50, active: 0, color: '#ffffff' });
                Sfx.telegraph();
            }
            if (b.dash) {
                if (b.dash.tele > 0) b.dash.tele--;
                else {
                    b.x += Math.cos(b.dash.a) * 17; b.y += Math.sin(b.dash.a) * 17; b.dash.run++;
                    if (b.x < 70 || b.x > W - 70 || b.y < 70 || b.y > H - 70 || b.dash.run > 90) {
                        b.x = Math.min(W - 70, Math.max(70, b.x)); b.y = Math.min(H - 70, Math.max(70, b.y));
                        ring(b, L, 26, 3, { color: '#ff6bd8' }, rand(0, 1)); L.shake(10); Sfx.explode(true);
                        b.dash = null;
                    }
                }
            }
            if (t % 7 === 0) ring(b, L, 2, 3.4, { color: '#ffffff', r: 5 }, -t * 0.06);
        }
    };
    b.draw = (ctx) => {
        for (let i = 0; i < 3; i++) circle(ctx, b.x, b.y, b.r + 20 + i * 14 + Math.sin(b.t * 0.05 + i) * 4, null, hexA(i % 2 ? '#ff6bd8' : '#ffffff', 0.25), 2);
        drawCore(ctx, b, 3, b.t * 0.03, '#1a0418');
        poly(ctx, b.x, b.y, b.r * 0.45, 3, -b.t * 0.05, null, '#ff6bd8', 2);
    };
    b.targets = () => [{ x: b.x, y: b.y, r: b.r, hit: d => { b.hp -= d; b.flash = 4; } }];
    return b;
}

const FACTORIES = [phishKing, hive, locker, ghost, zeroDay];

export function makeBoss(index, L, scale = 1) {
    const b = FACTORIES[index](L);
    if (scale !== 1) { b.hp = b.maxHp = Math.round(b.maxHp * scale); }
    return b;
}
