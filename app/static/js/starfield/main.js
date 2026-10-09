/**
 * main.js — Starfield's entry point: the screens (title, map, level,
 * hangar, results…), the fixed-step game loop, the HTML HUD and the glue
 * between the save, the map and the running level.
 */
import { W, H, WORLDS, WEAPONS, UPGRADES, SKINS, DIFFICULTIES, ENEMIES, BOSSES, levelDef, upgradeCost } from './data.js';
import * as Save from './save.js';
import { Sfx, Music, Audio } from './audio.js';
import { createInput } from './input.js';
import { makeStars, drawBackground, drawShip } from './render.js';
import { createMap } from './worldmap.js';
import { createLevel } from './level.js';

const $ = id => document.getElementById(id);
const stage = $('sf-stage');
const canvas = $('sf-canvas');
const ctx = canvas.getContext('2d');
const input = createInput(canvas);
const bgImage = new Image();
bgImage.src = stage.dataset.bg;

const S = Save.load();
Audio.setMuted(!!S.settings.muted);
Music.setEnabled(S.settings.music !== false);

const stars = makeStars(7);
const map = createMap();
let screen = 'title';          // title | map | level | endless
let overlay = null;            // id of the open panel, if any
let level = null;
let current = null;            // { world, index } of the running level, or { endless: true }
let paused = false;
let introT = 0;
let t = 0;
let drift = { x: 0, y: 0 };

const skin = () => SKINS.find(s => s.id === S.skin) || SKINS[0];
const diff = () => DIFFICULTIES.find(d => d.id === S.difficulty) || DIFFICULTIES[1];

// ── Canvas sizing: 1280×720 logical arena, letterboxed ────────────────
let view = { scale: 1, ox: 0, oy: 0, dpr: 1 };
function resize() {
    const r = stage.getBoundingClientRect();
    // cap the backing store around 2.4 Mpx — a 4K fullscreen canvas at dpr 2 was very heavy
    const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1, Math.sqrt(2.4e6 / Math.max(1, r.width * r.height))));
    canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr);
    const scale = Math.min(r.width / W, r.height / H);
    view = { scale, ox: (r.width - W * scale) / 2, oy: (r.height - H * scale) / 2, dpr };
}
window.addEventListener('resize', resize);
document.addEventListener('fullscreenchange', () => setTimeout(resize, 50));
resize();

// ── Screens ───────────────────────────────────────────────────────────
const PANELS = ['sf-title', 'sf-difficulty', 'sf-pause', 'sf-results', 'sf-endless', 'sf-hangar', 'sf-help', 'sf-settings'];
let backTo = null;
function openPanel(id, back = null) {
    PANELS.forEach(p => $(p).classList.toggle('is-open', p === id));
    overlay = id; backTo = back;
}
function closePanels() { PANELS.forEach(p => $(p).classList.remove('is-open')); overlay = null; }
document.querySelectorAll('[data-back]').forEach(b => b.addEventListener('click', () => goBack()));
function goBack() {
    Sfx.move();
    if (backTo === 'map') { closePanels(); showMap(); }
    else if (backTo === 'pause') openPanel('sf-pause');
    else showTitle();
}

function setHue(color) { stage.style.setProperty('--sf-hue', color); }

function toast(msg) {
    const el = $('sf-toast');
    el.textContent = msg; el.classList.add('show');
    clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove('show'), 2400);
}

// ── Title ─────────────────────────────────────────────────────────────
function showTitle() {
    screen = 'title'; level = null; current = null; paused = false;
    introT = 0; $('sf-intro').classList.remove('is-open');
    $('sf-hud').classList.remove('is-open'); $('sf-maphud').classList.remove('is-open');
    stage.classList.remove('is-playing'); input.setCapture(false);
    openPanel('sf-title');
    setHue(WORLDS[0].hue);
    const started = Object.keys(S.stars).length > 0 || S.pos.world > 0 || S.pos.node > 0;
    $('sf-btn-continue').style.display = started ? '' : 'none';
    $('sf-btn-new').classList.toggle('sf-btn--primary', !started);
    const best = S.endless[0] ? S.endless[0].score.toLocaleString() : '—';
    $('sf-title-stats').innerHTML = `
        <span><i class="fa-solid fa-star" style="color:#ffd166"></i> <b>${Save.totalStars()}</b> stars</span>
        <span><i class="fa-solid fa-skull"></i> <b>${S.bosses.length}</b>/5 bosses</span>
        <span><i class="fa-solid fa-microchip" style="color:#5be7ff"></i> <b>${S.bytes}</b> bytes</span>
        <span><i class="fa-solid fa-infinity"></i> best hunt <b>${best}</b></span>`;
    Music.play('map');
}

$('sf-btn-continue').addEventListener('click', () => { Audio.unlock(); Sfx.move(); closePanels(); showMap(); });
$('sf-btn-new').addEventListener('click', () => { Audio.unlock(); Sfx.move(); renderDifficulty(); openPanel('sf-difficulty'); });
$('sf-btn-endless').addEventListener('click', () => { Audio.unlock(); startEndless(); });
$('sf-btn-hangar').addEventListener('click', () => { Audio.unlock(); renderHangar('upgrades'); openPanel('sf-hangar'); });
$('sf-btn-help').addEventListener('click', () => { Audio.unlock(); renderHelp('controls'); openPanel('sf-help'); });
$('sf-btn-settings').addEventListener('click', () => { Audio.unlock(); renderSettings(); openPanel('sf-settings'); });

function renderDifficulty() {
    $('sf-diff-cards').innerHTML = DIFFICULTIES.map(d => `
        <button class="sf-card" data-diff="${d.id}"><b>${d.name}</b><span>${d.desc}</span></button>`).join('');
    $('sf-diff-cards').querySelectorAll('[data-diff]').forEach(b => b.addEventListener('click', () => {
        const started = Object.keys(S.stars).length > 0;
        if (started && !confirm('Start a new campaign? Map progress and stars are reset; bytes, upgrades and weapons are kept.')) return;
        S.difficulty = b.dataset.diff;
        S.unlocked = { '0-0': true }; S.stars = {}; S.best = {}; S.pos = { world: 0, node: 0 };
        Save.save();
        Sfx.levelUp(); closePanels(); showMap();
    }));
}

// ── Map ───────────────────────────────────────────────────────────────
map.onWorldChange = w => { S.pos = { world: w, node: map.node }; Save.save(); refreshMapHud(); toast(`${WORLDS[w].sub} — ${WORLDS[w].name}`); };
map.onArrive = node => { S.pos = { world: map.world, node }; Save.save(); refreshMapHud(); };

function showMap() {
    screen = 'map'; level = null; current = null; paused = false;
    introT = 0; $('sf-intro').classList.remove('is-open');
    closePanels();
    $('sf-hud').classList.remove('is-open'); $('sf-maphud').classList.add('is-open');
    stage.classList.remove('is-playing'); input.setCapture(true);
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    map.enter(Math.min(S.pos.world, WORLDS.length - 1), S.pos.node);
    refreshMapHud();
    Music.play('map');
}

const KIND_LABEL = { waves: 'WAVES', survive: 'SURVIVE', beacons: 'CUT THE C2', protect: 'PROTECT', boss: 'BOSS', honeypot: 'BONUS' };
function refreshMapHud() {
    const w = WORLDS[map.world];
    setHue(w.hue);
    $('sf-world-sub').textContent = w.sub;
    $('sf-world-name').textContent = w.name;
    $('sf-world-story').textContent = w.story;
    $('sf-map-wstars').textContent = Save.worldStars(map.world);
    $('sf-map-bytes').textContent = S.bytes;
    const { world, index, def } = map.selected();
    const kind = $('sf-lc-kind');
    kind.textContent = KIND_LABEL[def.kind];
    kind.className = 'sf-kind' + (def.kind === 'boss' ? ' sf-kind--boss' : def.kind === 'honeypot' ? ' sf-kind--honeypot' : '');
    const st = Save.starsOf(world, index);
    $('sf-lc-stars').innerHTML = [0, 1, 2].map(i => `<i class="fa-solid fa-star ${i < st ? 'on' : ''}"></i>`).join('');
    $('sf-lc-name').textContent = (index < 4 ? `${index + 1}. ` : '') + def.name;
    $('sf-lc-desc').textContent = def.kind === 'boss' ? BOSSES[def.boss].intro : def.desc;
    const best = S.best[`${world}-${index}`];
    $('sf-lc-best').textContent = best ? `Best score ${best.toLocaleString()}` : 'Not cleared yet';
    $('sf-lc-play').disabled = !map.canPlay();
}
$('sf-lc-play').addEventListener('click', () => { if (map.canPlay()) startLevel(map.world, map.node); });
$('sf-map-hangar').addEventListener('click', () => { renderHangar('upgrades'); openPanel('sf-hangar', 'map'); });
$('sf-map-menu').addEventListener('click', () => showTitle());

// ── Levels ────────────────────────────────────────────────────────────
function envFor() {
    return {
        skin: skin(), upgrades: S.upgrades, weapons: Save.weaponsUnlocked(), diff: diff(), settings: S.settings,
        callbacks: { onEnd: onLevelEnd, onBoss: updateBossBar },
    };
}

function startLevel(world, index) {
    Audio.unlock();
    const def = levelDef(world, index);
    current = { world, index };
    level = createLevel(def, envFor());
    beginPlay(def.kind === 'boss' ? (world === 4 ? 'final' : 'boss') : `w${world}`);
    $('sf-intro-kicker').textContent = def.kind === 'boss' ? `${WORLDS[world].sub.toUpperCase()} — BOSS`
        : def.kind === 'honeypot' ? `${WORLDS[world].sub.toUpperCase()} — SECRET` : `${WORLDS[world].sub.toUpperCase()} — LEVEL ${index + 1}`;
    $('sf-intro-name').textContent = def.name;
    $('sf-intro-desc').textContent = def.desc;
    setHue(WORLDS[world].hue);
}

function startEndless() {
    const pool = [...new Set(WORLDS.flatMap(w => w.pool))].filter(k => !ENEMIES[k].static);
    current = { endless: true };
    level = createLevel({ kind: 'endless', world: 4, pool, tier: 0 }, envFor());
    beginPlay('w4');
    $('sf-intro-kicker').textContent = 'ENDLESS';
    $('sf-intro-name').textContent = 'Threat hunt';
    $('sf-intro-desc').textContent = 'Waves never stop. A boss every 5 waves. How long does your rule hold?';
    setHue(WORLDS[4].hue);
}

function beginPlay(music) {
    screen = current.endless ? 'endless' : 'level';
    closePanels(); paused = false;
    $('sf-maphud').classList.remove('is-open'); $('sf-hud').classList.add('is-open');
    $('sf-intro').classList.add('is-open');
    $('sf-intro-keys').innerHTML = controlsHint();
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();   // Space must not re-click a button
    stage.classList.add('is-playing'); input.setCapture(true);
    stage.classList.toggle('is-mouse', S.settings.controls === 'twin');
    introT = 110;
    buildWeaponsBar();
    updateBossBar(null);
    S.stats.played++; Save.save();
    Music.play(music);
}

function restart() {
    if (!current) return;
    if (current.endless) startEndless(); else startLevel(current.world, current.index);
}

function togglePause(force) {
    if (!level || level.finished) return;
    paused = force ?? !paused;
    if (paused) { $('sf-pause-obj').textContent = level.objective.label || ''; openPanel('sf-pause'); }
    else closePanels();
}
$('sf-pause-resume').addEventListener('click', () => togglePause(false));
$('sf-pause-restart').addEventListener('click', () => restart());
$('sf-pause-quit').addEventListener('click', () => { const endless = current && current.endless; level = null; endless ? showTitle() : showMap(); });

function onLevelEnd(result) {
    const wasEndless = current && current.endless;
    if (!result.won) S.stats.deaths++;
    S.stats.kills += result.kills;
    stage.classList.remove('is-playing');
    if (wasEndless) {
        S.bytes += result.bytes;
        const rank = Save.addEndlessScore(result.score, result.wave);
        $('sf-end-grid').innerHTML = cells([['Score', result.score.toLocaleString()], ['Wave', result.wave], ['Bytes', `+${result.bytes}`],
            ['Kills', result.kills], ['Best combo', result.maxCombo], ['Time', fmtTime(result.time)]]);
        $('sf-end-table').innerHTML = '<tr><th>#</th><th>Score</th><th>Wave</th><th>Date</th></tr>' +
            S.endless.map((e, i) => `<tr class="${i === rank ? 'me' : ''}"><td>${i + 1}</td><td>${e.score.toLocaleString()}</td><td>${e.wave}</td><td>${e.date}</td></tr>`).join('');
        openPanel('sf-endless');
        return;
    }
    const { world, index } = current;
    let info = { newStars: 0, unlockedNow: [], newWeapon: null };
    if (result.won) info = Save.completeLevel(world, index, result);
    else { S.bytes += result.bytes; Save.save(); }

    $('sf-res-title').textContent = result.won ? (index === 4 ? `${BOSSES[WORLDS[world].boss].name} defeated` : 'Level cleared') : result.reason || 'Rule disabled';
    const starsEl = $('sf-res-stars');
    starsEl.innerHTML = [0, 1, 2].map(() => '<i class="fa-solid fa-star"></i>').join('');
    if (result.won) [...starsEl.children].forEach((s, i) => { if (i < result.stars) setTimeout(() => { s.classList.add('on'); Sfx.star(i); }, 350 + i * 380); });
    $('sf-res-crit').innerHTML = result.crit.map(c => `<li class="${c.ok ? 'ok' : 'ko'}"><i class="fa-solid ${c.ok ? 'fa-check' : 'fa-xmark'} me-1"></i>${c.label}</li>`).join('');
    $('sf-res-grid').innerHTML = cells([['Score', result.score.toLocaleString()], ['Bytes', `+${result.bytes}`], ['Time', fmtTime(result.time)],
        ['Kills', result.kills], ['Best combo', result.maxCombo], ['Hits taken', result.hits]]);
    const unlocks = [];
    if (info.newWeapon) unlocks.push(`<i class="fa-solid ${info.newWeapon.icon}"></i> New weapon: ${info.newWeapon.name} — key ${info.newWeapon.key}`);
    if (index === 4 && result.won && world + 1 < WORLDS.length) unlocks.push(`<i class="fa-solid fa-earth-europe"></i> ${WORLDS[world + 1].sub} unlocked: ${WORLDS[world + 1].name}`);
    if (info.unlockedNow.includes(`${world}-5`)) unlocks.push('<i class="fa-solid fa-gem"></i> Secret honeypot found on this world\'s map!');
    if (index === 4 && result.won && world === 4) unlocks.push('<i class="fa-solid fa-trophy"></i> Campaign complete — the graph is quiet. Try Red team, or the endless hunt.');
    if (!result.won) unlocks.push(`<i class="fa-solid fa-microchip"></i> Half of the bytes collected were kept: +${result.bytes}`);
    $('sf-res-unlocks').innerHTML = unlocks.map(u => `<div class="sf-unlock">${u}</div>`).join('');

    const next = nextLevel(world, index);
    $('sf-res-next').style.display = result.won && next ? '' : 'none';
    $('sf-res-next').onclick = () => { S.pos = { world: next[0], node: next[1] }; Save.save(); startLevel(next[0], next[1]); };
    if (result.won && next) { S.pos = { world: next[0], node: next[1] }; Save.save(); }
    openPanel('sf-results');
    if (result.won && index === 4 && world === 4) Sfx.victory();
}
function nextLevel(world, index) {
    if (index < 4) return Save.isUnlocked(world, index + 1) ? [world, index + 1] : null;
    if (index === 4 && world + 1 < WORLDS.length) return [world + 1, 0];
    return null;
}
$('sf-res-retry').addEventListener('click', () => restart());
$('sf-res-map').addEventListener('click', () => showMap());
$('sf-end-retry').addEventListener('click', () => startEndless());
$('sf-end-menu').addEventListener('click', () => showTitle());

const cells = list => list.map(([k, v]) => `<div class="sf-res-cell"><b>${v}</b><span>${k}</span></div>`).join('');
const fmtTime = s => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

// ── Controls hint (intro card, footnote) ───────────────────────────────
function controlsHint() {
    return S.settings.controls === 'twin'
        ? '<kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> move · mouse aims · click fires · <kbd>Shift</kbd> dash · <kbd>E</kbd> bomb'
        : '<kbd>&larr;</kbd><kbd>&rarr;</kbd> turn · <kbd>&uarr;</kbd> thrust · <kbd>&darr;</kbd> brake · <kbd>Space</kbd> fire · <kbd>Shift</kbd> dash · <kbd>E</kbd> bomb';
}
function updateFootnote() {
    $('sf-footnote').innerHTML = controlsHint() + ' · <kbd>1</kbd>–<kbd>4</kbd> / <kbd>Q</kbd> weapons · <kbd>P</kbd> pause · <kbd>M</kbd> mute — change controls in Settings';
}
updateFootnote();

// ── HUD ───────────────────────────────────────────────────────────────
function buildWeaponsBar() {
    const owned = Save.weaponsUnlocked();
    $('sf-hud-weapons').innerHTML = WEAPONS.map(w => `
        <div class="sf-weapon ${owned.includes(w.id) ? '' : 'locked'}" data-w="${w.id}" style="--wc:${w.color}">
            <kbd>${w.key}</kbd><i class="fa-solid ${owned.includes(w.id) ? w.icon : 'fa-lock'}"></i>${owned.includes(w.id) ? w.name : '???'}
        </div>`).join('');
}

let lastCombo = 1;
function updateHud() {
    if (!level) return;
    const h = level.hud();
    $('sf-hud-hp').innerHTML = Array.from({ length: h.maxHp }, (_, i) => `<i class="fa-solid fa-heart ${i < h.hp ? '' : 'off'}"></i>`).join('');
    $('sf-hud-bombs').innerHTML = `<i class="fa-solid fa-bomb"></i>${h.bombs}`;
    $('sf-hud-dash').style.width = `${Math.round(h.dash * 100)}%`;
    $('sf-hud-score').textContent = h.score.toLocaleString();
    $('sf-hud-bytes').textContent = h.bytes;
    const combo = $('sf-hud-combo');
    combo.textContent = h.combo > 1 ? `COMBO x${h.combo}` : '';
    if (h.combo > lastCombo) { combo.classList.remove('pop'); void combo.offsetWidth; combo.classList.add('pop'); }
    lastCombo = h.combo;
    $('sf-hud-obj').textContent = h.objective.label;
    const bar = $('sf-hud-objbar');
    bar.style.display = h.objective.progress === null || h.objective.progress === undefined ? 'none' : '';
    $('sf-hud-objfill').style.width = `${Math.round((h.objective.progress || 0) * 100)}%`;
    const BUFF = { rapid: ['fa-bolt', '#ffd166', 'RAPID', 480], shield: ['fa-shield-halved', '#6ea8ff', 'SHIELD', 600], overclock: ['fa-fire', '#ff6bd8', 'OVERCLOCK', 480] };
    $('sf-hud-buffs').innerHTML = Object.entries(h.buffs).filter(([, v]) => v > 0).map(([k, v]) =>
        `<div class="sf-buff" style="color:${BUFF[k][1]}"><i class="fa-solid ${BUFF[k][0]}"></i>${BUFF[k][2]}<span class="sf-meter"><span style="width:${Math.round(v / BUFF[k][3] * 100)}%"></span></span></div>`).join('')
        + (h.disarmed > 0 ? '<div class="sf-buff" style="color:#ff7a3c"><i class="fa-solid fa-lock"></i>ENCRYPTED</div>' : '');
    document.querySelectorAll('.sf-weapon').forEach(el => {
        el.classList.toggle('active', el.dataset.w === h.weapon);
        el.classList.toggle('disarmed', el.dataset.w === h.weapon && h.disarmed > 0);
    });
}

function updateBossBar(b) {
    const el = $('sf-hud-boss');
    if (!b || b.hp <= 0) { el.classList.remove('is-open'); return; }
    el.classList.add('is-open');
    $('sf-hud-bossname').textContent = b.name + (b.invulnerable ? ' — SHIELDED' : '');
    $('sf-hud-bossfill').style.width = `${Math.max(0, b.hp / b.maxHp * 100)}%`;
}

// ── Hangar ────────────────────────────────────────────────────────────
function renderHangar(tab) {
    $('sf-hangar-bytes').textContent = S.bytes;
    document.querySelectorAll('#sf-hangar-tabs .sf-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    const body = $('sf-hangar-body');
    body.classList.remove('is-text');
    if (tab === 'upgrades') {
        body.innerHTML = UPGRADES.map(u => {
            const lvl = Save.upgradeLevel(u.id), maxed = lvl >= u.max, cost = upgradeCost(u, lvl);
            return `<div class="sf-item">
                <div class="sf-item-icon"><i class="fa-solid ${u.icon}"></i></div>
                <div class="sf-item-body"><b>${u.name}</b><span>${u.desc}</span>
                    <div class="sf-pips">${Array.from({ length: u.max }, (_, i) => `<i class="${i < lvl ? 'on' : ''}"></i>`).join('')}</div>
                    <button class="sf-btn sf-btn--small ${maxed ? '' : 'sf-btn--primary'}" data-buy="${u.id}" ${maxed || S.bytes < cost ? 'disabled' : ''}>
                        ${maxed ? 'Maxed' : `<i class="fa-solid fa-microchip"></i> ${cost}`}</button>
                </div></div>`;
        }).join('');
        body.querySelectorAll('[data-buy]').forEach(b => b.addEventListener('click', () => {
            const u = UPGRADES.find(x => x.id === b.dataset.buy);
            const lvl = Save.upgradeLevel(u.id), cost = upgradeCost(u, lvl);
            if (lvl >= u.max || S.bytes < cost) { Sfx.deny(); return; }
            S.bytes -= cost; S.upgrades[u.id] = lvl + 1; Save.save(); Sfx.buy();
            renderHangar('upgrades'); if (screen === 'map') refreshMapHud();
        }));
    } else if (tab === 'weapons') {
        const owned = Save.weaponsUnlocked();
        body.innerHTML = WEAPONS.map(w => `<div class="sf-item ${owned.includes(w.id) ? '' : 'locked'}">
            <div class="sf-item-icon" style="color:${w.color}"><i class="fa-solid ${owned.includes(w.id) ? w.icon : 'fa-lock'}"></i></div>
            <div class="sf-item-body"><b>${w.name} <kbd>${w.key}</kbd></b><span>${w.desc}</span>
            <span>${owned.includes(w.id) ? 'Unlocked' : `Defeat ${BOSSES[WORLDS[w.unlock].boss].name} (${WORLDS[w.unlock].sub}) to unlock`}</span></div></div>`).join('');
    } else {
        body.innerHTML = SKINS.map(s => `<div class="sf-item ${s.id === S.skin ? 'selected' : ''}" data-skin="${s.id}" style="cursor:pointer">
            <div class="sf-swatch" style="--hull:${s.hull};--glow:${s.glow}"></div>
            <div class="sf-item-body"><b>${s.name}</b><span>${s.id === S.skin ? 'Equipped' : 'Click to equip'}</span></div></div>`).join('');
        body.querySelectorAll('[data-skin]').forEach(el => el.addEventListener('click', () => { S.skin = el.dataset.skin; Save.save(); Sfx.buy(); renderHangar('skins'); }));
    }
}
document.querySelectorAll('#sf-hangar-tabs .sf-tab').forEach(b => b.addEventListener('click', () => { Sfx.move(); renderHangar(b.dataset.tab); }));

// ── Help ──────────────────────────────────────────────────────────────
const BESTIARY = {
    worm: 'Crawls towards you and splits into two wormlets when destroyed.',
    spammer: 'Keeps its distance and sprays five-way bursts.',
    trojan: 'Looks exactly like a heal pickup — until you get close. Then it charges.',
    phisher: 'Throws hooks: if one lands, you are dragged towards it.',
    drone: 'Swarms in numbers. Fragile alone, deadly together.',
    botnet: 'A static C2 node that keeps producing bots. Take it down first.',
    miner: 'Avoids you and eats the bytes you collected while it lives.',
    locker: 'Shielded at the front (shoot its back or use the Sigma Rail). Its touch encrypts your weapon.',
    mine: 'Arms when you come near and blows up after a short fuse.',
    keylogger: 'Nearly invisible. Shows itself only when lining up a sniper shot.',
    rootkit: 'Burrows, pops up next to you with a ring of bullets, then hides again. Hit it while surfaced.',
    apt: 'An elite operator: strafes, dodges your shots and fires precise bursts.',
    wiper: 'Rushes you and detonates — keep moving.',
    beacon: 'A command-and-control beacon calling reinforcements. Objective target.',
};
function renderHelp(tab) {
    document.querySelectorAll('#sf-help-tabs .sf-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    const body = $('sf-help-body');
    if (tab === 'bestiary') {
        body.classList.remove('is-text');
        body.innerHTML = Object.entries(BESTIARY).map(([k, d]) => `<div class="sf-item">
            <div class="sf-item-icon" style="color:${ENEMIES[k].color}"><i class="fa-solid fa-${({ worm: 'bug', spammer: 'envelope', trojan: 'gift', phisher: 'fish', drone: 'robot', botnet: 'network-wired', miner: 'coins', locker: 'lock', mine: 'bomb', keylogger: 'keyboard', rootkit: 'microchip', apt: 'user-secret', wiper: 'biohazard', beacon: 'satellite' })[k]}"></i></div>
            <div class="sf-item-body"><b>${ENEMIES[k].name}</b><span>${d}</span></div></div>`).join('');
        return;
    }
    body.classList.add('is-text');
    if (tab === 'controls') {
        body.innerHTML = `<div class="sf-help-section">
            <p>You are a detection rule deployed into the graph. Five worlds of malware stand between you and the zero-day.</p>
            <h3>Classic controls (default — keyboard only)</h3>
            <div class="sf-controls">
                <span><kbd>&larr;</kbd><kbd>&rarr;</kbd> or <kbd>A</kbd><kbd>D</kbd></span><span>Turn</span>
                <span><kbd>&uarr;</kbd> or <kbd>W</kbd></span><span>Thrust forward (the ship keeps its momentum)</span>
                <span><kbd>&darr;</kbd> or <kbd>S</kbd></span><span>Brake</span>
                <span><kbd>Space</kbd></span><span>Fire straight ahead (hold)</span>
            </div>
            <h3>Twin-stick controls (Settings → Controls)</h3>
            <div class="sf-controls">
                <span><kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> / arrows</span><span>Move in that direction</span>
                <span>Mouse</span><span>Aim — click or <kbd>Space</kbd> to fire, right-click to dash</span>
            </div>
            <h3>Both</h3>
            <div class="sf-controls">
                <span><kbd>Shift</kbd></span><span>Dash — a quick burst, invulnerable while dashing</span>
                <span><kbd>E</kbd></span><span>Quarantine bomb — clears every bullet on screen and hurts everything</span>
                <span><kbd>1</kbd>–<kbd>4</kbd> / <kbd>Q</kbd></span><span>Switch weapon</span>
                <span><kbd>P</kbd> / <kbd>Esc</kbd></span><span>Pause</span>
                <span><kbd>M</kbd></span><span>Sound on / off</span>
                <span>Gamepad</span><span>Left stick turn/thrust (classic) or move (twin) · right stick aim · RT fire · A dash · B bomb · LB/RB weapons</span>
            </div>
            <h3>Progress</h3>
            <p>Bytes dropped by malware are spent in the hangar. Each world boss unlocks a new weapon and the next world.
            Get 10 stars in a world to reveal its secret honeypot. Kill fast to build a combo (up to x8).</p></div>`;
    } else {
        body.innerHTML = `<div class="sf-help-section">
            <h3>Objectives</h3><ul>
                <li><b>Waves</b> — clear every wave.</li>
                <li><b>Survive</b> — hold out until the timer runs out.</li>
                <li><b>Cut the C2</b> — destroy every beacon; they keep calling reinforcements.</li>
                <li><b>Protect</b> — keep the network sensor alive until the scan completes. Malware goes for it too.</li>
                <li><b>Boss</b> — three phases each. Watch the dashed lines and red sectors: they are attacks about to land.</li>
                <li><b>Honeypot</b> (secret) — 45 seconds, triple bytes.</li></ul>
            <h3>Stars</h3><ul>
                <li>★ Complete the level.</li><li>★ Take 2 hits or fewer (3 against a boss).</li>
                <li>★ Beat the par time — or take no hit (survive), keep the sensor above 70% (protect), collect enough bytes (honeypot).</li></ul>
            <h3>Pickups</h3><ul>
                <li><i class="fa-solid fa-heart" style="color:#ff5d73"></i> +1 integrity · <i class="fa-solid fa-bolt" style="color:#ffd166"></i> rapid fire ·
                <i class="fa-solid fa-shield-halved" style="color:#6ea8ff"></i> shield (absorbs a hit) · <i class="fa-solid fa-fire" style="color:#ff6bd8"></i> overclock (double damage) ·
                <i class="fa-solid fa-bomb" style="color:#ff9f43"></i> +1 bomb</li>
                <li>Beware: a heart that wobbles a little too much might be a trojan.</li></ul></div>`;
    }
}
document.querySelectorAll('#sf-help-tabs .sf-tab').forEach(b => b.addEventListener('click', () => { Sfx.move(); renderHelp(b.dataset.tab); }));

// ── Settings ──────────────────────────────────────────────────────────
function renderSettings() {
    const sw = (key, label, invert = false) => {
        const on = invert ? !S.settings[key] : S.settings[key] !== false;
        return `<div class="sf-setting"><span>${label}</span><button class="sf-switch ${on ? 'on' : ''}" data-set="${key}" data-invert="${invert ? 1 : 0}"></button></div>`;
    };
    const assistOn = S.settings.assist === true;
    $('sf-settings-list').innerHTML = sw('muted', 'Sound', true) + sw('music', 'Music') + sw('shake', 'Screen shake')
        + `<div class="sf-setting"><span>Controls</span><select id="sf-set-controls">
              <option value="classic" ${S.settings.controls !== 'twin' ? 'selected' : ''}>Classic — arrows only (turn &amp; thrust)</option>
              <option value="twin" ${S.settings.controls === 'twin' ? 'selected' : ''}>Twin-stick — WASD move, mouse aims</option></select></div>`
        + (S.settings.controls === 'twin' ? `<div class="sf-setting"><span>Auto-aim when the mouse isn't used</span><button class="sf-switch ${assistOn ? 'on' : ''}" data-set="assist"></button></div>` : '')
        + `<div class="sf-setting"><span>Audio engine: <b id="sf-audio-state">${Audio.status()}</b>${S.settings.muted ? ' (muted)' : ''}</span><button class="sf-btn sf-btn--small" id="sf-audio-test"><i class="fa-solid fa-volume-high"></i> Test sound</button></div>`
        + `<div class="sf-setting"><span>Difficulty</span><select id="sf-set-diff">${DIFFICULTIES.map(d => `<option value="${d.id}" ${d.id === S.difficulty ? 'selected' : ''}>${d.name}</option>`).join('')}</select></div>`;
    $('sf-settings-list').querySelectorAll('[data-set]').forEach(b => b.addEventListener('click', () => {
        const key = b.dataset.set;
        if (key === 'muted') S.settings.muted = !S.settings.muted;
        else if (key === 'assist') S.settings.assist = S.settings.assist !== true;
        else S.settings[key] = S.settings[key] === false;
        applySettings(); Save.save(); renderSettings(); Sfx.move();
    }));
    $('sf-set-diff').addEventListener('change', e => { S.difficulty = e.target.value; Save.save(); });
    $('sf-audio-test').addEventListener('click', async () => {
        if (S.settings.muted) { S.settings.muted = false; applySettings(); Save.save(); }
        const state = await Audio.test();
        $('sf-audio-state').textContent = state;
        toast(state === 'running' ? 'You should hear two beeps. Nothing? Check the tab / system volume.'
            : state === 'unsupported' ? 'This browser has no Web Audio.' : `The browser keeps audio ${state} — click the page once more.`);
    });
    $('sf-set-controls').addEventListener('change', e => { S.settings.controls = e.target.value; Save.save(); renderSettings(); updateFootnote(); });
}
function applySettings() {
    Audio.setMuted(!!S.settings.muted);
    Music.setEnabled(S.settings.music !== false);
    $('sf-btn-mute').innerHTML = `<i class="fa-solid ${S.settings.muted ? 'fa-volume-xmark' : 'fa-volume-high'}"></i>`;
}
$('sf-reset').addEventListener('click', () => {
    if (!confirm('Erase every star, byte, upgrade and score? This cannot be undone.')) return;
    Save.reset(); applySettings(); showTitle();
});
$('sf-btn-mute').addEventListener('click', () => { S.settings.muted = !S.settings.muted; applySettings(); Save.save(); });
$('sf-btn-full').addEventListener('click', () => {
    const p = document.fullscreenElement ? document.exitFullscreen() : (stage.requestFullscreen ? stage.requestFullscreen() : null);
    if (p && p.catch) p.catch(() => {});
});
applySettings();

// ── Loop: fixed 60 Hz updates, render every frame ─────────────────────
function update() {
    t++;
    input.frame();
    if (input.hit('KeyM')) { S.settings.muted = !S.settings.muted; applySettings(); Save.save(); }
    const pad = input.state.pad;

    if (screen === 'map' && !overlay) {
        map.update();
        if (input.hit('ArrowRight', 'KeyD', 'ArrowDown', 'KeyS') || (pad && (pad.right || pad.down))) map.step(1);
        if (input.hit('ArrowLeft', 'KeyA', 'ArrowUp', 'KeyW') || (pad && (pad.left || pad.up))) map.step(-1);
        if (input.hit('PageDown', 'KeyE')) map.changeWorld(map.world + 1, 0);
        if (input.hit('PageUp', 'KeyQ')) map.changeWorld(map.world - 1, 4);
        if ((input.hit('Enter', 'Space') || (pad && pad.confirm)) && map.canPlay()) { startLevel(map.world, map.node); }
        else if (input.hit('KeyH')) { renderHangar('upgrades'); openPanel('sf-hangar', 'map'); }
        else if (input.hit('Escape') || (pad && pad.back)) showTitle();
        const r = map.pointer(input.state.mx, input.state.my, input.hit('Mouse0'));
        if (r === 'play' && map.canPlay()) startLevel(map.world, map.node);
        if (t % 10 === 0 && !map.moving) refreshMapHud();
    } else if (screen === 'map' && overlay && input.hit('Escape')) goBack();
    else if ((screen === 'level' || screen === 'endless') && level) {
        if (input.hit('KeyP', 'Escape') || (pad && pad.pause)) togglePause();
        if (!paused) {
            if (introT > 0) { introT--; if (introT === 0) $('sf-intro').classList.remove('is-open'); }
            else level.update(input);
            if (t % 3 === 0) updateHud();
        }
    } else if (screen === 'title' && overlay && overlay !== 'sf-title' && input.hit('Escape')) goBack();

    drift.x += 0.25; drift.y += 0.08;
    if (level && level.player && !paused) { drift.x += level.player.vx * 0.3; drift.y += level.player.vy * 0.3; }
    input.endFrame();
}

function render() {
    const { scale, ox, oy, dpr } = view;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = '#02030a'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(dpr * scale, 0, 0, dpr * scale, dpr * ox, dpr * oy);
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, W, H); ctx.clip();
    const world = level ? (level.world ?? 0) : screen === 'map' ? map.world : 0;
    drawBackground(ctx, stars, t * 16, WORLDS[world], drift, bgImage);
    if (screen === 'map') map.draw(ctx, skin());
    else if (level) level.draw(ctx);
    else {
        // title: the rule ship drifting through the field
        drawShip(ctx, W / 2 + Math.sin(t * 0.01) * 300, H / 2 + 170 + Math.sin(t * 0.023) * 30, -Math.PI / 2 + Math.sin(t * 0.01) * 0.3, skin(), { thrust: 1, t, scale: 1.6 });
    }
    ctx.restore();
}

let acc = 0, lastTs = 0;
function frame(ts) {
    if (!lastTs) lastTs = ts;
    acc += Math.min(100, ts - lastTs); lastTs = ts;
    let steps = 0;
    while (acc >= 1000 / 60 && steps < 4) { update(); acc -= 1000 / 60; steps++; }
    if (steps === 4) acc = 0;          // too slow to catch up: drop the backlog instead of spiralling
    render();
    requestAnimationFrame(frame);
}

// A clicked button keeps the focus: drop it, so the keyboard stays with the game
stage.addEventListener('click', e => { const b = e.target.closest('button'); if (b) setTimeout(() => b.blur(), 0); });

// Audio may only start after a user gesture — unlock it on the first one
['pointerdown', 'keydown'].forEach(ev => window.addEventListener(ev, () => Audio.unlock(), { capture: true }));

// Pause automatically when the tab is hidden
document.addEventListener('visibilitychange', () => {
    Music.sleep(document.hidden);
    if (document.hidden && level && !level.finished && !paused) togglePause(true);
});

showTitle();
requestAnimationFrame(frame);
