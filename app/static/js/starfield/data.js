/**
 * data.js — everything the game is made of, as data: worlds, levels,
 * enemies, bosses, weapons, upgrades, pickups, skins. The engine
 * (level.js, bosses.js…) reads these tables; balancing the game means
 * editing numbers here.
 *
 * The arena is a fixed 1280×720 logical space, scaled to the canvas.
 */

import { tr } from './i18n.js';

export const W = 1280;
export const H = 720;
export const TAU = Math.PI * 2;

// ── FontAwesome 6 Free (solid) glyphs, drawn on the canvas with fillText ──
export const FA = {
    bug: '', robot: '', skull: '', lock: '', bolt: '',
    shield: '', heart: '', secret: '', envelope: '', fish: '',
    network: '', chip: '', bomb: '', keyboard: '', ghost: '',
    virus: '若', coins: '', eyeSlash: '', crosshairs: '', gem: '',
    gift: '', fire: '', magnet: '', star: '', flag: '',
    eye: '', satellite: '', biohazard: '', key: '', sun: '',
};

// ── Ships — you ARE a detection rule. Each format has its own super power
// (F / gamepad Y), always available, recharging on its own (cd in seconds).
export const SKINS = [
    { id: 'yara',     name: 'YARA',     hull: '#dce6ff', glow: '#6ea8ff', flame: '#ffb35c',
      special: { id: 'sweep', name: 'Signature Sweep', icon: 'fa-fingerprint', cd: 14,
                 desc: 'A ring of 24 piercing shots in every direction.' } },
    { id: 'suricata', name: 'Suricata', hull: '#ffe3d8', glow: '#ff7a5c', flame: '#ffe16a',
      special: { id: 'ips', name: 'IPS Drop', icon: 'fa-shield-halved', cd: 18, dur: 5,
                 desc: 'For 5 s, a field around the ship drops every enemy bullet and burns what touches it.' } },
    { id: 'sigma',    name: 'Sigma',    hull: '#dcffe6', glow: '#4be08a', flame: '#6af0ff',
      special: { id: 'correlate', name: 'Correlation', icon: 'fa-hourglass-half', cd: 20, dur: 6,
                 desc: 'For 6 s, malware and their bullets move at half speed.' } },
    { id: 'zeek',     name: 'Zeek',     hull: '#e8dcff', glow: '#a06bff', flame: '#ff6bd8',
      special: { id: 'inspect', name: 'Deep Inspection', icon: 'fa-satellite-dish', cd: 15,
                 desc: 'Launches a swarm of 10 homing probes.' } },
];

// ── Keyboard actions — two configurable keys each (Settings → Keys).
// 1..4 (weapons) and Esc (pause / cancel) stay fixed.
export const KEY_ACTIONS = [
    { id: 'up', label: 'Thrust / move up' },
    { id: 'down', label: 'Brake / move down' },
    { id: 'left', label: 'Turn / move left' },
    { id: 'right', label: 'Turn / move right' },
    { id: 'fire', label: 'Fire' },
    { id: 'dash', label: 'Dash' },
    { id: 'bomb', label: 'Quarantine bomb' },
    { id: 'special', label: 'Ship power' },
    { id: 'weapon', label: 'Next weapon' },
    { id: 'pause', label: 'Pause' },
    { id: 'mute', label: 'Sound on / off' },
];
export const DEFAULT_KEYS = {
    up: ['ArrowUp', 'KeyW'], down: ['ArrowDown', 'KeyS'], left: ['ArrowLeft', 'KeyA'], right: ['ArrowRight', 'KeyD'],
    fire: ['Space', 'KeyJ'], dash: ['ShiftLeft', 'KeyK'], bomb: ['KeyE', 'KeyB'], special: ['KeyF', 'KeyL'],
    weapon: ['KeyQ', null], pause: ['KeyP', null], mute: ['KeyM', null],
};
export const RESERVED_KEYS = ['Escape', 'Digit1', 'Digit2', 'Digit3', 'Digit4'];

// ── Weapons — 1..4 to switch. Unlocked by beating the world bosses. ──────
export const WEAPONS = [
    { id: 'pulse',  name: 'Suricata Pulse', key: '1', icon: 'fa-circle-dot',
      desc: 'Fast single shots.', rate: 7, dmg: 1, speed: 13, count: 1, spread: 0, color: '#6ea8ff', unlock: null },
    { id: 'spread', name: 'YARA Spread', key: '2', icon: 'fa-burst',
      desc: 'Five-way fan, short range.', rate: 13, dmg: 0.8, speed: 11, count: 5, spread: 0.22, life: 42, color: '#ffd166', unlock: 0 },
    { id: 'rail',   name: 'Sigma Rail', key: '3', icon: 'fa-grip-lines',
      desc: 'Slow, heavy, pierces everything.', rate: 28, dmg: 4, speed: 24, count: 1, spread: 0, pierce: true, color: '#4be08a', unlock: 1 },
    { id: 'seeker', name: 'Zeek Seeker', key: '4', icon: 'fa-location-arrow',
      desc: 'Twin homing missiles.', rate: 20, dmg: 1.6, speed: 7, count: 2, spread: 0.6, homing: true, color: '#ff6bd8', unlock: 2 },
];

// ── Hangar upgrades — bought with bytes ────────────────────────────────
export const UPGRADES = [
    { id: 'damage',  name: 'Signature depth', icon: 'fa-crosshairs', desc: '+15% damage per level.', max: 5, base: 60 },
    { id: 'rate',    name: 'Parser speed',    icon: 'fa-gauge-high', desc: 'Fire 8% faster per level.', max: 5, base: 60 },
    { id: 'hp',      name: 'Integrity',       icon: 'fa-heart',      desc: '+1 max shield cell per level.', max: 3, base: 120 },
    { id: 'speed',   name: 'Thrusters',       icon: 'fa-forward',    desc: '+6% speed per level.', max: 4, base: 50 },
    { id: 'dash',    name: 'Hot patch',       icon: 'fa-person-running', desc: 'Dash recharges 12% faster per level.', max: 4, base: 50 },
    { id: 'bombs',   name: 'Quarantine bombs', icon: 'fa-bomb',      desc: '+1 bomb capacity per level.', max: 2, base: 140 },
    { id: 'magnet',  name: 'Collector',       icon: 'fa-magnet',     desc: 'Pick bytes up from further away.', max: 3, base: 40 },
];
export const upgradeCost = (u, lvl) => Math.round(u.base * Math.pow(1.7, lvl));

// ── Pickups ─────────────────────────────────────────────────────────────
export const PICKUPS = {
    byte:     { glyph: null,         color: '#5be7ff', r: 6 },
    heal:     { glyph: 'heart',      color: '#ff5d73', r: 13, label: '+1 INTEGRITY' },
    rapid:    { glyph: 'bolt',       color: '#ffd166', r: 13, label: 'RAPID FIRE', frames: 480 },
    shield:   { glyph: 'shield',     color: '#6ea8ff', r: 13, label: 'SHIELD', frames: 600 },
    bomb:     { glyph: 'bomb',       color: '#ff9f43', r: 13, label: '+1 BOMB' },
    overclock:{ glyph: 'fire',       color: '#ff6bd8', r: 13, label: 'OVERCLOCK x2', frames: 480 },
};

// ── Enemies ─────────────────────────────────────────────────────────────
// hp / speed / radius / score / bytes; behaviour lives in enemies.js.
export const ENEMIES = {
    worm:      { name: 'Worm',       hp: 2,  speed: 1.7, r: 16, score: 60,  bytes: 2, color: '#ff5d73', glyph: 'bug' },
    wormlet:   { name: 'Wormlet',    hp: 1,  speed: 2.6, r: 10, score: 25,  bytes: 1, color: '#ff8fa0', glyph: null },
    spammer:   { name: 'Spammer',    hp: 4,  speed: 0.9, r: 20, score: 120, bytes: 3, color: '#ffb35c', glyph: 'envelope' },
    trojan:    { name: 'Trojan',     hp: 3,  speed: 4.2, r: 15, score: 150, bytes: 4, color: '#ff4d4d', glyph: 'gift' },
    phisher:   { name: 'Phisher',    hp: 5,  speed: 1.1, r: 20, score: 160, bytes: 4, color: '#3ee0c8', glyph: 'fish' },
    drone:     { name: 'Bot',        hp: 1,  speed: 3.0, r: 11, score: 30,  bytes: 1, color: '#c08bff', glyph: null },
    botnet:    { name: 'C2 node',    hp: 16, speed: 0,   r: 30, score: 400, bytes: 12, color: '#a06bff', glyph: 'network', static: true },
    miner:     { name: 'Cryptominer', hp: 5, speed: 2.2, r: 17, score: 220, bytes: 8, color: '#ffd166', glyph: 'coins' },
    locker:    { name: 'Locker',     hp: 12, speed: 0.8, r: 26, score: 350, bytes: 8, color: '#ff7a3c', glyph: 'lock' },
    mine:      { name: 'Logic bomb', hp: 2,  speed: 0.5, r: 14, score: 80,  bytes: 2, color: '#ff9f43', glyph: 'bomb' },
    keylogger: { name: 'Keylogger',  hp: 4,  speed: 1.4, r: 16, score: 260, bytes: 6, color: '#7cf29a', glyph: 'keyboard' },
    rootkit:   { name: 'Rootkit',    hp: 6,  speed: 0,   r: 18, score: 300, bytes: 7, color: '#9b8cff', glyph: 'chip' },
    apt:       { name: 'APT operator', hp: 10, speed: 2.4, r: 18, score: 500, bytes: 12, color: '#ff3d7f', glyph: 'secret' },
    wiper:     { name: 'Wiper',      hp: 7,  speed: 3.4, r: 22, score: 320, bytes: 6, color: '#ffffff', glyph: 'biohazard' },
    beacon:    { name: 'C2 beacon',  hp: 22, speed: 0,   r: 32, score: 600, bytes: 15, color: '#ff5d73', glyph: 'satellite', static: true },
    decoy:     { name: 'Decoy',      hp: 1,  speed: 0,   r: 34, score: 50,  bytes: 0, color: '#8fa3ff', glyph: 'ghost' },
};

// ── Bosses (behaviour in bosses.js) ─────────────────────────────────────
export const BOSSES = [
    { id: 'phish',  name: 'PHISH KING',  hp: 300, color: '#3ee0c8', glyph: 'fish',
      intro: 'A lure so convincing the whole shallows took the bait. It hides its hooks behind gifts.' },
    { id: 'hive',   name: 'BOTNET HIVE', hp: 300, color: '#a06bff', glyph: 'network',
      intro: 'Ten thousand infected hosts, one brain. Take the C2 nodes down to reach the core.' },
    { id: 'locker', name: 'THE LOCKER',  hp: 420, color: '#ff7a3c', glyph: 'lock',
      intro: 'It encrypts everything it touches. Watch the arena: what turns red is lost.' },
    { id: 'ghost',  name: 'APT GHOST',   hp: 420, color: '#ff3d7f', glyph: 'ghost',
      intro: 'Patient, invisible, everywhere. Only one of them is real.' },
    { id: 'zeroday', name: 'ZERO-DAY',   hp: 820, color: '#ffffff', glyph: 'skull',
      intro: 'No signature. No patch. No name — until you write the rule that catches it.' },
];

// ── Worlds — map layout (node positions in 1280×720), theme, enemy pool ──
export const WORLDS = [
    {
        name: 'Phishing Shallows', sub: 'World 1', hue: '#3ee0c8', hue2: '#1b6f8f', bg: '#04131c',
        pool: ['worm', 'spammer', 'trojan', 'phisher'], boss: 0,
        story: 'Inboxes flooded, links everywhere. Every gift could be a trojan.',
        nodes: [[150, 560], [330, 430], [520, 520], [700, 360], [930, 300]],
        secret: [560, 190],
    },
    {
        name: 'Botnet Nebula', sub: 'World 2', hue: '#a06bff', hue2: '#4b2c8f', bg: '#0b0618',
        pool: ['worm', 'drone', 'botnet', 'miner', 'spammer'], boss: 1,
        story: 'A cloud of zombie hosts beams orders from command-and-control nodes.',
        nodes: [[160, 200], [360, 330], [300, 540], [620, 560], [930, 420]],
        secret: [760, 170],
    },
    {
        name: 'Ransomware Rift', sub: 'World 3', hue: '#ff7a3c', hue2: '#8f2b1b', bg: '#160604',
        pool: ['locker', 'mine', 'trojan', 'drone', 'miner'], boss: 2,
        story: 'Files locked, backups wiped, a countdown on every screen.',
        nodes: [[140, 380], [340, 220], [560, 330], [760, 520], [1000, 360]],
        secret: [420, 560],
    },
    {
        name: 'APT Deep', sub: 'World 4', hue: '#3ec7ff', hue2: '#173c6b', bg: '#030a14',
        pool: ['keylogger', 'rootkit', 'apt', 'phisher', 'mine'], boss: 3,
        story: 'Quiet. Too quiet. Someone has been inside for months.',
        nodes: [[180, 560], [260, 300], [520, 200], [760, 330], [1000, 520]],
        secret: [620, 600],
    },
    {
        name: 'Zero-Day Core', sub: 'World 5', hue: '#ff6bd8', hue2: '#6b1b5f', bg: '#0d0310',
        pool: ['apt', 'wiper', 'locker', 'rootkit', 'drone', 'keylogger'], boss: 4,
        story: 'The source. Every exploit chain in the graph leads here.',
        nodes: [[160, 360], [360, 200], [560, 360], [760, 200], [1010, 360]],
        secret: [560, 600],
    },
];

// ── Levels — 4 regular + 1 boss per world, plus a secret honeypot ──────
const OBJECTIVES = ['waves', 'survive', 'beacons', 'protect'];

export function levelDef(world, index) {
    const w = WORLDS[world];
    const tier = world * 4 + index;                 // 0..19 overall difficulty
    if (index === 4) {
        return { world, index, kind: 'boss', name: BOSSES[w.boss].name, boss: w.boss, par: 120 + world * 15,
                 desc: tr('Boss fight.') };
    }
    if (index === 5) {
        return { world, index, kind: 'honeypot', name: tr('Honeypot'), par: 45, duration: 45 * 60, tier,
                 desc: tr('Bonus level — bait the malware, collect every byte you can in 45 seconds.') };
    }
    const kind = OBJECTIVES[index];
    const base = { world, index, kind, tier, pool: w.pool };
    switch (kind) {
        case 'waves':
            return { ...base, name: tr('Initial access'), waves: 4 + Math.floor(world / 2), par: 70 + world * 10,
                     desc: tr('Clear every wave of malware.') };
        case 'survive':
            return { ...base, name: tr('Hold the line'), duration: (45 + world * 5) * 60, par: 0,
                     desc: tr('Survive {n} seconds of continuous infection.', { n: 45 + world * 5 }) };
        case 'beacons':
            return { ...base, name: tr('Cut the C2'), beacons: 3 + Math.min(2, world), par: 75 + world * 10,
                     desc: tr('Destroy the command-and-control beacons — they keep calling reinforcements.') };
        case 'protect':
            return { ...base, name: tr('Guard the sensor'), duration: (40 + world * 5) * 60, par: 0,
                     desc: tr('Keep the network sensor alive until the scan completes.') };
    }
}

export const levelKey = (world, index) => `${world}-${index}`;
export const LEVELS_PER_WORLD = 5;      // 4 regular + boss (the honeypot, index 5, is a bonus)

// Difficulty — scales enemy hp, enemy bullet speed and damage taken
export const DIFFICULTIES = [
    { id: 'analyst', name: 'Analyst', desc: 'Relaxed — tougher you, softer malware.', hp: 0.8, bullet: 0.85, spawn: 0.85, bytes: 1 },
    { id: 'hunter',  name: 'Threat hunter', desc: 'The intended experience.', hp: 1, bullet: 1, spawn: 1, bytes: 1 },
    { id: 'redteam', name: 'Red team', desc: 'Everything hits harder. Bytes x1.5.', hp: 1.35, bullet: 1.2, spawn: 1.2, bytes: 1.5 },
];
