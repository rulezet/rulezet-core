/**
 * input.js — keyboard, mouse and gamepad, merged into one state the game
 * reads each frame. Mouse coordinates are converted to the 1280×720 arena.
 */
import { W, H } from './data.js';

export function createInput(canvas) {
    const keys = new Set();
    const pressed = new Set();          // keys pressed since last frame
    const state = {
        mx: W / 2, my: H / 2, mouseDown: false, rightDown: false,
        mouseActive: 0,                  // frames since the mouse last moved
        wheel: 0,
        pad: null,
    };

    const GAME_KEYS = new Set(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space', 'Tab']);

    // While the game has the keyboard, Space / Enter / arrows must never
    // reach a focused button: browsers "click" a button on Space key-up, so
    // firing would toggle the sound or fullscreen button again and again.
    const isButton = e => e.target && e.target.tagName === 'BUTTON';
    function onKeyDown(e) {
        if (e.target && /input|textarea|select/i.test(e.target.tagName)) return;
        if (state.capture && (GAME_KEYS.has(e.code) || (e.code === 'Enter' && isButton(e)))) e.preventDefault();
        if (state.capture && isButton(e)) e.target.blur();
        if (!keys.has(e.code)) pressed.add(e.code);
        keys.add(e.code);
    }
    function onKeyUp(e) {
        keys.delete(e.code);
        if (state.capture && (GAME_KEYS.has(e.code) || e.code === 'Enter')) e.preventDefault();
    }

    function toArena(e) {
        const r = canvas.getBoundingClientRect();
        const scale = Math.min(r.width / W, r.height / H);
        const ox = (r.width - W * scale) / 2, oy = (r.height - H * scale) / 2;
        return [(e.clientX - r.left - ox) / scale, (e.clientY - r.top - oy) / scale];
    }
    function onMove(e) { [state.mx, state.my] = toArena(e); state.mouseActive = 0; }
    function onDown(e) {
        [state.mx, state.my] = toArena(e); state.mouseActive = 0;
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

    // ── Gamepad (standard mapping) ──
    let padPrev = [];
    function pollPad() {
        const pads = navigator.getGamepads ? navigator.getGamepads() : [];
        const p = pads && Array.from(pads).find(Boolean);
        if (!p) { state.pad = null; return; }
        const dz = v => (Math.abs(v) < 0.18 ? 0 : v);
        const b = p.buttons.map(x => x.pressed);
        const was = i => padPrev[i];
        state.pad = {
            lx: dz(p.axes[0] || 0), ly: dz(p.axes[1] || 0), rx: dz(p.axes[2] || 0), ry: dz(p.axes[3] || 0),
            fire: !!b[7],                                  // RT
            dash: b[0] && !was(0), bomb: b[1] && !was(1),
            next: b[5] && !was(5), prev: b[4] && !was(4),
            pause: b[9] && !was(9), confirm: b[0] && !was(0), back: b[1] && !was(1),
            up: b[12] && !was(12), down: b[13] && !was(13), left: b[14] && !was(14), right: b[15] && !was(15),
        };
        padPrev = b;
    }

    return {
        state,
        down: (code) => keys.has(code),
        any: (...codes) => codes.some(c => keys.has(c)),
        hit: (...codes) => codes.some(c => pressed.has(c)),
        frame() { state.mouseActive++; pollPad(); },
        endFrame() { pressed.clear(); state.wheel = 0; },
        setCapture(v) { state.capture = v; },
        /** Movement vector from WASD / arrows / left stick */
        move() {
            let x = 0, y = 0;
            if (keys.has('KeyA') || keys.has('ArrowLeft')) x -= 1;
            if (keys.has('KeyD') || keys.has('ArrowRight')) x += 1;
            if (keys.has('KeyW') || keys.has('ArrowUp')) y -= 1;
            if (keys.has('KeyS') || keys.has('ArrowDown')) y += 1;
            if (state.pad) { x += state.pad.lx; y += state.pad.ly; }
            const l = Math.hypot(x, y);
            return l > 1 ? [x / l, y / l] : [x, y];
        },
    };
}
