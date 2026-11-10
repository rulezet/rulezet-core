/**
 * enemies.js — every enemy type's behaviour and look. An enemy is a plain
 * object { type, def, x, y, vx, vy, hp, r, t, … }; `L` is the running
 * Level (level.js) — the enemy calls back into it to shoot, spawn, etc.
 * The arena is L.aw × L.ah (bigger than the screen in open levels).
 *
 * Shared states, on any enemy:
 *   stun   — frames left stunned (Nmap Port Sweep)
 *   frozen — frames left frozen (Plum Island Quarantine Net)
 *   ally   — fights for the player for allyT frames (NOVA Prompt Injection)
 *   guard  — sleeps near its home until the player comes close (key vaults)
 *   disguised — drawn as clean traffic until close (triage levels)
 *   buffT  — boosted by a nearby jailbreaker
 */
import { ENEMIES, TAU } from './data.js';
import { circle, poly, glyph, glow, hexA } from './render.js';
import { Sfx } from './audio.js';

const rand = (a, b) => a + Math.random() * (b - a);
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const angleTo = (a, b) => Math.atan2(b.y - a.y, b.x - a.x);

/** Who an enemy goes after: a sensor / server for some of them, else the player */
function target(e, L) {
    if (e.huntsSensor && L.sensors.length) {
        if (!e.sensorRef || e.sensorRef.hp <= 0) {
            const alive = L.sensors.filter(s => s.hp > 0);
            e.sensorRef = alive.length ? alive[Math.floor(Math.random() * alive.length)] : null;
        }
        if (e.sensorRef) return e.sensorRef;
    }
    return L.player;
}

function steer(e, tx, ty, speed, accel = 0.08) {
    const a = Math.atan2(ty - e.y, tx - e.x);
    e.vx += (Math.cos(a) * speed - e.vx) * accel;
    e.vy += (Math.sin(a) * speed - e.vy) * accel;
}

function keepInArena(e, L, margin = 20) {
    if (e.x < margin) { e.x = margin; e.vx = Math.abs(e.vx); }
    if (e.x > L.aw - margin) { e.x = L.aw - margin; e.vx = -Math.abs(e.vx); }
    if (e.y < margin) { e.y = margin; e.vy = Math.abs(e.vy); }
    if (e.y > L.ah - margin) { e.y = L.ah - margin; e.vy = -Math.abs(e.vy); }
}

/** Rocks are solid for enemies too: push out and slide */
function avoidRocks(e, L) {
    for (const k of L.rocks) {
        const dx = e.x - k.x, dy = e.y - k.y, min = k.r + e.r;
        const d2 = dx * dx + dy * dy;
        if (d2 < min * min && d2 > 0.01) {
            const d = Math.sqrt(d2);
            e.x = k.x + dx / d * min; e.y = k.y + dy / d * min;
            const dot = (e.vx * dx + e.vy * dy) / d;
            if (dot < 0) { e.vx -= dot * dx / d * 1.6; e.vy -= dot * dy / d * 1.6; }
        }
    }
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

/** A random point near the player, inside the arena (open levels) */
function nearPlayer(L, d) {
    const p = L.player, a = rand(0, TAU), r = rand(d * 0.5, d);
    return { x: Math.min(L.aw - 80, Math.max(80, p.x + Math.cos(a) * r)), y: Math.min(L.ah - 80, Math.max(80, p.y + Math.sin(a) * r)) };
}

export function makeEnemy(type, x, y, L, extra = {}) {
    const def = ENEMIES[type];
    const hpScale = (L.diff.hp) * (1 + (L.tier || 0) * 0.035);
    const e = {
        type, def, x, y, vx: 0, vy: 0, r: def.r,
        hp: Math.max(1, Math.round(def.hp * hpScale * 10) / 10), t: 0, flash: 0,
        cool: rand(40, 120), state: 'idle', stateT: 0, alpha: 1, spawnT: 30,
        huntsSensor: !!(L.sensors.length && !def.static && !def.benign && Math.random() < 0.45),
        stun: 0, frozen: 0, buffT: 0, spin: rand(0, TAU),
        ...extra,
    };
    if (type === 'shard') {
        e.size = extra.size || 3;
        e.r = 12 + e.size * 8;
        e.hp = Math.max(1, Math.round(def.hp * (e.size / 3) * hpScale * 10) / 10);
        if (!extra.vx && !extra.vy) { const a = rand(0, TAU), s = rand(0.6, 1.5) * (4 - e.size) * 0.55 + 0.4; e.vx = Math.cos(a) * s; e.vy = Math.sin(a) * s; }
        e.verts = Array.from({ length: 7 }, () => rand(0.75, 1.1));
    }
    if (type === 'benign' && !extra.dir) {
        // clean traffic crosses the arena from one side to the other
        const fromLeft = x < L.aw / 2;
        e.dir = fromLeft ? rand(-0.35, 0.35) : Math.PI + rand(-0.35, 0.35);
    }
    if (type === 'scanbot' && e.dir === undefined) e.dir = angleTo(e, L.player) + rand(-0.4, 0.4);
    if (type === 'halluc') { e.ax = x; e.ay = y; }
    if (type === 'scanner') e.coneA = rand(0, TAU);
    e.maxHp = e.hp;
    if (type === 'trojan') e.state = 'disguised';
    if (type === 'rootkit') { e.state = 'burrowed'; e.stateT = rand(30, 90); e.alpha = 0; }
    if (type === 'miner') e.orbit = rand(0, TAU);
    if (type === 'toolcall') e.lifeT = 360;
    if (type === 'implant') e.pulse = rand(0, TAU);
    return e;
}

/** Can the player's bullets hit it right now? */
export function hittable(e) {
    if (e.spawnT > 0 || e.ally) return false;
    if (e.type === 'rootkit') return e.state === 'surfaced' || e.state === 'firing';
    return true;
}

/** Returns true if the bullet is deflected (locker's front shield) */
export function deflects(e, b) {
    if (e.type !== 'locker' || b.pierce || e.stun > 0 || e.frozen > 0) return false;
    const facing = e.facing || 0;
    const from = Math.atan2(b.y - e.y, b.x - e.x);
    let d = Math.abs(((from - facing) + Math.PI * 3) % TAU - Math.PI);
    return d < Math.PI / 3;
}

/** An obfuscator's noise cloud eats some of the bullets that cross it */
export const CLOUD_R = 125;

/** Converted by NOVA's Prompt Injection: hunts the other malware */
function updateAlly(e, L) {
    e.allyT--;
    let best = null, bd = 700 * 700;
    for (const o of L.enemies) {
        if (o === e || o.dead || o.ally || o.def.benign || !hittable(o)) continue;
        const d = (o.x - e.x) ** 2 + (o.y - e.y) ** 2;
        if (d < bd) { bd = d; best = o; }
    }
    if (best) {
        steer(e, best.x, best.y, 4, 0.12);
        if (bd < (best.r + e.r + 4) ** 2) L.damageEnemy(best, 0.3);
    } else steer(e, L.player.x + Math.cos(e.t * 0.05) * 70, L.player.y + Math.sin(e.t * 0.05) * 70, 3, 0.08);
    e.x += e.vx; e.y += e.vy;
    keepInArena(e, L, e.r);
    if (e.allyT <= 0) e.hp = 0;
}

export function updateEnemy(e, L) {
    e.t++;
    if (e.flash > 0) e.flash--;
    if (e.spawnT > 0) { e.spawnT--; return; }
    if (e.frozen > 0) { e.frozen--; return; }
    if (e.stun > 0) {
        e.stun--; e.vx *= 0.85; e.vy *= 0.85; e.x += e.vx; e.y += e.vy;
        if (!e.def.static) keepInArena(e, L, e.r);
        return;
    }
    if (e.ally) { updateAlly(e, L); return; }
    const p = L.player;
    if (e.guard && !e.alerted) {
        if (dist(e, p) < 520 || e.hp < e.maxHp) { e.alerted = true; Sfx.telegraph(); }
        else {
            steer(e, e.home.x + Math.cos(e.t * 0.01 + e.spin) * 60, e.home.y + Math.sin(e.t * 0.012 + e.spin) * 60, 0.8, 0.03);
            e.x += e.vx; e.y += e.vy;
            return;
        }
    }
    if (e.disguised && dist(e, p) < 230) { e.disguised = false; e.flash = 10; Sfx.telegraph(); }
    const tgt = target(e, L);
    if (e.buffT > 0) e.buffT--;
    const sp = e.def.speed * (L.slow ? 0.5 : 1) * (e.buffT > 0 ? 1.45 : 1);
    e.cool -= e.buffT > 0 ? 1.5 : 1;
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
            if (e.cool <= 0 && d < 900) {
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
            if (e.cool <= 0 && d < 800) { shootAt(e, L, p, 5.2, { kind: 'hook', r: 8, color: '#3ee0c8', life: 120 }); e.cool = 170; Sfx.enemyShoot(); }
            break;
        }
        case 'botnet':
        case 'beacon': {
            e.vx = e.vy = 0;
            if (e.cool <= 0) {
                const cap = e.type === 'botnet' ? 10 : 8 + Math.min(6, L.world);
                const kids = L.enemies.filter(o => o.parent === e).length;
                const far = L.open && dist(e, p) > 1100;       // in open space, beacons only call when you are around
                if (!far && kids < (e.type === 'botnet' ? 5 : 3) && L.enemies.length < cap + 12) {
                    const pool = L.pool.filter(k => !ENEMIES[k].static);
                    const kind = e.type === 'botnet' ? 'drone' : L.pick(pool.length ? pool : ['worm']);
                    const a = rand(0, TAU);
                    L.spawnEnemy(kind, e.x + Math.cos(a) * 50, e.y + Math.sin(a) * 50, { parent: e });
                }
                e.cool = (e.type === 'botnet' ? 150 : 230) / L.diff.spawn;
            }
            if (e.type === 'beacon' && e.t % 200 === 100 && dist(e, p) < 900) ring(e, L, 10, 2.4, { color: '#ff5d73' }, e.t * 0.01);
            break;
        }
        case 'miner': {
            const d = dist(e, p);
            const cx = L.open ? p.x : L.aw / 2, cy = L.open ? p.y : L.ah / 2;
            if (d < 200) { const a = angleTo(p, e); steer(e, e.x + Math.cos(a) * 100, e.y + Math.sin(a) * 100, sp * 1.3, 0.1); }
            else { e.orbit += 0.008; steer(e, cx + Math.cos(e.orbit) * 420, cy + Math.sin(e.orbit) * 250, sp, 0.04); }
            if (e.t % 60 === 0) L.drainBytes(e, 1);
            break;
        }
        case 'locker': {
            e.facing = angleTo(e, p);
            steer(e, tgt.x, tgt.y, sp, 0.03);
            if (e.cool <= 0 && dist(e, p) < 800) {
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
                if (!e.wp || dist(e, e.wp) < 30) e.wp = L.open ? nearPlayer(L, 500) : { x: rand(80, L.aw - 80), y: rand(80, L.ah - 80) };
                steer(e, e.wp.x, e.wp.y, sp, 0.04);
                if (e.cool <= 0 && dist(e, p) < 900) { e.state = 'aim'; e.stateT = 55; Sfx.telegraph(); }
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
                    e.x = Math.min(L.aw - 60, Math.max(60, p.x + Math.cos(a) * d));
                    e.y = Math.min(L.ah - 60, Math.max(60, p.y + Math.sin(a) * d));
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
            if (e.cool <= 0 && d < 800) { e.burst = 3; e.cool = 130; }
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

        // ── Act II ───────────────────────────────────────────────────────
        case 'flood': {
            const a = angleTo(e, tgt) + Math.sin(e.t * 0.03) * 0.9;
            steer(e, e.x + Math.cos(a) * 100, e.y + Math.sin(a) * 100, sp, 0.04);
            // a trail of log lines: slow bullets that hang in space
            if (e.t % 12 === 0 && L.ebullets.length < 520) {
                L.enemyBullet(e.x - e.vx * 6, e.y - e.vy * 6, -e.vx * 0.08, -e.vy * 0.08, { r: 5, color: '#ffb347', life: 230, kind: 'log' });
            }
            break;
        }
        case 'tamper': {
            // goes for the bytes and pickups lying around and wipes them
            let best = null, bd = 420 * 420;
            for (const pk of L.pickups) { const d = (pk.x - e.x) ** 2 + (pk.y - e.y) ** 2; if (d < bd) { bd = d; best = pk; } }
            if (best) {
                steer(e, best.x, best.y, sp * 1.2, 0.08);
                if (bd < 22 * 22) { best.life = 0; L.float(e.x, e.y - 18, 'ERASED', '#ff8f6b'); }
            } else {
                const a = angleTo(p, e) + 0.9;
                steer(e, p.x + Math.cos(a) * 260, p.y + Math.sin(a) * 260, sp, 0.05);
            }
            if (e.cool <= 0 && dist(e, p) < 700) { for (let i = -1; i <= 1; i++) shootAt(e, L, p, 3.8, { offset: i * 0.18, color: '#ff8f6b' }); e.cool = 140; Sfx.enemyShoot(); }
            break;
        }
        case 'injector': {
            const d = dist(e, p);
            if (e.state === 'idle') {
                const want = d < 360 ? -1 : d > 480 ? 1 : 0;
                const a = angleTo(e, p);
                e.vx += (Math.cos(a) * want * sp + Math.cos(a + 1.57) * sp * 0.4 - e.vx) * 0.05;
                e.vy += (Math.sin(a) * want * sp + Math.sin(a + 1.57) * sp * 0.4 - e.vy) * 0.05;
                if (e.cool <= 0 && d < 750) {
                    e.state = 'aim'; e.stateT = 50; e.aim = angleTo(e, p);
                    L.addBeam({ x: e.x, y: e.y, angle: e.aim, rot: 0, len: 950, width: 12, tele: 50, active: 14, color: '#ff4fa0', owner: e });
                    Sfx.telegraph();
                }
            } else {
                e.vx *= 0.8; e.vy *= 0.8;
                if (e.stateT <= 0) { e.state = 'idle'; e.cool = 170; }
            }
            break;
        }
        case 'xss': {
            const a = angleTo(e, tgt), z = Math.sin(e.t * 0.15) * 1.3;
            steer(e, e.x + Math.cos(a + z) * 100, e.y + Math.sin(a + z) * 100, sp, 0.1);
            break;
        }
        case 'scanner': {
            if (!e.wp || dist(e, e.wp) < 40) e.wp = L.open ? nearPlayer(L, 420) : { x: rand(100, L.aw - 100), y: rand(100, L.ah - 100) };
            steer(e, e.wp.x, e.wp.y, sp, 0.03);
            e.coneA += 0.014 * (e.alarm > 0 ? 0.3 : 1);
            const d = dist(e, p);
            let off = ((angleTo(e, p) - e.coneA) % TAU + TAU * 1.5) % TAU - Math.PI;
            const seen = d < 420 && Math.abs(off) < 0.45 && !L.blocked(e.x, e.y, p.x, p.y);
            if (seen) { e.alarm = (e.alarm || 0) + 1; e.coneA += Math.sign(off) * 0.02; }
            else if (e.alarm > 0) e.alarm = Math.max(0, e.alarm - 0.5);
            if (e.alarm >= 30) {
                e.alarm = -150;               // cooldown before it can alarm again
                L.float(e.x, e.y - 30, 'DETECTED!', '#5bd1ff'); Sfx.warning();
                for (let i = 0; i < 2; i++) L.spawnEnemy('scanbot', e.x + rand(-40, 40), e.y + rand(-40, 40), { spawnT: 15 });
                for (let i = -1; i <= 1; i++) shootAt(e, L, p, 5, { offset: i * 0.15, color: '#5bd1ff' });
            }
            if (e.alarm < 0) e.alarm++;
            break;
        }
        case 'scanbot': {
            e.vx += (Math.cos(e.dir) * sp - e.vx) * 0.1; e.vy += (Math.sin(e.dir) * sp - e.vy) * 0.1;
            if (e.x < 30 || e.x > L.aw - 30) e.dir = Math.PI - e.dir;
            if (e.y < 30 || e.y > L.ah - 30) e.dir = -e.dir;
            if (e.t % 80 === 40 && dist(e, p) < 700) {
                for (const s of [-1, 1]) { const a = e.dir + s * Math.PI / 2; L.enemyBullet(e.x, e.y, Math.cos(a) * 3, Math.sin(a) * 3, { color: '#7fe3ff', r: 5 }); }
            }
            break;
        }
        case 'jailbreak': {
            const d = dist(e, p), a = angleTo(e, p);
            const want = d < 280 ? -1 : d > 400 ? 1 : 0;
            e.vx += (Math.cos(a) * want * sp - e.vx) * 0.04; e.vy += (Math.sin(a) * want * sp - e.vy) * 0.04;
            if (e.t % 50 === 0) {
                for (const o of L.enemies) {
                    if (o === e || o.dead || o.ally || o.def.benign) continue;
                    if ((o.x - e.x) ** 2 + (o.y - e.y) ** 2 < 230 * 230) { o.buffT = 80; o.hp = Math.min(o.maxHp, o.hp + 0.4); }
                }
            }
            if (e.cool <= 0 && d < 700) { ring(e, L, 6, 2.6, { color: '#ff5bd7' }, e.t * 0.1); e.cool = 160; Sfx.enemyShoot(); }
            break;
        }
        case 'halluc': {
            // mirrors the player around its anchor: you go left, it goes right
            const tx = Math.min(L.aw - 40, Math.max(40, 2 * e.ax - p.x)), ty = Math.min(L.ah - 40, Math.max(40, 2 * e.ay - p.y));
            steer(e, tx, ty, 5 * (L.slow ? 0.5 : 1), 0.12);
            e.alpha = 0.65 + 0.35 * Math.sin(e.t * 0.12);
            const aligned = Math.abs(e.x - p.x) < 34 || Math.abs(e.y - p.y) < 34;
            if (e.cool <= 0 && aligned && dist(e, p) < 800) { shootAt(e, L, p, 6.5, { color: '#c9a7ff', r: 7 }); e.cool = 45; Sfx.enemyShoot(); }
            break;
        }
        case 'rogue': {
            let best = null, bd = 380 * 380;
            for (const pk of L.pickups) if (pk.type !== 'byte') { const d = (pk.x - e.x) ** 2 + (pk.y - e.y) ** 2; if (d < bd) { bd = d; best = pk; } }
            if (best) {
                steer(e, best.x, best.y, sp * 1.3, 0.08);
                if (bd < 24 * 24) {
                    best.life = 0;
                    if (best.type === 'heal') e.hp = Math.min(e.maxHp, e.hp + 3);
                    e.buffT = 300;
                    L.float(e.x, e.y - 22, 'STOLEN!', '#6fffd2');
                }
            } else {
                const d = dist(e, p), a = angleTo(e, p);
                const want = d < 280 ? -1 : d > 360 ? 1 : 0;
                e.vx += (Math.cos(a) * want * sp + Math.cos(a - 1.57) * sp * 0.5 - e.vx) * 0.05;
                e.vy += (Math.sin(a) * want * sp + Math.sin(a - 1.57) * sp * 0.5 - e.vy) * 0.05;
            }
            if (e.cool <= 0 && dist(e, p) < 800) {
                if (L.enemies.filter(o => o.type === 'toolcall').length < 8) {
                    for (let i = 0; i < 2; i++) L.spawnEnemy('toolcall', e.x + rand(-20, 20), e.y + rand(-20, 20), { spawnT: 6 });
                }
                e.cool = 170; Sfx.enemyShoot();
            }
            break;
        }
        case 'toolcall': {
            steer(e, tgt.x, tgt.y, sp, 0.045);
            if (--e.lifeT <= 0) { e.hp = 0; e.silent = true; }
            break;
        }
        case 'brute': {
            const d = dist(e, tgt);
            if (e.state === 'idle') {
                steer(e, tgt.x, tgt.y, d > 340 ? sp : 0, 0.05);
                if (e.cool <= 0 && d < 700) {
                    e.state = 'aim'; e.stateT = 42; e.aim = angleTo(e, tgt); e.charges = e.charges || 3;
                    L.addBeam({ x: e.x, y: e.y, angle: e.aim, rot: 0, len: 520, width: e.r * 1.6, tele: 42, active: 0, color: '#ff6a3d', owner: e });
                    Sfx.telegraph();
                }
            } else if (e.state === 'aim') {
                e.vx *= 0.7; e.vy *= 0.7;
                if (e.stateT <= 0) { e.state = 'charge'; e.stateT = 34; e.vx = Math.cos(e.aim) * 12; e.vy = Math.sin(e.aim) * 12; }
            } else if (e.state === 'charge') {
                if (e.stateT <= 0) {
                    e.charges--; e.vx *= 0.2; e.vy *= 0.2;
                    if (e.charges > 0) { e.state = 'idle'; e.cool = 18; }
                    else { e.state = 'idle'; e.cool = 150; e.charges = 3; }
                }
            }
            break;
        }
        case 'lateral': {
            if (e.state === 'idle') {
                const a = angleTo(e, p) + 1.2;
                steer(e, p.x - Math.cos(a) * 320, p.y - Math.sin(a) * 320, sp, 0.03);
                if (e.cool <= 0) {
                    // jumps next to another malware, or behind you
                    const others = L.enemies.filter(o => o !== e && !o.dead && !o.def.static && !o.def.benign);
                    const via = others.length && Math.random() < 0.5 ? L.pick(others) : null;
                    const ba = P_angle(p) + Math.PI + rand(-0.6, 0.6);
                    e.dest = via ? { x: via.x + rand(-60, 60), y: via.y + rand(-60, 60) }
                        : { x: p.x + Math.cos(ba) * 220, y: p.y + Math.sin(ba) * 220 };
                    e.dest.x = Math.min(L.aw - 40, Math.max(40, e.dest.x)); e.dest.y = Math.min(L.ah - 40, Math.max(40, e.dest.y));
                    e.state = 'blink'; e.stateT = 28; Sfx.telegraph();
                }
            } else if (e.state === 'blink') {
                e.vx *= 0.8; e.vy *= 0.8; e.alpha = 0.4 + 0.6 * (e.stateT / 28);
                if (e.stateT <= 0) {
                    e.x = e.dest.x; e.y = e.dest.y; e.alpha = 1; e.state = 'idle'; e.cool = 150;
                    ring(e, L, 6, 3, { color: '#9dff6a' }, rand(0, 1)); Sfx.enemyShoot();
                }
            }
            break;
        }
        case 'obfusc': {
            if (!e.wp || dist(e, e.wp) < 40) e.wp = L.open ? nearPlayer(L, 380) : { x: rand(100, L.aw - 100), y: rand(100, L.ah - 100) };
            steer(e, e.wp.x, e.wp.y, sp, 0.03);
            if (e.cool <= 0 && dist(e, p) < 750) { for (let i = -1; i <= 1; i += 2) shootAt(e, L, p, 2.8, { offset: i * 0.12, color: '#b0c4ff', r: 8 }); e.cool = 110; }
            break;
        }
        case 'exfil': {
            // runs away with the data; escapes after a while if it reaches an edge
            if (!e.exit) {
                const exits = [{ x: 20, y: e.y }, { x: L.aw - 20, y: e.y }, { x: e.x, y: 20 }, { x: e.x, y: L.ah - 20 }];
                exits.sort((a, b) => dist(b, p) - dist(a, p));
                e.exit = exits[0];
            }
            const d = dist(e, p);
            if (d < 260) { const a = angleTo(p, e); steer(e, e.x + Math.cos(a) * 100, e.y + Math.sin(a) * 100, sp * 1.2, 0.1); }
            else steer(e, e.exit.x, e.exit.y, sp * 0.8, 0.05);
            if (e.t > 540 && dist(e, e.exit) < 50) {
                L.drainBytes(e, 8);
                L.float(e.x, e.y - 20, 'EXFILTRATED', '#ffd84f');
                L.removeEnemy(e);
            }
            break;
        }
        case 'shard': {
            e.spin += 0.01 * (4 - e.size);
            if (L.slow) { e.x -= e.vx * 0.5; e.y -= e.vy * 0.5; }
            break;
        }
        case 'fork': {
            steer(e, tgt.x + Math.cos(e.t * 0.02 + e.spin) * 80, tgt.y + Math.sin(e.t * 0.02 + e.spin) * 80, sp, 0.04);
            if (e.t % 330 === 300 && L.enemies.filter(o => o.type === 'fork').length < 16) {
                L.spawnEnemy('fork', e.x + rand(-30, 30), e.y + rand(-30, 30), { spawnT: 18 });
                L.float(e.x, e.y - 20, 'fork()', '#ff9e3d');
            }
            if (e.cool <= 0 && dist(e, p) < 600) { shootAt(e, L, p, 3.4, { color: '#ff9e3d', r: 5 }); e.cool = 150; }
            break;
        }
        case 'latch': {
            if (e.latched) {
                e.x = p.x + Math.cos(e.latchA) * 16; e.y = p.y + Math.sin(e.latchA) * 16;
                e.vx = e.vy = 0;
                L.player.slowT = 2;
                if (++e.latchT >= 150) { L.hurtPlayer(); L.removeEnemy(e); }
                return;
            }
            steer(e, p.x, p.y, sp, 0.06);
            break;
        }
        case 'spore': {
            if (e.state === 'idle') {
                steer(e, tgt.x, tgt.y, sp, 0.02);
                e.vx += Math.cos(e.t * 0.05 + e.spin) * 0.03; e.vy += Math.sin(e.t * 0.04 + e.spin) * 0.03;
                if (dist(e, p) < 150) { e.state = 'swell'; e.stateT = 34; Sfx.telegraph(); }
            } else {
                e.vx *= 0.85; e.vy *= 0.85;
                if (e.stateT <= 0) { ring(e, L, 9, 2.4, { color: '#d77bff', r: 6 }, rand(0, 1)); Sfx.explode(false); e.hp = 0; e.silent = true; }
            }
            break;
        }
        case 'benign': {
            // a grazed clean packet recovers if you leave it alone; only destroying it is a false positive
            if (e.hp < e.maxHp && L.t - (e.lastHitT || 0) > 80) e.hp = e.maxHp;
            e.vx += (Math.cos(e.dir) * sp - e.vx) * 0.1; e.vy += (Math.sin(e.dir) * sp - e.vy) * 0.1;
            e.dir += Math.sin(e.t * 0.02 + e.spin) * 0.004;
            if (e.t > 60 && (e.x < -10 || e.x > L.aw + 10 || e.y < -10 || e.y > L.ah + 10)) L.removeEnemy(e);
            e.x += e.vx; e.y += e.vy;
            return;           // clean traffic may leave the arena
        }
        case 'courier': {
            const path = L.courierPath || [];
            const wp = path[e.wpi || 0];
            if (e.state === 'upload') {
                e.vx *= 0.9; e.vy *= 0.9;
                if (e.stateT <= 0) { e.state = 'idle'; e.cool = rand(320, 460); }
            } else if (wp) {
                const near = dist(e, p) < 520;
                steer(e, wp.x, wp.y, (near ? 3.4 : 2.3) * (L.slow ? 0.5 : 1), 0.05);
                const dwp = dist(e, wp);
                // stuck behind a rock: give up on that hop
                if (dwp < (e.bestD ?? 1e9) - 4) { e.bestD = dwp; e.stuckT = 0; } else if (++e.stuckT > 200) { e.wpi = (e.wpi || 0) + 1; e.bestD = 1e9; e.stuckT = 0; }
                if (dwp < 70) { e.wpi = (e.wpi || 0) + 1; e.bestD = 1e9; e.stuckT = 0; }
                if (e.cool <= 0) { e.state = 'upload'; e.stateT = 140; L.say('The courier stopped to upload — strike now!', '#ffd84f'); }
            }
            if (e.t % 140 === 70 && L.enemies.filter(o => o.type === 'mine').length < 10) L.spawnEnemy('mine', e.x - e.vx * 10, e.y - e.vy * 10, { spawnT: 10 });
            if (!wp && path.length) e.escaped = true;
            break;
        }
        case 'implant': {
            e.vx = e.vy = 0;
            e.pulse += 0.05;
            const d = dist(e, p);
            if (e.cool <= 0 && d < 520) {
                ring(e, L, 8, 2.4, { color: '#ff4d6d' }, e.t * 0.02); e.cool = 200; Sfx.enemyShoot();
                if (L.enemies.length < 30) { const pool = L.pool.filter(k => !ENEMIES[k].static); L.spawnEnemy(L.pick(pool), e.x + rand(-50, 50), e.y + rand(-50, 50)); }
            }
            break;
        }
    }

    e.x += e.vx; e.y += e.vy;
    if (!e.def.static) { keepInArena(e, L, e.r); if (L.rocks.length) avoidRocks(e, L); }
}

// the lateral mover jumps behind you: which way are you facing?
function P_angle(p) { return (Math.abs(p.vx) + Math.abs(p.vy) > 0.5) ? Math.atan2(p.vy, p.vx) : p.angle; }

export function onEnemyDeath(e, L) {
    if (e.type === 'worm') {
        for (let i = 0; i < 2; i++) L.spawnEnemy('wormlet', e.x + rand(-10, 10), e.y + rand(-10, 10), { spawnT: 0 });
    } else if (e.type === 'xss') {
        // a reflected script: it bounces back at you
        for (let i = -1; i <= 1; i++) shootAt(e, L, L.player, 3.6, { offset: i * 0.3, color: '#ffe14f', r: 5 });
    } else if (e.type === 'shard' && e.size > 1) {
        const a0 = Math.atan2(e.vy, e.vx) + Math.PI / 2;
        for (const s of [-1, 1]) {
            const a = a0 + (s > 0 ? 0 : Math.PI) + rand(-0.4, 0.4), sp = 1.2 + (3 - e.size) * 0.7;
            L.spawnEnemy('shard', e.x + Math.cos(a) * 10, e.y + Math.sin(a) * 10,
                { size: e.size - 1, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, spawnT: 0, fromBoss: e.fromBoss });
        }
    }
}

// ── Drawing ─────────────────────────────────────────────────────────────
function drawBenignShape(ctx, e, c) {
    const a = Math.atan2(e.vy, e.vx);
    glow(ctx, e.x, e.y, 30, '#4be08a', 0.25);
    ctx.save(); ctx.translate(e.x, e.y); ctx.rotate(a);
    ctx.beginPath(); ctx.roundRect ? ctx.roundRect(-16, -10, 32, 20, 5) : ctx.rect(-16, -10, 32, 20);
    ctx.fillStyle = '#062a16'; ctx.fill(); ctx.strokeStyle = c; ctx.lineWidth = 2; ctx.stroke();
    ctx.restore();
    glyph(ctx, 'paperPlane', e.x, e.y, 12, c);
}

export function drawEnemy(ctx, e, L) {
    const c = e.flash > 0 ? '#ffffff' : e.ally ? '#6fffd2' : e.def.color;
    ctx.save();
    ctx.globalAlpha = e.alpha;
    if (e.spawnT > 0) {                      // spawn-in portal
        const k = 1 - e.spawnT / 30;
        circle(ctx, e.x, e.y, e.r * 1.8 * (1 - k) + 4, null, hexA(e.def.color, 0.8), 2);
        poly(ctx, e.x, e.y, e.r * 2.2 * (1 - k) + 6, 6, e.t * 0.2, null, hexA(e.def.color, 0.4), 1.5);
        ctx.globalAlpha *= k;
    }
    if (e.disguised) { drawBenignShape(ctx, e, '#4be08a'); ctx.restore(); return; }
    if (e.buffT > 0) circle(ctx, e.x, e.y, e.r + 7 + Math.sin(e.t * 0.3) * 2, null, hexA('#ff5bd7', 0.6), 2);
    if (e.ally) circle(ctx, e.x, e.y, e.r + 8, hexA('#6fffd2', 0.12), hexA('#6fffd2', 0.8), 2);
    const t = e.t;
    switch (e.type) {
        case 'worm': case 'wormlet': {
            for (let i = 3; i >= 1; i--) {
                const a = Math.atan2(e.vy, e.vx) + Math.PI;
                circle(ctx, e.x + Math.cos(a + Math.sin(t * 0.2 + i) * 0.4) * i * e.r * 0.7,
                    e.y + Math.sin(a + Math.sin(t * 0.2 + i) * 0.4) * i * e.r * 0.7, e.r * (1 - i * 0.18), hexA(e.def.color, 0.55));
            }
            glow(ctx, e.x, e.y, e.r * 2, e.def.color, 0.25);
            circle(ctx, e.x, e.y, e.r, c);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 1.1, '#2b0008');
            break;
        }
        case 'drone':
            glow(ctx, e.x, e.y, 22, e.def.color, 0.25);
            poly(ctx, e.x, e.y, e.r, 3, Math.atan2(e.vy, e.vx), c, hexA('#ffffff', 0.5), 1);
            break;
        case 'trojan': {
            if (e.state === 'disguised') {          // looks exactly like a heal pickup… almost
                glow(ctx, e.x, e.y, 30, '#5be08a', 0.35);
                circle(ctx, e.x, e.y, 13, '#123', '#5be08a', 2);
                glyph(ctx, 'heart', e.x, e.y, 14, '#ff5d73');
            } else {
                const shake = e.state === 'reveal' ? rand(-3, 3) : 0;
                glow(ctx, e.x, e.y, 34, e.def.color, 0.3);
                poly(ctx, e.x + shake, e.y, e.r + 2, 4, t * 0.1, c, '#fff', 1.5);
                glyph(ctx, e.def.glyph, e.x + shake, e.y, e.r, '#2b0008');
            }
            break;
        }
        case 'botnet': case 'beacon': case 'implant': {
            glow(ctx, e.x, e.y, e.r * 2.6, e.def.color, 0.3 + 0.15 * Math.sin(t * 0.1));
            circle(ctx, e.x, e.y, e.r + 8 + Math.sin(t * 0.08) * 3, null, hexA(e.def.color, 0.6), 2);
            if (e.type !== 'botnet') {
                ctx.save(); ctx.globalAlpha *= 0.5;
                for (let i = 0; i < 3; i++) { const rr = ((t * 1.2 + i * 40) % 120); circle(ctx, e.x, e.y, e.r + rr, null, hexA(e.def.color, 1 - rr / 120), 1.5); }
                ctx.restore();
            }
            poly(ctx, e.x, e.y, e.r, 6, t * 0.01, '#140a24', c, 3);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 0.9, c);
            break;
        }
        case 'locker': {
            glow(ctx, e.x, e.y, 50, e.def.color, 0.22);
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
            for (let i = 0; i < 8; i++) {
                const a = i * TAU / 8 + t * 0.02;
                ctx.beginPath(); ctx.moveTo(e.x + Math.cos(a) * e.r, e.y + Math.sin(a) * e.r);
                ctx.lineTo(e.x + Math.cos(a) * (e.r + 5), e.y + Math.sin(a) * (e.r + 5));
                ctx.strokeStyle = c; ctx.lineWidth = 2; ctx.stroke();
            }
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
            glow(ctx, e.x, e.y, 40, e.def.color, 0.25);
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
        // ── Act II ──
        case 'flood': {
            glow(ctx, e.x, e.y, 40, e.def.color, 0.25);
            ctx.save(); ctx.translate(e.x, e.y); ctx.rotate(Math.atan2(e.vy, e.vx));
            ctx.fillStyle = '#2a1602'; ctx.strokeStyle = c; ctx.lineWidth = 2.5;
            ctx.beginPath(); ctx.rect(-e.r, -e.r * 0.7, e.r * 2, e.r * 1.4); ctx.fill(); ctx.stroke();
            for (let i = -1; i <= 1; i++) { ctx.fillStyle = hexA(e.def.color, 0.6); ctx.fillRect(-e.r * 0.7, i * 6 - 1, e.r * (1.1 + Math.sin(t * 0.2 + i) * 0.3), 2); }
            ctx.restore();
            break;
        }
        case 'injector': {
            glow(ctx, e.x, e.y, 40, e.def.color, 0.3);
            const a = e.state === 'aim' ? e.aim : Math.atan2(L.player.y - e.y, L.player.x - e.x);
            ctx.save(); ctx.translate(e.x, e.y); ctx.rotate(a);
            ctx.beginPath(); ctx.moveTo(e.r + 8, 0); ctx.lineTo(-e.r, -e.r * 0.7); ctx.lineTo(-e.r * 0.5, 0); ctx.lineTo(-e.r, e.r * 0.7); ctx.closePath();
            ctx.fillStyle = '#2a0618'; ctx.fill(); ctx.strokeStyle = c; ctx.lineWidth = 2.5; ctx.stroke();
            ctx.restore();
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 0.8, c);
            break;
        }
        case 'xss':
            glow(ctx, e.x, e.y, 26, e.def.color, 0.3);
            poly(ctx, e.x, e.y, e.r, 4, t * 0.15, '#2a2402', c, 2);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 0.95, c);
            break;
        case 'scanner': {
            const alarm = (e.alarm || 0) > 0;
            ctx.save();
            ctx.globalAlpha *= alarm ? 0.32 : 0.16;
            ctx.beginPath(); ctx.moveTo(e.x, e.y); ctx.arc(e.x, e.y, 420, e.coneA - 0.45, e.coneA + 0.45); ctx.closePath();
            ctx.fillStyle = alarm ? '#ff5d73' : '#5bd1ff'; ctx.fill();
            ctx.restore();
            circle(ctx, e.x, e.y, e.r, '#03141c', c, 2.5);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 0.9, alarm ? '#ff5d73' : c);
            break;
        }
        case 'scanbot':
            poly(ctx, e.x, e.y, e.r, 4, e.dir, '#03141c', c, 2);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 0.9, c);
            break;
        case 'jailbreak': {
            ctx.save(); ctx.globalAlpha *= 0.15 + 0.08 * Math.sin(t * 0.1);
            circle(ctx, e.x, e.y, 230, '#ff5bd7'); ctx.restore();
            glow(ctx, e.x, e.y, 46, e.def.color, 0.35);
            poly(ctx, e.x, e.y, e.r, 6, -t * 0.03, '#2a0624', c, 2.5);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r, c);
            break;
        }
        case 'halluc': {
            for (let i = 0; i < 3; i++) circle(ctx, e.x + Math.sin(t * 0.1 + i * 2) * 4, e.y + Math.cos(t * 0.13 + i * 2) * 4, e.r, null, hexA(e.def.color, 0.35), 1.5);
            circle(ctx, e.x, e.y, e.r, '#140a24', c, 2);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r, c);
            break;
        }
        case 'rogue':
            glow(ctx, e.x, e.y, 42, e.def.color, 0.28);
            poly(ctx, e.x, e.y, e.r, 6, t * 0.02, '#04201a', c, 2.5);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r, c);
            break;
        case 'toolcall':
            glow(ctx, e.x, e.y, 18, e.def.color, 0.35);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 1.9, c) || circle(ctx, e.x, e.y, e.r, c);
            break;
        case 'brute': {
            glow(ctx, e.x, e.y, 50, e.def.color, e.state === 'charge' ? 0.5 : 0.25);
            const a = e.state === 'idle' ? Math.atan2(e.vy, e.vx) : e.aim;
            poly(ctx, e.x, e.y, e.r, 5, a, '#2a0a02', c, 3);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 0.95, c);
            break;
        }
        case 'lateral': {
            if (e.state === 'blink' && e.dest) {
                circle(ctx, e.dest.x, e.dest.y, e.r + (e.stateT / 28) * 20, null, hexA(e.def.color, 0.7), 2);
                ctx.save(); ctx.setLineDash([4, 6]); ctx.beginPath(); ctx.moveTo(e.x, e.y); ctx.lineTo(e.dest.x, e.dest.y);
                ctx.strokeStyle = hexA(e.def.color, 0.4); ctx.lineWidth = 1.5; ctx.stroke(); ctx.restore();
            }
            circle(ctx, e.x, e.y, e.r, '#0e2402', c, 2.5);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r, c);
            break;
        }
        case 'obfusc': {
            ctx.save(); ctx.globalAlpha *= 0.22;
            for (let i = 0; i < 6; i++) {
                const a = i * TAU / 6 + t * 0.01;
                circle(ctx, e.x + Math.cos(a) * CLOUD_R * 0.5, e.y + Math.sin(a) * CLOUD_R * 0.5, CLOUD_R * 0.6, '#b0c4ff');
            }
            ctx.restore();
            circle(ctx, e.x, e.y, e.r, '#0a1030', c, 2);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r, c);
            break;
        }
        case 'exfil': case 'courier': {
            glow(ctx, e.x, e.y, e.r * 2.6, e.def.color, 0.3);
            const a = Math.atan2(e.vy, e.vx);
            ctx.save(); ctx.translate(e.x, e.y); ctx.rotate(a);
            ctx.beginPath(); ctx.moveTo(e.r * 1.2, 0); ctx.lineTo(-e.r, -e.r * 0.8); ctx.lineTo(-e.r * 0.6, 0); ctx.lineTo(-e.r, e.r * 0.8); ctx.closePath();
            ctx.fillStyle = '#2a2202'; ctx.fill(); ctx.strokeStyle = c; ctx.lineWidth = 2.5; ctx.stroke();
            ctx.restore();
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 0.8, c);
            if (e.type === 'courier' && e.state === 'upload') {
                ctx.save(); ctx.globalAlpha *= 0.7;
                for (let i = 0; i < 3; i++) { const rr = (t * 2 + i * 25) % 75; circle(ctx, e.x, e.y, e.r + rr, null, hexA('#ffd84f', 1 - rr / 75), 2); }
                ctx.restore();
            }
            break;
        }
        case 'shard': {
            glow(ctx, e.x, e.y, e.r * 1.8, e.def.color, 0.18);
            ctx.beginPath();
            e.verts.forEach((k, i) => {
                const a = e.spin + i / e.verts.length * TAU;
                const px = e.x + Math.cos(a) * e.r * k, py = e.y + Math.sin(a) * e.r * k;
                i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
            });
            ctx.closePath();
            ctx.fillStyle = '#04182a'; ctx.fill(); ctx.strokeStyle = c; ctx.lineWidth = 2.5; ctx.stroke();
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 0.7, hexA(e.def.color, 0.8));
            break;
        }
        case 'fork':
            glow(ctx, e.x, e.y, 26, e.def.color, 0.3);
            poly(ctx, e.x, e.y, e.r, 4, Math.PI / 4 + Math.sin(t * 0.1) * 0.3, '#2a1402', c, 2);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 0.95, c);
            break;
        case 'latch': {
            if (e.latched) {
                const k = e.latchT / 150;
                circle(ctx, L.player.x, L.player.y, 22 + k * 10, null, hexA('#c0ff5b', 0.4 + k * 0.5), 2);
            }
            glow(ctx, e.x, e.y, 20, e.def.color, 0.4);
            circle(ctx, e.x, e.y, e.r, '#142a02', c, 2);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 1.1, c);
            break;
        }
        case 'spore': {
            const sw = e.state === 'swell' ? 1 + (1 - e.stateT / 34) * 0.6 : 1 + Math.sin(t * 0.08) * 0.08;
            glow(ctx, e.x, e.y, e.r * 2.4 * sw, e.def.color, 0.3);
            for (let i = 0; i < 7; i++) {
                const a = i * TAU / 7 + t * 0.03;
                circle(ctx, e.x + Math.cos(a) * e.r * sw, e.y + Math.sin(a) * e.r * sw, 3, c);
            }
            circle(ctx, e.x, e.y, e.r * sw, e.state === 'swell' && t % 6 < 3 ? '#fff' : '#22062a', c, 2);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * sw, c);
            break;
        }
        case 'benign':
            drawBenignShape(ctx, e, e.flash > 0 ? '#ffffff' : '#4be08a');
            break;
        default: {
            circle(ctx, e.x, e.y, e.r, '#120812', c, 2.5);
            glyph(ctx, e.def.glyph, e.x, e.y, e.r * 1.1, c);
        }
    }
    if (e.stun > 0) { for (let i = 0; i < 3; i++) { const a = e.t * 0.2 + i * TAU / 3; glyph(ctx, 'star', e.x + Math.cos(a) * (e.r + 6), e.y - e.r - 4 + Math.sin(a) * 4, 9, '#ffd166'); } }
    if (e.frozen > 0) circle(ctx, e.x, e.y, e.r + 5, hexA('#bfe9ff', 0.25), hexA('#bfe9ff', 0.9), 2);
    // health pip for tough enemies
    if (e.maxHp >= 6 && e.hp < e.maxHp && e.alpha > 0.5) {
        const w = Math.max(24, e.r * 2);
        ctx.fillStyle = 'rgba(0,0,0,0.5)'; ctx.fillRect(e.x - w / 2, e.y - e.r - 12, w, 4);
        ctx.fillStyle = e.def.color; ctx.fillRect(e.x - w / 2, e.y - e.r - 12, w * Math.max(0, e.hp / e.maxHp), 4);
    }
    ctx.restore();
}
