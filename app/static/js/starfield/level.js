/**
 * level.js — one running level: the player, weapons, enemies, boss,
 * hazards, pickups, objectives, scoring and stars. Pure game logic +
 * canvas drawing; the DOM side (HUD, menus) lives in main.js and gets
 * data through the callbacks.
 *
 * Kinds: waves | survive | beacons | protect | boss | honeypot | endless
 */
import { W, H, TAU, WEAPONS, ENEMIES, PICKUPS, WORLDS, BOSSES } from './data.js';
import { makeEnemy, updateEnemy, drawEnemy, onEnemyDeath, hittable, deflects } from './enemies.js';
import { makeBoss } from './bosses.js';
import { circle, poly, glyph, glow, hexA, text, drawShip } from './render.js';
import { Sfx } from './audio.js';

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

    const L = {
        def, world, tier: def.tier ?? world * 4, diff: env.diff, theme,
        pool: def.pool || theme.pool,
        t: 0, score: 0, kills: 0, combo: 0, comboT: 0, maxCombo: 0,
        levelBytes: 0, hits: 0, finished: false, result: null,
        bullets: [], ebullets: [], enemies: [], pickups: [], particles: [], floaters: [],
        beams: [], zones: [], messages: [], boss: null, sensor: null,
        shakeT: 0, shakeMag: 0, slow: false,
        objective: { label: '', progress: 0 }, phaseLabel: '',
        wave: 0, waveQueue: [], waveDelay: 0,
        timer: def.duration || 0,
        endingT: 0,
    };

    const weapons = WEAPONS.filter(w => (env.weapons || ['pulse']).includes(w.id));
    const scheme = env.settings?.controls === 'twin' ? 'twin' : 'classic';
    let mouseUsed = false;
    let lastMove = [0, -1];
    const P = L.player = {
        x: W / 2, y: H - 140, vx: 0, vy: 0, angle: -Math.PI / 2, r: 12,
        maxHp: 3 + lv('hp'), hp: 3 + lv('hp'), inv: 120, dashCd: 0, dashT: 0,
        bombs: 2 + lv('bombs'), maxBombs: 2 + lv('bombs'),
        weapon: 0, cool: 0, buffs: { rapid: 0, shield: 0, overclock: 0 },
        disarmed: 0, pulled: null, thrust: 0,
        speed: 4.3 * (1 + 0.06 * lv('speed')), dmgMul: 1 + 0.15 * lv('damage'),
        rateMul: 1 - 0.08 * lv('rate'), dashMax: Math.round(75 * (1 - 0.12 * lv('dash'))),
        magnet: 80 + 55 * lv('magnet'),
    };

    // ── API used by enemies.js / bosses.js ─────────────────────────────
    L.pick = arr => arr[Math.floor(Math.random() * arr.length)];
    L.enemyBullet = (x, y, vx, vy, o = {}) => {
        const s = L.diff.bullet;
        L.ebullets.push({ x, y, vx: vx * s, vy: vy * s, r: o.r || 6, color: o.color || '#ff5d73', life: o.life || 420, kind: o.kind || 'shot', dmg: o.dmg || 1 });
    };
    L.spawnEnemy = (type, x, y, extra = {}) => {
        const e = makeEnemy(type, clamp(x, 30, W - 30), clamp(y, 30, H - 30), L, extra);
        L.enemies.push(e);
        return e;
    };
    L.addBeam = b => { L.beams.push({ x: 0, y: 0, rot: 0, ...b, t: 0 }); };
    L.addZone = z => { L.zones.push({ ...z, t: 0 }); };
    L.shake = m => { if (env.settings?.shake !== false) { L.shakeT = 14; L.shakeMag = Math.max(L.shakeMag, m); } };
    L.announce = (str, color = '#fff', sub = '') => { L.messages.push({ kind: 'big', str, sub, color, t: 0, life: 110 }); };
    L.say = (str, color = '#fff') => { if (str) L.messages.push({ kind: 'line', str, color, t: 0, life: 200 }); };
    L.float = (x, y, str, color = '#fff') => { L.floaters.push({ x, y, str, color, t: 0, life: 50 }); };
    L.addScore = n => { L.score += n; };
    L.drainBytes = (e, n) => {
        if (L.levelBytes <= 0) return;
        L.levelBytes = Math.max(0, L.levelBytes - n);
        L.float(e.x, e.y - 20, `-${n} byte`, '#ffd166');
    };
    L.explosion = (x, y, radius, color, hurtsPlayer) => {
        burst(x, y, 26, color, 6);
        L.particles.push({ kind: 'ring', x, y, r: 10, max: radius, life: 22, t: 0, color });
        Sfx.explode(true); L.shake(8);
        if (hurtsPlayer && dist2(x, y, P.x, P.y) < (radius + P.r) ** 2) hurt();
        if (hurtsPlayer && L.sensor && dist2(x, y, L.sensor.x, L.sensor.y) < (radius + L.sensor.r) ** 2) damageSensor(3);
    };

    function burst(x, y, n, color, speed = 4) {
        for (let i = 0; i < n; i++) {
            const a = rand(0, TAU), s = rand(0.5, speed);
            L.particles.push({ kind: 'spark', x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: rand(18, 40), t: 0, color, size: rand(1.5, 3.5) });
        }
    }

    // ── Spawning helpers ──────────────────────────────────────────────
    function spawnPoint(minDist = 220) {
        for (let i = 0; i < 20; i++) {
            const x = rand(60, W - 60), y = rand(60, H - 60);
            if (dist2(x, y, P.x, P.y) > minDist * minDist && (!L.sensor || dist2(x, y, L.sensor.x, L.sensor.y) > 160 * 160)) return [x, y];
        }
        return [Math.random() < 0.5 ? 60 : W - 60, rand(60, H - 60)];
    }
    function pickType(allowStatic = false) {
        const pool = L.pool.filter(k => allowStatic || !ENEMIES[k].static);
        // earlier entries of the pool are the world's "common" malware
        const weights = pool.map((_, i) => 1 / (1 + i * 0.35));
        let r = Math.random() * weights.reduce((a, b) => a + b, 0);
        for (let i = 0; i < pool.length; i++) { r -= weights[i]; if (r <= 0) return pool[i]; }
        return pool[0];
    }
    function spawnOne(type) { const [x, y] = spawnPoint(); return L.spawnEnemy(type || pickType(), x, y); }

    function buildWave(n) {
        const count = Math.round((5 + L.tier * 0.55 + n * 2) * L.diff.spawn);
        const q = [];
        for (let i = 0; i < count; i++) q.push(pickType(false));
        if (L.pool.includes('botnet') && n >= 2) q.push('botnet');
        return q;
    }

    // ── Setup per kind ───────────────────────────────────────────────
    const kind = def.kind;
    if (kind === 'beacons') {
        const placed = [];
        for (let i = 0; i < def.beacons; i++) {
            let x, y, ok = false;
            for (let k = 0; k < 40 && !ok; k++) {
                x = rand(120, W - 120); y = rand(100, H - 260);
                ok = placed.every(([px, py]) => dist2(x, y, px, py) > 230 * 230);
            }
            placed.push([x, y]);
            L.spawnEnemy('beacon', x, y, { spawnT: 40 + i * 15 });
        }
    }
    if (kind === 'protect') {
        const hp = 26 + world * 3;
        L.sensor = { x: W / 2, y: H / 2, r: 30, hp, maxHp: hp, flash: 0 };
        P.y = H / 2 + 120;
    }
    if (kind === 'boss') {
        L.boss = makeBoss(def.boss, L);
        L.bossIntroT = 150;
        Sfx.warning();
    }

    // ── Player actions ───────────────────────────────────────────────
    function currentWeapon() { return weapons[P.weapon] || weapons[0]; }

    function fire() {
        const wp = currentWeapon();
        if (P.cool > 0 || P.disarmed > 0) return;
        const rapid = P.buffs.rapid > 0 ? 0.5 : 1;
        P.cool = Math.max(3, Math.round(wp.rate * P.rateMul * rapid));
        const dmg = wp.dmg * P.dmgMul * (P.buffs.overclock > 0 ? 2 : 1);
        for (let i = 0; i < wp.count; i++) {
            const off = wp.count > 1 ? (i - (wp.count - 1) / 2) * wp.spread : 0;
            const a = P.angle + off;
            L.bullets.push({
                x: P.x + Math.cos(P.angle) * 18, y: P.y + Math.sin(P.angle) * 18,
                vx: Math.cos(a) * wp.speed + P.vx * 0.3, vy: Math.sin(a) * wp.speed + P.vy * 0.3,
                r: wp.id === 'rail' ? 5 : wp.id === 'seeker' ? 5 : 3.5, dmg, life: wp.life || 90,
                pierce: !!wp.pierce, homing: !!wp.homing, color: wp.color, hitIds: wp.pierce ? new Set() : null, id: wp.id,
            });
        }
        Sfx.shoot(wp.id);
    }

    function dash(mx, my) {
        if (P.dashCd > 0) return;
        let [dx, dy] = [mx, my];
        if (!dx && !dy) { dx = Math.cos(P.angle); dy = Math.sin(P.angle); }
        const l = Math.hypot(dx, dy) || 1;
        P.vx = dx / l * 15; P.vy = dy / l * 15;
        P.dashT = 12; P.inv = Math.max(P.inv, 16); P.dashCd = P.dashMax;
        burst(P.x, P.y, 12, env.skin.glow, 3);
        Sfx.dash();
    }

    function bomb() {
        if (P.bombs <= 0) { Sfx.deny(); return; }
        P.bombs--;
        L.ebullets.length = 0;
        L.beams.forEach(b => { if (b.t < b.tele) b.cancel = true; });
        L.particles.push({ kind: 'ring', x: P.x, y: P.y, r: 20, max: 900, life: 40, t: 0, color: '#ffffff' });
        for (const e of L.enemies) if (hittable(e)) damageEnemy(e, 6 * P.dmgMul);
        if (L.boss && !L.boss.entering) for (const tg of L.boss.targets()) if (!tg.shielded) tg.hit(18 * P.dmgMul);
        P.inv = Math.max(P.inv, 60);
        L.shake(20); Sfx.bomb();
        L.announce('QUARANTINE', '#ffffff');
    }

    function hurt() {
        if (P.inv > 0 || L.finished) return;
        if (P.buffs.shield > 0) { P.buffs.shield = 0; P.inv = 60; Sfx.shieldBreak(); burst(P.x, P.y, 20, '#6ea8ff'); return; }
        P.hp--; L.hits++; P.inv = 100; L.combo = 0; L.comboT = 0;
        L.shake(16); Sfx.hurt(); burst(P.x, P.y, 30, '#ff5d73', 5);
        if (P.hp <= 0) lose('Rule disabled');
    }

    function damageSensor(n) {
        const s = L.sensor; if (!s || s.hp <= 0) return;
        s.hp -= n; s.flash = 6;
        if (s.hp <= 0) { L.explosion(s.x, s.y, 120, '#5be7ff', false); lose('Sensor lost'); }
    }

    // ── Enemies dying, drops ─────────────────────────────────────────
    function damageEnemy(e, d) {
        e.hp -= d; e.flash = 4;
        if (e.hp <= 0) killEnemy(e);
        else Sfx.hit();
    }

    function killEnemy(e) {
        if (e.dead) return;
        e.dead = true;
        L.kills++;
        L.comboT = 150; L.combo++;
        L.maxCombo = Math.max(L.maxCombo, L.combo);
        const mult = Math.min(8, 1 + Math.floor(L.combo / 5));
        const pts = e.def.score * mult;
        L.score += pts;
        L.float(e.x, e.y, `+${pts}`, mult > 1 ? '#ffd166' : '#ffffff');
        burst(e.x, e.y, e.def.static ? 30 : 14, e.def.color, e.def.static ? 6 : 4);
        Sfx.explode(!!e.def.static);
        if (e.def.static) L.shake(8);
        const byteMul = kind === 'honeypot' ? 3 : 1;
        const n = Math.round(e.def.bytes * byteMul);
        for (let i = 0; i < n; i++) dropPickup('byte', e.x + rand(-12, 12), e.y + rand(-12, 12));
        const chance = kind === 'honeypot' ? 0.1 : e.def.static ? 0.6 : 0.055;
        if (Math.random() < chance) {
            const r = Math.random();
            dropPickup(r < 0.28 ? 'heal' : r < 0.52 ? 'rapid' : r < 0.72 ? 'shield' : r < 0.86 ? 'overclock' : 'bomb', e.x, e.y);
        }
        if (!e.silent) onEnemyDeath(e, L);
    }

    function dropPickup(type, x, y) {
        const a = rand(0, TAU), s = type === 'byte' ? rand(1, 3) : 1;
        L.pickups.push({ type, x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, t: 0, life: type === 'byte' ? 600 : 720 });
    }

    function collect(pk) {
        const def = PICKUPS[pk.type];
        if (pk.type === 'byte') { L.levelBytes++; Sfx.pickup(); return; }
        if (pk.type === 'heal') { if (P.hp < P.maxHp) P.hp++; else L.score += 250; }
        else if (pk.type === 'bomb') { P.bombs = Math.min(P.maxBombs + 1, P.bombs + 1); }
        else P.buffs[pk.type] = def.frames;
        L.float(pk.x, pk.y - 14, def.label, def.color);
        Sfx.powerup();
    }

    // ── Objectives ───────────────────────────────────────────────────
    function startWave(n) {
        L.wave = n; L.waveQueue = buildWave(n); L.waveSpawnT = 0;
        L.announce(kind === 'endless' ? `WAVE ${n}` : `WAVE ${n} / ${def.waves}`, theme.hue);
        Sfx.levelUp();
    }

    function updateObjective() {
        const alive = L.enemies.filter(e => !e.dead);
        switch (kind) {
            case 'waves':
            case 'endless': {
                if (L.wave === 0 && L.t === 90) startWave(1);
                if (L.wave > 0 && L.waveQueue.length && --L.waveSpawnT <= 0) {
                    spawnOne(L.waveQueue.shift());
                    L.waveSpawnT = Math.max(10, 28 - L.tier) / L.diff.spawn;
                }
                const bossAlive = L.boss && L.boss.hp > 0;
                if (L.wave > 0 && !L.waveQueue.length && !alive.length && !bossAlive) {
                    if (L.waveDelay === 0) L.waveDelay = 100;
                    if (--L.waveDelay === 0) {
                        if (kind === 'waves' && L.wave >= def.waves) return win();
                        const next = L.wave + 1;
                        if (kind === 'endless' && next % 5 === 0) {
                            L.wave = next;
                            const bi = ((next / 5) - 1) % BOSSES.length;
                            L.boss = makeBoss(bi, L, 0.45 + next * 0.03);
                            L.announce(`WAVE ${next} — ${BOSSES[bi].name}`, BOSSES[bi].color);
                            Sfx.warning();
                        } else startWave(next);
                    }
                }
                L.objective = kind === 'waves'
                    ? { label: `Wave ${Math.max(1, L.wave)} / ${def.waves}`, progress: (Math.max(0, L.wave - 1) + (L.waveQueue.length || alive.length ? 0 : 1)) / def.waves }
                    : { label: `Wave ${Math.max(1, L.wave)}`, progress: null };
                if (kind === 'endless') { L.tier = Math.min(30, L.wave * 0.8); }
                break;
            }
            case 'survive':
            case 'protect':
            case 'honeypot': {
                L.timer--;
                const every = kind === 'honeypot' ? 14 : Math.max(26, 85 - L.tier * 2.6) / L.diff.spawn;
                const cap = kind === 'honeypot' ? 26 : Math.round((9 + L.tier * 0.5) * L.diff.spawn);
                if (L.t > 90 && L.t % Math.round(every) === 0 && alive.length < cap) {
                    if (kind === 'honeypot') spawnOne(L.pick(['wormlet', 'drone', 'trojan', 'worm', 'miner']));
                    else spawnOne();
                }
                if (kind !== 'honeypot' && L.t % 900 === 450) {          // a swarm every 15 s
                    L.say('Incoming swarm!', theme.hue);
                    for (let i = 0; i < 4 + world; i++) spawnOne(L.pool.includes('drone') ? 'drone' : 'wormlet');
                }
                const total = def.duration;
                const secs = Math.ceil(Math.max(0, L.timer) / 60);
                L.objective = {
                    label: kind === 'protect' ? `Scan ${Math.round(100 * (1 - L.timer / total))}% — sensor ${Math.max(0, Math.ceil(L.sensor.hp))}/${L.sensor.maxHp}`
                         : kind === 'honeypot' ? `Honeypot — ${secs}s — ${L.levelBytes} bytes` : `Survive — ${secs}s`,
                    progress: 1 - L.timer / total,
                };
                if (L.timer <= 0) {
                    for (const e of L.enemies) if (!e.dead && !e.def.static) { burst(e.x, e.y, 10, e.def.color); e.dead = true; }
                    win();
                }
                break;
            }
            case 'beacons': {
                if (L.t > 120 && L.t % Math.round(Math.max(60, 150 - L.tier * 4) / L.diff.spawn) === 0 && alive.length < 6 + L.tier * 0.4) spawnOne();
                const left = alive.filter(e => e.type === 'beacon').length;
                L.objective = { label: `C2 beacons — ${def.beacons - left} / ${def.beacons} down`, progress: (def.beacons - left) / def.beacons };
                if (L.t > 120 && left === 0) win();
                break;
            }
            case 'boss': {
                const b = L.boss;
                L.objective = { label: b.name, progress: null };
                if (b.hp <= 0 && !L.endingT) {
                    L.endingT = 150; L.ebullets.length = 0; L.beams.length = 0; L.zones.length = 0;
                    for (const e of L.enemies) e.dead = true;
                    L.announce(`${b.name} NEUTRALIZED`, b.def.color);
                    Sfx.bossRoar();
                }
                if (L.endingT) {
                    if (L.endingT % 12 === 0) L.explosion(b.x + rand(-60, 60), b.y + rand(-60, 60), 70, L.pick([b.def.color, '#fff', '#ffd166']), false);
                    if (--L.endingT === 1) { for (let i = 0; i < 25; i++) dropPickup('byte', b.x, b.y); L.boss = null; win(); }
                }
                break;
            }
        }
    }

    function stars() {
        const crit = [{ label: 'Complete the level', ok: true }];
        const secs = L.t / 60;
        const maxHits = kind === 'boss' ? 3 : 2;
        crit.push({ label: `Take ${maxHits} hits or fewer`, ok: L.hits <= maxHits });
        if (kind === 'survive') crit.push({ label: 'Take no hit at all', ok: L.hits === 0 });
        else if (kind === 'protect') crit.push({ label: 'Sensor above 70%', ok: L.sensor.hp >= L.sensor.maxHp * 0.7 });
        else if (kind === 'honeypot') { const goal = 120 + world * 30; crit.push({ label: `Collect ${goal} bytes`, ok: L.levelBytes >= goal }); }
        else crit.push({ label: `Finish under ${def.par}s`, ok: secs <= def.par });
        return { crit, stars: crit.filter(c => c.ok).length };
    }

    function finishResult(won, reason) {
        const s = won ? stars() : { crit: [], stars: 0 };
        const bytes = Math.round(L.levelBytes * L.diff.bytes * (won ? 1 : 0.5));
        L.result = {
            won, reason, stars: s.stars, crit: s.crit, score: L.score + (won ? Math.round(P.hp * 300 + L.levelBytes * 5) : 0),
            bytes, time: Math.round(L.t / 60), hits: L.hits, kills: L.kills, maxCombo: L.maxCombo, wave: L.wave,
        };
        L.finished = true;
        L.finishT = 70;
    }
    function win() { if (L.finished) return; Sfx.victory(); finishResult(true); }
    function lose(reason) { if (L.finished) return; Sfx.gameOver(); finishResult(false, reason); }

    // ── Per-frame update ─────────────────────────────────────────────
    L.update = (input) => {
        L.t++;
        if (L.finished) {
            updateParticles();
            if (--L.finishT === 0) env.callbacks.onEnd(L.result);
            return;
        }
        if (L.boss && L.bossIntroT > 0) { L.bossIntroT--; L.boss.update(); updateParticles(); return; }

        // ── controls: "classic" (turn + thrust, like the original
        // Starfield) or "twin" (move with WASD, aim with the mouse) ──
        const st = input.state;
        const padAim = st.pad && (Math.abs(st.pad.rx) > 0.2 || Math.abs(st.pad.ry) > 0.2);
        let mx = 0, my = 0;
        if (scheme === 'classic') {
            const turn = (input.any('ArrowLeft', 'KeyA') ? -1 : 0) + (input.any('ArrowRight', 'KeyD') ? 1 : 0) + (st.pad ? st.pad.lx : 0);
            P.angle += clamp(turn, -1, 1) * 0.075;
            if (padAim) P.angle = Math.atan2(st.pad.ry, st.pad.rx);
            const thrust = (input.any('ArrowUp', 'KeyW') || (st.pad && st.pad.ly < -0.4)) ? 1 : 0;
            const brake = input.any('ArrowDown', 'KeyS') || (st.pad && st.pad.ly > 0.4);
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
            if (mx || my) lastMove = [mx, my];
            if (padAim) P.angle = Math.atan2(st.pad.ry, st.pad.rx);
            else if (mouseUsed) P.angle = Math.atan2(st.my - P.y, st.mx - P.x);
            else {
                let target = null;
                if (env.settings?.assist === true) {
                    let bd = Infinity;
                    const cands = L.enemies.filter(e => !e.dead && hittable(e) && e.alpha > 0.3);
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
        P.x = clamp(P.x + P.vx, 16, W - 16);
        P.y = clamp(P.y + P.vy, 16, H - 16);

        // actions
        const wantFire = (scheme === 'twin' && st.mouseDown) || input.any('Space', 'KeyJ') || (st.pad && st.pad.fire);
        if (wantFire) fire();
        if (input.hit('ShiftLeft', 'ShiftRight', 'KeyK') || (scheme === 'twin' && input.hit('Mouse2')) || (st.pad && st.pad.dash)) dash(mx, my);
        if (input.hit('KeyE', 'KeyB') || (st.pad && st.pad.bomb)) bomb();
        weapons.forEach((wp, i) => { if (input.hit(`Digit${WEAPONS.indexOf(wp) + 1}`)) P.weapon = i; });
        if (input.hit('KeyQ') || st.wheel > 0 || (st.pad && st.pad.next)) P.weapon = (P.weapon + 1) % weapons.length;
        if (st.wheel < 0 || (st.pad && st.pad.prev)) P.weapon = (P.weapon - 1 + weapons.length) % weapons.length;

        if (P.cool > 0) P.cool--;
        if (P.inv > 0) P.inv--;
        if (P.dashCd > 0) P.dashCd--;
        if (P.disarmed > 0) P.disarmed--;
        for (const k in P.buffs) if (P.buffs[k] > 0) P.buffs[k]--;
        if (L.comboT > 0 && --L.comboT === 0) L.combo = 0;

        updateObjective();

        // player bullets
        for (const b of L.bullets) {
            if (b.homing) {
                let best = null, bd = 380 * 380;
                for (const e of L.enemies) if (!e.dead && hittable(e)) { const d = dist2(e.x, e.y, b.x, b.y); if (d < bd) { bd = d; best = e; } }
                if (!best && L.boss && !L.boss.entering) for (const t of L.boss.targets()) { const d = dist2(t.x, t.y, b.x, b.y); if (d < bd) { bd = d; best = t; } }
                if (best) {
                    const a = Math.atan2(best.y - b.y, best.x - b.x), sp = Math.hypot(b.vx, b.vy) + 0.12;
                    const cur = Math.atan2(b.vy, b.vx);
                    let d = ((a - cur + Math.PI * 3) % TAU) - Math.PI;
                    const na = cur + clamp(d, -0.12, 0.12);
                    b.vx = Math.cos(na) * Math.min(sp, 11); b.vy = Math.sin(na) * Math.min(sp, 11);
                }
                if (L.t % 2 === 0) L.particles.push({ kind: 'spark', x: b.x, y: b.y, vx: 0, vy: 0, life: 14, t: 0, color: b.color, size: 2 });
            }
            b.x += b.vx; b.y += b.vy; b.life--;
            if (b.x < -20 || b.x > W + 20 || b.y < -20 || b.y > H + 20) b.life = 0;
            if (b.life <= 0) continue;
            for (const e of L.enemies) {
                if (e.dead || !hittable(e) || (b.hitIds && b.hitIds.has(e))) continue;
                if (dist2(b.x, b.y, e.x, e.y) < (b.r + e.r) ** 2) {
                    if (deflects(e, b)) { b.life = 0; burst(b.x, b.y, 4, '#ffd166', 2); Sfx.hit(); break; }
                    damageEnemy(e, b.dmg);
                    if (b.hitIds) b.hitIds.add(e); else { b.life = 0; break; }
                }
            }
            if (b.life > 0 && L.boss && !L.boss.entering && L.boss.hp > 0) {
                for (const tg of L.boss.targets()) {
                    if (dist2(b.x, b.y, tg.x, tg.y) < (b.r + tg.r) ** 2) {
                        if (tg.shielded) { burst(b.x, b.y, 3, '#c08bff', 2); b.life = 0; break; }
                        tg.hit(b.dmg); Sfx.hit();
                        if (!b.pierce) { b.life = 0; break; }
                    }
                }
            }
        }
        L.bullets = L.bullets.filter(b => b.life > 0);

        // enemies
        for (const e of L.enemies) {
            if (e.dead) continue;
            updateEnemy(e, L);
            if (e.hp <= 0) { killEnemy(e); continue; }
            if (e.spawnT > 0 || e.alpha < 0.3) continue;
            if (dist2(e.x, e.y, P.x, P.y) < (e.r + P.r) ** 2 && e.type !== 'decoy') {
                if (e.type === 'locker' && P.inv <= 0) { P.disarmed = 120; L.float(P.x, P.y - 24, 'ENCRYPTED!', '#ff7a3c'); }
                hurt();
                if (!e.def.static && e.type !== 'locker') damageEnemy(e, 2);
            }
            if (L.sensor && !e.def.static && dist2(e.x, e.y, L.sensor.x, L.sensor.y) < (e.r + L.sensor.r) ** 2) {
                if (e.t % 30 === 0) damageSensor(1);
                e.vx -= (L.sensor.x - e.x) * 0.01; e.vy -= (L.sensor.y - e.y) * 0.01;
            }
        }
        L.enemies = L.enemies.filter(e => !e.dead);

        // boss
        if (L.boss && L.boss.hp > 0) {
            L.boss.update();
            if (!L.boss.entering) {
                for (const tg of L.boss.targets()) {
                    if (dist2(tg.x, tg.y, P.x, P.y) < (tg.r * 0.8 + P.r) ** 2 && (L.boss.alpha ?? 1) > 0.3) hurt();
                }
            }
            if (env.callbacks.onBoss) env.callbacks.onBoss(L.boss);
        } else if (L.boss && kind !== 'boss') {
            // endless: a boss between waves just blows up and pays out
            const b = L.boss;
            for (let i = 0; i < 4; i++) L.explosion(b.x + rand(-50, 50), b.y + rand(-50, 50), 80, b.def.color, false);
            for (let i = 0; i < 20; i++) dropPickup('byte', b.x, b.y);
            L.score += 5000; L.float(b.x, b.y, '+5000', '#ffd166');
            L.ebullets.length = 0; L.beams.length = 0; L.zones.length = 0;
            L.boss = null;
            if (env.callbacks.onBoss) env.callbacks.onBoss(null);
        } else if (L.boss && env.callbacks.onBoss) env.callbacks.onBoss(L.boss);

        // enemy bullets
        for (const b of L.ebullets) {
            b.x += b.vx; b.y += b.vy; b.life--;
            if (b.x < -40 || b.x > W + 40 || b.y < -40 || b.y > H + 40) b.life = 0;
            if (b.life <= 0) continue;
            if (dist2(b.x, b.y, P.x, P.y) < (b.r + P.r - 3) ** 2) {
                b.life = 0;
                if (b.kind === 'hook' && P.inv <= 0) { P.pulled = { x: b.x - b.vx * 30, y: b.y - b.vy * 30, frames: 50 }; L.float(P.x, P.y - 24, 'HOOKED!', '#3ee0c8'); }
                hurt();
            } else if (L.sensor && dist2(b.x, b.y, L.sensor.x, L.sensor.y) < (b.r + L.sensor.r) ** 2) {
                b.life = 0; damageSensor(b.dmg);
            }
        }
        L.ebullets = L.ebullets.filter(b => b.life > 0);
        if (L.ebullets.length > 700) L.ebullets.splice(0, L.ebullets.length - 700);

        // hazards
        for (const bm of L.beams) {
            bm.t++;
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
            pk.x = clamp(pk.x + pk.vx, 10, W - 10); pk.y = clamp(pk.y + pk.vy, 10, H - 10);
            if (d2 < (P.r + 14) ** 2) { collect(pk); pk.life = 0; }
        }
        L.pickups = L.pickups.filter(pk => pk.life > 0);
        if (L.sensor && L.sensor.flash > 0) L.sensor.flash--;

        updateParticles();
    };

    function updateParticles() {
        for (const p of L.particles) {
            p.t++;
            if (p.kind === 'spark') { p.x += p.vx; p.y += p.vy; p.vx *= 0.95; p.vy *= 0.95; }
            else p.r += (p.max - p.r) * 0.15;
        }
        L.particles = L.particles.filter(p => p.t < p.life);
        if (L.particles.length > 500) L.particles.splice(0, L.particles.length - 500);
        for (const f of L.floaters) { f.t++; f.y -= 0.6; }
        L.floaters = L.floaters.filter(f => f.t < f.life);
        for (const m of L.messages) m.t++;
        L.messages = L.messages.filter(m => m.t < m.life);
        if (L.shakeT > 0) { L.shakeT--; if (!L.shakeT) L.shakeMag = 0; }
    }

    // ── Drawing ──────────────────────────────────────────────────────
    L.draw = (ctx) => {
        ctx.save();
        if (L.shakeT > 0) ctx.translate(rand(-1, 1) * L.shakeMag * L.shakeT / 14, rand(-1, 1) * L.shakeMag * L.shakeT / 14);

        for (const z of L.zones) {
            const active = z.t > z.tele;
            const blink = !active && Math.floor(z.t / 8) % 2;
            ctx.fillStyle = hexA(z.color, active ? 0.28 : blink ? 0.14 : 0.06);
            ctx.fillRect(z.x, z.y, z.w, z.h);
            ctx.strokeStyle = hexA(z.color, 0.8); ctx.lineWidth = 2; ctx.setLineDash(active ? [] : [12, 8]);
            ctx.strokeRect(z.x + 2, z.y + 2, z.w - 4, z.h - 4); ctx.setLineDash([]);
            if (active) glyph(ctx, 'lock', z.x + z.w / 2, z.y + z.h / 2, 60, hexA(z.color, 0.35));
        }

        if (L.sensor) {
            const s = L.sensor;
            glow(ctx, s.x, s.y, 90, '#5be7ff', 0.25);
            circle(ctx, s.x, s.y, s.r + 12, null, hexA('#5be7ff', 0.4), 2);
            const prog = 1 - L.timer / def.duration;
            ctx.beginPath(); ctx.arc(s.x, s.y, s.r + 12, -Math.PI / 2, -Math.PI / 2 + prog * TAU);
            ctx.strokeStyle = '#5be7ff'; ctx.lineWidth = 4; ctx.stroke();
            circle(ctx, s.x, s.y, s.r, s.flash ? '#fff' : '#06202a', '#5be7ff', 3);
            glyph(ctx, 'eye', s.x, s.y, 24, '#5be7ff');
            ctx.save(); ctx.globalAlpha = 0.25;
            ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.arc(s.x, s.y, 160, L.t * 0.03, L.t * 0.03 + 0.5); ctx.closePath();
            ctx.fillStyle = '#5be7ff'; ctx.fill(); ctx.restore();
        }

        for (const pk of L.pickups) {
            const def = PICKUPS[pk.type];
            const fading = pk.life < 120 && Math.floor(pk.life / 6) % 2;
            if (fading) continue;
            if (pk.type === 'byte') {
                poly(ctx, pk.x, pk.y, 6, 4, pk.t * 0.08, def.color);
            } else {
                const bob = Math.sin(pk.t * 0.1) * 3;
                glow(ctx, pk.x, pk.y + bob, 32, def.color, 0.4);
                circle(ctx, pk.x, pk.y + bob, def.r, '#0b1020', def.color, 2);
                glyph(ctx, def.glyph, pk.x, pk.y + bob, 14, def.color);
            }
        }

        for (const e of L.enemies) drawEnemy(ctx, e, L);
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

        for (const b of L.bullets) {
            if (b.id === 'rail') {
                ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(b.x - b.vx * 2.2, b.y - b.vy * 2.2);
                ctx.strokeStyle = b.color; ctx.lineWidth = 5; ctx.stroke();
            } else if (b.id === 'seeker') {
                poly(ctx, b.x, b.y, 6, 3, Math.atan2(b.vy, b.vx), b.color);
            } else circle(ctx, b.x, b.y, b.r, b.color);
        }
        for (const b of L.ebullets) {
            if (b.kind === 'hook') {
                circle(ctx, b.x, b.y, b.r + 3, null, b.color, 2);
                glyph(ctx, 'key', b.x, b.y, 10, b.color);
            } else {
                circle(ctx, b.x, b.y, b.r + 2, hexA(b.color, 0.35));
                circle(ctx, b.x, b.y, b.r * 0.6, '#ffffff');
            }
        }

        // player
        if (!(L.finished && !L.result.won)) {
            const blink = P.inv > 0 && P.inv % 8 < 4 && P.dashT === 0;
            if (P.pulled) {
                ctx.beginPath(); ctx.moveTo(P.x, P.y); ctx.lineTo(P.pulled.x, P.pulled.y);
                ctx.strokeStyle = hexA('#3ee0c8', 0.6); ctx.lineWidth = 2; ctx.stroke();
            }
            drawShip(ctx, P.x, P.y, P.angle, env.skin, { thrust: P.thrust, alpha: blink ? 0.35 : 1, t: L.t });
            if (P.buffs.shield > 0) circle(ctx, P.x, P.y, 26 + Math.sin(L.t * 0.2) * 2, hexA('#6ea8ff', 0.12), hexA('#6ea8ff', 0.8), 2);
            if (P.disarmed > 0) glyph(ctx, 'lock', P.x, P.y - 28, 14, '#ff7a3c');
            if (P.buffs.overclock > 0) glow(ctx, P.x, P.y, 40, '#ff6bd8', 0.3);
        }

        for (const p of L.particles) {
            const k = 1 - p.t / p.life;
            if (p.kind === 'spark') { ctx.globalAlpha = k; ctx.fillStyle = p.color; ctx.fillRect(p.x, p.y, p.size, p.size); }
            else { ctx.globalAlpha = k * 0.8; circle(ctx, p.x, p.y, p.r, null, p.color, 3); }
        }
        ctx.globalAlpha = 1;
        for (const f of L.floaters) text(ctx, f.str, f.x, f.y, { size: 14, color: f.color, alpha: 1 - f.t / f.life });
        ctx.restore();

        // announcements (not shaken)
        const big = L.messages.filter(m => m.kind === 'big').slice(-1)[0];
        if (big) {
            const a = Math.min(1, big.t / 10, (big.life - big.t) / 20);
            text(ctx, big.str, W / 2, H / 2 - 80, { size: 46, color: big.color, alpha: a });
        }
        const line = L.messages.filter(m => m.kind === 'line').slice(-1)[0];
        if (line) {
            const a = Math.min(1, line.t / 10, (line.life - line.t) / 20);
            ctx.save(); ctx.globalAlpha = a * 0.6; ctx.fillStyle = '#000'; ctx.fillRect(W / 2 - 360, H - 70, 720, 40); ctx.restore();
            text(ctx, line.str, W / 2, H - 50, { size: 17, color: line.color, alpha: a, weight: 600 });
        }
        if (L.boss && L.bossIntroT > 0) {
            const a = Math.min(1, (150 - L.bossIntroT) / 20, L.bossIntroT / 20);
            ctx.save(); ctx.globalAlpha = a * 0.55; ctx.fillStyle = '#000'; ctx.fillRect(0, H / 2 - 90, W, 180); ctx.restore();
            text(ctx, 'WARNING', W / 2, H / 2 - 45, { size: 22, color: '#ff5d73', alpha: a * (L.t % 20 < 12 ? 1 : 0.4) });
            text(ctx, L.boss.name, W / 2, H / 2 + 5, { size: 54, color: L.boss.def.color, alpha: a });
            text(ctx, L.boss.def.intro, W / 2, H / 2 + 55, { size: 16, color: '#ddd', alpha: a, weight: 500 });
        }
    };

    /** Data for the HTML HUD */
    L.hud = () => ({
        hp: P.hp, maxHp: P.maxHp, bombs: P.bombs, score: L.score, bytes: L.levelBytes,
        combo: L.combo >= 5 ? Math.min(8, 1 + Math.floor(L.combo / 5)) : 1, comboT: L.comboT,
        weapon: currentWeapon().id, weapons: weapons.map(w => w.id), dash: 1 - P.dashCd / P.dashMax,
        buffs: { ...P.buffs }, disarmed: P.disarmed, objective: L.objective,
    });

    return L;
}
