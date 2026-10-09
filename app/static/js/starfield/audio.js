/**
 * audio.js — procedural sound effects and music (Web Audio API). No audio
 * files: every sound is synthesised, so there is nothing to license. Safe
 * where Web Audio is missing (every call becomes a no-op).
 */

let ctx = null;
let master = null;
let sfxGain = null;
let musicGain = null;
let muted = false;
let musicOn = true;
// Browsers only let audio start after a user gesture: nothing is created
// before Audio.unlock() (first click / key press), music asked for earlier
// waits in pendingTheme.
let unlocked = false;
let pendingTheme = null;

function ensure() {
    if (typeof window === 'undefined' || !unlocked) return null;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    if (!ctx) {
        ctx = new AC();
        // a compressor keeps 30 explosions + music from clipping
        const comp = ctx.createDynamicsCompressor();
        comp.threshold.value = -14; comp.knee.value = 12; comp.ratio.value = 6;
        comp.connect(ctx.destination);
        master = ctx.createGain(); master.gain.value = muted ? 0 : 1; master.connect(comp);
        sfxGain = ctx.createGain(); sfxGain.gain.value = 1.6; sfxGain.connect(master);
        musicGain = ctx.createGain(); musicGain.gain.value = 1.1; musicGain.connect(master);
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
}

function tone({ type = 'square', f0, f1 = f0, dur = 0.1, vol = 0.2, delay = 0, out = null }) {
    const c = ensure(); if (!c || muted) return;
    const t = c.currentTime + delay;
    const o = c.createOscillator(); const g = c.createGain();
    o.type = type;
    o.frequency.setValueAtTime(f0, t);
    if (f1 !== f0) o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(out || sfxGain);
    o.start(t); o.stop(t + dur + 0.02);
}

let noiseBuf = null;
function noise({ dur = 0.3, freq = 1200, vol = 0.3, delay = 0, q = 0.8, sweep = null }) {
    const c = ensure(); if (!c || muted) return;
    if (!noiseBuf) {
        noiseBuf = c.createBuffer(1, c.sampleRate, c.sampleRate);
        const d = noiseBuf.getChannelData(0);
        for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    const t = c.currentTime + delay;
    const s = c.createBufferSource(); s.buffer = noiseBuf;
    const f = c.createBiquadFilter(); f.type = 'lowpass'; f.Q.value = q;
    f.frequency.setValueAtTime(freq, t);
    if (sweep) f.frequency.exponentialRampToValueAtTime(sweep, t + dur);
    const g = c.createGain();
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f); f.connect(g); g.connect(sfxGain);
    s.start(t, Math.random() * 0.5); s.stop(t + dur + 0.02);
}

// Throttle very frequent sounds so 40 bullets don't make 40 voices
const last = {};
function throttled(key, ms) {
    const now = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    if (last[key] && now - last[key] < ms) return false;
    last[key] = now; return true;
}

export const Sfx = {
    shoot(weapon) {
        if (!throttled('shoot', 45)) return;
        if (weapon === 'rail') { tone({ type: 'sawtooth', f0: 1400, f1: 120, dur: 0.22, vol: 0.12 }); noise({ dur: 0.12, freq: 4000, vol: 0.08 }); }
        else if (weapon === 'spread') tone({ type: 'square', f0: 520, f1: 260, dur: 0.07, vol: 0.06 });
        else if (weapon === 'seeker') tone({ type: 'triangle', f0: 300, f1: 700, dur: 0.12, vol: 0.08 });
        else tone({ type: 'square', f0: 880, f1: 440, dur: 0.06, vol: 0.06 });
    },
    enemyShoot() { if (throttled('eshoot', 70)) tone({ type: 'sawtooth', f0: 300, f1: 160, dur: 0.09, vol: 0.04 }); },
    hit() { if (throttled('hit', 40)) tone({ type: 'square', f0: 220, f1: 110, dur: 0.05, vol: 0.05 }); },
    explode(big) {
        if (!throttled(big ? 'boom' : 'pop', big ? 60 : 35)) return;
        noise({ dur: big ? 0.7 : 0.25, freq: big ? 900 : 2200, sweep: 80, vol: big ? 0.45 : 0.2 });
        if (big) tone({ type: 'sine', f0: 90, f1: 30, dur: 0.6, vol: 0.35 });
    },
    hurt() { tone({ type: 'sawtooth', f0: 400, f1: 60, dur: 0.35, vol: 0.2 }); noise({ dur: 0.3, freq: 600, vol: 0.2 }); },
    pickup() { if (throttled('pick', 30)) tone({ type: 'sine', f0: 1200, f1: 1800, dur: 0.06, vol: 0.05 }); },
    powerup() { [660, 880, 1320].forEach((f, i) => tone({ type: 'triangle', f0: f, dur: 0.12, vol: 0.12, delay: i * 0.07 })); },
    dash() { noise({ dur: 0.18, freq: 3000, sweep: 400, vol: 0.12 }); },
    bomb() { noise({ dur: 1.2, freq: 1800, sweep: 40, vol: 0.6 }); tone({ type: 'sine', f0: 140, f1: 20, dur: 1.1, vol: 0.45 }); },
    shieldBreak() { tone({ type: 'triangle', f0: 1600, f1: 300, dur: 0.3, vol: 0.15 }); },
    warning() { [0, 0.35, 0.7].forEach(d => tone({ type: 'square', f0: 220, f1: 220, dur: 0.22, vol: 0.12, delay: d })); },
    telegraph() { if (throttled('tele', 200)) tone({ type: 'sine', f0: 900, f1: 1400, dur: 0.15, vol: 0.05 }); },
    beam() { if (throttled('beam', 250)) { tone({ type: 'sawtooth', f0: 80, f1: 60, dur: 0.5, vol: 0.12 }); } },
    countdown(go) { tone({ type: 'square', f0: go ? 1320 : 660, dur: go ? 0.3 : 0.12, vol: 0.12 }); },
    levelUp() { [523, 659, 784, 1047].forEach((f, i) => tone({ type: 'square', f0: f, dur: 0.14, vol: 0.1, delay: i * 0.09 })); },
    victory() { [523, 659, 784, 1047, 784, 1047, 1319].forEach((f, i) => tone({ type: 'triangle', f0: f, dur: 0.22, vol: 0.14, delay: i * 0.13 })); },
    gameOver() { [392, 330, 262, 196].forEach((f, i) => tone({ type: 'sawtooth', f0: f, dur: 0.35, vol: 0.12, delay: i * 0.25 })); },
    star(i) { tone({ type: 'triangle', f0: 880 + i * 220, dur: 0.25, vol: 0.14 }); },
    buy() { tone({ type: 'square', f0: 990, f1: 1480, dur: 0.12, vol: 0.1 }); tone({ type: 'square', f0: 1480, dur: 0.12, vol: 0.08, delay: 0.1 }); },
    deny() { tone({ type: 'square', f0: 180, dur: 0.15, vol: 0.1 }); },
    move() { tone({ type: 'sine', f0: 600, f1: 800, dur: 0.05, vol: 0.05 }); },
    bossRoar() { noise({ dur: 1.5, freq: 400, sweep: 60, vol: 0.5, q: 4 }); tone({ type: 'sawtooth', f0: 70, f1: 40, dur: 1.4, vol: 0.3 }); },
};

// ── Music: a tiny step sequencer. One scale / tempo per world, a darker,
// faster pattern for bosses, a calm one for the map. ─────────────────────
const SCALES = {
    map:    { root: 220, steps: [0, 3, 7, 10, 12, 10, 7, 3], bpm: 92, bass: [0, 0, 5, 3] },
    w0:     { root: 196, steps: [0, 4, 7, 11, 12, 11, 7, 4], bpm: 118, bass: [0, 0, 5, 7] },
    w1:     { root: 174.6, steps: [0, 3, 7, 8, 12, 8, 7, 3], bpm: 124, bass: [0, 8, 5, 3] },
    w2:     { root: 164.8, steps: [0, 1, 5, 7, 8, 7, 5, 1], bpm: 132, bass: [0, 0, 1, 5] },
    w3:     { root: 146.8, steps: [0, 3, 6, 10, 12, 10, 6, 3], bpm: 128, bass: [0, 6, 3, 0] },
    w4:     { root: 130.8, steps: [0, 2, 3, 7, 8, 7, 3, 2], bpm: 140, bass: [0, 1, 0, 6] },
    boss:   { root: 110, steps: [0, 1, 6, 7, 12, 7, 6, 1], bpm: 150, bass: [0, 0, 1, 1] },
    final:  { root: 98, steps: [0, 3, 6, 9, 12, 9, 6, 3], bpm: 158, bass: [0, 6, 0, 1] },
};

let timer = null;
let step = 0;
let nextTime = 0;
let theme = null;

function semis(root, s) { return root * Math.pow(2, s / 12); }

function schedule() {
    const c = ensure(); if (!c || !theme) return;
    const spb = 60 / theme.bpm / 2;               // eighth notes
    // Back from a hidden tab the timer ran late: skip the missed notes
    // instead of creating hundreds of them at once (that froze the page).
    if (nextTime < c.currentTime) nextTime = c.currentTime + 0.05;
    let guard = 0;
    while (nextTime < c.currentTime + 0.2 && guard++ < 8) {
        const t0 = nextTime - c.currentTime;
        if (!muted && musicOn) {
            const n = theme.steps[step % theme.steps.length];
            const oct = (Math.floor(step / 8) % 2) ? 12 : 0;
            tone({ type: 'square', f0: semis(theme.root * 2, n + oct), dur: spb * 0.9, vol: 0.05, delay: t0, out: musicGain });
            if (step % 4 === 0) {
                const b = theme.bass[(step / 4) % theme.bass.length];
                tone({ type: 'triangle', f0: semis(theme.root / 2, b), dur: spb * 3.5, vol: 0.18, delay: t0, out: musicGain });
            }
            if (step % 4 === 0) tone({ type: 'sine', f0: 140, f1: 40, dur: 0.12, vol: 0.25, delay: t0, out: musicGain });
            if (theme.bpm >= 140 && step % 2 === 1) noise({ dur: 0.04, freq: 8000, vol: 0.03, delay: t0 });
        }
        nextTime += spb;
        step++;
    }
}

export const Music = {
    play(name) {
        if (!unlocked) { pendingTheme = name; return; }
        const c = ensure(); if (!c) return;
        const next = SCALES[name] || SCALES.map;
        if (theme === next && timer) return;
        theme = next; step = 0; nextTime = c.currentTime + 0.05;
        if (!timer) timer = setInterval(schedule, 50);
    },
    stop() { if (timer) clearInterval(timer); timer = null; theme = null; pendingTheme = null; },
    /** Suspend the whole audio engine while the tab is hidden */
    sleep(hidden) { if (!ctx) return; try { hidden ? ctx.suspend() : ctx.resume(); } catch { /* ignore */ } },
    setEnabled(v) { musicOn = v; },
};

export const Audio = {
    unlock() {
        const first = !unlocked;
        unlocked = true;
        ensure();
        if (first && pendingTheme) { const name = pendingTheme; pendingTheme = null; Music.play(name); }
    },
    setMuted(v) { muted = v; if (master && ctx) master.gain.setValueAtTime(v ? 0 : 1, ctx.currentTime); },
    /** For the settings' diagnostic: unsupported | waiting | running | suspended | closed */
    status() {
        if (typeof window === 'undefined' || !(window.AudioContext || window.webkitAudioContext)) return 'unsupported';
        if (!ctx) return 'waiting';
        return ctx.state;
    },
    /** A short, loud-enough beep — ignores the music switch, respects mute */
    async test() {
        unlocked = true;
        const c = ensure(); if (!c) return 'unsupported';
        try { await c.resume(); } catch { /* reported through the state */ }
        tone({ type: 'square', f0: 660, f1: 990, dur: 0.25, vol: 0.25 });
        tone({ type: 'square', f0: 990, dur: 0.2, vol: 0.2, delay: 0.25 });
        return c.state;
    },
    isMuted() { return muted; },
};
