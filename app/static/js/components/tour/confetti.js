/**
 * confetti — a short burst of confetti over the page (a canvas, no dependency), then it cleans up.
 *   import confetti from '/static/js/components/tour/confetti.js'
 *   await confetti({ duration: 2600 })      // resolves when it is over
 * prefers-reduced-motion: nothing is drawn, it resolves at once.
 */
const COLORS = ['#0d6efd', '#0a58ca', '#40d4e2', '#ffc107', '#198754', '#fd7e14', '#d63384']

export default function confetti({ duration = 2600, count = 180 } = {}) {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return Promise.resolve()
    const canvas = document.createElement('canvas')
    Object.assign(canvas.style, { position: 'fixed', inset: '0', width: '100vw', height: '100vh', zIndex: '21000', pointerEvents: 'none' })
    canvas.setAttribute('aria-hidden', 'true')
    document.body.appendChild(canvas)
    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    const W = canvas.width = innerWidth * dpr, H = canvas.height = innerHeight * dpr
    const pieces = Array.from({ length: count }, (_, i) => {
        const fromLeft = i % 2 === 0                          // two cannons, bottom corners
        return {
            x: fromLeft ? 0 : W, y: H * .85,
            vx: (fromLeft ? 1 : -1) * (6 + Math.random() * 10) * dpr,
            vy: -(14 + Math.random() * 12) * dpr,
            size: (5 + Math.random() * 6) * dpr, rot: Math.random() * Math.PI, vr: (Math.random() - .5) * .35,
            color: COLORS[i % COLORS.length], shape: i % 3,
        }
    })
    const start = performance.now()
    return new Promise(resolve => {
        function frame(now) {
            const t = now - start
            ctx.clearRect(0, 0, W, H)
            ctx.globalAlpha = Math.max(0, 1 - Math.max(0, t - duration * .7) / (duration * .3))
            for (const p of pieces) {
                p.vy += .35 * dpr; p.vx *= .992; p.x += p.vx; p.y += p.vy; p.rot += p.vr
                ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.fillStyle = p.color
                if (p.shape === 0) ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2)
                else if (p.shape === 1) { ctx.beginPath(); ctx.arc(0, 0, p.size / 3, 0, Math.PI * 2); ctx.fill() }
                else { ctx.beginPath(); ctx.moveTo(0, -p.size / 2); ctx.lineTo(p.size / 2, p.size / 2); ctx.lineTo(-p.size / 2, p.size / 2); ctx.fill() }
                ctx.restore()
            }
            if (t < duration) requestAnimationFrame(frame)
            else { canvas.remove(); resolve() }
        }
        requestAnimationFrame(frame)
    })
}
