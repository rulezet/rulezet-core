/**
 * save.js — campaign progress, kept in this browser only (localStorage).
 * Every access is wrapped: a private window or blocked storage just means
 * the progress lives for the session.
 */
import { levelKey, WORLDS, WEAPONS } from './data.js';

const KEY = 'rz-starfield-v2';

function fresh() {
    return {
        unlocked: { [levelKey(0, 0)]: true },
        stars: {},                 // "w-i" → 0..3
        best: {},                  // "w-i" → best score
        bosses: [],                // world indexes whose boss is beaten
        bytes: 0,
        upgrades: {},              // id → level
        skin: 'yara',
        difficulty: 'hunter',
        endless: [],               // [{score, wave, date}] top 10
        settings: { muted: false, music: true, shake: true, assist: false, controls: 'classic' },
        pos: { world: 0, node: 0 }, // where the ship stands on the map
        stats: { kills: 0, deaths: 0, played: 0 },
        seenIntro: false,
    };
}

let data = fresh();

export function load() {
    try {
        const raw = localStorage.getItem(KEY);
        if (raw) data = Object.assign(fresh(), JSON.parse(raw));
    } catch { data = fresh(); }
    data.settings = Object.assign(fresh().settings, data.settings || {});
    return data;
}

export function save() {
    try { localStorage.setItem(KEY, JSON.stringify(data)); } catch { /* session only */ }
}

/** Wipe everything — in place, so references held by the UI stay valid */
export function reset() {
    Object.keys(data).forEach(k => delete data[k]);
    Object.assign(data, fresh());
    save();
    return data;
}

export const get = () => data;

export const isUnlocked = (w, i) => !!data.unlocked[levelKey(w, i)];
export const starsOf = (w, i) => data.stars[levelKey(w, i)] || 0;
export const worldStars = (w) => [0, 1, 2, 3, 4].reduce((s, i) => s + starsOf(w, i), 0);
export const totalStars = () => WORLDS.reduce((s, _, w) => s + worldStars(w), 0) + WORLDS.reduce((s, _, w) => s + starsOf(w, 5), 0);
export const worldUnlocked = (w) => w === 0 || data.bosses.includes(w - 1);
export const secretUnlocked = (w) => worldStars(w) >= 10;
export const upgradeLevel = (id) => data.upgrades[id] || 0;

export function weaponsUnlocked() {
    return WEAPONS.filter(wp => wp.unlock === null || data.bosses.includes(wp.unlock)).map(wp => wp.id);
}

/** Record a finished level; returns what changed (for the results screen). */
export function completeLevel(w, i, { stars, score, bytes }) {
    const k = levelKey(w, i);
    const prevStars = data.stars[k] || 0;
    data.stars[k] = Math.max(prevStars, stars);
    data.best[k] = Math.max(data.best[k] || 0, score);
    data.bytes += bytes;
    const unlockedNow = [];
    const unlock = (ww, ii) => { const kk = levelKey(ww, ii); if (!data.unlocked[kk]) { data.unlocked[kk] = true; unlockedNow.push(kk); } };
    if (i < 4) unlock(w, i + 1);
    let newWeapon = null;
    if (i === 4 && !data.bosses.includes(w)) {
        data.bosses.push(w);
        if (w + 1 < WORLDS.length) unlock(w + 1, 0);
        newWeapon = WEAPONS.find(wp => wp.unlock === w) || null;
    }
    if (secretUnlocked(w)) unlock(w, 5);
    save();
    return { newStars: Math.max(0, stars - prevStars), unlockedNow, newWeapon, record: score >= (data.best[k] || 0) };
}

export function addEndlessScore(score, wave) {
    data.endless.push({ score, wave, date: new Date().toISOString().slice(0, 10) });
    data.endless.sort((a, b) => b.score - a.score);
    data.endless = data.endless.slice(0, 10);
    save();
    return data.endless.findIndex(e => e.score === score && e.wave === wave);
}
