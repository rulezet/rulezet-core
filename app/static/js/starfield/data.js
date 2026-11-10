/**
 * data.js — everything the game is made of, as data: worlds, levels,
 * enemies, bosses, weapons, upgrades, pickups, ships. The engine
 * (level.js, enemies.js, bosses*.js…) reads these tables; balancing the
 * game means editing numbers here.
 *
 * Act I  (worlds 0-4)  — the five threats that lead to the Zero-Day.
 * Act II (worlds 5-15) — the Deep Graph: one world per Rulezet format,
 *                        each engine freed gives its ship.
 * World / level indexes are the keys of every save ("w-i"): never reorder.
 *
 * The screen is a fixed 1280×720 logical space, scaled to the canvas;
 * "open" levels are bigger worlds (def.size) seen through a camera.
 */

import { tr } from './i18n.js';
import { levelStory } from './story.js';

export const W = 1280;
export const H = 720;
export const TAU = Math.PI * 2;

// ── Font Awesome 7 Free (solid) glyphs, drawn on the canvas with fillText ──
export const FA = {
    bug: '', robot: '', skull: '', lock: '', bolt: '',
    shield: '', heart: '', secret: '', envelope: '', fish: '',
    network: '', chip: '', bomb: '', keyboard: '', ghost: '',
    virus: '', coins: '', eyeSlash: '', crosshairs: '', gem: '',
    gift: '', fire: '', magnet: '', star: '', flag: '',
    eye: '', satellite: '', biohazard: '', key: '', sun: '',
    // Act II
    scroll: '', code: '', syringe: '', terminal: '', brain: '',
    mask: '', wand: '', userGear: '', gear: '', hammer: '',
    shuffle: '', cloud: '', fileExport: '', cube: '', clone: '',
    link: '', wifi: '', paperPlane: '', bacterium: '', virusCovid: '',
    database: '', server: '', fingerprint: '', binoculars: '', dragon: '',
    crown: '', snowflake: '', hourglass: '', door: '', flagCheck: '',
    atom: '', nodes: '', microscope: '', vial: '', dna: '',
    radiation: '', rocket: '', globe: '', chartLine: '', magnify: '',
    hurricane: '', spider: '', plug: '', filter: '', rewind: '',
    shieldVirus: '', heartPulse: '', fileLines: '', meteor: '', ban: '',
    tower: '', bullseye: '', diagram: '', wind: '', scissors: '',
    userShield: '', bookOpen: '', lockOpen: '',
};

// ── Ships — you ARE a detection rule. Each format has its own super power
// (F / gamepad Y), always available, recharging on its own (cd in seconds).
// unlock: world index whose boss frees the engine (null = from the start).
// shape: silhouette drawn by render.drawShip.
export const SKINS = [
    { id: 'yara',     name: 'YARA',     hull: '#dce6ff', glow: '#6ea8ff', flame: '#ffb35c', shape: 'dart', unlock: null,
      special: { id: 'sweep', name: 'Signature Sweep', icon: 'fa-fingerprint', cd: 14,
                 desc: 'A ring of 24 piercing shots in every direction.' } },
    { id: 'suricata', name: 'Suricata', hull: '#ffe3d8', glow: '#ff7a5c', flame: '#ffe16a', shape: 'wing', unlock: null,
      special: { id: 'ips', name: 'IPS Drop', icon: 'fa-shield-halved', cd: 18, dur: 5,
                 desc: 'For 5 s, a field around the ship drops every enemy bullet and burns what touches it.' } },
    { id: 'sigma',    name: 'Sigma',    hull: '#dcffe6', glow: '#4be08a', flame: '#6af0ff', shape: 'arrow', unlock: null,
      special: { id: 'correlate', name: 'Correlation', icon: 'fa-hourglass-half', cd: 20, dur: 6,
                 desc: 'For 6 s, malware and their bullets move at half speed.' } },
    { id: 'zeek',     name: 'Zeek',     hull: '#e8dcff', glow: '#a06bff', flame: '#ff6bd8', shape: 'ring', unlock: null,
      special: { id: 'inspect', name: 'Deep Inspection', icon: 'fa-satellite-dish', cd: 15,
                 desc: 'Launches a swarm of 10 homing probes.' } },
    // Act II — freed one world at a time
    { id: 'sagan',    name: 'Sagan',    hull: '#fff0d6', glow: '#ffb347', flame: '#ff7a3c', shape: 'scroll', unlock: 5,
      special: { id: 'threshold', name: 'Threshold Alert', icon: 'fa-bullseye', cd: 16,
                 desc: 'Marks every malware in sight; a second later each mark detonates for heavy damage.' } },
    { id: 'crs',      name: 'OWASP CRS', hull: '#ffe0f0', glow: '#ff4fa0', flame: '#ffd166', shape: 'shield', unlock: 6,
      special: { id: 'paranoia', name: 'Paranoia Level 4', icon: 'fa-shield-virus', cd: 18, dur: 5,
                 desc: 'For 5 s, every enemy bullet that comes close is reflected back as yours.' } },
    { id: 'nse',      name: 'Nmap NSE', hull: '#d8f4ff', glow: '#5bd1ff', flame: '#a0ffea', shape: 'dish', unlock: 7,
      special: { id: 'portscan', name: 'Port Sweep', icon: 'fa-tower-broadcast', cd: 15,
                 desc: 'A huge scan pulse: stuns every malware for 2 s, reveals what hides, lights the dark and the radar.' } },
    { id: 'nova',     name: 'NOVA',     hull: '#f0e4ff', glow: '#c9a7ff', flame: '#ff6bd8', shape: 'star', unlock: 8,
      special: { id: 'inject', name: 'Prompt Injection', icon: 'fa-wand-magic-sparkles', cd: 22, dur: 8,
                 desc: 'Rewrites the prompt of the 5 nearest malware: for 8 s they fight on your side.' } },
    { id: 'atr',      name: 'ATR',      hull: '#dcfff4', glow: '#6fffd2', flame: '#5bd1ff', shape: 'hex', unlock: 9,
      special: { id: 'agents', name: 'Agent Swarm', icon: 'fa-user-gear', cd: 22, dur: 10,
                 desc: 'Deploys 3 guardian agents that orbit the ship and shoot for 10 s.' } },
    { id: 'wazuh',    name: 'Wazuh',    hull: '#ffe6dc', glow: '#ff6a3d', flame: '#ffd166', shape: 'heavy', unlock: 10,
      special: { id: 'response', name: 'Active Response', icon: 'fa-bolt', cd: 9,
                 desc: 'Blinks forward, leaving a blast where you were and where you land.' } },
    { id: 'kql',      name: 'KQL',      hull: '#e0e8ff', glow: '#7f9cff', flame: '#5be7ff', shape: 'lance', unlock: 11,
      special: { id: 'join', name: 'Join Query', icon: 'fa-diagram-project', cd: 13,
                 desc: 'A lightning query that joins up to 10 malware in a chain.' } },
    { id: 'splunk',   name: 'Splunk',   hull: '#f4ffe0', glow: '#9dff6a', flame: '#ffd84f', shape: 'split', unlock: 12,
      special: { id: 'rewind', name: 'Timechart Rewind', icon: 'fa-clock-rotate-left', cd: 24,
                 desc: 'Rewinds your ship 3 seconds back in time — position and integrity — and clears the bullets around.' } },
    { id: 'elastic',  name: 'Elastic',  hull: '#e0faff', glow: '#5bc8ff', flame: '#ffd84f', shape: 'orb', unlock: 13,
      special: { id: 'gravity', name: 'Gravity Well', icon: 'fa-atom', cd: 18,
                 desc: 'Opens a well ahead that swallows bullets and pulls malware in, then collapses in a blast.' } },
    { id: 'kunai',    name: 'Kunai',    hull: '#fffbe0', glow: '#ffe14f', flame: '#ff6a3d', shape: 'blade', unlock: 14,
      special: { id: 'volley', name: 'Kunai Volley', icon: 'fa-wind', cd: 12,
                 desc: 'Throws 10 piercing kunai that fly out and come back to you.' } },
    { id: 'plum',     name: 'Plum Island', hull: '#f6e6ff', glow: '#d77bff', flame: '#6fffd2', shape: 'cross', unlock: 15,
      special: { id: 'net', name: 'Quarantine Net', icon: 'fa-snowflake', cd: 20, dur: 4,
                 desc: 'Throws a net ahead: everything inside — malware and bullets — freezes for 4 s.' } },
];

// ── Keyboard actions — two configurable keys each (Settings → Keys).
// 1..8 (weapons) and Esc (pause / cancel) stay fixed.
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
export const RESERVED_KEYS = ['Escape', 'Digit1', 'Digit2', 'Digit3', 'Digit4', 'Digit5', 'Digit6', 'Digit7', 'Digit8'];

// ── Weapons — 1..8 to switch. Unlocked by beating world bosses. ─────────
export const WEAPONS = [
    { id: 'pulse',  name: 'Suricata Pulse', key: '1', icon: 'fa-circle-dot',
      desc: 'Fast single shots.', rate: 7, dmg: 1, speed: 13, count: 1, spread: 0, color: '#6ea8ff', unlock: null },
    { id: 'spread', name: 'YARA Spread', key: '2', icon: 'fa-burst',
      desc: 'Five-way fan, short range.', rate: 13, dmg: 0.8, speed: 11, count: 5, spread: 0.22, life: 42, color: '#ffd166', unlock: 0 },
    { id: 'rail',   name: 'Sigma Rail', key: '3', icon: 'fa-grip-lines',
      desc: 'Slow, heavy, pierces everything.', rate: 28, dmg: 4, speed: 24, count: 1, spread: 0, pierce: true, color: '#4be08a', unlock: 1 },
    { id: 'seeker', name: 'Zeek Seeker', key: '4', icon: 'fa-location-arrow',
      desc: 'Twin homing missiles.', rate: 20, dmg: 1.6, speed: 7, count: 2, spread: 0.6, homing: true, color: '#ff6bd8', unlock: 2 },
    { id: 'beam',   name: 'CRS Beam', key: '5', icon: 'fa-wave-square',
      desc: 'A continuous laser: short range, burns everything on its line.', rate: 1, dmg: 0.2, range: 430, color: '#ff4fa0', unlock: 6 },
    { id: 'flak',   name: 'NOVA Flak', key: '6', icon: 'fa-meteor',
      desc: 'Slow shells that burst in a wide blast.', rate: 24, dmg: 2.4, speed: 9, count: 1, spread: 0, life: 36, blast: 80, color: '#c9a7ff', unlock: 8 },
    { id: 'arc',    name: 'Wazuh Arc', key: '7', icon: 'fa-bolt',
      desc: 'A bolt that jumps to 3 more malware.', rate: 15, dmg: 1.7, speed: 17, count: 1, spread: 0, chain: 3, color: '#7fe3ff', unlock: 10 },
    { id: 'blade',  name: 'Kunai Blades', key: '8', icon: 'fa-scissors',
      desc: 'Twin piercing blades that fly out and come back.', rate: 22, dmg: 1.8, speed: 12, count: 2, spread: 0.35, life: 64, pierce: true, boomerang: true, color: '#ffe14f', unlock: 14 },
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
    { id: 'power',   name: 'Engine tuning',   icon: 'fa-gears',      desc: 'Ship power recharges 10% faster per level.', max: 4, base: 90 },
    { id: 'armor',   name: 'Hardening',       icon: 'fa-user-shield', desc: '8% chance per level to shrug a hit off.', max: 3, base: 160 },
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
    // ── Act II ──
    flood:     { name: 'Log flooder', hp: 4, speed: 1.0, r: 19, score: 140, bytes: 3, color: '#ffb347', glyph: 'scroll' },
    tamper:    { name: 'Log tamperer', hp: 3, speed: 2.4, r: 15, score: 180, bytes: 4, color: '#ff8f6b', glyph: 'ban' },
    injector:  { name: 'SQL injector', hp: 5, speed: 1.2, r: 18, score: 220, bytes: 5, color: '#ff4fa0', glyph: 'syringe' },
    xss:       { name: 'XSS script', hp: 2,  speed: 3.2, r: 13, score: 120, bytes: 2, color: '#ffe14f', glyph: 'code' },
    scanner:   { name: 'Port scanner', hp: 6, speed: 0.9, r: 20, score: 260, bytes: 5, color: '#5bd1ff', glyph: 'binoculars' },
    scanbot:   { name: 'Mass scanner', hp: 2, speed: 3.4, r: 12, score: 70, bytes: 1, color: '#7fe3ff', glyph: 'wifi' },
    jailbreak: { name: 'Jailbreaker', hp: 6, speed: 1.6, r: 18, score: 300, bytes: 6, color: '#ff5bd7', glyph: 'mask' },
    halluc:    { name: 'Hallucination', hp: 5, speed: 0, r: 17, score: 260, bytes: 5, color: '#c9a7ff', glyph: 'wand' },
    rogue:     { name: 'Rogue agent', hp: 7, speed: 2.0, r: 18, score: 320, bytes: 7, color: '#6fffd2', glyph: 'userGear' },
    toolcall:  { name: 'Tool call',  hp: 1,  speed: 4.4, r: 9,  score: 30,  bytes: 0, color: '#b8fff0', glyph: 'gear' },
    brute:     { name: 'Brute-forcer', hp: 9, speed: 1.4, r: 22, score: 340, bytes: 7, color: '#ff6a3d', glyph: 'hammer' },
    lateral:   { name: 'Lateral mover', hp: 5, speed: 1.2, r: 16, score: 280, bytes: 6, color: '#9dff6a', glyph: 'shuffle' },
    obfusc:    { name: 'Obfuscator', hp: 7,  speed: 1.0, r: 19, score: 300, bytes: 6, color: '#b0c4ff', glyph: 'cloud' },
    exfil:     { name: 'Exfiltrator', hp: 6, speed: 2.8, r: 17, score: 400, bytes: 14, color: '#ffd84f', glyph: 'fileExport' },
    shard:     { name: 'Corrupted shard', hp: 8, speed: 1.2, r: 34, score: 160, bytes: 3, color: '#5bc8ff', glyph: 'cube' },
    fork:      { name: 'Fork bomb',  hp: 3,  speed: 1.8, r: 14, score: 110, bytes: 1, color: '#ff9e3d', glyph: 'clone' },
    latch:     { name: 'Kprobe hook', hp: 2, speed: 3.6, r: 11, score: 150, bytes: 2, color: '#c0ff5b', glyph: 'link' },
    spore:     { name: 'Spore',      hp: 3,  speed: 0.7, r: 16, score: 140, bytes: 3, color: '#d77bff', glyph: 'bacterium' },
    benign:    { name: 'Clean traffic', hp: 3, speed: 1.6, r: 15, score: 0, bytes: 0, color: '#4be08a', glyph: 'paperPlane', benign: true },
    courier:   { name: 'Exfil courier', hp: 70, speed: 3.0, r: 24, score: 2500, bytes: 30, color: '#ffd84f', glyph: 'fileExport' },
    implant:   { name: 'Implant',    hp: 10, speed: 0,   r: 20, score: 600, bytes: 10, color: '#ff4d6d', glyph: 'spider', static: true },
};

// ── Bosses (behaviour in bosses.js for Act I, bosses2.js for Act II) ──────
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
    // ── Act II ──
    { id: 'flood',   name: 'THE FLOOD',   hp: 560, color: '#ffb347', glyph: 'scroll',
      intro: 'A leviathan made of a billion log lines. Only its head is real — the rest is noise.' },
    { id: 'hydra',   name: 'SQL HYDRA',   hp: 600, color: '#ff4fa0', glyph: 'dragon',
      intro: 'Cut one query, two grow back. Strike the core while its heads are down.' },
    { id: 'recon',   name: 'RECON EYE',   hp: 620, color: '#5bd1ff', glyph: 'eye',
      intro: 'It scans every port in the sector. Stay out of its beam — hide behind the rocks.' },
    { id: 'halluc',  name: 'THE HALLUCINATOR', hp: 640, color: '#c9a7ff', glyph: 'wand',
      intro: 'It learned your rule by heart. Now it flies like you, shoots like you — and lies to your controls.' },
    { id: 'orch',    name: 'ROGUE ORCHESTRATOR', hp: 660, color: '#6fffd2', glyph: 'nodes',
      intro: 'A hundred agents, one corrupted planner. While they are tethered, it cannot be touched.' },
    { id: 'brute',   name: 'THE BRUTE',   hp: 720, color: '#ff6a3d', glyph: 'hammer',
      intro: 'Ten million passwords a second. Let it charge, dodge, and strike it while it reels from the wall.' },
    { id: 'obfusc',  name: 'THE OBFUSCATOR', hp: 600, color: '#b0c4ff', glyph: 'cloud',
      intro: 'Four copies, one real. Read the query at the top of the screen: only the matching one is it.' },
    { id: 'replay',  name: 'THE REPLAY',  hp: 700, color: '#ffd84f', glyph: 'rewind',
      intro: 'It indexes your past. Every path you fly comes back as a ghost three seconds later.' },
    { id: 'queen',   name: 'SHARD QUEEN', hp: 760, color: '#5bc8ff', glyph: 'crown',
      intro: 'The cluster mind. Break her and she reshards — every piece must fall.' },
    { id: 'panic',   name: 'KERNEL PANIC', hp: 780, color: '#ff9e3d', glyph: 'terminal',
      intro: 'Ring zero. It forks itself and burns the syscall table into laser grids.' },
    { id: 'zero',    name: 'PATIENT ZERO', hp: 1000, color: '#d77bff', glyph: 'virusCovid',
      intro: 'The source of the outbreak. Everything it touches turns into it. Quarantine it — forever.' },
];

// ── Worlds — map layout (node positions in 1280×720), theme, enemy pool ──
// format: the Rulezet format the world belongs to (Act II).
// levels: Act II levels, index 0-3 (the boss and the honeypot are generic).
export const WORLDS = [
    {
        name: 'Phishing Shallows', sub: 'World 1', hue: '#3ee0c8', hue2: '#1b6f8f', bg: '#04131c', planet: 'ocean',
        pool: ['worm', 'spammer', 'trojan', 'phisher'], boss: 0,
        story: 'Inboxes flooded, links everywhere. Every gift could be a trojan.',
        nodes: [[150, 560], [330, 430], [520, 520], [700, 360], [930, 300]],
        secret: [560, 190],
    },
    {
        name: 'Botnet Nebula', sub: 'World 2', hue: '#a06bff', hue2: '#4b2c8f', bg: '#0b0618', planet: 'gas',
        pool: ['worm', 'drone', 'botnet', 'miner', 'spammer'], boss: 1,
        story: 'A cloud of zombie hosts beams orders from command-and-control nodes.',
        nodes: [[160, 200], [360, 330], [300, 540], [620, 560], [930, 420]],
        secret: [760, 170],
    },
    {
        name: 'Ransomware Rift', sub: 'World 3', hue: '#ff7a3c', hue2: '#8f2b1b', bg: '#160604', planet: 'lava',
        pool: ['locker', 'mine', 'trojan', 'drone', 'miner'], boss: 2,
        story: 'Files locked, backups wiped, a countdown on every screen.',
        nodes: [[140, 380], [340, 220], [560, 330], [760, 520], [1000, 360]],
        secret: [420, 560],
    },
    {
        name: 'APT Deep', sub: 'World 4', hue: '#3ec7ff', hue2: '#173c6b', bg: '#030a14', planet: 'ice',
        pool: ['keylogger', 'rootkit', 'apt', 'phisher', 'mine'], boss: 3,
        story: 'Quiet. Too quiet. Someone has been inside for months.',
        nodes: [[180, 560], [260, 300], [520, 200], [760, 330], [1000, 520]],
        secret: [620, 600],
    },
    {
        name: 'Zero-Day Core', sub: 'World 5', hue: '#ff6bd8', hue2: '#6b1b5f', bg: '#0d0310', planet: 'core',
        pool: ['apt', 'wiper', 'locker', 'rootkit', 'drone', 'keylogger'], boss: 4,
        story: 'The source. Every exploit chain in the graph leads here.',
        nodes: [[160, 360], [360, 200], [560, 360], [760, 200], [1010, 360]],
        secret: [560, 600],
    },
    // ═════════════ ACT II — THE DEEP GRAPH ═════════════
    {
        name: 'Log Flood Delta', sub: 'World 6', format: 'sagan', hue: '#ffb347', hue2: '#8f4b1b', bg: '#140a02', planet: 'desert',
        pool: ['flood', 'tamper', 'spammer', 'worm', 'drone'], boss: 5,
        story: 'Sagan\'s log rivers burst their banks. Somewhere in the flood, someone is erasing the evidence.',
        nodes: [[150, 520], [330, 360], [540, 470], [740, 300], [960, 400]],
        secret: [560, 180],
        levels: [
            { kind: 'waves', waves: 5, par: 150, mods: { storm: true } },
            { kind: 'escort', size: [4400, 1500], par: 150, convoyHp: 34 },
            { kind: 'capture', size: [3000, 2000], nodes: 4, capTime: 5, par: 140 },
            { kind: 'survive', duration: 70 * 60, mods: { dark: true } },
        ],
    },
    {
        name: 'Injection Bay', sub: 'World 7', format: 'crs', hue: '#ff4fa0', hue2: '#7a1b4b', bg: '#12030b', planet: 'neon',
        pool: ['injector', 'xss', 'trojan', 'phisher', 'flood'], boss: 6,
        story: 'The web front of the graph. Every request could carry a payload — and most of them are clean.',
        nodes: [[170, 300], [360, 480], [560, 330], [760, 500], [980, 330]],
        secret: [600, 600],
        levels: [
            { kind: 'triage', quota: 26, maxFp: 5, par: 110 },
            { kind: 'gauntlet', size: [6400, 1000], gates: 10, par: 110 },
            { kind: 'waves', waves: 5, par: 170, mods: { rocks: 10 } },
            { kind: 'protect', duration: 65 * 60 },
        ],
    },
    {
        name: 'Scanner Expanse', sub: 'World 8', format: 'nse', hue: '#5bd1ff', hue2: '#174a6b', bg: '#020d14', planet: 'ringed',
        pool: ['scanner', 'scanbot', 'keylogger', 'drone', 'lateral'], boss: 7,
        story: 'Nmap\'s sky, now crawling with hostile recon. Somebody is mapping every port of the graph.',
        nodes: [[140, 420], [330, 250], [560, 400], [760, 230], [990, 380]],
        secret: [420, 600],
        levels: [
            { kind: 'keys', size: [3600, 2400], keys: 6, par: 170, mods: { rocks: 26 } },
            { kind: 'dark', size: [2800, 1800], targets: 6, par: 160 },
            { kind: 'beacons', size: [3000, 2000], beacons: 5, par: 150, mods: { rocks: 18 } },
            { kind: 'pursuit', size: [4000, 2600], courierHp: 70, par: 120, mods: { rocks: 20 } },
        ],
    },
    {
        name: 'Prompt Nebula', sub: 'World 9', format: 'nova', hue: '#c9a7ff', hue2: '#4b2c7a', bg: '#0a0614', planet: 'gas',
        pool: ['jailbreak', 'halluc', 'phisher', 'xss', 'drone'], boss: 8,
        story: 'NOVA guards the prompts that drive the graph\'s assistants. Jailbreakers are rewriting them, one token at a time.',
        nodes: [[160, 560], [300, 330], [540, 230], [760, 420], [990, 300]],
        secret: [700, 610],
        levels: [
            { kind: 'triage', quota: 28, maxFp: 5, par: 120 },
            { kind: 'survive', duration: 70 * 60, mods: { storm: true } },
            { kind: 'capture', size: [3000, 2000], nodes: 5, capTime: 5, par: 160 },
            { kind: 'waves', waves: 5, par: 190, mods: { dark: true } },
        ],
    },
    {
        name: 'Agent Ring', sub: 'World 10', format: 'atr', hue: '#6fffd2', hue2: '#1b6b5a', bg: '#02120e', planet: 'station',
        pool: ['rogue', 'toolcall', 'jailbreak', 'drone', 'apt'], boss: 9,
        story: 'A ring of autonomous agents that run the graph\'s chores. Some of them stopped listening.',
        nodes: [[150, 330], [330, 520], [540, 380], [740, 540], [980, 400]],
        secret: [560, 170],
        levels: [
            { kind: 'defend', size: [3000, 2000], servers: 3, duration: 75 * 60 },
            { kind: 'keys', size: [3600, 2400], keys: 6, par: 180 },
            { kind: 'escort', size: [4600, 1500], par: 160, convoyHp: 36, mods: { rocks: 14 } },
            { kind: 'waves', waves: 6, par: 200, mods: { rocks: 10 } },
        ],
    },
    {
        name: 'Brute Force Belt', sub: 'World 11', format: 'wazuh', hue: '#ff6a3d', hue2: '#7a2b14', bg: '#140602', planet: 'asteroid',
        pool: ['brute', 'lateral', 'keylogger', 'locker', 'mine'], boss: 10,
        story: 'Wazuh\'s asteroid belt of endpoints, hammered by a billion login attempts an hour.',
        nodes: [[150, 520], [350, 400], [560, 540], [740, 360], [980, 470]],
        secret: [360, 180],
        levels: [
            { kind: 'survive', duration: 75 * 60, mods: { rocks: 12 } },
            { kind: 'gauntlet', size: [7000, 1000], gates: 12, par: 120, mods: { mines: 10 } },
            { kind: 'defend', size: [3000, 2000], servers: 3, duration: 80 * 60 },
            { kind: 'pursuit', size: [4200, 2600], courierHp: 80, par: 130 },
        ],
    },
    {
        name: 'Kusto Clusters', sub: 'World 12', format: 'kql', hue: '#7f9cff', hue2: '#2b3a7a', bg: '#03061a', planet: 'crystal',
        pool: ['obfusc', 'lateral', 'rootkit', 'apt', 'injector'], boss: 11,
        story: 'Tables of telemetry as far as the eye can see. The attacker hides in the noise — you need the right query.',
        nodes: [[160, 250], [340, 420], [560, 280], [760, 470], [990, 320]],
        secret: [620, 610],
        levels: [
            { kind: 'capture', size: [3000, 2000], nodes: 5, capTime: 5, par: 170 },
            { kind: 'triage', quota: 30, maxFp: 4, par: 130 },
            { kind: 'dark', size: [3000, 2000], targets: 7, par: 180, mods: { rocks: 16 } },
            { kind: 'beacons', size: [3000, 2000], beacons: 6, par: 160, mods: { rocks: 14 } },
        ],
    },
    {
        name: 'Timeline Canyon', sub: 'World 13', format: 'splunk', hue: '#9dff6a', hue2: '#2f6b1b', bg: '#051202', planet: 'canyon',
        pool: ['exfil', 'flood', 'tamper', 'keylogger', 'miner'], boss: 12,
        story: 'Splunk\'s canyon of indexed time. Every event is here — until someone carries it away.',
        nodes: [[140, 400], [330, 230], [540, 420], [760, 260], [990, 430]],
        secret: [380, 600],
        levels: [
            { kind: 'pursuit', size: [4000, 2600], courierHp: 85, par: 120, mods: { rocks: 14 } },
            { kind: 'escort', size: [4800, 1500], par: 170, convoyHp: 38 },
            { kind: 'waves', waves: 6, par: 200, mods: { storm: true } },
            { kind: 'keys', size: [3800, 2400], keys: 6, par: 190, mods: { rocks: 20 } },
        ],
    },
    {
        name: 'Shard Field', sub: 'World 14', format: 'elastic', hue: '#5bc8ff', hue2: '#1b4b7a', bg: '#020a14', planet: 'shattered',
        pool: ['shard', 'exfil', 'scanbot', 'wiper', 'drone'], boss: 13,
        story: 'Elastic\'s cluster shattered into a field of drifting shards. Corrupted ones keep splitting.',
        nodes: [[160, 540], [320, 320], [560, 450], [760, 280], [990, 420]],
        secret: [580, 170],
        levels: [
            { kind: 'purge', waves: 3, par: 110 },
            { kind: 'keys', size: [3600, 2400], keys: 6, par: 180, mods: { rocks: 30 } },
            { kind: 'defend', size: [3000, 2000], servers: 3, duration: 80 * 60 },
            { kind: 'purge', waves: 4, par: 150, mods: { dark: true } },
        ],
    },
    {
        name: 'Kernel Ring', sub: 'World 15', format: 'kunai', hue: '#ff9e3d', hue2: '#7a3f14', bg: '#120802', planet: 'core',
        pool: ['fork', 'latch', 'rootkit', 'wiper', 'mine'], boss: 14,
        story: 'Ring zero of every Linux host in the graph. Kunai saw the hooks come in — then went silent.',
        nodes: [[150, 300], [330, 500], [540, 330], [760, 520], [990, 340]],
        secret: [560, 620],
        levels: [
            { kind: 'gauntlet', size: [7200, 1000], gates: 13, par: 125 },
            { kind: 'dark', size: [3000, 2000], targets: 7, par: 180 },
            { kind: 'survive', duration: 80 * 60 },
            { kind: 'capture', size: [3200, 2000], nodes: 5, capTime: 6, par: 180, mods: { rocks: 12 } },
        ],
    },
    {
        name: 'Plum Island', sub: 'World 16', format: 'plum', hue: '#d77bff', hue2: '#5f1b7a', bg: '#0c0312', planet: 'bio',
        pool: ['spore', 'scanbot', 'fork', 'apt', 'wiper', 'latch'], boss: 15,
        story: 'The quarantine lab at the edge of the internet. The outbreak started here — and here it must end.',
        nodes: [[160, 420], [340, 240], [560, 420], [760, 240], [1010, 380]],
        secret: [560, 620],
        levels: [
            { kind: 'triage', quota: 32, maxFp: 4, par: 130 },
            { kind: 'keys', size: [3800, 2600], keys: 6, par: 200, mods: { rocks: 22, dark: true } },
            { kind: 'escort', size: [5000, 1600], par: 180, convoyHp: 40, mods: { rocks: 12 } },
            { kind: 'defend', size: [3000, 2000], servers: 3, duration: 85 * 60, mods: { dark: true } },
        ],
    },
];
export const ACT2_FIRST_WORLD = 5;

// ── Levels — 4 regular + 1 boss per world, plus a secret honeypot ──────
const OBJECTIVES = ['waves', 'survive', 'beacons', 'protect'];

/** Overall difficulty of a level: grows fast in Act I, slowly in Act II (enemy hp would get spongy). */
function tierOf(world, index) {
    if (world < ACT2_FIRST_WORLD) return world * 4 + index;
    return 20 + (world - ACT2_FIRST_WORLD) * 1.6 + index * 0.4;
}

/** Short, objective text for a level kind (the story is in story.js) */
function objectiveText(d) {
    switch (d.kind) {
        case 'waves': return tr('Clear every wave of malware.');
        case 'survive': return tr('Survive {n} seconds of continuous infection.', { n: Math.round(d.duration / 60) });
        case 'beacons': return tr('Destroy the command-and-control beacons — they keep calling reinforcements.');
        case 'protect': return tr('Keep the network sensor alive until the scan completes.');
        case 'keys': return tr('Open space: find the {n} keys hidden in the sector, then reach the exit gate.', { n: d.keys });
        case 'escort': return tr('Escort the data convoy to the far end of the sector. It only moves when you stay close.');
        case 'capture': return tr('Stand inside each of the {n} relays until it is captured.', { n: d.nodes });
        case 'pursuit': return tr('An exfiltration courier is running for the exit gate. Catch it and destroy it.');
        case 'dark': return tr('Blackout: hunt down the {n} hidden implants. Your scanner pulses every few seconds.', { n: d.targets });
        case 'purge': return tr('Purge every corrupted shard — they split when hit.');
        case 'gauntlet': return tr('Fly through the firewall corridor to the exit — mind the laser gates.');
        case 'triage': return tr('Destroy {n} malicious packets. Green traffic is clean: shooting it is a false positive.', { n: d.quota });
        case 'defend': return tr('Keep the {n} servers alive for {s} seconds — they are far apart.', { n: d.servers, s: Math.round(d.duration / 60) });
        default: return '';
    }
}

export function levelDef(world, index) {
    const w = WORLDS[world];
    const tier = tierOf(world, Math.min(index, 3));
    const st = levelStory(world, index);
    let d;
    if (index === 4) {
        d = { world, index, kind: 'boss', name: BOSSES[w.boss].name, boss: w.boss, par: 120 + Math.min(world, 8) * 15, tier,
              desc: tr('Boss fight.') };
    } else if (index === 5) {
        d = { world, index, kind: 'honeypot', name: tr('Honeypot'), par: 45, duration: 45 * 60, tier,
              desc: tr('Bonus level — bait the malware, collect every byte you can in 45 seconds.') };
    } else if (w.levels) {
        d = { world, index, tier, pool: w.pool, mods: {}, ...w.levels[index] };
        d.mods = { ...(w.levels[index].mods || {}) };
    } else {
        const kind = OBJECTIVES[index];
        const base = { world, index, kind, tier, pool: w.pool, mods: {} };
        switch (kind) {
            case 'waves': d = { ...base, name: tr('Initial access'), waves: 4 + Math.floor(world / 2), par: 70 + world * 10 }; break;
            case 'survive': d = { ...base, name: tr('Hold the line'), duration: (45 + world * 5) * 60, par: 0 }; break;
            case 'beacons': d = { ...base, name: tr('Cut the C2'), beacons: 3 + Math.min(2, world), par: 75 + world * 10 }; break;
            default: d = { ...base, name: tr('Guard the sensor'), duration: (40 + world * 5) * 60, par: 0 }; break;
        }
    }
    if (!d.desc) d.desc = objectiveText(d);
    if (!d.par && d.par !== 0) d.par = 0;
    d.mods = d.mods || {};
    d.open = !!d.size;
    // the story: a name of its own, a briefing, radio lines and a debrief
    if (st) {
        if (index !== 4 && st.name) d.name = st.name;
        d.brief = st.brief || '';
        d.radio = st.radio || [];
        d.outro = st.outro || '';
    } else { d.brief = ''; d.radio = []; d.outro = ''; }
    return d;
}

export const levelKey = (world, index) => `${world}-${index}`;
export const LEVELS_PER_WORLD = 5;      // 4 regular + boss (the honeypot, index 5, is a bonus)

// Difficulty — scales enemy hp, enemy bullet speed and damage taken
export const DIFFICULTIES = [
    { id: 'analyst', name: 'Analyst', desc: 'Relaxed — tougher you, softer malware.', hp: 0.8, bullet: 0.85, spawn: 0.85, bytes: 1 },
    { id: 'hunter',  name: 'Threat hunter', desc: 'The intended experience.', hp: 1, bullet: 1, spawn: 1, bytes: 1 },
    { id: 'redteam', name: 'Red team', desc: 'Everything hits harder. Bytes x1.5.', hp: 1.35, bullet: 1.2, spawn: 1.2, bytes: 1.5 },
];
