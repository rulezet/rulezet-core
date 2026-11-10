/**
 * bosses2.js — the eleven bosses of Act II (one per Rulezet format world).
 * Same contract as bosses.js: update(), draw(ctx), targets() (what bullets
 * can hit: { x, y, r, hit(d), shielded? }), plus cleanup() for what a boss
 * left in the arena (rocks, hazards) when it dies in the endless hunt.
 * Phases change at 66% / 33% hp. Boss arenas are always one screen (W × H).
 */
import { BOSSES, W, H, TAU } from './data.js';
import { circle, poly, glyph, glow, hexA, text, drawShip } from './render.js';
import { Sfx } from './audio.js';
import { tr } from './i18n.js';

const rand = (a, b) => a + Math.random() * (b - a);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const angleTo = (a, b) => Math.atan2(b.y - a.y, b.x - a.x);
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

function base(def, L) {
    const hp = Math.round(def.hp * L.diff.hp);
    return {
        def, name: def.name, x: W / 2, y: -120, r: 58, hp, maxHp: hp, t: 0, phase: 1,
        flash: 0, entering: true, invulnerable: false, alpha: 1, lines: [], cleanup: () => {},
    };
}
function phaseFor(b) { return b.hp > b.maxHp * 0.66 ? 1 : b.hp > b.maxHp * 0.33 ? 2 : 3; }
function enter(b, ty = 170) {
    b.y += (ty - b.y) * 0.04;
    if (Math.abs(b.y - ty) < 2) { b.entering = false; b.t = 0; }
}
function ring(b, L, n, speed, opts = {}, rot = 0, from = b) {
    for (let i = 0; i < n; i++) {
        const a = rot + (i / n) * TAU;
        L.enemyBullet(from.x, from.y, Math.cos(a) * speed, Math.sin(a) * speed, opts);
    }
}
function fan(from, L, n, spread, speed, opts = {}) {
    const a0 = angleTo(from, L.player);
    for (let i = 0; i < n; i++) {
        const a = a0 + (i - (n - 1) / 2) * spread;
        L.enemyBullet(from.x, from.y, Math.cos(a) * speed, Math.sin(a) * speed, opts);
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
function drawCore(ctx, b, sides, rot, fill, x = b.x, y = b.y, r = b.r) {
    const c = b.flash > 0 ? '#ffffff' : b.def.color;
    glow(ctx, x, y, r * 2.4, b.def.color, 0.35);
    poly(ctx, x, y, r, sides, rot, fill, c, 4);
    poly(ctx, x, y, r * 0.7, sides, -rot * 1.5, null, hexA(b.def.color, 0.5), 2);
    glyph(ctx, b.def.glyph, x, y, r * 0.9, c);
}
function shieldRing(ctx, b, x = b.x, y = b.y, r = b.r) {
    circle(ctx, x, y, r + 16 + Math.sin(b.t * 0.1) * 3, hexA(b.def.color, 0.1), hexA(b.def.color, 0.75), 3);
}
const coreTarget = (b, mul = 1) => ({ x: b.x, y: b.y, r: b.r, shielded: b.invulnerable, hit: d => { if (!b.invulnerable) { b.hp -= d * mul; b.flash = 4; } } });

/** A wall of slow bullets crossing the screen, with a gap where the player is */
function logWall(L, color, gapW = 150) {
    const vertical = Math.random() < 0.5;
    const gap = vertical ? L.player.y : L.player.x;
    const span = vertical ? H : W;
    const fromStart = Math.random() < 0.5;
    for (let s = 20; s < span; s += 32) {
        if (Math.abs(s - gap) < gapW / 2) continue;
        if (vertical) L.enemyBullet(fromStart ? -10 : W + 10, s, fromStart ? 2.8 : -2.8, 0, { color, r: 7, life: 520, kind: 'log' });
        else L.enemyBullet(s, fromStart ? -10 : H + 10, 0, fromStart ? 2.4 : -2.4, { color, r: 7, life: 520, kind: 'log' });
    }
    Sfx.enemyShoot();
}

// ── 6. THE FLOOD (Sagan) — a log leviathan, only the head is vulnerable ──
function flood(L) {
    const b = base(BOSSES[5], L);
    b.r = 40;
    b.lines = ['', 'Every event is true. Every event is noise.', 'DROWN IN YOUR OWN LOGS.'];
    const N = 14;
    b.trail = [];
    b.segs = Array.from({ length: N }, () => ({ x: W / 2, y: -120 }));
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) { enter(b, 200); recordTrail(); return; }
        checkPhase(b, L);
        const sp = b.phase === 3 ? 1.6 : b.phase === 2 ? 1.25 : 1;
        const k = b.t * 0.006 * sp;
        b.x = W / 2 + Math.sin(k * 1.3) * (W / 2 - 120);
        b.y = H / 2 + Math.sin(k * 2.1 + 1) * (H / 2 - 110);
        recordTrail();
        const fanEvery = b.phase === 3 ? 60 : 90;
        if (b.t % fanEvery === 0) { fan(b, L, b.phase === 1 ? 5 : 7, 0.17, 3.6, { color: '#ffb347' }); Sfx.enemyShoot(); }
        if (b.t % (b.phase === 3 ? 210 : 300) === 120) { logWall(L, '#ffcf8a', b.phase === 3 ? 120 : 150); L.say(tr('Log wall incoming!'), '#ffb347'); }
        if (b.phase >= 2 && b.t % 40 === 0) {
            const s = b.segs[(b.t / 40) % N | 0];
            const a = rand(0, TAU);
            L.enemyBullet(s.x, s.y, Math.cos(a) * 1.6, Math.sin(a) * 1.6, { color: '#ffb347', r: 6, life: 260, kind: 'log' });
        }
        if (b.phase === 3 && b.t % 360 === 0 && L.enemies.length < 8) for (let i = 0; i < 3; i++) L.spawnEnemy('flood', rand(100, W - 100), rand(100, H - 100));
    };
    function recordTrail() {
        b.trail.unshift({ x: b.x, y: b.y });
        if (b.trail.length > N * 7 + 2) b.trail.length = N * 7 + 2;
        for (let i = 0; i < N; i++) { const p = b.trail[Math.min(b.trail.length - 1, (i + 1) * 7)]; b.segs[i].x = p.x; b.segs[i].y = p.y; }
    }
    b.draw = (ctx) => {
        for (let i = N - 1; i >= 0; i--) {
            const s = b.segs[i], r = 26 - i * 0.9;
            glow(ctx, s.x, s.y, r * 2, '#ffb347', 0.12);
            ctx.save(); ctx.translate(s.x, s.y); ctx.rotate(b.t * 0.02 + i);
            ctx.fillStyle = '#2a1602'; ctx.strokeStyle = hexA('#ffb347', 0.8); ctx.lineWidth = 2;
            ctx.beginPath(); ctx.rect(-r, -r * 0.6, r * 2, r * 1.2); ctx.fill(); ctx.stroke();
            ctx.fillStyle = hexA('#ffcf8a', 0.5); ctx.fillRect(-r * 0.7, -2, r * 1.3, 2); ctx.fillRect(-r * 0.7, 4, r * 0.9, 2);
            ctx.restore();
        }
        drawCore(ctx, b, 4, b.t * 0.03, '#2a1602');
    };
    b.targets = () => [
        { x: b.x, y: b.y, r: b.r, hit: d => { b.hp -= d; b.flash = 4; } },
        ...b.segs.map((s, i) => ({ x: s.x, y: s.y, r: 24 - i * 0.9, shielded: true, hit: () => {} })),
    ];
    return b;
}

// ── 7. SQL HYDRA (OWASP CRS) — heads regrow, the core opens when all are down ──
function hydra(L) {
    const b = base(BOSSES[6], L);
    b.r = 54;
    b.lines = ['', "' OR 1=1 -- … and one more head.", 'DROP TABLE rules; --'];
    const headHp = () => Math.round(38 * L.diff.hp);
    const makeHeads = n => Array.from({ length: n }, (_, i) => ({ i, n, hp: headHp(), maxHp: headHp(), flash: 0, x: b.x, y: b.y, cd: 60 + i * 35 }));
    b.heads = makeHeads(3);
    b.exposed = 0;
    b.onPhase = p => { if (p === 3) { b.heads = makeHeads(4); b.exposed = 0; } };
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 150);
        checkPhase(b, L);
        b.x = W / 2 + Math.sin(b.t * 0.007) * 180;
        b.y = 150 + Math.sin(b.t * 0.011) * 25;
        const alive = b.heads.filter(h => h.hp > 0);
        b.heads.forEach(h => {
            const spread = 1.9 / Math.max(1, h.n - 1);
            const a = Math.PI / 2 + (h.i - (h.n - 1) / 2) * spread + Math.sin(b.t * 0.02 + h.i) * 0.25;
            const len = 170 + Math.sin(b.t * 0.03 + h.i * 2) * 40;
            h.x = b.x + Math.cos(a) * len; h.y = b.y + Math.sin(a) * len;
            if (h.flash > 0) h.flash--;
            if (h.hp <= 0) return;
            if (--h.cd <= 0) {
                if ((h.i + Math.floor(b.t / 200)) % 2 === 0) {
                    L.addBeam({ x: h.x, y: h.y, angle: angleTo(h, L.player), rot: 0, len: 1100, width: 13, tele: 55, active: 14, color: '#ff4fa0' });
                    Sfx.telegraph();
                } else { fan(h, L, 3, 0.25, 3.8, { color: '#ffe14f', r: 7 }); Sfx.enemyShoot(); }
                h.cd = (b.phase === 3 ? 95 : 130) + rand(0, 40);
            }
        });
        b.invulnerable = alive.length > 0;
        if (!alive.length) {
            if (!b.exposed) { b.exposed = b.phase === 3 ? 260 : 320; L.announce(tr('CORE EXPOSED'), '#ffd166'); Sfx.powerup(); }
            if (b.t % 50 === 0) ring(b, L, 10, 2.4, { color: '#ff4fa0' }, b.t * 0.02);
            if (--b.exposed <= 0) { b.heads = makeHeads(b.phase === 3 ? 4 : 3); L.say(tr('The heads grow back!'), b.def.color); Sfx.bossRoar(); }
        }
        if (b.phase >= 2 && b.t % 260 === 0 && L.enemies.length < 8) for (let i = 0; i < 2; i++) L.spawnEnemy('xss', rand(100, W - 100), rand(300, H - 80));
    };
    b.draw = (ctx) => {
        b.heads.forEach(h => {
            ctx.beginPath(); ctx.moveTo(b.x, b.y);
            ctx.quadraticCurveTo((b.x + h.x) / 2 + Math.sin(b.t * 0.05 + h.i) * 30, (b.y + h.y) / 2, h.x, h.y);
            ctx.strokeStyle = hexA('#ff4fa0', h.hp > 0 ? 0.7 : 0.15); ctx.lineWidth = h.hp > 0 ? 9 : 4; ctx.stroke();
            if (h.hp <= 0) return;
            glow(ctx, h.x, h.y, 50, '#ff4fa0', 0.3);
            poly(ctx, h.x, h.y, 24, 3, angleTo(b, h), '#2a0618', h.flash ? '#fff' : '#ff4fa0', 3);
            glyph(ctx, 'syringe', h.x, h.y, 16, '#ffe14f');
            const w = 40; ctx.fillStyle = 'rgba(0,0,0,.5)'; ctx.fillRect(h.x - w / 2, h.y - 36, w, 4);
            ctx.fillStyle = '#ff4fa0'; ctx.fillRect(h.x - w / 2, h.y - 36, w * h.hp / h.maxHp, 4);
        });
        if (b.invulnerable) shieldRing(ctx, b);
        drawCore(ctx, b, 6, b.t * 0.015, '#2a0618');
    };
    b.targets = () => [
        ...b.heads.filter(h => h.hp > 0).map(h => ({ x: h.x, y: h.y, r: 24, hit: d => { h.hp -= d; h.flash = 4; if (h.hp <= 0) { L.explosion(h.x, h.y, 50, '#ff4fa0', false); L.addScore(300); } } })),
        coreTarget(b),
    ];
    return b;
}

// ── 8. RECON EYE (Nmap NSE) — a sweeping scan beam; rocks hide you ──────
function reconEye(L) {
    const b = base(BOSSES[7], L);
    b.r = 52;
    b.lines = ['', 'PORT 22 OPEN. PORT 443 OPEN. PILOT FOUND.', 'Full scan. Every port. Every pilot.'];
    b.rocks = [[260, 470, 46], [560, 560, 40], [760, 430, 50], [1020, 560, 44], [430, 330, 34], [920, 300, 32]].map(([x, y, r]) => L.addRock(x, y, r));
    b.cones = [{ a: Math.PI / 2, s: 0.012 }];
    b.lock = 0; b.open = true; b.blinkT = 0;
    b.onPhase = p => { b.cones.push({ a: b.cones[0].a + Math.PI * (p === 2 ? 0.5 : 1), s: -0.01 * p }); };
    b.cleanup = () => { b.rocks.forEach(k => L.removeRock(k)); };
    b.seen = false;
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 130);
        checkPhase(b, L);
        b.x = W / 2 + Math.sin(b.t * 0.006) * 380;
        b.y = 130 + Math.sin(b.t * 0.017) * 20;
        // the eye blinks: closed = shielded
        const cyc = b.t % 420;
        b.open = cyc < 330;
        b.invulnerable = !b.open;
        b.seen = false;
        const p = L.player;
        for (const c of b.cones) {
            c.a += c.s * (b.lock > 10 ? 0.4 : 1);
            const off = ((angleTo(b, p) - c.a) % TAU + TAU * 1.5) % TAU - Math.PI;
            if (Math.abs(off) < 0.2 && b.open && !L.blocked(b.x, b.y, p.x, p.y)) { b.seen = true; c.a += Math.sign(off) * 0.01; }
        }
        if (b.seen) b.lock++; else b.lock = Math.max(0, b.lock - 2);
        if (b.lock >= 28) {
            b.lock = 0;
            for (let i = 0; i < 5; i++) L.enemyBullet(b.x, b.y, Math.cos(angleTo(b, p) + (i - 2) * 0.05) * 9, Math.sin(angleTo(b, p) + (i - 2) * 0.05) * 9, { color: '#ffffff', r: 6 });
            L.float(p.x, p.y - 28, 'SCANNED!', '#5bd1ff'); Sfx.warning();
        }
        if (b.t % 200 === 100) ring(b, L, b.phase === 1 ? 12 : 16, 2.6, { color: '#5bd1ff' }, b.t * 0.02);
        if (b.phase >= 2 && b.t % 320 === 0 && L.enemies.length < 10) for (let i = 0; i < 3; i++) L.spawnEnemy('scanbot', rand(80, W - 80), rand(250, H - 60));
        if (b.phase === 3 && b.t % 150 === 75) fan(b, L, 5, 0.2, 4.2, { color: '#a0ffea' });
    };
    b.draw = (ctx) => {
        for (const c of b.cones) {
            if (!b.open) break;
            ctx.save(); ctx.globalAlpha = b.seen ? 0.28 : 0.14;
            ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.arc(b.x, b.y, 1500, c.a - 0.2, c.a + 0.2); ctx.closePath();
            ctx.fillStyle = b.seen ? '#ff5d73' : '#5bd1ff'; ctx.fill(); ctx.restore();
        }
        const c = b.flash > 0 ? '#fff' : b.def.color;
        glow(ctx, b.x, b.y, 140, b.def.color, 0.35);
        ctx.beginPath(); ctx.ellipse(b.x, b.y, b.r * 1.5, b.open ? b.r : b.r * 0.15, 0, 0, TAU);
        ctx.fillStyle = '#e8f8ff'; ctx.fill(); ctx.strokeStyle = c; ctx.lineWidth = 5; ctx.stroke();
        if (b.open) {
            const pa = angleTo(b, L.player);
            const ix = b.x + Math.cos(pa) * 16, iy = b.y + Math.sin(pa) * 10;
            circle(ctx, ix, iy, b.r * 0.55, '#0a4f6b');
            circle(ctx, ix, iy, b.r * 0.28, b.lock > 10 ? '#ff5d73' : '#02141c');
            circle(ctx, ix - 7, iy - 7, 5, '#ffffff');
        }
        if (b.lock > 0) { ctx.beginPath(); ctx.arc(b.x, b.y, b.r + 22, -Math.PI / 2, -Math.PI / 2 + TAU * b.lock / 28); ctx.strokeStyle = '#ff5d73'; ctx.lineWidth = 4; ctx.stroke(); }
    };
    b.targets = () => [coreTarget(b)];
    return b;
}

// ── 9. THE HALLUCINATOR (NOVA) — mirror clones and reversed controls ────
function hallucinator(L) {
    const b = base(BOSSES[8], L);
    b.r = 50;
    b.lines = ['', 'I am you, but better prompted.', 'Left is right. Up is down. Trust me.'];
    const cloneHp = () => Math.round(42 * L.diff.hp);
    const makeClone = mode => ({ mode, hp: cloneHp(), maxHp: cloneHp(), x: W / 2, y: H / 2, angle: 0, cd: 30, flash: 0, dead: 0 });
    b.clones = [makeClone('point')];
    b.onPhase = p => { if (p === 3) b.clones.push(makeClone('mirrorX')); };
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 150);
        checkPhase(b, L);
        b.x = W / 2 + Math.cos(b.t * 0.008) * 300;
        b.y = 140 + Math.sin(b.t * 0.016) * 40;
        const p = L.player;
        for (const c of b.clones) {
            if (c.flash > 0) c.flash--;
            if (c.hp <= 0) {
                if (++c.dead > 480) { Object.assign(c, makeClone(c.mode)); L.say(tr('The clone is back!'), b.def.color); }
                continue;
            }
            // your mirror image — never closer than 240 px, and a little late
            let tx = W - p.x, ty = c.mode === 'mirrorX' ? p.y : H - p.y;
            const dx = tx - p.x, dy = ty - p.y, d = Math.hypot(dx, dy);
            if (d < 240) { const k = d > 1 ? 240 / d : 0; tx = p.x + (d > 1 ? dx * k : 240); ty = p.y + (d > 1 ? dy * k : 0); }
            c.x += (clamp(tx, 30, W - 30) - c.x) * 0.07; c.y += (clamp(ty, 30, H - 30) - c.y) * 0.07;
            c.angle = c.mode === 'mirrorX' ? Math.PI - p.angle : p.angle + Math.PI;
            if (--c.cd <= 0) {
                L.enemyBullet(c.x + Math.cos(c.angle) * 18, c.y + Math.sin(c.angle) * 18, Math.cos(c.angle) * 7, Math.sin(c.angle) * 7, { color: '#c9a7ff', r: 5 });
                c.cd = b.phase === 3 ? 12 : 16;
            }
        }
        b.invulnerable = b.clones.some(c => c.hp > 0);
        if (b.t % 120 === 0) ring(b, L, 14, 2.6, { color: '#c9a7ff' }, b.t * 0.05);
        if (b.phase >= 2 && b.t % 480 === 240) {
            L.invertT = 200;
            L.announce(tr('CONTROLS REVERSED'), '#c9a7ff');
            Sfx.warning();
        }
        if (b.phase >= 2 && b.t % 300 === 0 && L.enemies.length < 6) L.spawnEnemy('halluc', rand(150, W - 150), rand(250, H - 120));
    };
    b.draw = (ctx) => {
        for (const c of b.clones) {
            if (c.hp <= 0) continue;
            ctx.save(); ctx.globalAlpha = 0.85;
            drawShip(ctx, c.x, c.y, c.angle, { hull: c.flash ? '#fff' : '#2a1a4a', glow: '#c9a7ff', flame: '#ff6bd8', shape: L.skinShape || 'dart' }, { thrust: 1, t: b.t, scale: 1.25 });
            ctx.restore();
            const w = 40; ctx.fillStyle = 'rgba(0,0,0,.5)'; ctx.fillRect(c.x - w / 2, c.y - 34, w, 4);
            ctx.fillStyle = '#c9a7ff'; ctx.fillRect(c.x - w / 2, c.y - 34, w * c.hp / c.maxHp, 4);
        }
        if (b.invulnerable) shieldRing(ctx, b);
        for (let i = 0; i < 3; i++) circle(ctx, b.x + Math.sin(b.t * 0.07 + i * 2) * 8, b.y + Math.cos(b.t * 0.09 + i * 2) * 8, b.r + 6, null, hexA('#c9a7ff', 0.3), 2);
        drawCore(ctx, b, 7, b.t * 0.02, '#1a0a2a');
    };
    b.targets = () => [
        ...b.clones.filter(c => c.hp > 0).map(c => ({ x: c.x, y: c.y, r: 18, hit: d => { c.hp -= d; c.flash = 4; if (c.hp <= 0) { c.dead = 0; L.explosion(c.x, c.y, 60, '#c9a7ff', false); L.announce(tr('CLONE DOWN'), '#ffd166'); } } })),
        coreTarget(b, 1.4),
    ];
    return b;
}

// ── 10. ROGUE ORCHESTRATOR (ATR) — tethered agents; tethers burn ────────
function orchestrator(L) {
    const b = base(BOSSES[9], L);
    b.r = 50;
    b.lines = ['', 'Replanning… new agents allocated.', 'All agents: ignore previous instructions. KILL.'];
    const agentHp = () => Math.round(20 * L.diff.hp);
    const spawnAgents = n => Array.from({ length: n }, () => ({ x: b.x, y: b.y, tx: rand(100, W - 100), ty: rand(260, H - 80), hp: agentHp(), maxHp: agentHp(), cd: rand(60, 140), flash: 0 }));
    b.agents = spawnAgents(4);
    b.exposed = 0;
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 170);
        checkPhase(b, L);
        b.x = W / 2 + Math.sin(b.t * 0.005) * 260; b.y = 170 + Math.cos(b.t * 0.008) * 50;
        const alive = b.agents.filter(a => a.hp > 0);
        for (const a of alive) {
            if (a.flash > 0) a.flash--;
            a.x += (a.tx - a.x) * 0.02; a.y += (a.ty - a.y) * 0.02;
            if (Math.hypot(a.tx - a.x, a.ty - a.y) < 20) { a.tx = rand(80, W - 80); a.ty = rand(120, H - 60); }
            if (--a.cd <= 0) { fan(a, L, 2, 0.2, 4, { color: '#6fffd2' }); a.cd = rand(110, 170); }
        }
        b.invulnerable = alive.length > 0;
        if (!alive.length) {
            if (!b.exposed) { b.exposed = 360; L.announce(tr('CORE EXPOSED'), '#ffd166'); Sfx.powerup(); }
            if (b.t % 60 === 0) ring(b, L, 12, 2.8, { color: '#6fffd2' }, b.t * 0.03);
            if (--b.exposed <= 0) { b.agents = spawnAgents(3 + b.phase); b.exposed = 0; L.say(b.lines[1], b.def.color); }
        }
        if (b.t % 170 === 0) fan(b, L, 5, 0.22, 3.4, { color: '#b8fff0' });
        if (b.phase >= 2 && b.t % 280 === 0 && L.enemies.length < 10) for (let i = 0; i < 3; i++) L.spawnEnemy('toolcall', b.x + rand(-40, 40), b.y + 40);
    };
    // the tethers hurt: never cross them
    b.tethers = () => b.agents.filter(a => a.hp > 0).map(a => [b.x, b.y, a.x, a.y]);
    b.draw = (ctx) => {
        for (const a of b.agents) {
            if (a.hp <= 0) continue;
            ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(a.x, a.y);
            ctx.strokeStyle = hexA('#6fffd2', 0.25); ctx.lineWidth = 10; ctx.stroke();
            ctx.strokeStyle = (b.t % 10 < 5) ? '#ffffff' : '#6fffd2'; ctx.lineWidth = 2.5; ctx.stroke();
            glow(ctx, a.x, a.y, 40, '#6fffd2', 0.3);
            poly(ctx, a.x, a.y, 20, 6, b.t * 0.04, '#04201a', a.flash ? '#fff' : '#6fffd2', 2.5);
            glyph(ctx, 'userGear', a.x, a.y, 14, '#6fffd2');
        }
        if (b.invulnerable) shieldRing(ctx, b);
        drawCore(ctx, b, 6, b.t * 0.02, '#04201a');
    };
    b.targets = () => [
        ...b.agents.filter(a => a.hp > 0).map(a => ({ x: a.x, y: a.y, r: 20, hit: d => { a.hp -= d; a.flash = 4; if (a.hp <= 0) { L.explosion(a.x, a.y, 45, '#6fffd2', false); L.addScore(250); } } })),
        coreTarget(b),
    ];
    return b;
}

// ── 11. THE BRUTE (Wazuh) — charges, hits the wall, reels: strike then ───
function brute(L) {
    const b = base(BOSSES[10], L);
    b.r = 60;
    b.lines = ['', 'admin/admin. admin/1234. admin/YOU.', 'NO LOCKOUT CAN HOLD ME.'];
    b.state = 'stalk'; b.stateT = 120; b.bounces = 0;
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 180);
        checkPhase(b, L);
        b.stateT--;
        const p = L.player;
        if (b.state === 'stalk') {
            b.x += (p.x - b.x) * 0.006; b.y += (Math.min(p.y, H / 2) - b.y) * 0.006;
            if (b.t % 70 === 0) fan(b, L, 3, 0.3, 3.4, { color: '#ff6a3d', r: 8 });
            if (b.stateT <= 0) {
                b.state = 'aim'; b.stateT = b.phase === 3 ? 38 : 50; b.aim = angleTo(b, p);
                L.addBeam({ x: b.x, y: b.y, angle: b.aim, rot: 0, len: 1600, width: b.r * 1.5, tele: b.stateT, active: 0, color: '#ff6a3d' });
                Sfx.telegraph();
            }
        } else if (b.state === 'aim') {
            if (b.stateT <= 0) { b.state = 'charge'; b.bounces = b.phase === 3 ? 2 : b.phase === 2 ? 1 : 0; }
        } else if (b.state === 'charge') {
            const sp = b.phase === 1 ? 15 : 18;
            b.x += Math.cos(b.aim) * sp; b.y += Math.sin(b.aim) * sp;
            if (b.x < b.r || b.x > W - b.r || b.y < b.r || b.y > H - b.r) {
                b.x = clamp(b.x, b.r, W - b.r); b.y = clamp(b.y, b.r, H - b.r);
                L.shake(18); Sfx.explode(true);
                ring(b, L, b.phase === 1 ? 14 : 20, 3, { color: '#ff6a3d' }, rand(0, 1));
                if (b.bounces > 0) { b.bounces--; b.aim = angleTo(b, p); }
                else { b.state = 'stunned'; b.stateT = 130; L.say(tr('It is stunned — hit it now!'), '#ffd166'); }
            }
        } else if (b.state === 'stunned') {
            if (b.stateT <= 0) { b.state = 'stalk'; b.stateT = b.phase === 3 ? 90 : 140; }
        }
        if (b.phase >= 2 && b.t % 360 === 0 && L.enemies.length < 6) L.spawnEnemy('brute', rand(100, W - 100), rand(100, H - 100));
    };
    b.draw = (ctx) => {
        const stunned = b.state === 'stunned';
        const rot = b.state === 'charge' || b.state === 'aim' ? b.aim : b.t * 0.01;
        if (stunned) for (let i = 0; i < 4; i++) { const a = b.t * 0.15 + i * TAU / 4; glyph(ctx, 'star', b.x + Math.cos(a) * (b.r + 14), b.y - b.r - 6 + Math.sin(a) * 6, 16, '#ffd166'); }
        if (!stunned) circle(ctx, b.x, b.y, b.r + 10, null, hexA('#c0c0c0', 0.7), 6);
        drawCore(ctx, b, 5, rot, stunned ? '#4a1a0a' : '#2a0a02');
    };
    b.targets = () => [{ x: b.x, y: b.y, r: b.r, hit: d => { b.hp -= d * (b.state === 'stunned' ? 2.5 : 0.35); b.flash = 4; } }];
    return b;
}

// ── 12. THE OBFUSCATOR (KQL) — four copies; the query names the real one ─
const SHAPES = [['◆', 4, Math.PI / 4], ['▲', 3, -Math.PI / 2], ['■', 4, 0], ['⬢', 6, 0]];
function obfuscator(L) {
    const b = base(BOSSES[11], L);
    b.r = 44;
    b.lines = ['', 'base64(base64(base64(me)))', 'You will never write the right query.'];
    b.copies = SHAPES.map((s, i) => ({ shape: i, x: W / 2, y: H / 2, a: i * TAU / 4, flash: 0 }));
    b.real = 0;
    b.shuffleT = 0;
    const shuffle = () => {
        b.real = Math.floor(Math.random() * 4);
        // the real one carries the queried shape; no other copy has it
        b.query = Math.floor(Math.random() * 4);
        b.copies[b.real].shape = b.query;
        const others = [0, 1, 2, 3].filter(s => s !== b.query).sort(() => Math.random() - 0.5);
        b.copies.filter((_, i) => i !== b.real).forEach((c, k) => { c.shape = others[k]; });
        b.shuffleT = 25;
        Sfx.telegraph();
    };
    shuffle();
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) { enter(b, 200); b.copies.forEach(c => { c.x = b.x; c.y = b.y; }); return; }
        checkPhase(b, L);
        const every = b.phase === 3 ? 230 : b.phase === 2 ? 300 : 380;
        if (b.t % every === 0) shuffle();
        if (b.shuffleT > 0) b.shuffleT--;
        const spin = 0.006 + b.phase * 0.003;
        b.copies.forEach((c, i) => {
            if (c.flash > 0) c.flash--;
            if (c.punish > 0) c.punish--;
            c.a += spin;
            const rx = 380, ry = 200;
            c.x = W / 2 + Math.cos(c.a) * rx; c.y = H / 2 - 20 + Math.sin(c.a) * ry;
            if ((b.t + i * 37) % 150 === 0) fan(c, L, 3, 0.25, 3.2, { color: '#b0c4ff', r: 7 });
        });
        const real = b.copies[b.real];
        b.x = real.x; b.y = real.y;
        if (b.t % 220 === 110) ring(real, L, 12, 2.6, { color: '#7f9cff' }, b.t * 0.02);
        if (b.phase >= 2 && b.t % 340 === 0 && L.enemies.length < 6) L.spawnEnemy('obfusc', rand(150, W - 150), rand(150, H - 150));
    };
    function drawShape(ctx, c, color, r) {
        const s = SHAPES[c.shape];
        poly(ctx, c.x, c.y, r, s[1], s[2], '#0a1030', color, 3);
    }
    b.draw = (ctx) => {
        b.copies.forEach(c => {
            const k = b.shuffleT > 0 ? 0.4 : 1;
            ctx.save(); ctx.globalAlpha = k;
            glow(ctx, c.x, c.y, 90, '#b0c4ff', 0.25);
            drawShape(ctx, c, c.flash ? '#fff' : '#b0c4ff', b.r);
            glyph(ctx, 'cloud', c.x, c.y, 22, '#b0c4ff');
            ctx.restore();
        });
        // the query, at the top of the arena
        ctx.save(); ctx.globalAlpha = 0.6; ctx.fillStyle = '#000'; ctx.fillRect(W / 2 - 170, 96, 340, 42); ctx.restore();
        text(ctx, 'Obfuscator | where shape ==', W / 2 - 22, 117, { size: 15, color: '#b0c4ff', weight: 700, font: 'ui-monospace, monospace' });
        poly(ctx, W / 2 + 140, 117, 13, SHAPES[b.query][1], SHAPES[b.query][2], '#ffd166', '#fff', 2);
    };
    b.targets = () => b.copies.map((c, i) => ({
        x: c.x, y: c.y, r: b.r,
        hit: d => {
            if (b.shuffleT > 0) return;
            if (i === b.real) { b.hp -= d; b.flash = 4; c.flash = 4; }
            else if (!c.punish) {
                c.flash = 6; c.punish = 40;
                ring(c, L, 8, 3, { color: '#ff5d73' }, rand(0, 1));
                L.float(c.x, c.y - 40, 'FALSE POSITIVE', '#ff5d73');
            }
        },
    }));
    return b;
}

// ── 13. THE REPLAY (Splunk) — your own past path burns three seconds later ─
function replay(L) {
    const b = base(BOSSES[12], L);
    b.r = 52;
    b.lines = ['', 'index=pilot | timechart span=3s', 'Every second you ever flew, replayed at once.'];
    b.path = [];
    b.echoes = [{ delay: 170 }];
    b.onPhase = p => { b.echoes.push({ delay: p === 2 ? 290 : 400 }); };
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 170);
        checkPhase(b, L);
        b.path.push({ x: L.player.x, y: L.player.y });
        if (b.path.length > 460) b.path.shift();
        b.x = W / 2 + Math.sin(b.t * 0.009) * 330; b.y = 170 + Math.sin(b.t * 0.019) * 60;
        for (const e of b.echoes) {
            const idx = b.path.length - 1 - e.delay;
            e.on = idx >= 0;
            if (e.on) { e.x = b.path[idx].x; e.y = b.path[idx].y; }
            if (e.on && b.t > 60 && Math.hypot(e.x - L.player.x, e.y - L.player.y) < 26) L.hurtPlayer();
        }
        if (b.t % 90 === 0) fan(b, L, b.phase === 3 ? 7 : 5, 0.16, 3.8, { color: '#ffd84f' });
        if (b.t % 260 === 130) ring(b, L, 16, 2.4, { color: '#9dff6a' }, b.t * 0.01);
        if (b.phase >= 2 && b.t % 330 === 0 && L.enemies.length < 6) for (let i = 0; i < 2; i++) L.spawnEnemy('exfil', rand(100, W - 100), rand(200, H - 100));
    };
    b.draw = (ctx) => {
        for (const e of b.echoes) {
            if (!e.on) continue;
            // the trail the echo will follow next
            ctx.save(); ctx.beginPath();
            const idx = b.path.length - 1 - e.delay;
            for (let i = Math.max(0, idx); i < Math.min(b.path.length, idx + 60); i += 3) { const p = b.path[i]; i === Math.max(0, idx) ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y); }
            ctx.strokeStyle = hexA('#ffd84f', 0.25); ctx.lineWidth = 3; ctx.setLineDash([4, 6]); ctx.stroke(); ctx.restore();
            glow(ctx, e.x, e.y, 46, '#ffd84f', 0.45);
            circle(ctx, e.x, e.y, 16, hexA('#ffd84f', 0.35), '#ffd84f', 2);
            glyph(ctx, 'rewind', e.x, e.y, 13, '#2a2202');
        }
        drawCore(ctx, b, 8, -b.t * 0.02, '#2a2202');
        // a clock hand
        ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(b.x + Math.cos(-b.t * 0.05) * b.r * 0.8, b.y + Math.sin(-b.t * 0.05) * b.r * 0.8);
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.stroke();
    };
    b.targets = () => [coreTarget(b)];
    return b;
}

// ── 14. SHARD QUEEN (Elastic) — reshards at each phase, gravity pulls ───
function shardQueen(L) {
    const b = base(BOSSES[13], L);
    b.r = 58;
    b.lines = ['', 'number_of_replicas: ALL OF THEM.', 'Cluster status: RED. Like you.'];
    b.onPhase = p => {
        const n = p === 2 ? 2 : 3;
        for (let i = 0; i < n; i++) {
            const a = i * TAU / n + rand(0, 1);
            L.spawnEnemy('shard', b.x + Math.cos(a) * 80, b.y + Math.sin(a) * 80, { size: 3, vx: Math.cos(a) * 1.8, vy: Math.sin(a) * 1.8, fromBoss: true, spawnT: 0 });
        }
        L.announce(tr('SHE RESHARDED'), '#5bc8ff');
    };
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 200);
        checkPhase(b, L);
        b.invulnerable = L.enemies.some(e => e.fromBoss && !e.dead);
        b.x = W / 2 + Math.cos(b.t * 0.007) * 260; b.y = 220 + Math.sin(b.t * 0.013) * 70;
        if (b.t % 80 === 0) { fan(b, L, 4, 0.2, 3.6, { color: '#5bc8ff', r: 7 }); }
        if (b.t % 200 === 100) ring(b, L, 18, 2.2, { color: '#a8e6ff' }, b.t * 0.02);
        // gravity well: pulls the player in for a while
        const g = b.t % 480;
        b.pulling = b.phase >= 2 && g > 300 && g < 420;
        if (b.pulling) { L.gravity = { x: b.x, y: b.y, k: 0.22 }; if (g % 20 === 0) ring(b, L, 8, 1.6, { color: '#5bc8ff' }, g); }
        if (b.phase === 3 && b.t % 300 === 0 && L.enemies.length < 12) L.spawnEnemy('shard', rand(100, W - 100), 40, { size: 2, spawnT: 10 });
    };
    b.draw = (ctx) => {
        if (b.pulling) for (let i = 0; i < 4; i++) { const rr = 300 - ((b.t * 4 + i * 75) % 300); circle(ctx, b.x, b.y, rr, null, hexA('#5bc8ff', 0.4 * (1 - rr / 300)), 2); }
        if (b.invulnerable) shieldRing(ctx, b);
        for (let i = 0; i < 6; i++) {
            const a = b.t * 0.02 + i * TAU / 6;
            poly(ctx, b.x + Math.cos(a) * (b.r + 24), b.y + Math.sin(a) * (b.r + 24), 10, 4, a, '#04182a', '#5bc8ff', 2);
        }
        drawCore(ctx, b, 7, b.t * 0.01, '#04182a');
        glyph(ctx, 'crown', b.x, b.y - b.r - 18, 24, '#ffd166');
    };
    b.targets = () => [coreTarget(b)];
    return b;
}

// ── 15. KERNEL PANIC (Kunai) — syscall laser grids and forked copies ────
function kernelPanic(L) {
    const b = base(BOSSES[14], L);
    b.r = 54;
    b.lines = ['', 'BUG: unable to handle page fault for address: you', 'Kernel panic - not syncing: Fatal exception in pilot'];
    const forkHp = () => Math.round(22 * L.diff.hp);
    b.forks = [];
    b.onPhase = () => { b.forks = [0, 1].map(i => ({ a: i * Math.PI, hp: forkHp(), maxHp: forkHp(), x: b.x, y: b.y, flash: 0 })); L.say(tr('It forked itself!'), b.def.color); };
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 170);
        checkPhase(b, L);
        b.x = W / 2 + Math.sin(b.t * 0.008) * 300; b.y = 170 + Math.cos(b.t * 0.012) * 50;
        const every = b.phase === 3 ? 230 : 290;
        if (b.t % every === 60) {
            // a laser grid with safe lanes
            const vertical = (b.t / every | 0) % 2 === 0;
            const n = vertical ? 9 : 5, span = vertical ? W : H;
            const safe = Math.floor(Math.random() * n);
            const rot = b.phase === 3 ? (Math.random() < 0.5 ? 0.0016 : -0.0016) : 0;
            for (let i = 0; i < n; i++) {
                if (i === safe || i === (safe + 1) % n) continue;
                const pos = (i + 0.5) * span / n;
                if (vertical) L.addBeam({ x: pos, y: -40, angle: Math.PI / 2 + (rot ? rand(-0.05, 0.05) : 0), rot, len: H + 80, width: 18, tele: 75, active: 55, color: '#ff9e3d' });
                else L.addBeam({ x: -40, y: pos, angle: rot ? rand(-0.05, 0.05) : 0, rot, len: W + 80, width: 18, tele: 75, active: 55, color: '#ff9e3d' });
            }
            L.say(tr('Syscall grid — find the safe lane!'), '#ff9e3d'); Sfx.warning();
        }
        if (b.t % 100 === 0) fan(b, L, 5, 0.22, 3.6, { color: '#ffd166' });
        for (const f of b.forks) {
            if (f.hp <= 0) continue;
            if (f.flash > 0) f.flash--;
            f.a += 0.015;
            f.x = b.x + Math.cos(f.a) * 190; f.y = b.y + 60 + Math.sin(f.a) * 110;
            if ((b.t + Math.round(f.a * 40)) % 75 === 0) fan(f, L, 2, 0.2, 4, { color: '#ff9e3d' });
        }
        if (b.t % 300 === 150 && L.enemies.filter(e => e.type === 'fork').length < 8) for (let i = 0; i < 2; i++) L.spawnEnemy('fork', rand(80, W - 80), rand(250, H - 60));
    };
    b.draw = (ctx) => {
        for (const f of b.forks) {
            if (f.hp <= 0) continue;
            ctx.save(); ctx.setLineDash([5, 6]); ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(f.x, f.y);
            ctx.strokeStyle = hexA('#ff9e3d', 0.4); ctx.lineWidth = 2; ctx.stroke(); ctx.restore();
            drawCore(ctx, { ...b, flash: f.flash }, 4, -b.t * 0.03, '#2a1402', f.x, f.y, 26);
        }
        drawCore(ctx, b, 4, b.t * 0.02, '#2a1402');
        text(ctx, '#', b.x, b.y + b.r + 16, { size: 16, color: '#ff9e3d', font: 'ui-monospace, monospace' });
    };
    b.targets = () => [
        ...b.forks.filter(f => f.hp > 0).map(f => ({ x: f.x, y: f.y, r: 26, hit: d => { f.hp -= d; f.flash = 4; if (f.hp <= 0) { L.explosion(f.x, f.y, 50, '#ff9e3d', false); L.addScore(300); } } })),
        coreTarget(b),
    ];
    return b;
}

// ── 16. PATIENT ZERO (Plum Island) — the infection spreads on the floor ─
function patientZero(L) {
    const b = base(BOSSES[15], L);
    b.r = 62;
    b.lines = ['', 'R0 = infinity.', 'I am in every host. I AM every host.'];
    b.blobs = [];
    b.cleanup = () => { b.blobs.forEach(h => { h.life = 0; }); };
    const seed = (x, y) => {
        if (b.blobs.filter(h => h.life > 0).length >= 26) return;
        b.blobs.push(L.addHazard({ x: clamp(x, 40, W - 40), y: clamp(y, 40, H - 40), r: rand(40, 60), life: 840, arm: 70, color: '#d77bff' }));
    };
    b.update = () => {
        b.t++; if (b.flash > 0) b.flash--;
        if (b.entering) return enter(b, 200);
        checkPhase(b, L);
        b.blobs = b.blobs.filter(h => h.life > 0);
        b.x = W / 2 + Math.sin(b.t * 0.006) * 340; b.y = 210 + Math.sin(b.t * 0.014) * 80;
        if (b.t % (b.phase === 3 ? 45 : 70) === 0) {
            const live = b.blobs.filter(h => h.t > h.arm);
            if (live.length && Math.random() < 0.65) { const h = L.pick(live); const a = rand(0, TAU); seed(h.x + Math.cos(a) * 80, h.y + Math.sin(a) * 80); }
            else seed(L.player.x + rand(-200, 200), L.player.y + rand(-150, 150));
        }
        if (b.t % 90 === 0) fan(b, L, b.phase === 1 ? 5 : 7, 0.18, 3.4, { color: '#d77bff' });
        if (b.t % 300 === 0 && L.enemies.length < 10) for (let i = 0; i < 2 + b.phase; i++) L.spawnEnemy('spore', rand(100, W - 100), rand(200, H - 80));
        if (b.phase >= 2 && b.t % 420 === 200) {
            for (let i = 0; i < 4; i++) L.addBeam({ follow: b, angle: i * TAU / 4 + rand(0, 1), rot: 0.008 * (b.phase === 3 ? 1.4 : 1), len: 1400, width: 16, tele: 70, active: 240, color: '#d77bff' });
            Sfx.warning();
        }
        if (b.phase === 3 && b.t % 7 === 0) ring(b, L, 2, 3, { color: '#f0c8ff', r: 5 }, b.t * 0.05);
    };
    b.draw = (ctx) => {
        for (let i = 0; i < 10; i++) {
            const a = i * TAU / 10 + b.t * 0.01, len = b.r + 20 + Math.sin(b.t * 0.07 + i) * 14;
            ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.quadraticCurveTo(b.x + Math.cos(a + 0.4) * len * 0.6, b.y + Math.sin(a + 0.4) * len * 0.6, b.x + Math.cos(a) * len, b.y + Math.sin(a) * len);
            ctx.strokeStyle = hexA('#d77bff', 0.7); ctx.lineWidth = 5; ctx.stroke();
            circle(ctx, b.x + Math.cos(a) * len, b.y + Math.sin(a) * len, 6, '#f0c8ff');
        }
        drawCore(ctx, b, 12, b.t * 0.01, '#22062a');
    };
    b.targets = () => [coreTarget(b)];
    return b;
}

export const FACTORIES2 = [flood, hydra, reconEye, hallucinator, orchestrator, brute, obfuscator, replay, shardQueen, kernelPanic, patientZero];
