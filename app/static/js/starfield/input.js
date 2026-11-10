/**
 * input.js — keyboard, mouse and gamepad, merged into one state the game
 * reads each frame. Mouse coordinates are converted to the 1280×720 arena.
 *
 * Gamepad: standard mapping (Xbox / PlayStation / Switch Pro in a browser).
 * Every game action has a configurable button (Settings → Gamepad); A / B
 * (bottom / right face buttons) always confirm / go back in the menus, the
 * d-pad and the left stick move the menu focus, LB / RB switch tabs.
 */
import { W, H } from './data.js';

/** Left / right Shift, Ctrl, Alt count as one key */
export const normalizeKey = code => code.replace(/^(Shift|Control|Alt|Meta)Right$/, '$1Left');

// ── Gamepad: actions, default buttons, button names per controller family ──
export const PAD_ACTIONS = [
    { id: 'fire', label: 'Fire' },
    { id: 'dash', label: 'Dash' },
    { id: 'bomb', label: 'Quarantine bomb' },
    { id: 'special', label: 'Ship power' },
    { id: 'next', label: 'Next weapon' },
    { id: 'prev', label: 'Previous weapon' },
    { id: 'pause', label: 'Pause' },
];
export const DEFAULT_PAD = { fire: 7, dash: 0, bomb: 1, special: 3, next: 5, prev: 4, pause: 9 };
export const DEFAULT_PAD_SETTINGS = { map: { ...DEFAULT_PAD }, deadzone: 0.18, swap: false, invertY: false, vibration: true, layout: 'auto' };
// index = button of the standard mapping
export const PAD_LAYOUTS = {
    xbox: ['A', 'B', 'X', 'Y', 'LB', 'RB', 'LT', 'RT', 'View', 'Menu', 'LS', 'RS', '↑', '↓', '←', '→', 'Guide'],
    ps: ['✕', '○', '□', '△', 'L1', 'R1', 'L2', 'R2', 'Share', 'Options', 'L3', 'R3', '↑', '↓', '←', '→', 'PS'],
    nintendo: ['B', 'A', 'Y', 'X', 'L', 'R', 'ZL', 'ZR', '−', '+', 'LS', 'RS', '↑', '↓', '←', '→', 'Home'],
};
export const PAD_LAYOUT_NAMES = { xbox: 'Xbox', ps: 'PlayStation', nintendo: 'Nintendo' };
/** Guess the controller family from the Gamepad id string */
export function padFamily(id = '') {
    const s = id.toLowerCase();
    if (/xbox|045e|xinput/.test(s)) return 'xbox';
    if (/(playstation|dualshock|dualsense|054c)/.test(s)) return 'ps';
    if (/(nintendo|pro controller|joy-con|057e)/.test(s)) return 'nintendo';
    return 'xbox';
}
/** A short readable name for a controller id ("Xbox Wireless Controller (STANDARD GAMEPAD …)" → "Xbox Wireless Controller") */
export const padShortName = id => (id || '').replace(/\s*\(.*$/, '').trim() || 'Gamepad';

export function createInput(canvas) {
    let keymap = {};                    // action → [code, code]
    let padCfg = { ...DEFAULT_PAD_SETTINGS, map: { ...DEFAULT_PAD } };
    const keys = new Set();
    const pressed = new Set();          // keys pressed since last frame
    const state = {
        mx: W / 2, my: H / 2, mouseDown: false, rightDown: false,
        mouseActive: 0,                  // frames since the mouse last moved
        wheel: 0,
        pad: null,
        padId: '', padConnected: false,
        lastDevice: 'kbm',               // 'kbm' | 'pad': what the prompts should show
    };
    let onPadChange = null;

    const GAME_KEYS = new Set(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space', 'Tab']);

    // While the game has the keyboard, Space / Enter / arrows must never
    // reach a focused button: browsers "click" a button on Space key-up, so
    // firing would toggle the sound or fullscreen button again and again.
    const isButton = e => e.target && e.target.tagName === 'BUTTON';
    function onKeyDown(e) {
        if (e.target && /input|textarea|select/i.test(e.target.tagName)) return;
        const code = normalizeKey(e.code);
        if (state.capture && (GAME_KEYS.has(code) || isBound(code) || (code === 'Enter' && isButton(e)))) e.preventDefault();
        if (state.capture && isButton(e)) e.target.blur();
        if (!keys.has(code)) pressed.add(code);
        keys.add(code);
        state.lastDevice = 'kbm';
    }
    const isBound = code => Object.values(keymap).some(k => k.includes(code));
    function onKeyUp(e) {
        keys.delete(normalizeKey(e.code));
        if (state.capture && (GAME_KEYS.has(e.code) || e.code === 'Enter')) e.preventDefault();
    }

    function toArena(e) {
        const r = canvas.getBoundingClientRect();
        const scale = Math.min(r.width / W, r.height / H);
        const ox = (r.width - W * scale) / 2, oy = (r.height - H * scale) / 2;
        return [(e.clientX - r.left - ox) / scale, (e.clientY - r.top - oy) / scale];
    }
    function onMove(e) { [state.mx, state.my] = toArena(e); state.mouseActive = 0; state.lastDevice = 'kbm'; }
    function onDown(e) {
        [state.mx, state.my] = toArena(e); state.mouseActive = 0; state.lastDevice = 'kbm';
        if (e.button === 0) { state.mouseDown = true; pressed.add('Mouse0'); }
        if (e.button === 2) { state.rightDown = true; pressed.add('Mouse2'); }
    }
    function onUp(e) { if (e.button === 0) state.mouseDown = false; if (e.button === 2) state.rightDown = false; }
    function onWheel(e) { if (state.capture) { e.preventDefault(); state.wheel += Math.sign(e.deltaY); } }

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    window.addEventListener('blur', () => { keys.clear(); state.mouseDown = false; state.rightDown = false; });
    canvas.addEventListener('mousemove', onMove);
    canvas.addEventListener('mousedown', onDown);
    window.addEventListener('mouseup', onUp);
    canvas.addEventListener('wheel', onWheel, { passive: false });
    canvas.addEventListener('contextmenu', e => e.preventDefault());
    window.addEventListener('gamepadconnected', e => { if (onPadChange) onPadChange(true, e.gamepad.id); });
    window.addEventListener('gamepaddisconnected', e => { if (onPadChange) onPadChange(false, e.gamepad.id); });

    // ── Gamepad (standard mapping) ──
    let padPrev = [];
    const nav = { dir: null, held: 0 };          // menu navigation repeat (stick / d-pad held)
    let activePad = null;
    function pollPad() {
        let pads = [];
        try { pads = navigator.getGamepads ? Array.from(navigator.getGamepads()) : []; } catch { pads = []; }
        const p = pads.find(g => g && g.connected && g.mapping === 'standard') || pads.find(g => g && g.connected);
        activePad = p || null;
        state.padConnected = !!p;
        if (!p) { state.pad = null; padPrev = []; return; }
        state.padId = p.id;
        const dzv = padCfg.deadzone ?? 0.18;
        const dz = v => (Math.abs(v) < dzv ? 0 : (v - Math.sign(v) * dzv) / (1 - dzv));
        const b = p.buttons.map(x => x.pressed || x.value > 0.4);
        const edge = i => b[i] && !padPrev[i];
        const m = padCfg.map;
        let lx = dz(p.axes[0] || 0), ly = dz(p.axes[1] || 0), rx = dz(p.axes[2] || 0), ry = dz(p.axes[3] || 0);
        if (padCfg.swap) [lx, ly, rx, ry] = [rx, ry, lx, ly];
        if (padCfg.invertY) ry = -ry;
        // menu directions: d-pad or left stick, with key-repeat when held
        const raw = (p.axes[0] || 0), rawY = (p.axes[1] || 0);
        let dir = b[12] ? 'up' : b[13] ? 'down' : b[14] ? 'left' : b[15] ? 'right' : null;
        if (!dir && Math.max(Math.abs(raw), Math.abs(rawY)) > 0.6) dir = Math.abs(raw) > Math.abs(rawY) ? (raw > 0 ? 'right' : 'left') : (rawY > 0 ? 'down' : 'up');
        let navEdge = null;
        if (dir !== nav.dir) { nav.dir = dir; nav.held = 0; navEdge = dir; }
        else if (dir) { nav.held++; if (nav.held > 22 && nav.held % 7 === 0) navEdge = dir; }
        const firstEdge = b.findIndex((v, i) => v && !padPrev[i]);
        state.pad = {
            lx, ly, rx, ry,
            fire: !!b[m.fire],
            dash: edge(m.dash), bomb: edge(m.bomb), special: edge(m.special),
            next: edge(m.next), prev: edge(m.prev), pause: edge(m.pause),
            confirm: edge(0), back: edge(1), tabPrev: edge(4), tabNext: edge(5),
            up: navEdge === 'up', down: navEdge === 'down', left: navEdge === 'left', right: navEdge === 'right',
            held: b, edgeButton: firstEdge,      // for the settings tester and rebinding
            axes: [p.axes[0] || 0, p.axes[1] || 0, p.axes[2] || 0, p.axes[3] || 0],
        };
        if (firstEdge >= 0 || Math.abs(lx) + Math.abs(ly) + Math.abs(rx) + Math.abs(ry) > 0.3) state.lastDevice = 'pad';
        padPrev = b;
    }

    return {
        state,
        down: (code) => keys.has(code),
        any: (...codes) => codes.some(c => keys.has(c)),
        hit: (...codes) => codes.some(c => pressed.has(c)),
        /** Configurable actions (Settings → Keys) */
        setKeys(map) { keymap = map || {}; },
        /** Gamepad settings (Settings → Gamepad) */
        setPad(cfg) { padCfg = { ...DEFAULT_PAD_SETTINGS, ...(cfg || {}), map: { ...DEFAULT_PAD, ...((cfg && cfg.map) || {}) } }; },
        onPadChange(fn) { onPadChange = fn; },
        /** Short rumble, if the controller and the setting allow it */
        rumble(strong = 0.5, weak = 0.5, ms = 150) {
            if (!padCfg.vibration || !activePad) return;
            try {
                const a = activePad.vibrationActuator;
                if (a && a.playEffect) a.playEffect('dual-rumble', { duration: ms, strongMagnitude: Math.min(1, strong), weakMagnitude: Math.min(1, weak) }).catch(() => {});
            } catch { /* not supported */ }
        },
        act: (a) => (keymap[a] || []).some(c => c && keys.has(c)),
        actHit: (a) => (keymap[a] || []).some(c => c && pressed.has(c)),
        frame() { state.mouseActive++; pollPad(); },
        endFrame() { pressed.clear(); state.wheel = 0; },
        setCapture(v) { state.capture = v; },
        /** Movement vector from WASD / arrows / left stick */
        move() {
            let x = 0, y = 0;
            const on = a => (keymap[a] || []).some(c => c && keys.has(c));
            if (on('left')) x -= 1;
            if (on('right')) x += 1;
            if (on('up')) y -= 1;
            if (on('down')) y += 1;
            if (state.pad) { x += state.pad.lx; y += state.pad.ly; }
            const l = Math.hypot(x, y);
            return l > 1 ? [x / l, y / l] : [x, y];
        },
    };
}
