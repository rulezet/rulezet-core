/**
 * enemies.js — every enemy type's behaviour and look. An enemy is a plain
 * object { type, def, x, y, vx, vy, hp, r, t, … }; `L` is the running
 * Level (level.js) — the enemy calls back into it to shoot, spawn, etc.
 */
import { ENEMIES, W, H, TAU } from './data.js';
import { circle, poly, glyph, glow, hexA } from './render.js';
import { Sfx } from './audio.js';

const rand = (a, b) => a + Math.random() * (b - a);
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const angleTo = (a, b) => Math.atan2(b.y - a.y, b.x - a.x);

/** Who an enemy goes after: the sensor in "protect" levels for some of them */
function target(e, L) {
    return (e.huntsSensor && L.sensor && L.sensor.hp > 0) ? L.sensor : L.player;
}

function steer(e, tx, ty, speed, accel = 0.08) {
    const a = Math.atan2(ty - e.y, tx - e.x);
    e.vx += (Math.cos(a) * speed - e.vx) * accel;
    e.vy += (Math.sin(a) * speed - e.vy) * accel;
}

function keepInArena(e, margin = 20) {
    if (e.x < margin) { e.x = margin; e.vx = Math.abs(e.vx); }
    if (e.x > W - margin) { e.x = W - margin; e.vx = -Math.abs(e.vx); }
    if (e.y < margin) { e.y = margin; e.vy = Math.abs(e.vy); }
    if (e.y > H - margin) { e.y = H - margin; e.vy = -Math.abs(e.vy); }
}

function shootAt(e, L, tgt, speed, opts = {}) {
    const a = angleTo(e, tgt) + (opts.offset || 0);
    L.enemyBullet(e.x, e.y, Math.cos(a) * speed, Math.sin(a) * speed, opts);
}

function ring(e, L, n, speed, opts = {}, rot = 0) {
    for (let i = 0; i < n; i++) {
        const a = rot + (i / n) * TAU;
        L.enemyBullet(e.x, e.y, Math.cos(a) * speed, Math.sin(a) * speed, opts);
    }
}

export function makeEnemy(type, x, y, L, extra = {}) {
    const def = ENEMIES[type];
    const hpScale = (L.diff.hp) * (1 + (L.tier || 0) * 0.035);
    const e = {
        type, def, x, y, vx: 0, vy: 0, r: def.r,
        hp: Math.max(1, Math.round(def.hp * hpScale * 10) / 10), t: 0, flash: 0,
        cool: rand(40, 120), state: 'idle', stateT: 0, alpha: 1, spawnT: 30,
        huntsSensor: !!(L.sensor && !def.static && Math.random() < 0.45),
        ...extra,
    };
    e.maxHp = e.hp;
    if (type === 'trojan') e.state = 'disguised';
    if (type === 'rootkit') { e.state = 'burrowed'; e.stateT = rand(30, 90); e.alpha = 0; }
    if (type === 'miner') e.orbit = rand(0, TAU);
    return e;
}

/** Can the player's bullets hit it right now? */
export function hittable(e) {
    if (e.spawnT > 0) return false;
    if (e.type === 'rootkit') return e.state === 'surfaced' || e.state === 'firing';
    return true;
}

/** Returns true if the bullet is deflected (locker's front shield) */
export function deflects(e, b) {
    if (e.type !== 'locker' || b.pierce) return false;
    const facing = e.facing || 0;
    const from = Math.atan2(b.y - e.y, b.x - e.x);
    let d = Math.abs(((from - facing) + Math.PI * 3) % TAU - Math.PI);
    return d < Math.PI / 3;
}

export function updateEnemy(e, L) {
    e.t++;
    if (e.flash > 0) e.flash--;
    if (e.spawnT > 0) { e.spawnT--; return; }
    const p = L.player;
    const tgt = target(e, L);
    const sp = e.def.speed * (L.slow ? 0.5 : 1);
    e.cool--;
    e.stateT--;

    switch (e.type) {
        case 'worm': {
            const wob = Math.sin(e.t * 0.12) * 0.9;
            const a = angleTo(e, tgt) + wob * 0.6;
            steer(e, e.x + Math.cos(a) * 100, e.y + Math.sin(a) * 100, sp, 0.06);
            break;
        }
        case 'wormlet':
        case 'drone': {
            steer(e, tgt.x, tgt.y, sp, e.type === 'drone' ? 0.05 : 0.08);
            if (e.type === 'drone') {          // separation — swarms spread out
                for (const o of L.enemies) {
                    if (o === e || o.type !== 'drone') continue;
                    const d = dist(e, o);
                    if (d < 26 && d > 0) { e.vx += (e.x - o.x) / d * 0.25; e.vy += (e.y - o.y) / d * 0.25; }
                }
            }
            break;
        }
        case 'spammer': {
            const d = dist(e, p);
            const want = d < 260 ? -1 : d > 380 ? 1 : 0;
            const a = angleTo(e, p) + Math.PI / 2;
            e.vx += (Math.cos(angleTo(e, p)) * want * sp + Math.cos(a) * sp * 0.6 - e.vx) * 0.04;
            e.vy += (Math.sin(angleTo(e, p)) * want * sp + Math.sin(a) * sp * 0.6 - e.vy) * 0.04;
            if (e.cool <= 0) {
                for (let i = -2; i <= 2; i++) shootAt(e, L, tgt, 3.2, { offset: i * 0.2, color: '#ffb35c' });
                e.cool = 120; Sfx.enemyShoot();
            }
            break;
        }
        case 'trojan': {
            if (e.state === 'disguised') {
                e.vx *= 0.96; e.vy *= 0.96;
                e.vx += Math.cos(e.t * 0.02) * 0.02; e.vy += Math.sin(e.t * 0.017) * 0.02;
                if (dist(e, p) < 170) { e.state = 'reveal'; e.stateT = 24; Sfx.telegraph(); }
            } else if (e.state === 'reveal') {
                e.vx = e.vy = 0;
                if (e.stateT <= 0) { e.state = 'charge'; e.stateT = 55; const a = angleTo(e, tgt); e.vx = Math.cos(a) * sp * 2.2; e.vy = Math.sin(a) * sp * 2.2; }
            } else if (e.state === 'charge') {
                if (e.stateT <= 0) { e.state = 'recover'; e.stateT = 70; }
            } else {
                e.vx *= 0.94; e.vy *= 0.94;
                if (e.stateT <= 0) { e.state = 'reveal'; e.stateT = 30; }
            }
            break;
        }
        case 'phisher': {
            const d = dist(e, p);
            const a = angleTo(e, p);
            const want = d < 300 ? -1 : d > 420 ? 0.8 : 0;
            e.vx += (Math.cos(a) * want * sp + Math.cos(a + 1.57) * 0.5 - e.vx) * 0.05;
            e.vy += (Math.sin(a) * want * sp + Math.sin(a + 1.57) * 0.5 - e.vy) * 0.05;
            if (e.cool <= 0) { shootAt(e, L, p, 5.2, { kind: 'hook', r: 8, color: '#3ee0c8', life: 120 }); e.cool = 170; Sfx.enemyShoot(); }
            break;
        }
        case 'botnet':
        case 'beacon': {
            e.vx = e.vy = 0;
            if (e.cool <= 0) {
                const cap = e.type === 'botnet' ? 10 : 8 + L.world;
                const kids = L.enemies.filter(o => o.parent === e).length;
                if (kids < (e.type === 'botnet' ? 5 : 3) && L.enemies.length < cap + 12) {
                    const kind = e.type === 'botnet' ? 'drone' : L.pick(L.pool.filter(k => !ENEMIES[k].static));
                    const a = rand(0, TAU);
                    L.spawnEnemy(kind, e.x + Math.cos(a) * 50, e.y + Math.sin(a) * 50, { parent: e });
                }
                e.cool = (e.type === 'botnet' ? 150 : 230) / L.diff.spawn;
            }
            if (e.type === 'beacon' && e.t % 200 === 100) ring(e, L, 10, 2.4, { color: '#ff5d73' }, e.t * 0.01);
            break;
        }
        case 'miner': {
            const d = dist(e, p);
            if (d < 200) { const a = angleTo(p, e); steer(e, e.x + Math.cos(a) * 100, e.y + Math.sin(a) * 100, sp * 1.3, 0.1); }
            else { e.orbit += 0.008; steer(e, W / 2 + Math.cos(e.orbit) * 420, H / 2 + Math.sin(e.orbit) * 250, sp, 0.04); }
            if (e.t % 60 === 0) L.drainBytes(e, 1);
            break;
        }
        case 'locker': {
            e.facing = angleTo(e, p);
            steer(e, tgt.x, tgt.y, sp, 0.03);
            if (e.cool <= 0) {
                for (let i = -1; i <= 1; i++) shootAt(e, L, p, 2.2, { offset: i * 0.35, r: 11, color: '#ff7a3c', dmg: 1 });
                e.cool = 150; Sfx.enemyShoot();
            }
            break;
        }
        case 'mine': {
            if (e.state === 'idle') {
                e.vx += Math.cos(e.t * 0.01 + e.x) * 0.01; e.vy += Math.sin(e.t * 0.013 + e.y) * 0.01;
                e.vx *= 0.99; e.vy *= 0.99;
                if (dist(e, p) < 110) { e.state = 'armed'; e.stateT = 45; Sfx.telegraph(); }
            } else if (e.state === 'armed') {
                e.vx *= 0.8; e.vy *= 0.8;
                if (e.stateT <= 0) { L.explosion(e.x, e.y, 105, e.def.color, true); e.hp = 0; e.silent = true; }
            }
            break;
        }
        case 'keylogger': {
            if (e.state === 'idle') {
                e.alpha += (0.12 - e.alpha) * 0.1;
                if (!e.wp || dist(e, e.wp) < 30) e.wp = { x: rand(80, W - 80), y: rand(80, H - 80) };
                steer(e, e.wp.x, e.wp.y, sp, 0.04);
                if (e.cool <= 0) { e.state = 'aim'; e.stateT = 55; Sfx.telegraph(); }
            } else if (e.state === 'aim') {
                e.alpha += (1 - e.alpha) * 0.2; e.vx *= 0.85; e.vy *= 0.85;
                e.aim = angleTo(e, p);
                if (e.stateT <= 0) {
                    L.enemyBullet(e.x, e.y, Math.cos(e.aim) * 10, Math.sin(e.aim) * 10, { r: 6, color: '#7cf29a', life: 140 });
                    e.state = 'idle'; e.cool = 140; Sfx.enemyShoot();
                }
            }
            break;
        }
        case 'rootkit': {
            if (e.state === 'burrowed') {
                e.alpha = 0;
                if (e.stateT <= 0) {
                    const a = rand(0, TAU), d = rand(150, 240);
                    e.x = Math.min(W - 60, Math.max(60, p.x + Math.cos(a) * d));
                    e.y = Math.min(H - 60, Math.max(60, p.y + Math.sin(a) * d));
                    e.state = 'emerging'; e.stateT = 42; Sfx.telegraph();
                }
            } else if (e.state === 'emerging') {
                e.alpha = 0.25;
                if (e.stateT <= 0) { e.state = 'firing'; e.stateT = 10; ring(e, L, 10, 3, { color: '#9b8cff' }, rand(0, 1)); Sfx.enemyShoot(); }
            } else if (e.state === 'firing') {
                e.alpha = 1;
                if (e.stateT <= 0) { e.state = 'surfaced'; e.stateT = 110; }
            } else {
                e.alpha = 1;
                if (e.stateT === 55) ring(e, L, 6, 2.6, { color: '#9b8cff' }, 0.5);
                if (e.stateT <= 0) { e.state = 'burrowed'; e.stateT = rand(60, 110); }
            }
            e.vx = e.vy = 0;
            break;
        }
        case 'apt': {
            const d = dist(e, p), a = angleTo(e, p);
            const want = d < 220 ? -1 : d > 320 ? 1 : 0;
            const side = Math.sin(e.t * 0.02) > 0 ? 1 : -1;
            e.vx += (Math.cos(a) * want * sp + Math.cos(a + 1.57 * side) * sp * 0.8 - e.vx) * 0.06;
            e.vy += (Math.sin(a) * want * sp + Math.sin(a + 1.57 * side) * sp * 0.8 - e.vy) * 0.06;
            // dodge: side-step a bullet coming at it
            if (e.dodgeCool > 0) e.dodgeCool--;
            else for (const b of L.bullets) {
                if (Math.hypot(b.x - e.x, b.y - e.y) < 80) {
                    const ba = Math.atan2(b.vy, b.vx) + Math.PI / 2;
                    e.vx += Math.cos(ba) * 5; e.vy += Math.sin(ba) * 5; e.dodgeCool = 50; break;
                }
            }
            if (e.cool <= 0) { e.burst = 3; e.cool = 130; }
            if (e.burst > 0 && e.t % 7 === 0) { shootAt(e, L, p, 6.5, { color: '#ff3d7f' }); e.burst--; Sfx.enemyShoot(); }
            break;
        }
        case 'wiper': {
            if (e.state === 'idle') {
                steer(e, tgt.x, tgt.y, sp, 0.06);
                if (dist(e, tgt) < 90) { e.state = 'armed'; e.stateT = 32; Sfx.telegraph(); }
            } else {
                e.vx *= 0.85; e.vy *= 0.85;
                if (e.stateT <= 0) { L.explosion(e.x, e.y, 115, '#ffffff', true); e.hp = 0; e.silent = true; }
            }
            break;
        }
        case 'decoy': {
            e.vx *= 0.9; e.vy *= 0.9;
            if (e.cool <= 0) { shootAt(e, L, p, 4, { color: '#8fa3ff' }); e.cool = 110; }
            if (e.t > 600) { e.hp = 0; e.silent = true; }
            break;
        }
    }

    e.x += e.vx; e.y += e.vy;
    if (!e.def.static) keepInArena(e, e.r);
}

export function onEnemyDeath(e, L) {
    if (e.type === 'worm') {
        for (let i = 0; i < 2; i++) L.spawnEnemy('wormlet', e.x + rand(-10, 10), e.y + rand(-10, 10), { spawnT: 0 });
    }
}

// ── Drawing ─────────────────────────────────────────────────────────────
export function drawEnemy(ctx, e, L) {
    const c = e.flash > 0 ? '#ffffff' : e.def.color;
    ctx.save();
    ctx.globalAlpha = e.alpha;
    if (e.spawnT > 0) {                      // spawn-in portal
        const k = 1 - e.spawnT / 30;
        circle(ctx, e.x, e.y, e.r * 1.8 * (1 - k) + 4, null, hexA(e.def.color, 0.8), 2);
        ctx.globalAlpha *= k;
    }
    const t = e.t;
    switch (e.type) {
        case 'worm': case 'wormlet': {
            for (let i = 3; i >= 1; i--) {
                const a = Math.atan2(e.vy, e.vx) + Math.PI;
                circle(ctx, e.x + Math.cos(a + Math.sin(t * 0.2 + i) * 0.4) * i * e.r * 0.7,
                    e.y + Math.sin(a + Math.sin(t * 0.2 + i) * 0.4) * i * e.r * 0.7, e.r * (1 - i * 0.18), hexA(e.def.color, 0.55));
            }
            circle(ctx, e.x, e.y, e.r, c);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 1.1, '#2b0008');
            break;
        }
        case 'drone':
            poly(ctx, e.x, e.y, e.r, 3, Math.atan2(e.vy, e.vx), c);
            break;
        case 'trojan': {
            if (e.state === 'disguised') {          // looks exactly like a heal pickup… almost
                glow(ctx, e.x, e.y, 30, '#5be08a', 0.35);
                circle(ctx, e.x, e.y, 13, '#123', '#5be08a', 2);
                glyph(ctx, 'heart', e.x, e.y, 14, '#ff5d73');
            } else {
                const shake = e.state === 'reveal' ? rand(-3, 3) : 0;
                poly(ctx, e.x + shake, e.y, e.r + 2, 4, t * 0.1, c, '#fff', 1.5);
                glyph(ctx, e.def.glyph, e.x + shake, e.y, e.r, '#2b0008');
            }
            break;
        }
        case 'botnet': case 'beacon': {
            glow(ctx, e.x, e.y, e.r * 2.6, e.def.color, 0.3 + 0.15 * Math.sin(t * 0.1));
            circle(ctx, e.x, e.y, e.r + 8 + Math.sin(t * 0.08) * 3, null, hexA(e.def.color, 0.6), 2);
            poly(ctx, e.x, e.y, e.r, 6, t * 0.01, '#140a24', c, 3);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 0.9, c);
            break;
        }
        case 'locker': {
            poly(ctx, e.x, e.y, e.r, 4, Math.PI / 4, '#2a0f05', c, 3);
            ctx.beginPath();
            ctx.arc(e.x, e.y, e.r + 9, (e.facing || 0) - Math.PI / 3, (e.facing || 0) + Math.PI / 3);
            ctx.strokeStyle = '#ffd166'; ctx.lineWidth = 5; ctx.stroke();
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 0.9, c);
            break;
        }
        case 'mine': {
            const armed = e.state === 'armed';
            if (armed) circle(ctx, e.x, e.y, 105, (t % 8 < 4) ? 'rgba(255,90,40,0.12)' : 'rgba(255,90,40,0.04)', 'rgba(255,90,40,0.6)', 1.5);
            circle(ctx, e.x, e.y, e.r, armed && t % 8 < 4 ? '#fff' : c);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 1.1, '#2b1000');
            break;
        }
        case 'keylogger': {
            if (e.state === 'aim') {
                ctx.save(); ctx.globalAlpha = 0.55;
                ctx.beginPath(); ctx.moveTo(e.x, e.y); ctx.lineTo(e.x + Math.cos(e.aim) * 1400, e.y + Math.sin(e.aim) * 1400);
                ctx.strokeStyle = '#7cf29a'; ctx.setLineDash([8, 8]); ctx.lineWidth = 1.5; ctx.stroke(); ctx.restore();
            }
            circle(ctx, e.x, e.y, e.r, '#06180c', c, 2);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 1.1, c);
            break;
        }
        case 'rootkit': {
            if (e.state === 'emerging') {
                circle(ctx, e.x, e.y, 40 - e.stateT * 0.5, null, '#9b8cff', 2);
                break;
            }
            poly(ctx, e.x, e.y, e.r, 8, t * 0.02, '#100a2a', c, 2);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r, c);
            break;
        }
        case 'apt':
            glow(ctx, e.x, e.y, 40, e.def.color, 0.3);
            poly(ctx, e.x, e.y, e.r, 5, t * 0.05, '#2a0012', c, 2.5);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 1.1, c);
            break;
        case 'wiper': {
            const armed = e.state === 'armed';
            if (armed) circle(ctx, e.x, e.y, 115, 'rgba(255,255,255,0.08)', 'rgba(255,255,255,0.6)', 1.5);
            circle(ctx, e.x, e.y, e.r, armed && t % 6 < 3 ? '#ff3d3d' : '#1a1a1a', c, 3);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 1.1, armed ? '#fff' : c);
            break;
        }
        default: {
            circle(ctx, e.x, e.y, e.r, '#120812', c, 2.5);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 1.1, c);
        }
    }
    // health pip for tough enemies
    if (e.maxHp >= 6 && e.hp < e.maxHp && e.alpha > 0.5) {
        const w = e.r * 2;
        ctx.fillStyle = 'rgba(0,0,0,0.5)'; ctx.fillRect(e.x - w / 2, e.y - e.r - 12, w, 4);
        ctx.fillStyle = e.def.color; ctx.fillRect(e.x - w / 2, e.y - e.r - 12, w * (e.hp / e.maxHp), 4);
    }
    ctx.restore();
}
