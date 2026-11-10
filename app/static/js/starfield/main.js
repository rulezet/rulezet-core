/**
 * main.js — Starfield's entry point: the screens (title, map, level,
 * hangar, results…), the fixed-step game loop, the HTML HUD and the glue
 * between the save, the map and the running level.
 */
import { W, H, WORLDS, WEAPONS, UPGRADES, SKINS, DIFFICULTIES, ENEMIES, BOSSES, KEY_ACTIONS, RESERVED_KEYS, PICKUPS, ACT2_FIRST_WORLD, levelDef, levelKey, upgradeCost } from './data.js';
import { actText, levelStory, STORY_KEYS } from './story.js';
import * as Save from './save.js';
import { Sfx, Music, Audio } from './audio.js';
import { createInput, normalizeKey, PAD_ACTIONS, PAD_LAYOUTS, PAD_LAYOUT_NAMES, padFamily, padShortName } from './input.js';
import { tr, setLang, getLang, defaultLang, localizeData, localizeDom } from './i18n.js';
import { makeStars, drawBackground, drawShip, GFX } from './render.js';
import { createMap } from './worldmap.js';
import { createLevel } from './level.js';
import { reportRun } from './report.js';

const $ = id => document.getElementById(id);
const stage = $('sf-stage');
const canvas = $('sf-canvas');
const ctx = canvas.getContext('2d');
const input = createInput(canvas);
const bgImage = new Image();
bgImage.src = stage.dataset.bg;

const S = Save.load();
if (!S.settings.lang) S.settings.lang = defaultLang();
setLang(S.settings.lang);
localizeData([WORLDS, WEAPONS, UPGRADES, SKINS, DIFFICULTIES, ENEMIES, BOSSES, KEY_ACTIONS, PICKUPS]);
localizeDom(stage);
$('sf-shoutout').hidden = getLang() !== 'fr';      // a little message for the French players
Audio.setMuted(!!S.settings.muted);
Music.setEnabled(S.settings.music !== false);
input.setKeys(S.settings.keys);
input.setPad(S.settings.pad);
Audio.setVolumes(S.settings.volume);
GFX.low = S.settings.quality === 'low';

// ── Key labels (bindings are configurable in Settings → Keys) ─────────
const KEY_NAMES = { ArrowUp: '↑', ArrowDown: '↓', ArrowLeft: '←', ArrowRight: '→', Space: 'Space', ShiftLeft: 'Shift',
    ControlLeft: 'Ctrl', AltLeft: 'Alt', MetaLeft: 'Meta', Enter: 'Enter', Tab: 'Tab', Backquote: '`', Minus: '-', Equal: '=',
    BracketLeft: '[', BracketRight: ']', Semicolon: ';', Quote: "'", Comma: ',', Period: '.', Slash: '/', Backslash: '\\' };
// Bindings store the physical key (e.code); the label follows the real
// layout when the browser tells it (AZERTY: KeyW is labelled Z).
let layout = null;
if (navigator.keyboard && navigator.keyboard.getLayoutMap) {
    navigator.keyboard.getLayoutMap().then(m => { layout = m; updateFootnote(); }).catch(() => {});
}
// Browsers without getLayoutMap (Firefox): learn each label when the key is pressed
const seenKeys = {};
window.addEventListener('keydown', e => { if (e.key && e.key.length === 1 && e.key !== ' ') seenKeys[normalizeKey(e.code)] = e.key.toUpperCase(); }, { capture: true });
function keyName(code) {
    if (!code) return '—';
    if (KEY_NAMES[code]) return KEY_NAMES[code];
    if (layout && layout.get(code)) return layout.get(code).toUpperCase();
    if (seenKeys[code]) return seenKeys[code];
    return code.replace(/^Key/, '').replace(/^Digit/, '').replace(/^Numpad/, 'Num ');
}
// ── Gamepad labels: the controller's own button names (Xbox / PlayStation / Nintendo) ──
const padLayout = () => (S.settings.pad.layout && S.settings.pad.layout !== 'auto' ? S.settings.pad.layout : padFamily(input.state.padId));
const padName = i => ((PAD_LAYOUTS[padLayout()] || PAD_LAYOUTS.xbox)[i] ?? `#${i}`);
const pbtn = i => `<kbd class="sf-pad sf-pad--${padLayout()} sf-pad-b${i}">${padName(i)}</kbd>`;
const usingPad = () => input.state.lastDevice === 'pad' && input.state.padConnected;
// keyboard action → gamepad action
const KEY_TO_PAD = { fire: 'fire', dash: 'dash', bomb: 'bomb', special: 'special', weapon: 'next', pause: 'pause' };

/** <kbd> of the keys bound to an action (first one, or both with all=true) — the controller button when playing with one */
function kbd(action, all = false) {
    if (usingPad() && KEY_TO_PAD[action]) return pbtn(S.settings.pad.map[KEY_TO_PAD[action]]);
    const ks = (S.settings.keys[action] || []).filter(Boolean);
    if (!ks.length) return '<kbd>—</kbd>';
    return (all ? ks : ks.slice(0, 1)).map(k => `<kbd>${keyName(k)}</kbd>`).join(' / ');
}

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
const PANELS = ['sf-title', 'sf-difficulty', 'sf-pause', 'sf-results', 'sf-endless', 'sf-hangar', 'sf-help', 'sf-settings', 'sf-story', 'sf-confirm'];
let backTo = null;
function openPanel(id, back = null) {
    PANELS.forEach(p => $(p).classList.toggle('is-open', p === id));
    overlay = id; backTo = back;
    setNav(null);
    refreshPadHint();
}
function closePanels() { PANELS.forEach(p => $(p).classList.remove('is-open')); overlay = null; setNav(null); refreshPadHint(); }

// ── An in-game "are you sure?" (browser dialogs can't be answered with a controller) ──
let confirmCtx = null;
function askConfirm(text, onYes, yesLabel = 'Yes') {
    confirmCtx = { onYes, prev: overlay, prevBack: backTo };
    $('sf-confirm-text').textContent = text;
    $('sf-confirm-yes').innerHTML = `<i class="fa-solid fa-check"></i> ${tr(yesLabel)}`;
    openPanel('sf-confirm');
    Sfx.telegraph();
}
function confirmNo() {
    const c = confirmCtx; confirmCtx = null; Sfx.move();
    if (c && c.prev) openPanel(c.prev, c.prevBack); else showTitle();
}
$('sf-confirm-no').addEventListener('click', () => confirmNo());
$('sf-confirm-yes').addEventListener('click', () => { const c = confirmCtx; confirmCtx = null; if (c) c.onYes(); });
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
    stage.classList.remove('is-playing'); input.setCapture(true);
    openPanel('sf-title');
    const tw = titleWorld();
    setHue(WORLDS[tw].hue);
    $('sf-title-world').innerHTML = (Object.keys(S.stars).length || S.pos.world > 0)
        ? `<i class="fa-solid fa-location-dot"></i> ${WORLDS[tw].sub} · <b>${WORLDS[tw].name}</b>${S.pos.world >= ACT2_FIRST_WORLD ? ` · <span class="sf-title-act">${tr('ACT II')}</span>` : ''}` : '';
    const started = Object.keys(S.stars).length > 0 || S.pos.world > 0 || S.pos.node > 0;
    $('sf-btn-continue').style.display = started ? '' : 'none';
    $('sf-btn-new').classList.toggle('sf-btn--primary', !started);
    const best = S.endless[0] ? S.endless[0].score.toLocaleString() : '—';
    $('sf-title-stats').innerHTML = `
        <span><i class="fa-solid fa-star" style="color:#ffd166"></i> <b>${Save.totalStars()}</b> ${tr('stars')}</span>
        <span><i class="fa-solid fa-skull"></i> <b>${S.bosses.length}</b>/${WORLDS.length} ${tr('bosses')}</span>
        <span><i class="fa-solid fa-rocket" style="color:#c9a7ff"></i> <b>${Save.shipsUnlocked().length}</b>/${SKINS.length} ${tr('ships')}</span>
        <span><i class="fa-solid fa-microchip" style="color:#5be7ff"></i> <b>${S.bytes}</b> ${tr('bytes')}</span>
        <span><i class="fa-solid fa-infinity"></i> ${tr('best hunt')} <b>${best}</b></span>`;
    Music.play('map');
}

const titleWorld = () => Math.max(0, Math.min(WORLDS.length - 1, S.pos.world || 0));
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
        const go = () => {
            S.difficulty = b.dataset.diff;
            S.unlocked = { '0-0': true }; S.stars = {}; S.best = {}; S.pos = { world: 0, node: 0 };
            Save.save();
            Sfx.levelUp(); closePanels(); showMap();
        };
        if (Object.keys(S.stars).length > 0) askConfirm(tr('Start a new campaign? Map progress and stars are reset; bytes, upgrades and weapons are kept.'), go, 'Start over');
        else go();
    }));
}

// ── Map ───────────────────────────────────────────────────────────────
map.onWorldChange = w => {
    S.pos = { world: w, node: map.node }; Save.save(); refreshMapHud(); toast(`${WORLDS[w].sub} — ${WORLDS[w].name}`);
    if (w >= ACT2_FIRST_WORLD && !S.seenAct2) { S.seenAct2 = true; Save.save(); showStory('act2', 'map'); }
};

/** A story card (act break): title, text, a Continue button back to where we were */
function showStory(key, back) {
    const a = actText(key);
    if (!a) return;
    $('sf-story-title').textContent = a.title;
    $('sf-story-text').textContent = a.text;
    openPanel('sf-story', back);
    Sfx.levelUp();
}
$('sf-story-ok').addEventListener('click', () => goBack());
map.onArrive = node => { S.pos = { world: map.world, node }; Save.save(); refreshMapHud(); };

function showMap() {
    screen = 'map'; level = null; current = null; paused = false;
    introT = 0; $('sf-intro').classList.remove('is-open');
    closePanels();
    $('sf-hud').classList.remove('is-open'); $('sf-maphud').classList.add('is-open');
    stage.classList.remove('is-playing'); input.setCapture(true);
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    map.galaxy = false;
    map.enter(Math.min(S.pos.world, WORLDS.length - 1), S.pos.node);
    refreshMapHud();
    Music.play('map');
    if (map.world >= ACT2_FIRST_WORLD && !S.seenAct2) { S.seenAct2 = true; Save.save(); showStory('act2', 'map'); }
}

const KIND_LABEL = { waves: 'WAVES', survive: 'SURVIVE', beacons: 'CUT THE C2', protect: 'PROTECT', boss: 'BOSS', honeypot: 'BONUS',
    keys: 'FIND THE KEYS', escort: 'ESCORT', capture: 'CAPTURE', pursuit: 'PURSUIT', dark: 'BLACKOUT', purge: 'PURGE',
    gauntlet: 'GAUNTLET', triage: 'TRIAGE', defend: 'DEFEND' };
const MOD_LABEL = { storm: ['fa-wind', 'Ion storm'], dark: ['fa-eye-slash', 'Darkness'], rocks: ['fa-meteor', 'Asteroids'], mines: ['fa-bomb', 'Minefield'] };
function levelTags(def) {
    const tags = [];
    if (def.open) tags.push(`<span class="sf-tag"><i class="fa-solid fa-up-down-left-right"></i>${tr('Open space')}</span>`);
    for (const [k, v] of Object.entries(def.mods || {})) if (v && MOD_LABEL[k]) tags.push(`<span class="sf-tag"><i class="fa-solid ${MOD_LABEL[k][0]}"></i>${tr(MOD_LABEL[k][1])}</span>`);
    return tags.join('');
}
function refreshMapHud() {
    const w = WORLDS[map.world];
    $('sf-maphud').classList.toggle('is-galaxy', !!map.galaxy);
    setHue(w.hue);
    $('sf-world-sub').textContent = w.sub;
    $('sf-world-name').textContent = w.name;
    $('sf-world-story').textContent = w.story;
    $('sf-map-wstars').textContent = Save.worldStars(map.world);
    $('sf-map-bytes').textContent = S.bytes;
    const { world, index, def } = map.selected();
    const kind = $('sf-lc-kind');
    kind.textContent = tr(KIND_LABEL[def.kind]);
    kind.className = 'sf-kind' + (def.kind === 'boss' ? ' sf-kind--boss' : def.kind === 'honeypot' ? ' sf-kind--honeypot' : '');
    const st = Save.starsOf(world, index);
    $('sf-lc-stars').innerHTML = [0, 1, 2].map(i => `<i class="fa-solid fa-star ${i < st ? 'on' : ''}"></i>`).join('');
    $('sf-lc-name').textContent = (index < 4 ? `${index + 1}. ` : '') + def.name;
    $('sf-lc-desc').textContent = def.kind === 'boss' ? BOSSES[def.boss].intro : def.desc;
    $('sf-lc-brief').textContent = def.brief || '';
    $('sf-lc-tags').innerHTML = levelTags(def);
    const best = S.best[`${world}-${index}`];
    $('sf-lc-best').textContent = best ? tr('Best score {n}', { n: best.toLocaleString() }) : tr('Not cleared yet');
    $('sf-lc-play').disabled = !map.canPlay();
}
$('sf-lc-play').addEventListener('click', () => { if (map.canPlay()) startLevel(map.world, map.node); });
$('sf-map-hangar').addEventListener('click', () => { renderHangar('upgrades'); openPanel('sf-hangar', 'map'); });
$('sf-map-menu').addEventListener('click', () => showTitle());
$('sf-map-galaxy').addEventListener('click', () => { if (screen === 'map') { closePanels(); map.openGalaxy(); refreshMapHud(); } });

// ── Levels ────────────────────────────────────────────────────────────
function envFor() {
    return {
        skin: skin(), upgrades: S.upgrades, weapons: Save.weaponsUnlocked(), diff: diff(), settings: S.settings,
        callbacks: { onEnd: onLevelEnd, onBoss: updateBossBar, rumble: (a, b, ms) => input.rumble(a, b, ms) },
    };
}

function startLevel(world, index) {
    Audio.unlock();
    const def = levelDef(world, index);
    current = { world, index };
    level = createLevel(def, envFor());
    beginPlay(def.kind === 'boss' ? (world === 4 ? 'final' : 'boss') : `w${world}`);
    $('sf-intro-kicker').textContent = def.kind === 'boss' ? `${WORLDS[world].sub.toUpperCase()} — ${tr('BOSS')}`
        : def.kind === 'honeypot' ? `${WORLDS[world].sub.toUpperCase()} — ${tr('SECRET')}` : `${WORLDS[world].sub.toUpperCase()} — ${tr('LEVEL {n}', { n: index + 1 })}`;
    $('sf-intro-name').textContent = def.name;
    $('sf-intro-desc').textContent = def.desc;
    $('sf-intro-brief').textContent = def.brief || '';
    $('sf-intro-tags').innerHTML = levelTags(def);
    // the first time, the briefing waits for the pilot
    const key = levelKey(world, index);
    if (world >= ACT2_FIRST_WORLD) S.seenAct2 = true;     // the first briefing of Act II tells the act break itself
    briefWait = !!def.brief && !S.briefed[key];
    if (briefWait) { introT = 1; S.briefed[key] = true; Save.save(); }
    $('sf-intro-go').hidden = !briefWait;
    $('sf-intro-go').innerHTML = `${usingPad() ? pbtn(0) : `${kbd('fire')} / <kbd>Enter</kbd>`} ${tr('launch')}`;
    setHue(WORLDS[world].hue);
}
let briefWait = false;

function startEndless() {
    const pool = [...new Set(WORLDS.flatMap(w => w.pool))].filter(k => !ENEMIES[k].static);
    current = { endless: true };
    level = createLevel({ kind: 'endless', world: 4, pool, tier: 0 }, envFor());
    beginPlay('w4');
    $('sf-intro-kicker').textContent = tr('ENDLESS');
    $('sf-intro-name').textContent = tr('Threat hunt');
    $('sf-intro-desc').textContent = tr('Waves never stop. A boss every 5 waves. How long does your rule hold?');
    $('sf-intro-brief').textContent = '';
    $('sf-intro-tags').innerHTML = '';
    $('sf-intro-go').hidden = true;
    briefWait = false;
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
    briefWait = false;
    if (current.endless) startEndless(); else startLevel(current.world, current.index);
}

function togglePause(force) {
    if (!level || level.finished) return;
    paused = force ?? !paused;
    if (paused) { fillPause(); openPanel('sf-pause'); }
    else closePanels();
}
function fillPause() {
    const def = level.def || {};
    const w = WORLDS[level.world ?? 0];
    $('sf-pause-where').innerHTML = current && current.endless ? `<i class="fa-solid fa-infinity"></i> ${tr('Threat hunt')}`
        : `<span style="color:${w.hue}">${w.sub} · ${w.name}</span> — <b>${def.name || ''}</b>`;
    $('sf-pause-obj').textContent = level.objective.label || '';
    $('sf-pause-stats').innerHTML = cells([['Time', fmtTime(Math.round(level.t / 60))], ['Score', level.score.toLocaleString()],
        ['Kills', level.kills], ['Bytes', level.levelBytes]]);
    $('sf-pause-controls').innerHTML = controlsHint();
}
$('sf-pause-resume').addEventListener('click', () => togglePause(false));
$('sf-pause-settings').addEventListener('click', () => { Sfx.move(); renderSettings(); openPanel('sf-settings', 'pause'); });
$('sf-pause-restart').addEventListener('click', () => restart());
$('sf-pause-quit').addEventListener('click', () => { const endless = current && current.endless; level = null; endless ? showTitle() : showMap(); });

// Everything about a finished run, for the admin score tracking (report.js).
function runReport(result, extra) {
    return {
        won: result.won, reason: result.reason || null, score: result.score, stars: result.stars,
        crit: result.crit || [], wave: result.wave, kills: result.kills, hits: result.hits, maxCombo: result.maxCombo,
        bytes: result.bytes, time: result.time, hpLeft: result.hpLeft, maxHp: result.maxHp, bombsLeft: result.bombsLeft,
        bossName: result.bossName, stats: result.stats,
        ship: S.skin, difficulty: S.difficulty, controls: S.settings.controls, assist: !!S.settings.assist,
        upgrades: S.upgrades, weapons: Save.weaponsUnlocked(),
        campaignStars: Object.values(S.stars || {}).reduce((a, b) => a + b, 0), campaignBytes: S.bytes,
        ...extra,
    };
}

function onLevelEnd(result) {
    const wasEndless = current && current.endless;
    if (wasEndless) {
        reportRun(runReport(result, { mode: 'endless', levelName: 'Threat hunt', levelKind: 'endless' }));
    } else if (current) {
        const def = levelDef(current.world, current.index);
        reportRun(runReport(result, {
            mode: 'level', world: current.world, levelIndex: current.index,
            levelName: def.name, levelKind: def.kind,
        }));
    }
    if (!result.won) S.stats.deaths++;
    S.stats.kills += result.kills;
    stage.classList.remove('is-playing');
    if (wasEndless) {
        S.bytes += result.bytes;
        const rank = Save.addEndlessScore(result.score, result.wave);
        $('sf-end-grid').innerHTML = cells([['Score', result.score.toLocaleString()], ['Wave', result.wave], ['Bytes', `+${result.bytes}`],
            ['Kills', result.kills], ['Best combo', result.maxCombo], ['Time', fmtTime(result.time)]]);
        $('sf-end-table').innerHTML = `<tr><th>#</th><th>${tr('Score')}</th><th>${tr('Wave')}</th><th>${tr('Date')}</th></tr>` +
            S.endless.map((e, i) => `<tr class="${i === rank ? 'me' : ''}"><td>${i + 1}</td><td>${e.score.toLocaleString()}</td><td>${e.wave}</td><td>${e.date}</td></tr>`).join('');
        openPanel('sf-endless');
        return;
    }
    const { world, index } = current;
    let info = { newStars: 0, unlockedNow: [], newWeapon: null };
    if (result.won) info = Save.completeLevel(world, index, result);
    else { S.bytes += result.bytes; Save.save(); }

    $('sf-res-title').textContent = result.won ? (index === 4 ? tr('{name} defeated', { name: BOSSES[WORLDS[world].boss].name }) : tr('Level cleared')) : result.reason || tr('Rule disabled');
    const starsEl = $('sf-res-stars');
    starsEl.innerHTML = [0, 1, 2].map(() => '<i class="fa-solid fa-star"></i>').join('');
    if (result.won) [...starsEl.children].forEach((s, i) => { if (i < result.stars) setTimeout(() => { s.classList.add('on'); Sfx.star(i); }, 350 + i * 380); });
    $('sf-res-crit').innerHTML = result.crit.map(c => `<li class="${c.ok ? 'ok' : 'ko'}"><i class="fa-solid ${c.ok ? 'fa-check' : 'fa-xmark'} me-1"></i>${c.label}</li>`).join('');
    $('sf-res-grid').innerHTML = cells([['Score', result.score.toLocaleString()], ['Bytes', `+${result.bytes}`], ['Time', fmtTime(result.time)],
        ['Kills', result.kills], ['Best combo', result.maxCombo], ['Hits taken', result.hits]]);
    const unlocks = [];
    if (info.newWeapon) unlocks.push(`<i class="fa-solid ${info.newWeapon.icon}"></i> ${tr('New weapon: {name} — key {key}', { name: info.newWeapon.name, key: info.newWeapon.key })}`);
    if (index === 4 && result.won && world + 1 < WORLDS.length) unlocks.push(`<i class="fa-solid fa-earth-europe"></i> ${tr('{sub} unlocked: {name}', { sub: WORLDS[world + 1].sub, name: WORLDS[world + 1].name })}`);
    if (info.newShip) unlocks.push(`<i class="fa-solid fa-rocket"></i> ${tr('New ship: {name} — {power} (Hangar → Rule engine)', { name: info.newShip.name, power: info.newShip.special.name })}`);
    if (info.unlockedNow.includes(`${world}-5`)) unlocks.push(`<i class="fa-solid fa-gem"></i> ${tr('Secret honeypot found on this world\'s map!')}`);
    if (index === 4 && result.won && world === ACT2_FIRST_WORLD - 1) unlocks.push(`<i class="fa-solid fa-book-open"></i> ${tr('Act I complete — but the Zero-Day was only a scout. Act II, the Deep Graph, is open.')}`);
    if (index === 4 && result.won && world === WORLDS.length - 1) unlocks.push(`<i class="fa-solid fa-trophy"></i> ${tr('Campaign complete — the graph is quiet. Try Red team, or the endless hunt.')}`);
    if (!result.won) unlocks.push(`<i class="fa-solid fa-microchip"></i> ${tr('Half of the bytes collected were kept: +{n}', { n: result.bytes })}`);
    $('sf-res-unlocks').innerHTML = unlocks.map(u => `<div class="sf-unlock">${u}</div>`).join('');
    const ldef = levelDef(world, index);
    $('sf-res-outro').textContent = result.won && ldef.outro ? ldef.outro : '';
    $('sf-res-outro').hidden = !(result.won && ldef.outro);

    const next = nextLevel(world, index);
    $('sf-res-next').style.display = result.won && next ? '' : 'none';
    $('sf-res-next').onclick = () => { S.pos = { world: next[0], node: next[1] }; Save.save(); startLevel(next[0], next[1]); };
    if (result.won && next) { S.pos = { world: next[0], node: next[1] }; Save.save(); }
    openPanel('sf-results');
    if (result.won && index === 4 && world === WORLDS.length - 1) Sfx.victory();
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

const cells = list => list.map(([k, v]) => `<div class="sf-res-cell"><b>${v}</b><span>${tr(k)}</span></div>`).join('');
const fmtTime = s => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

// ── Controls hint (intro card, footnote) ───────────────────────────────
function controlsHint() {
    if (usingPad()) {
        const m = S.settings.pad.map;
        const left = S.settings.pad.swap ? tr('Right stick') : tr('Left stick'), right = S.settings.pad.swap ? tr('Left stick') : tr('Right stick');
        return `<span class="sf-padtag"><i class="fa-solid fa-gamepad"></i></span> ${left} ${S.settings.controls === 'twin' ? tr('move') : tr('turn & thrust')} · ${right} ${tr('aim')} · ${pbtn(m.fire)} ${tr('fire')} · ${pbtn(m.dash)} ${tr('dash')} · ${pbtn(m.bomb)} ${tr('bomb')} · ${pbtn(m.special)} ${tr('ship power')}`;
    }
    return S.settings.controls === 'twin'
        ? `${kbd('up')}${kbd('left')}${kbd('down')}${kbd('right')} ${tr('move')} · ${tr('mouse aims')} · ${tr('click fires')} · ${kbd('dash')} ${tr('dash')} · ${kbd('bomb')} ${tr('bomb')} · ${kbd('special')} ${tr('ship power')}`
        : `${kbd('left')}${kbd('right')} ${tr('turn')} · ${kbd('up')} ${tr('thrust')} · ${kbd('down')} ${tr('brake')} · ${kbd('fire')} ${tr('fire')} · ${kbd('dash')} ${tr('dash')} · ${kbd('bomb')} ${tr('bomb')} · ${kbd('special')} ${tr('ship power')}`;
}
function updateFootnote() {
    if (usingPad()) {
        const m = S.settings.pad.map;
        $('sf-footnote').innerHTML = controlsHint() + ` · ${pbtn(m.prev)}${pbtn(m.next)} ${tr('weapons')} · ${pbtn(m.pause)} ${tr('pause')} — ${tr('change the buttons in Settings → Gamepad')}`;
    } else {
        $('sf-footnote').innerHTML = controlsHint() + ` · <kbd>1</kbd>–<kbd>8</kbd> / ${kbd('weapon')} ${tr('weapons')} · ${kbd('pause')} ${tr('pause')} · ${kbd('mute')} ${tr('mute')} — ${tr('change controls and keys in Settings')}`;
    }
    const mh = $('sf-maphint');
    if (mh) mh.innerHTML = usingPad()
        ? `${pbtn(14)}${pbtn(15)} ${tr('travel')} · ${pbtn(0)} ${tr('deploy')} · ${pbtn(2)} ${tr('hangar')} · ${pbtn(3)} ${tr('galaxy')} · ${pbtn(1)} ${tr('menu')}`
        : `<kbd>&larr;</kbd><kbd>&rarr;</kbd> ${tr('travel')} &nbsp; <kbd>Enter</kbd> ${tr('deploy')} &nbsp; <kbd>H</kbd> ${tr('hangar')} &nbsp; <kbd>G</kbd> ${tr('galaxy')} &nbsp; <kbd>Esc</kbd> ${tr('menu · 10 stars in a world open its secret honeypot')}`;
}
updateFootnote();

// ── HUD ───────────────────────────────────────────────────────────────
function buildWeaponsBar() {
    const owned = Save.weaponsUnlocked();
    // the weapons of Act II only show up once owned, to keep the bar short
    $('sf-hud-weapons').innerHTML = WEAPONS.filter((w, i) => i < 4 || owned.includes(w.id)).map(w => `
        <div class="sf-weapon ${owned.includes(w.id) ? '' : 'locked'}" data-w="${w.id}" style="--wc:${w.color}">
            <kbd>${w.key}</kbd><i class="fa-solid ${owned.includes(w.id) ? w.icon : 'fa-lock'}"></i><span class="sf-wname">${owned.includes(w.id) ? w.name : '???'}</span>
        </div>`).join('');
}

let lastCombo = 1;
function updateHud() {
    if (!level) return;
    const h = level.hud();
    $('sf-hud-hp').innerHTML = Array.from({ length: h.maxHp }, (_, i) => `<i class="fa-solid fa-heart ${i < h.hp ? '' : 'off'}"></i>`).join('');
    $('sf-hud-bombs').innerHTML = `<i class="fa-solid fa-bomb"></i>${h.bombs}${kbd('bomb')}`;
    $('sf-hud-dash').style.width = `${Math.round(h.dash * 100)}%`;
    $('sf-hud-dash-key').innerHTML = usingPad() ? padName(S.settings.pad.map.dash) : keyName(S.settings.keys.dash.find(Boolean));
    $('sf-hud-special-key').innerHTML = usingPad() ? padName(S.settings.pad.map.special) : keyName(S.settings.keys.special.find(Boolean));
    const sp = skin().special, spWrap = $('sf-hud-special-wrap');
    spWrap.style.setProperty('--sf-special', skin().glow);
    spWrap.title = `${sp.name} (${keyName(S.settings.keys.special.find(Boolean))}) — ${sp.desc}`;
    $('sf-hud-special-icon').className = `fa-solid ${sp.icon}`;
    $('sf-hud-special').style.width = `${Math.round(h.special * 100)}%`;
    spWrap.classList.toggle('ready', h.special >= 1 && !h.specialActive);
    spWrap.classList.toggle('active', h.specialActive);
    $('sf-hud-score').textContent = h.score.toLocaleString();
    $('sf-hud-bytes').textContent = h.bytes;
    const combo = $('sf-hud-combo');
    combo.textContent = h.combo > 1 ? tr('COMBO x{n}', { n: h.combo }) : '';
    if (h.combo > lastCombo) { combo.classList.remove('pop'); void combo.offsetWidth; combo.classList.add('pop'); }
    lastCombo = h.combo;
    $('sf-hud-obj').textContent = h.objective.label;
    const bar = $('sf-hud-objbar');
    bar.style.display = h.objective.progress === null || h.objective.progress === undefined ? 'none' : '';
    $('sf-hud-objfill').style.width = `${Math.round((h.objective.progress || 0) * 100)}%`;
    const BUFF = { rapid: ['fa-bolt', '#ffd166', 'RAPID', 480], shield: ['fa-shield-halved', '#6ea8ff', 'SHIELD', 600], overclock: ['fa-fire', '#ff6bd8', 'OVERCLOCK', 480] };
    $('sf-hud-buffs').innerHTML = Object.entries(h.buffs).filter(([, v]) => v > 0).map(([k, v]) =>
        `<div class="sf-buff" style="color:${BUFF[k][1]}"><i class="fa-solid ${BUFF[k][0]}"></i>${tr(BUFF[k][2])}<span class="sf-meter"><span style="width:${Math.round(v / BUFF[k][3] * 100)}%"></span></span></div>`).join('')
        + (h.disarmed > 0 ? '<div class="sf-buff" style="color:#ff7a3c"><i class="fa-solid fa-lock"></i>' + tr('ENCRYPTED') + '</div>' : '')
        + (h.inverted ? '<div class="sf-buff" style="color:#c9a7ff"><i class="fa-solid fa-shuffle"></i>' + tr('REVERSED') + '</div>' : '');
    document.querySelectorAll('.sf-weapon').forEach(el => {
        el.classList.toggle('active', el.dataset.w === h.weapon);
        el.classList.toggle('disarmed', el.dataset.w === h.weapon && h.disarmed > 0);
    });
}

function updateBossBar(b) {
    const el = $('sf-hud-boss');
    if (!b || b.hp <= 0) { el.classList.remove('is-open'); return; }
    el.classList.add('is-open');
    $('sf-hud-bossname').textContent = b.name + (b.invulnerable ? tr(' — SHIELDED') : '');
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
                        ${maxed ? tr('Maxed') : `<i class="fa-solid fa-microchip"></i> ${cost}`}</button>
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
            <span>${owned.includes(w.id) ? tr('Unlocked') : tr('Defeat {boss} ({sub}) to unlock', { boss: BOSSES[WORLDS[w.unlock].boss].name, sub: WORLDS[w.unlock].sub })}</span></div></div>`).join('');
    } else {
        body.innerHTML = SKINS.map(s => {
            const open = Save.shipUnlocked(s.id);
            const where = s.unlock === null ? '' : tr('Free {format} — beat {boss} ({sub})', { format: s.name, boss: BOSSES[WORLDS[s.unlock].boss].name, sub: WORLDS[s.unlock].sub });
            return `<div class="sf-item ${s.id === S.skin ? 'selected' : ''} ${open ? '' : 'locked'}" data-skin="${s.id}" style="cursor:${open ? 'pointer' : 'default'}">
            <canvas class="sf-ship-preview" width="72" height="72" data-preview="${s.id}"></canvas>
            <div class="sf-item-body"><b>${open ? s.name : '???'}</b><span><i class="fa-solid ${s.special.icon}" style="color:${s.glow}"></i> <b>${s.special.name}</b> ${kbd('special')} — ${s.special.desc} ${tr('Recharges in {n} s.', { n: s.special.cd })}</span>
            <span>${!open ? `<i class="fa-solid fa-lock"></i> ${where}` : s.id === S.skin ? tr('Equipped') : tr('Click to equip')}</span></div></div>`;
        }).join('');
        body.querySelectorAll('[data-preview]').forEach(cv => {
            const s = SKINS.find(x => x.id === cv.dataset.preview), c = cv.getContext('2d');
            const open = Save.shipUnlocked(s.id);
            drawShip(c, 36, 38, -Math.PI / 2, open ? s : { ...s, hull: '#2a2f40', glow: '#556', flame: '#556' }, { thrust: open ? 1 : 0, t: 0, scale: 1.25 });
        });
        body.querySelectorAll('[data-skin]').forEach(el => el.addEventListener('click', () => {
            if (!Save.shipUnlocked(el.dataset.skin)) { Sfx.deny(); return; }
            S.skin = el.dataset.skin; Save.save(); Sfx.buy(); renderHangar('skins');
        }));
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
    flood: 'Floods the sector with log lines that hang in space. Its trail hurts.',
    tamper: 'Erases the bytes and bonuses lying around — the evidence.',
    injector: 'Draws a line, then fires a payload down it. Step off the line.',
    xss: 'Fast and zig-zagging; reflects a script back at you when destroyed.',
    scanner: 'Sweeps a vision cone. Stay in it too long and it calls scanners and fires. Rocks hide you.',
    scanbot: 'Crosses the sector in straight lines, firing sideways.',
    jailbreak: 'Boosts and heals every malware around it. Kill it first.',
    halluc: 'Mirrors your moves around its anchor and fires when lined up with you.',
    rogue: 'Steals bonuses (and heals with them), and launches homing tool calls.',
    toolcall: 'A small homing call. Short-lived — shoot it or dash through.',
    brute: 'Telegraphs a line and charges along it, three times in a row.',
    lateral: 'Jumps next to another malware or right behind you, then fires a ring.',
    obfusc: 'Its noise cloud swallows some of your bullets. Get inside the cloud.',
    exfil: 'Runs away with data. If it escapes from an edge, your bytes go with it.',
    shard: 'Splits into two smaller shards when destroyed, three sizes deep.',
    fork: 'Copies itself every few seconds. Kill them before they pile up.',
    latch: 'Hooks onto your ship and drains it. Dash to tear it off.',
    spore: 'Swells and bursts into a ring of bullets when you come close.',
    benign: 'Clean traffic. Harmless — shooting it is a false positive.',
    courier: 'Carries stolen data to an exit gate. Stops sometimes to upload.',
    implant: 'Hidden in the dark, calls malware and fires when you are near. Objective target.',
};
const BESTIARY_ICON = { worm: 'bug', spammer: 'envelope', trojan: 'gift', phisher: 'fish', drone: 'robot', botnet: 'network-wired', miner: 'coins', locker: 'lock', mine: 'bomb', keylogger: 'keyboard', rootkit: 'microchip', apt: 'user-secret', wiper: 'biohazard', beacon: 'satellite',
    flood: 'scroll', tamper: 'ban', injector: 'syringe', xss: 'code', scanner: 'binoculars', scanbot: 'wifi', jailbreak: 'mask', halluc: 'wand-magic-sparkles', rogue: 'user-gear', toolcall: 'gear',
    brute: 'hammer', lateral: 'shuffle', obfusc: 'cloud', exfil: 'file-export', shard: 'cube', fork: 'clone', latch: 'link', spore: 'bacterium', benign: 'paper-plane', courier: 'file-export', implant: 'spider' };
function renderHelp(tab) {
    document.querySelectorAll('#sf-help-tabs .sf-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    const body = $('sf-help-body');
    if (tab === 'bestiary') {
        body.classList.remove('is-text');
        body.innerHTML = Object.entries(BESTIARY).map(([k, d]) => `<div class="sf-item">
            <div class="sf-item-icon" style="color:${ENEMIES[k].color}"><i class="fa-solid fa-${BESTIARY_ICON[k]}"></i></div>
            <div class="sf-item-body"><b>${ENEMIES[k].name}</b><span>${tr(d)}</span></div></div>`).join('');
        return;
    }
    if (tab === 'story') {
        // the archives: briefings and debriefs of every level cleared so far
        body.classList.add('is-text');
        const done = STORY_KEYS.filter(k => S.stars[k] > 0 || (k.endsWith('-4') && S.bosses.includes(+k.split('-')[0])));
        let html = `<div class="sf-help-section"><p>${tr('The story so far: every level you cleared, with its briefing and debrief.')}</p>`;
        if (!done.length) html += `<p class="sf-sub">${tr('Nothing yet — clear a level to start the archives.')}</p>`;
        let lastWorld = -1;
        for (const k of done) {
            const [w, i] = k.split('-').map(Number);
            const st = levelStory(w, i), d = levelDef(w, i);
            if (w !== lastWorld) { html += `<h3 style="color:${WORLDS[w].hue}">${WORLDS[w].sub} — ${WORLDS[w].name}</h3>`; lastWorld = w; }
            html += `<div class="sf-archive"><b>${d.name}</b><p>${st.brief}</p>${st.outro ? `<p class="sf-archive-outro"><i class="fa-solid fa-flag-checkered"></i> ${st.outro}</p>` : ''}</div>`;
        }
        body.innerHTML = html + '</div>';
        return;
    }
    body.classList.add('is-text');
    if (tab === 'controls') {
        body.innerHTML = `<div class="sf-help-section">
            <p>${tr('You are a detection rule deployed into the graph. Five worlds of malware stand between you and the zero-day.')}</p>
            <h3>${tr('Classic controls (default — keyboard only)')}</h3>
            <div class="sf-controls">
                <span>${kbd('left', true)} ${kbd('right', true)}</span><span>${tr('Turn')}</span>
                <span>${kbd('up', true)}</span><span>${tr('Thrust forward (the ship keeps its momentum)')}</span>
                <span>${kbd('down', true)}</span><span>${tr('Brake')}</span>
                <span>${kbd('fire', true)}</span><span>${tr('Fire straight ahead (hold)')}</span>
            </div>
            <h3>${tr('Twin-stick controls (Settings → Controls)')}</h3>
            <div class="sf-controls">
                <span>${kbd('up')}${kbd('left')}${kbd('down')}${kbd('right')}</span><span>${tr('Move in that direction')}</span>
                <span>${tr('Mouse')}</span><span>${tr('Aim — click or {key} to fire, right-click to dash', { key: kbd('fire') })}</span>
            </div>
            <h3>${tr('Both')}</h3>
            <div class="sf-controls">
                <span>${kbd('dash', true)}</span><span>${tr('Dash — a quick burst, invulnerable while dashing')}</span>
                <span>${kbd('bomb', true)}</span><span>${tr('Quarantine bomb — clears every bullet on screen and hurts everything')}</span>
                <span>${kbd('special', true)}</span><span>${tr('Ship power — each ship (Hangar → Rule engine) has its own, recharging on its own: YARA Signature Sweep, Suricata IPS Drop, Sigma Correlation, Zeek Deep Inspection')}</span>
                <span><kbd>1</kbd>–<kbd>8</kbd> / ${kbd('weapon')}</span><span>${tr('Switch weapon')}</span>
                <span>${kbd('pause')} / <kbd>Esc</kbd></span><span>${tr('Pause')}</span>
                <span>${kbd('mute')}</span><span>${tr('Sound on / off')}</span>
                <span></span><span>${tr('Every key can be changed in Settings → Keys.')}</span>
                <span>${tr('Gamepad')}</span><span>${tr('Left stick turn/thrust (classic) or move (twin) · right stick aim · RT fire · A dash · B bomb · Y ship power · LB/RB weapons')}</span>
            </div>
            <h3>${tr('Progress')}</h3>
            <p>${tr('Bytes dropped by malware are spent in the hangar. Each world boss unlocks a new weapon and the next world. Get 10 stars in a world to reveal its secret honeypot. Kill fast to build a combo (up to x8).')}</p>
            <p>${tr('Act II: every boss of the Deep Graph frees a detection engine — its ship joins your hangar, with its own power. The galaxy map (G on the map) warps you to any open world.')}</p></div>`;
    } else {
        body.innerHTML = `<div class="sf-help-section">
            <h3>${tr('Objectives')}</h3><ul>
                <li><b>${tr('Waves')}</b> ${tr('— clear every wave.')}</li>
                <li><b>${tr('Survive')}</b> ${tr('— hold out until the timer runs out.')}</li>
                <li><b>${tr('Cut the C2')}</b> ${tr('— destroy every beacon; they keep calling reinforcements.')}</li>
                <li><b>${tr('Protect')}</b> ${tr('— keep the network sensor alive until the scan completes. Malware goes for it too.')}</li>
                <li><b>${tr('Boss')}</b> ${tr('— three phases each. Watch the dashed lines and red sectors: they are attacks about to land.')}</li>
                <li><b>${tr('Honeypot')}</b> ${tr('(secret) — 45 seconds, triple bytes.')}</li>
                <li><b>${tr('Find the keys')}</b> ${tr('— open space: explore the sector, pick up every key, then reach the exit gate. Keys appear on the radar once close; a ping shows the nearest.')}</li>
                <li><b>${tr('Escort')}</b> ${tr('— the convoy only moves while you stay close to it.')}</li>
                <li><b>${tr('Capture')}</b> ${tr('— stay inside each relay ring until it is captured.')}</li>
                <li><b>${tr('Pursuit')}</b> ${tr('— destroy the courier before it reaches its exit gate.')}</li>
                <li><b>${tr('Blackout')}</b> ${tr('— in the dark, find the hidden implants; your scanner pulses every few seconds.')}</li>
                <li><b>${tr('Purge')}</b> ${tr('— destroy every shard; big ones split.')}</li>
                <li><b>${tr('Gauntlet')}</b> ${tr('— fly through a long corridor of laser gates to the exit.')}</li>
                <li><b>${tr('Triage')}</b> ${tr('— destroy the malicious traffic, spare the clean (green) packets. Too many false positives and you lose.')}</li>
                <li><b>${tr('Defend')}</b> ${tr('— keep several far-apart servers alive; arrows show where they are.')}</li></ul>
            <h3>${tr('Open space')}</h3>
            <p>${tr('Some sectors are much bigger than the screen: the camera follows you, the radar (bottom right) shows the whole sector and arrows on the screen edges point at what matters.')}</p>
            <h3>${tr('Stars')}</h3><ul>
                <li>${tr('★ Complete the level.')}</li><li>${tr('★ Take 2 hits or fewer (3 against a boss).')}</li>
                <li>${tr('★ Beat the par time — or take no hit (survive), keep the sensor above 70% (protect), collect enough bytes (honeypot).')}</li>
                <li>${tr('★ Act II: keep the convoy above 70% (escort), lose no server (defend), make no false positive (triage).')}</li></ul>
            <h3>${tr('Pickups')}</h3><ul>
                <li><i class="fa-solid fa-heart" style="color:#ff5d73"></i> ${tr('+1 integrity ·')} <i class="fa-solid fa-bolt" style="color:#ffd166"></i> ${tr('rapid fire ·')}
                <i class="fa-solid fa-shield-halved" style="color:#6ea8ff"></i> ${tr('shield (absorbs a hit) ·')} <i class="fa-solid fa-fire" style="color:#ff6bd8"></i> ${tr('overclock (double damage) ·')}
                <i class="fa-solid fa-bomb" style="color:#ff9f43"></i> ${tr('+1 bomb')}</li>
                <li>${tr('Beware: a heart that wobbles a little too much might be a trojan.')}</li></ul></div>`;
    }
}
document.querySelectorAll('#sf-help-tabs .sf-tab').forEach(b => b.addEventListener('click', () => { Sfx.move(); renderHelp(b.dataset.tab); }));

// ── Settings: General · Audio & display · Keyboard · Gamepad ──────────
let settingsTab = 'general';
let padRebind = null;            // { act, t } while waiting for a controller button
function renderSettings(tab = settingsTab) {
    settingsTab = tab;
    document.querySelectorAll('#sf-settings-tabs .sf-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    $('sf-reset').style.display = tab === 'general' ? '' : 'none';
    const sw = (key, label, invert = false, extra = '') => {
        const on = invert ? !S.settings[key] : S.settings[key] !== false;
        return `<div class="sf-setting"><span>${tr(label)}${extra}</span><button class="sf-switch ${on ? 'on' : ''}" data-set="${key}" aria-label="${tr(label)}"></button></div>`;
    };
    const padSw = (key, label) => `<div class="sf-setting"><span>${tr(label)}</span><button class="sf-switch ${S.settings.pad[key] ? 'on' : ''}" data-padset="${key}" aria-label="${tr(label)}"></button></div>`;
    const sel = (id, label, opts, val) => `<div class="sf-setting"><span>${tr(label)}</span><select id="${id}">${opts.map(([v, l]) => `<option value="${v}" ${v === val ? 'selected' : ''}>${l}</option>`).join('')}</select></div>`;
    const range = (key, label, val, min = 0, max = 100, step = 5, unit = '%') => `<div class="sf-setting"><span>${tr(label)}</span><div class="sf-range"><input type="range" min="${min}" max="${max}" step="${step}" value="${val}" data-range="${key}" aria-label="${tr(label)}"><b>${val}${unit}</b></div></div>`;
    const head = (icon, label) => `<div class="sf-settings-head"><i class="fa-solid ${icon}"></i> ${tr(label)}</div>`;
    let html = '';
    if (tab === 'general') {
        html = head('fa-earth-europe', 'Game')
            + sel('sf-set-lang', 'Language', [['fr', 'Français'], ['en', 'English']], getLang())
            + sel('sf-set-diff', 'Difficulty', DIFFICULTIES.map(d => [d.id, d.name]), S.difficulty)
            + head('fa-arrows-up-down-left-right', 'Steering')
            + sel('sf-set-controls', 'Controls', [['classic', tr('Classic — arrows only (turn & thrust)')], ['twin', tr('Twin-stick — WASD move, mouse aims')]], S.settings.controls === 'twin' ? 'twin' : 'classic')
            + (S.settings.controls === 'twin' ? sw('assist', 'Auto-aim when the mouse isn\'t used') : '')
            + `<p class="sf-sub sf-settings-note">${tr('With a controller, classic = left stick turns and pushes, twin-stick = left stick moves and right stick aims.')}</p>`;
    } else if (tab === 'audio') {
        const v = S.settings.volume;
        html = head('fa-volume-high', 'Sound')
            + sw('muted', 'Sound', true)
            + range('master', 'Main volume', Math.round(v.master * 100))
            + range('sfx', 'Effects', Math.round(v.sfx * 100))
            + sw('music', 'Music')
            + range('music', 'Music volume', Math.round(v.music * 100))
            + `<div class="sf-setting"><span>${tr('Audio engine:')} <b id="sf-audio-state">${Audio.status()}</b>${S.settings.muted ? ' ' + tr('(muted)') : ''}</span><button class="sf-btn sf-btn--small" id="sf-audio-test"><i class="fa-solid fa-volume-high"></i> ${tr('Test sound')}</button></div>`
            + head('fa-display', 'Display')
            + sel('sf-set-quality', 'Graphics', [['high', tr('High — glows, nebulas, planets')], ['low', tr('Low — faster on small machines')]], S.settings.quality === 'low' ? 'low' : 'high')
            + sw('shake', 'Screen shake')
            + sw('flashes', 'Flashes (explosions, hit screen)')
            + sw('fps', 'Show frames per second');
    } else if (tab === 'keys') {
        html = `<div class="sf-keys-head"><b><i class="fa-solid fa-keyboard"></i> ${tr('Keys')}</b><button class="sf-btn sf-btn--small" id="sf-keys-reset"><i class="fa-solid fa-rotate-left"></i> ${tr('Default keys')}</button></div>
           <p class="sf-sub">${tr('Click a key, then press the new one. {esc} cancels, {back} clears it.', { esc: '<kbd>Esc</kbd>', back: '<kbd>Backspace</kbd>' })}</p>
           <div class="sf-keys">${KEY_ACTIONS.map(a => `<span>${a.label}</span>${[0, 1].map(i =>
                `<button class="sf-key ${rebinding && rebinding.act === a.id && rebinding.slot === i ? 'listening' : ''}" data-act="${a.id}" data-slot="${i}">${rebinding && rebinding.act === a.id && rebinding.slot === i ? '…' : keyName(S.settings.keys[a.id][i])}</button>`).join('')}`).join('')}</div>`;
    } else {
        const P = S.settings.pad, st = input.state;
        const fam = padLayout();
        html = `<div class="sf-padcard ${st.padConnected ? 'on' : ''}">
                <i class="fa-solid fa-gamepad"></i>
                <div><b>${st.padConnected ? padShortName(st.padId) : tr('No controller detected')}</b>
                <span>${st.padConnected ? tr('{family} layout — press any button to try it below', { family: PAD_LAYOUT_NAMES[fam] }) : tr('Plug a controller in (or pair it) and press any of its buttons.')}</span></div>
            </div>`
            + sel('sf-set-padlayout', 'Button names', [['auto', tr('Automatic')], ['xbox', 'Xbox'], ['ps', 'PlayStation'], ['nintendo', 'Nintendo']], P.layout || 'auto')
            + `<div class="sf-padtest" id="sf-padtest">
                <div class="sf-stick"><span id="sf-stick-l"></span><em>${tr('Left stick')}</em></div>
                <div class="sf-padbtns">${Array.from({ length: 17 }, (_, i) => `<span class="sf-pb" id="sf-pb-${i}">${padName(i)}</span>`).join('')}</div>
                <div class="sf-stick"><span id="sf-stick-r"></span><em>${tr('Right stick')}</em></div>
            </div>`
            + `<div class="sf-keys-head"><b><i class="fa-solid fa-gamepad"></i> ${tr('Buttons')}</b><button class="sf-btn sf-btn--small" id="sf-pad-reset"><i class="fa-solid fa-rotate-left"></i> ${tr('Default buttons')}</button></div>
               <p class="sf-sub">${tr('Choose an action, then press the controller button for it. In the menus {a} confirms, {b} goes back and {lb} {rb} switch tabs.', { a: pbtn(0), b: pbtn(1), lb: pbtn(4), rb: pbtn(5) })}</p>
               <div class="sf-keys sf-keys--pad">${PAD_ACTIONS.map(a => `<span>${tr(a.label)}</span><button class="sf-key ${padRebind && padRebind.act === a.id ? 'listening' : ''}" data-padact="${a.id}">${padRebind && padRebind.act === a.id ? tr('press…') : padName(P.map[a.id])}</button>`).join('')}</div>`
            + head('fa-sliders', 'Sticks & feel')
            + range('deadzone', 'Stick dead zone', Math.round((P.deadzone ?? 0.18) * 100), 5, 40, 1)
            + padSw('swap', 'Swap the sticks (move with the right one)')
            + padSw('invertY', 'Invert the aim stick vertically')
            + `<div class="sf-setting"><span>${tr('Vibration')}</span><span class="sf-setting-pair"><button class="sf-btn sf-btn--small" id="sf-pad-rumble"><i class="fa-solid fa-wave-square"></i> ${tr('Test')}</button><button class="sf-switch ${P.vibration ? 'on' : ''}" data-padset="vibration" aria-label="${tr('Vibration')}"></button></span></div>`;
    }
    const list = $('sf-settings-list');
    list.innerHTML = html;
    list.querySelectorAll('[data-set]').forEach(b => b.addEventListener('click', () => {
        const key = b.dataset.set;
        if (key === 'muted') S.settings.muted = !S.settings.muted;
        else if (key === 'assist' || key === 'fps') S.settings[key] = S.settings[key] !== true;
        else S.settings[key] = S.settings[key] === false;
        applySettings(); Save.save(); renderSettings(); Sfx.move();
    }));
    list.querySelectorAll('[data-padset]').forEach(b => b.addEventListener('click', () => {
        const key = b.dataset.padset;
        S.settings.pad[key] = !S.settings.pad[key];
        applySettings(); Save.save(); renderSettings(); Sfx.move();
        if (key === 'vibration' && S.settings.pad.vibration) input.rumble(0.6, 0.6, 200);
    }));
    list.querySelectorAll('[data-range]').forEach(r => {
        const show = () => { r.nextElementSibling.textContent = r.value + (r.dataset.range === 'deadzone' ? '%' : '%'); };
        r.addEventListener('input', () => {
            const k = r.dataset.range, v = +r.value / 100;
            if (k === 'deadzone') S.settings.pad.deadzone = v; else S.settings.volume[k] = v;
            show(); applySettings();
        });
        r.addEventListener('change', () => { Save.save(); if (r.dataset.range !== 'deadzone' && r.dataset.range !== 'music') Sfx.move(); });
    });
    const on = (id, ev, fn) => { const el = $(id); if (el) el.addEventListener(ev, fn); };
    on('sf-set-diff', 'change', e => { S.difficulty = e.target.value; Save.save(); });
    // every text is translated at start-up: switching language reloads the page
    on('sf-set-lang', 'change', e => { S.settings.lang = e.target.value; Save.save(); location.reload(); });
    on('sf-set-controls', 'change', e => { S.settings.controls = e.target.value; Save.save(); renderSettings(); updateFootnote(); });
    on('sf-set-quality', 'change', e => { S.settings.quality = e.target.value; applySettings(); Save.save(); });
    on('sf-set-padlayout', 'change', e => { S.settings.pad.layout = e.target.value; Save.save(); renderSettings(); updateFootnote(); refreshPadHint(); });
    list.querySelectorAll('.sf-key[data-act]').forEach(b => b.addEventListener('click', () => {
        rebinding = { act: b.dataset.act, slot: +b.dataset.slot }; Sfx.move(); renderSettings();
    }));
    list.querySelectorAll('.sf-key[data-padact]').forEach(b => b.addEventListener('click', () => {
        padRebind = { act: b.dataset.padact, t: 0 }; Sfx.move(); renderSettings();
    }));
    on('sf-keys-reset', 'click', () => {
        S.settings.keys = Save.defaultKeys(); rebinding = null; applySettings(); Save.save(); renderSettings(); updateFootnote(); Sfx.buy();
    });
    on('sf-pad-reset', 'click', () => {
        S.settings.pad = Save.defaultPad(); padRebind = null; applySettings(); Save.save(); renderSettings(); updateFootnote(); Sfx.buy();
    });
    on('sf-pad-rumble', 'click', () => {
        if (!input.state.padConnected) { toast(tr('No controller detected')); Sfx.deny(); return; }
        if (!S.settings.pad.vibration) { toast(tr('Vibration is off')); Sfx.deny(); return; }
        input.rumble(1, 0.4, 350);
    });
    on('sf-audio-test', 'click', async () => {
        if (S.settings.muted) { S.settings.muted = false; applySettings(); Save.save(); }
        const state = await Audio.test();
        const el = $('sf-audio-state'); if (el) el.textContent = state;
        toast(state === 'running' ? tr('You should hear two beeps. Nothing? Check the tab / system volume.')
            : state === 'unsupported' ? tr('This browser has no Web Audio.') : tr('The browser keeps audio {state} — click the page once more.', { state }));
    });
}
document.querySelectorAll('#sf-settings-tabs .sf-tab').forEach(b => b.addEventListener('click', () => { Sfx.move(); rebinding = null; padRebind = null; renderSettings(b.dataset.tab); }));

/** The live controller tester of Settings → Gamepad */
function updatePadTester() {
    const p = input.state.pad;
    for (let i = 0; i < 17; i++) { const el = $(`sf-pb-${i}`); if (el) el.classList.toggle('on', !!(p && p.held[i])); }
    const dot = (id, x, y) => { const el = $(id); if (el) el.style.transform = `translate(${x * 18}px, ${y * 18}px)`; };
    dot('sf-stick-l', p ? p.axes[0] : 0, p ? p.axes[1] : 0);
    dot('sf-stick-r', p ? p.axes[2] : 0, p ? p.axes[3] : 0);
}

/** Waiting for the controller button of an action (Settings → Gamepad) */
function updatePadRebind() {
    const p = input.state.pad;
    padRebind.t++;
    if (input.hit('Escape') || padRebind.t > 60 * 8) { padRebind = null; renderSettings(); return; }
    if (!p || p.edgeButton < 0) return;
    const b = p.edgeButton, map = S.settings.pad.map, act = padRebind.act;
    // a button does one thing: swap with the action that had it
    const other = Object.keys(map).find(k => map[k] === b && k !== act);
    if (other) map[other] = map[act];
    map[act] = b;
    padRebind = null;
    Sfx.buy(); applySettings(); Save.save(); renderSettings(); updateFootnote();
    if (other) toast(tr('{a} ↔ {b} swapped', { a: tr(PAD_ACTIONS.find(x => x.id === act).label), b: tr(PAD_ACTIONS.find(x => x.id === other).label) }));
}

// Waiting for the new key of an action: grabbed before the game sees it
let rebinding = null;
window.addEventListener('keydown', e => {
    if (!rebinding || overlay !== 'sf-settings') { rebinding = null; return; }
    e.preventDefault(); e.stopImmediatePropagation();
    const code = normalizeKey(e.code);
    const { act, slot } = rebinding;
    if (code === 'Backspace' || code === 'Delete') S.settings.keys[act][slot] = null;
    else if (RESERVED_KEYS.includes(code)) { if (code !== 'Escape') { toast(tr('{key} is kept for the weapons', { key: keyName(code) })); Sfx.deny(); } }
    else {
        // a key does one thing: take it away from wherever it was
        for (const k of Object.keys(S.settings.keys)) S.settings.keys[k] = S.settings.keys[k].map(c => (c === code ? null : c));
        S.settings.keys[act][slot] = code;
        Sfx.buy();
    }
    rebinding = null;
    applySettings(); Save.save(); renderSettings(); updateFootnote();
}, { capture: true });

function applySettings() {
    input.setKeys(S.settings.keys);
    input.setPad(S.settings.pad);
    Audio.setVolumes(S.settings.volume);
    GFX.low = S.settings.quality === 'low';
    Audio.setMuted(!!S.settings.muted);
    Music.setEnabled(S.settings.music !== false);
    $('sf-btn-mute').innerHTML = `<i class="fa-solid ${S.settings.muted ? 'fa-volume-xmark' : 'fa-volume-high'}"></i>`;
}
$('sf-reset').addEventListener('click', () => {
    askConfirm(tr('Erase every star, byte, upgrade and score? This cannot be undone.'), () => { Save.reset(); applySettings(); showTitle(); }, 'Erase everything');
});
$('sf-btn-mute').addEventListener('click', () => { S.settings.muted = !S.settings.muted; applySettings(); Save.save(); });
$('sf-btn-full').addEventListener('click', () => {
    const p = document.fullscreenElement ? document.exitFullscreen() : (stage.requestFullscreen ? stage.requestFullscreen() : null);
    if (p && p.catch) p.catch(() => {});
});
applySettings();

// ── Menu navigation: d-pad / left stick / arrows move a focus ring, A / Enter clicks ──
const NAV_SEL = 'button:not([disabled]), select, input[type=range], [data-skin]';
let navEl = null, navKey = null;
function keyOf(el) {
    if (el.id) return `#${el.id}`;
    const d = Object.entries(el.dataset).map(([k, v]) => `[data-${k.replace(/[A-Z]/g, c => '-' + c.toLowerCase())}="${v}"]`).join('');
    return d || null;
}
function setNav(el) {
    if (navEl) navEl.classList.remove('sf-focus');
    navEl = el; navKey = el ? keyOf(el) : null;
    if (el) { el.classList.add('sf-focus'); el.scrollIntoView({ block: 'nearest', inline: 'nearest' }); }
}
function navItems() {
    const root = overlay ? $(overlay) : null;
    if (!root) return [];
    return [...root.querySelectorAll(NAV_SEL)].filter(el => el.offsetParent !== null && el.getBoundingClientRect().width > 0 && el.style.display !== 'none');
}
const navDefault = items => items.find(e => e.classList.contains('sf-btn--primary')) || items.find(e => e.classList.contains('sf-tab') && e.classList.contains('active')) || items[0];
function navMove(dir) {
    const items = navItems();
    if (!items.length) return;
    if (!navEl || !items.includes(navEl)) { setNav(navDefault(items)); Sfx.move(); return; }
    const a = navEl.getBoundingClientRect(), ax = a.left + a.width / 2, ay = a.top + a.height / 2;
    let best = null, bs = Infinity;
    for (const el of items) {
        if (el === navEl) continue;
        const r = el.getBoundingClientRect(), dx = r.left + r.width / 2 - ax, dy = r.top + r.height / 2 - ay;
        const [main, side] = dir === 'up' ? [-dy, dx] : dir === 'down' ? [dy, dx] : dir === 'left' ? [-dx, dy] : [dx, dy];
        if (main <= 4) continue;
        const sc = main + Math.abs(side) * 2.2;
        if (sc < bs) { bs = sc; best = el; }
    }
    if (best) { setNav(best); Sfx.move(); }
}
function navAdjust(dir) {
    if (!navEl) return false;
    const d = dir === 'right' ? 1 : -1;
    if (navEl.tagName === 'SELECT') {
        const n = navEl.options.length;
        navEl.selectedIndex = (navEl.selectedIndex + d + n) % n;
        navEl.dispatchEvent(new Event('change')); Sfx.move(); return true;
    }
    if (navEl.type === 'range') {
        const st = +navEl.step || 1;
        navEl.value = Math.max(+navEl.min, Math.min(+navEl.max, +navEl.value + d * st));
        navEl.dispatchEvent(new Event('input')); navEl.dispatchEvent(new Event('change')); return true;
    }
    return false;
}
function navConfirm() {
    const items = navItems();
    if (!navEl || !items.includes(navEl)) { if (items.length) { setNav(navDefault(items)); Sfx.move(); } return; }
    if (navEl.tagName === 'SELECT') { navAdjust('right'); return; }
    if (navEl.type === 'range') return;
    navEl.click();
}
function switchTab(d) {
    const root = overlay ? $(overlay) : null;
    const tabs = root ? [...root.querySelectorAll('.sf-tab')] : [];
    if (!tabs.length) return;
    const i = Math.max(0, tabs.findIndex(t => t.classList.contains('active')));
    const next = tabs[(i + d + tabs.length) % tabs.length];
    next.click();
    setNav(next);
}
function padBack() {
    if (overlay === 'sf-title') return;
    if (overlay === 'sf-pause') return togglePause(false);
    if (overlay === 'sf-results') return $('sf-res-map').click();
    if (overlay === 'sf-endless') return $('sf-end-menu').click();
    if (overlay === 'sf-confirm') return confirmNo();
    if (overlay === 'sf-story') return $('sf-story-ok').click();
    goBack();
}
function menuInput(pad) {
    // a panel re-rendered under the focus: find the same control again
    if (navEl && !navEl.isConnected) { const root = overlay && $(overlay); const again = root && navKey ? root.querySelector(navKey) : null; navEl = null; if (again) setNav(again); }
    if (!navEl && usingPad()) { const items = navItems(); if (items.length) setNav(navDefault(items)); }
    const kDir = input.hit('ArrowUp') ? 'up' : input.hit('ArrowDown') ? 'down' : input.hit('ArrowLeft') ? 'left' : input.hit('ArrowRight') ? 'right' : null;
    const pDir = pad ? (pad.up ? 'up' : pad.down ? 'down' : pad.left ? 'left' : pad.right ? 'right' : null) : null;
    const dir = pDir || kDir;
    if (dir && !((dir === 'left' || dir === 'right') && navAdjust(dir))) navMove(dir);
    let used = !!dir;
    if ((pad && pad.confirm) || (navEl && input.hit('Enter'))) { navConfirm(); used = true; }
    if (pad && (pad.tabPrev || pad.tabNext)) { switchTab(pad.tabNext ? 1 : -1); used = true; }
    if (pad && pad.back) { padBack(); used = true; }
    return used;          // this frame's input was for the menu: the screen behind must not see it
}

/** The button guide at the bottom of the panels, while a controller is in use */
function refreshPadHint() {
    const el = $('sf-padhint');
    if (!el) return;
    const show = usingPad() && overlay && overlay !== 'sf-title';
    el.hidden = !show;
    if (!show) return;
    const tabs = $(overlay) && $(overlay).querySelector('.sf-tab');
    el.innerHTML = `${pbtn(0)} ${tr('select')} &nbsp; ${pbtn(1)} ${tr('back')}${tabs ? ` &nbsp; ${pbtn(4)}${pbtn(5)} ${tr('tabs')}` : ''}`;
}
input.onPadChange((on, id) => {
    toast(on ? tr('Controller connected: {name}', { name: padShortName(id) }) : tr('Controller disconnected'));
    if (on) input.state.lastDevice = 'pad';
    if (!on && level && !level.finished && !paused) togglePause(true);
    if (overlay === 'sf-settings' && settingsTab === 'pad') renderSettings();
    deviceChanged();
});
let lastDevice = null;
function deviceChanged() {
    updateFootnote(); refreshPadHint();
    if (overlay === 'sf-pause' && level) $('sf-pause-controls').innerHTML = controlsHint();
    if (screen === 'level' || screen === 'endless') $('sf-intro-keys').innerHTML = controlsHint();
    if (briefWait) $('sf-intro-go').innerHTML = `${usingPad() ? pbtn(0) : `${kbd('fire')} / <kbd>Enter</kbd>`} ${tr('launch')}`;
}

// ── Loop: fixed 60 Hz updates, render every frame ─────────────────────
function update() {
    t++;
    input.frame();
    if (input.actHit('mute')) { S.settings.muted = !S.settings.muted; applySettings(); Save.save(); }
    const pad = input.state.pad;
    const dev = usingPad() ? 'pad' : 'kbm';
    if (dev !== lastDevice) { lastDevice = dev; deviceChanged(); }
    if (overlay === 'sf-settings' && settingsTab === 'pad') updatePadTester();
    let consumed = false;
    if (padRebind && overlay === 'sf-settings') { updatePadRebind(); consumed = true; }
    else if (overlay && !rebinding) consumed = menuInput(pad);

    if (consumed) { /* the menu used this frame's input */ }
    else if (screen === 'map' && !overlay && map.galaxy) {
        map.update();
        if (input.hit('ArrowRight', 'KeyD', 'ArrowDown', 'KeyS') || (pad && (pad.right || pad.down))) map.galaxyStep(1);
        if (input.hit('ArrowLeft', 'KeyA', 'ArrowUp', 'KeyW') || (pad && (pad.left || pad.up))) map.galaxyStep(-1);
        if (input.hit('Enter', 'Space') || (pad && pad.confirm)) map.galaxyWarp();
        else if (input.hit('Escape', 'KeyG') || (pad && (pad.back || pad.edgeButton === 3))) { map.openGalaxy(false); refreshMapHud(); }
        map.pointer(input.state.mx, input.state.my, input.hit('Mouse0'));
        if (t % 10 === 0) refreshMapHud();
    } else if (screen === 'map' && !overlay) {
        map.update();
        if (input.hit('KeyG') || (pad && pad.edgeButton === 3)) { map.openGalaxy(true); refreshMapHud(); }
        if (pad && pad.edgeButton === 2) { renderHangar('upgrades'); openPanel('sf-hangar', 'map'); }
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
        if (paused && overlay === 'sf-settings') { if (input.hit('Escape')) goBack(); }
        else if (input.actHit('pause') || input.hit('Escape') || (pad && pad.pause)) togglePause();
        if (!paused) {
            if (briefWait) {
                if (input.actHit('fire') || input.hit('Enter', 'Mouse0') || (pad && pad.confirm)) { briefWait = false; introT = 1; $('sf-intro-go').hidden = true; }
            } else if (introT > 0) { introT--; if (introT === 0) $('sf-intro').classList.remove('is-open'); }
            else level.update(input);
            if (t % 3 === 0) updateHud();
        }
    } else if (screen === 'title' && overlay && overlay !== 'sf-title' && input.hit('Escape')) goBack();

    drift.x += 0.25; drift.y += 0.08;
    if (level && level.player && !paused && !level.open) { drift.x += level.player.vx * 0.3; drift.y += level.player.vy * 0.3; }
    input.endFrame();
}

function render() {
    const { scale, ox, oy, dpr } = view;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = '#02030a'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(dpr * scale, 0, 0, dpr * scale, dpr * ox, dpr * oy);
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, W, H); ctx.clip();
    const world = level ? (level.world ?? 0) : screen === 'map' ? map.world : titleWorld();
    const cam = level && level.open ? level.cam : null;
    drawBackground(ctx, stars, t * 16, WORLDS[world], cam ? { x: drift.x + cam.x, y: drift.y + cam.y } : drift, bgImage, !!level);
    if (screen === 'map') map.draw(ctx, skin());
    else if (level) level.draw(ctx);
    else {
        // title: the fleet of engines you freed flies by in formation, your ship in front
        const fleet = SKINS.filter(sk => Save.shipUnlocked(sk.id) && sk.id !== skin().id).slice(0, 6);
        const lx = W / 2 + Math.sin(t * 0.01) * 300, ly = H / 2 + 170 + Math.sin(t * 0.023) * 30, la = -Math.PI / 2 + Math.sin(t * 0.01) * 0.3;
        fleet.forEach((sk, i) => {
            const side = i % 2 ? 1 : -1, rank = 1 + (i >> 1);
            drawShip(ctx, lx + side * rank * 70 + Math.sin(t * 0.03 + i) * 6, ly + rank * 46, la, sk, { thrust: 1, t: t + i * 7, scale: 0.9, alpha: 0.75 });
        });
        drawShip(ctx, lx, ly, la, skin(), { thrust: 1, t, scale: 1.6 });
    }
    ctx.restore();
    if (S.settings.fps) {
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.font = '700 11px ui-monospace, monospace'; ctx.fillStyle = 'rgba(0,0,0,.55)'; ctx.fillRect(4, canvas.height / dpr - 20, 62, 16);
        ctx.fillStyle = fps >= 55 ? '#4be08a' : fps >= 40 ? '#ffd166' : '#ff5d73'; ctx.fillText(`${Math.round(fps)} FPS`, 8, canvas.height / dpr - 8);
    }
}

let acc = 0, lastTs = 0, fps = 60;
function frame(ts) {
    if (lastTs && ts > lastTs) fps += (1000 / (ts - lastTs) - fps) * 0.05;
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
