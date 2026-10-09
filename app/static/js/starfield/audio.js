/**
 * audio.js — procedural sound effects and a looping background track (Web
 * Audio API). Sound effects are synthesised; the music is a CC0 file (see
 * static/audio/starfield/CREDITS.md). Safe where Web Audio is missing
 * (every call becomes a no-op).
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
        musicGain = ctx.createGain(); musicGain.gain.value = musicOn ? MUSIC_VOL : 0.0001; musicGain.connect(master);
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

// ── Music: one calm looping track (CC0, see static/audio/starfield/CREDITS.md)
// played through musicGain so mute / the music switch / tab sleep all apply.
const MUSIC_URL = new URL('../../audio/starfield/outer_space.mp3', import.meta.url).href;
const MUSIC_VOL = 0.45;
let musicBuf = null;
let musicLoading = null;
let musicSrc = null;
let wanted = false;

function loadMusic(c) {
    if (!musicLoading) {
        musicLoading = fetch(MUSIC_URL)
            .then(r => r.arrayBuffer())
            .then(data => new Promise((ok, ko) => c.decodeAudioData(data, ok, ko)))
            .then(buf => { musicBuf = buf; return buf; })
            .catch(() => null);         // no music, the game still runs
    }
    return musicLoading;
}

function startLoop() {
    const c = ensure(); if (!c || !wanted || musicSrc) return;
    loadMusic(c).then(buf => {
        if (!buf || !wanted || musicSrc) return;
        musicSrc = c.createBufferSource();
        musicSrc.buffer = buf; musicSrc.loop = true;
        musicSrc.connect(musicGain);
        // soft fade-in instead of the track slamming in
        musicGain.gain.setValueAtTime(0.0001, c.currentTime);
        musicGain.gain.exponentialRampToValueAtTime(musicOn ? MUSIC_VOL : 0.0001, c.currentTime + 2);
        musicSrc.start();
    });
}

export const Music = {
    // The same track plays on the map, in levels and against bosses: the
    // name is kept so callers don't change, and switching never restarts it.
    play(name) {
        wanted = true;
        if (!unlocked) { pendingTheme = name; return; }
        startLoop();
    },
    stop() {
        wanted = false; pendingTheme = null;
        if (musicSrc) { try { musicSrc.stop(); } catch { /* already stopped */ } musicSrc = null; }
    },
    /** Suspend the whole audio engine while the tab is hidden */
    sleep(hidden) { if (!ctx) return; try { hidden ? ctx.suspend() : ctx.resume(); } catch { /* ignore */ } },
    setEnabled(v) {
        musicOn = v;
        if (musicGain && ctx) musicGain.gain.setTargetAtTime(v ? MUSIC_VOL : 0.0001, ctx.currentTime, 0.2);
    },
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
