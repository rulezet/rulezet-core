/**
 * rain.js — the window behind the analyst: a city skyline at night and rain.
 * Purely decorative; stops when the tab is hidden.
 */
export function startRain(canvas) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let drops = [], skyline = [], w = 0, h = 0;

    function resize() {
        w = canvas.width = canvas.clientWidth;
        h = canvas.height = canvas.clientHeight;
        drops = Array.from({ length: Math.round(w / 6) }, () => ({ x: Math.random() * w, y: Math.random() * h, s: 4 + Math.random() * 6 }));
        skyline = [];
        for (let x = 0; x < w;) {
            const bw = 20 + Math.random() * 50, bh = 15 + Math.random() * (h * 0.7);
            const windows = Array.from({ length: Math.round(bw * bh / 260) }, () => ({
                x: x + 3 + Math.random() * (bw - 6), y: h - bh + 4 + Math.random() * (bh - 8), on: Math.random() < 0.35,
            }));
            skyline.push({ x, w: bw, h: bh, windows });
            x += bw + 2;
        }
    }

    function frame() {
        ctx.clearRect(0, 0, w, h);
        for (const b of skyline) {
            ctx.fillStyle = '#0b1026';
            ctx.fillRect(b.x, h - b.h, b.w, b.h);
            for (const win of b.windows) {
                if (!win.on) continue;
                ctx.fillStyle = 'rgba(255, 190, 90, .55)';
                ctx.fillRect(Math.round(win.x), Math.round(win.y), 2, 3);
            }
        }
        ctx.strokeStyle = 'rgba(160, 180, 255, .35)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (const d of drops) {
            ctx.moveTo(d.x, d.y);
            ctx.lineTo(d.x - 1, d.y + d.s);
            if (!reduced) {
                d.y += d.s * 1.6;
                d.x -= 0.3;
                if (d.y > h) { d.y = -10; d.x = Math.random() * w; }
            }
        }
        ctx.stroke();
        if (!reduced && !document.hidden) requestAnimationFrame(frame);
    }

    resize();
    window.addEventListener('resize', resize);
    document.addEventListener('visibilitychange', () => { if (!document.hidden && !reduced) requestAnimationFrame(frame); });
    frame();
}
