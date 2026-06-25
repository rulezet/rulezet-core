/**
 * kpiTransition.js
 *   rules   → slow security scan, clearly readable
 *   bundles → 3D box opens, item drops in, lid closes
 *   attacks → crosshair + converging rings, contained to card
 */
;(function () {

    const PAD = 14

    const canvas = document.createElement('canvas')
    Object.assign(canvas.style, {
        position: 'fixed', zIndex: '9999',
        pointerEvents: 'none', display: 'none',
        borderRadius: '14px',
    })
    document.body.appendChild(canvas)
    const ctx = canvas.getContext('2d')

    function hexRgba(hex, a) {
        const r = parseInt(hex.slice(1, 3), 16)
        const g = parseInt(hex.slice(3, 5), 16)
        const b = parseInt(hex.slice(5, 7), 16)
        return `rgba(${r},${g},${b},${a})`
    }
    function easeOut(t) { return 1 - Math.pow(1 - t, 3) }
    function easeIn(t)  { return t * t * t }
    function easeInOut(t) { return t < .5 ? 2*t*t : -1+(4-2*t)*t }

    let CW, CH

    function clipCard() {
        ctx.beginPath()
        ctx.roundRect(PAD, PAD, CW, CH, 10)
        ctx.clip()
    }

    // ─────────────────────────────────────────────────────────────────────────
    // RULES — slow deliberate scan, visibly reads as a security scan
    // ─────────────────────────────────────────────────────────────────────────
    function drawScan(t, color) {
        ctx.save()
        clipCard()

        // Overlay builds up gradually (dark but not instant)
        ctx.fillStyle = `rgba(2,8,18,${Math.min(t * 2.5, 0.80)})`
        ctx.fillRect(PAD, PAD, CW, CH)

        const e = easeInOut(t)
        const y = PAD + e * (CH + 10)

        // Wide trailing glow — makes the scan feel physical
        const grad = ctx.createLinearGradient(0, y - CH * 0.35, 0, y + 4)
        grad.addColorStop(0,   hexRgba(color, 0))
        grad.addColorStop(0.55, hexRgba(color, 0.07))
        grad.addColorStop(1,   hexRgba(color, 0.28))
        ctx.fillStyle = grad
        ctx.fillRect(PAD, Math.max(PAD, y - CH * 0.35), CW, CH * 0.35 + 4)

        // Fine scanline grid in the wake
        ctx.strokeStyle = hexRgba(color, 0.07)
        ctx.lineWidth = 1
        for (let gy = Math.floor(y / 8) * 8; gy > Math.max(PAD, y - CH * 0.5); gy -= 8) {
            ctx.beginPath(); ctx.moveTo(PAD, gy); ctx.lineTo(PAD + CW, gy); ctx.stroke()
        }

        // The scan line itself — thick, bright, impossible to miss
        ctx.save()
        ctx.shadowColor = color; ctx.shadowBlur = 20
        ctx.strokeStyle = hexRgba(color, 1)
        ctx.lineWidth   = 2
        ctx.beginPath(); ctx.moveTo(PAD, y); ctx.lineTo(PAD + CW, y); ctx.stroke()
        ctx.shadowBlur  = 40
        ctx.strokeStyle = hexRgba(color, 0.4)
        ctx.lineWidth   = 12
        ctx.beginPath(); ctx.moveTo(PAD, y); ctx.lineTo(PAD + CW, y); ctx.stroke()
        ctx.restore()

        // "SCAN" label that rides with the line
        if (t > 0.08 && t < 0.92) {
            ctx.fillStyle   = hexRgba(color, 0.7)
            ctx.font        = `500 9px monospace`
            ctx.textAlign   = 'right'
            ctx.shadowColor = color; ctx.shadowBlur = 6
            ctx.fillText('SCAN', PAD + CW - 6, y - 5)
        }

        ctx.restore()
    }

    // ─────────────────────────────────────────────────────────────────────────
    // BUNDLES — 3D box grows in, item drops inside, lid seals shut
    // ─────────────────────────────────────────────────────────────────────────
    function drawBox(t, color) {
        const cx = PAD + CW / 2
        const cy = PAD + CH / 2 + 4

        // Box geometry
        const bw  = CW * 0.46
        const bh  = CH * 0.38
        const dx  = bw * 0.32   // depth x-offset
        const dy  = dx * 0.42   // depth y-offset
        const bx  = cx - bw / 2
        const by  = cy - bh / 2

        // Phase timing
        const pAppear = Math.min(t / 0.32, 1)
        const pItem   = Math.min(Math.max((t - 0.28) / 0.28, 0), 1)
        const pClose  = Math.min(Math.max((t - 0.58) / 0.32, 0), 1)
        const pGlow   = Math.max((t - 0.88) / 0.12, 0)

        ctx.save()
        clipCard()
        ctx.fillStyle = `rgba(0,0,0,${Math.min(t * 3.5, 0.68)})`
        ctx.fillRect(PAD, PAD, CW, CH)
        ctx.restore()

        const sc = easeOut(pAppear)
        ctx.save()
        clipCard()
        ctx.translate(cx, cy); ctx.scale(sc, sc); ctx.translate(-cx, -cy)

        ctx.lineWidth = 1.8
        ctx.shadowColor = color; ctx.shadowBlur = 10

        // Right side face
        ctx.beginPath()
        ctx.moveTo(bx + bw,      by)
        ctx.lineTo(bx + bw + dx, by - dy)
        ctx.lineTo(bx + bw + dx, by + bh - dy)
        ctx.lineTo(bx + bw,      by + bh)
        ctx.closePath()
        ctx.fillStyle   = hexRgba(color, 0.08)
        ctx.strokeStyle = hexRgba(color, 0.75)
        ctx.fill(); ctx.stroke()

        // Front face
        ctx.beginPath()
        ctx.rect(bx, by, bw, bh)
        ctx.fillStyle   = hexRgba(color, 0.10)
        ctx.strokeStyle = hexRgba(color, 0.85)
        ctx.fill(); ctx.stroke()

        // Horizontal center line on front (cardboard fold)
        ctx.strokeStyle = hexRgba(color, 0.25)
        ctx.lineWidth   = 1
        ctx.setLineDash([4, 3])
        ctx.beginPath()
        ctx.moveTo(bx, by + bh * 0.5)
        ctx.lineTo(bx + bw, by + bh * 0.5)
        ctx.stroke()
        ctx.setLineDash([])

        ctx.restore()

        // Item dropping in (while lid still open)
        if (pItem > 0 && pClose < 0.5) {
            ctx.save()
            clipCard()
            const drop    = easeIn(Math.min(pItem / 0.7, 1))
            const startY  = by - 26
            const endY    = by + bh * 0.35
            const iy      = startY + drop * (endY - startY)
            const iAlpha  = pClose > 0 ? (1 - pClose * 2) : 1
            const is      = 9

            ctx.shadowColor = color; ctx.shadowBlur = 12
            ctx.fillStyle   = hexRgba(color, iAlpha * 0.85)
            ctx.strokeStyle = hexRgba(color, iAlpha)
            ctx.lineWidth   = 1.5
            // Small 3D cube icon
            ctx.beginPath(); ctx.rect(cx - is / 2, iy - is / 2, is, is)
            ctx.fill(); ctx.stroke()
            // Cube top face
            const td = is * 0.4
            ctx.beginPath()
            ctx.moveTo(cx - is/2, iy - is/2)
            ctx.lineTo(cx - is/2 + td, iy - is/2 - td * 0.5)
            ctx.lineTo(cx + is/2 + td, iy - is/2 - td * 0.5)
            ctx.lineTo(cx + is/2, iy - is/2)
            ctx.closePath()
            ctx.fillStyle = hexRgba(color, iAlpha * 0.55)
            ctx.fill(); ctx.stroke()
            ctx.restore()
        }

        // Box top — open first, then closes
        if (pAppear > 0.3) {
            ctx.save()
            clipCard()
            ctx.translate(cx, cy); ctx.scale(sc, sc); ctx.translate(-cx, -cy)

            // The top parallelogram (opening)
            // pClose drives a clip that sweeps from back edge forward, sealing it
            const lidClosed = easeOut(pClose)
            const clipDepth = dy + (bh * 0.02)  // how far back the top goes

            if (lidClosed < 1) {
                // Draw open top (darker, transparent)
                ctx.beginPath()
                ctx.moveTo(bx,      by)
                ctx.lineTo(bx + dx, by - dy)
                ctx.lineTo(bx + bw + dx, by - dy)
                ctx.lineTo(bx + bw, by)
                ctx.closePath()
                ctx.fillStyle   = hexRgba(color, 0.06 * (1 - lidClosed))
                ctx.strokeStyle = hexRgba(color, 0.5 * (1 - lidClosed))
                ctx.lineWidth   = 1.5; ctx.shadowBlur = 6
                ctx.fill(); ctx.stroke()
            }

            if (lidClosed > 0) {
                // Lid sweeps from back (top of parallelogram) toward front
                ctx.save()
                // Clip to the portion of the lid that has "closed"
                ctx.beginPath()
                const lidProgress = lidClosed
                // Interpolate the lid front edge from the back edge down toward by
                const frontY = (by - dy) + lidProgress * dy
                const frontX = bx + lidProgress * 0
                ctx.moveTo(bx,               by - dy + lidProgress * dy)
                ctx.lineTo(bx + bw,          by - dy + lidProgress * dy)
                ctx.lineTo(bx + bw + dx,     by - dy)
                ctx.lineTo(bx + dx,          by - dy)
                ctx.closePath()
                ctx.clip()

                ctx.beginPath()
                ctx.moveTo(bx,           by)
                ctx.lineTo(bx + dx,      by - dy)
                ctx.lineTo(bx + bw + dx, by - dy)
                ctx.lineTo(bx + bw,      by)
                ctx.closePath()
                ctx.fillStyle   = hexRgba(color, 0.18 * lidClosed)
                ctx.strokeStyle = hexRgba(color, 0.85 * lidClosed)
                ctx.lineWidth   = 1.8; ctx.shadowBlur = 10
                ctx.fill(); ctx.stroke()
                ctx.restore()
            }

            ctx.restore()
        }

        // Seal glow at the end
        if (pGlow > 0) {
            ctx.save()
            clipCard()
            ctx.fillStyle = hexRgba(color, pGlow * (1 - pGlow) * 4 * 0.2)
            ctx.fillRect(PAD, PAD, CW, CH)
            ctx.restore()
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // ATTACKS — crosshair from center, rings converge, lock flash
    // ─────────────────────────────────────────────────────────────────────────
    function drawTarget(t, color) {
        const cx = PAD + CW / 2
        const cy = PAD + CH / 2

        const p1 = Math.min(t / 0.40, 1)
        const p2 = Math.min(Math.max((t - 0.25) / 0.40, 0), 1)
        const p3 = Math.max((t - 0.72) / 0.28, 0)

        ctx.save()
        clipCard()
        ctx.fillStyle = `rgba(8,4,0,${Math.min(t * 4, 0.72)})`
        ctx.fillRect(PAD, PAD, CW, CH)

        ctx.strokeStyle = hexRgba(color, 0.85 * (1 - p3 * 0.4))
        ctx.shadowColor = color; ctx.shadowBlur = 10
        ctx.lineWidth   = 1.2
        const le = easeOut(p1)
        ctx.beginPath()
        ctx.moveTo(cx - le * CW * 0.5, cy); ctx.lineTo(cx + le * CW * 0.5, cy)
        ctx.moveTo(cx, cy - le * CH * 0.5); ctx.lineTo(cx, cy + le * CH * 0.5)
        ctx.stroke()

        const gapR = 10
        ctx.clearRect(cx - gapR, cy - 2, gapR * 2, 4)
        ctx.clearRect(cx - 2, cy - gapR, 4, gapR * 2)

        if (p2 > 0) {
            const maxR = Math.min(CW, CH) * 0.42
            const r1   = maxR * (1 - easeOut(p2)) + 8
            const r2   = maxR * 0.5 * (1 - easeOut(p2)) + 5

            ctx.shadowBlur  = 8 + p2 * 14
            ctx.lineWidth   = 1.4
            ctx.strokeStyle = hexRgba(color, (0.6 + p2 * 0.3) * (1 - p3 * 0.5))
            ctx.beginPath(); ctx.arc(cx, cy, r1, 0, Math.PI * 2); ctx.stroke()
            ctx.lineWidth = 0.9
            ctx.beginPath(); ctx.arc(cx, cy, r2, 0, Math.PI * 2); ctx.stroke()

            const tl = 5
            for (let a = 0; a < Math.PI * 2; a += Math.PI / 2) {
                const rx = cx + Math.cos(a) * r1, ry = cy + Math.sin(a) * r1
                const nx = Math.cos(a), ny = Math.sin(a)
                ctx.lineWidth = 1.8
                ctx.beginPath()
                ctx.moveTo(rx - ny * tl, ry + nx * tl)
                ctx.lineTo(rx, ry)
                ctx.lineTo(rx + ny * tl, ry - nx * tl)
                ctx.stroke()
            }
        }

        if (p3 > 0) {
            ctx.shadowBlur  = 24
            ctx.strokeStyle = hexRgba(color, 1 - p3 * 0.35)
            ctx.lineWidth   = 2
            ctx.beginPath(); ctx.arc(cx, cy, 14 + easeOut(p3) * 4, 0, Math.PI * 2); ctx.stroke()
            ctx.fillStyle   = hexRgba(color, (1 - p3) * 0.85)
            ctx.beginPath(); ctx.arc(cx, cy, 3, 0, Math.PI * 2); ctx.fill()
            const burst = p3 * (1 - p3) * 4
            ctx.fillStyle = `rgba(255,255,255,${burst * 0.28})`
            ctx.fillRect(PAD, PAD, CW, CH)
        }

        ctx.restore()
    }

    // ─────────────────────────────────────────────────────────────────────────

    const DRAW = {
        rules:   { fn: drawScan,   dur: 920, nav: 820 },
        bundles: { fn: drawBox,    dur: 680, nav: 580 },
        attacks: { fn: drawTarget, dur: 600, nav: 490 },
    }

    function run(type, color, href, rect) {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            window.location.href = href; return
        }

        CW = rect.width
        CH = rect.height
        canvas.width  = CW + PAD * 2
        canvas.height = CH + PAD * 2
        canvas.style.width   = canvas.width  + 'px'
        canvas.style.height  = canvas.height + 'px'
        canvas.style.left    = (rect.left - PAD) + 'px'
        canvas.style.top     = (rect.top  - PAD) + 'px'
        canvas.style.display = 'block'

        const cfg   = DRAW[type] || DRAW.rules
        const start = performance.now()

        setTimeout(() => { window.location.href = href }, cfg.nav)

        function frame(now) {
            const t = Math.min((now - start) / cfg.dur, 1)
            ctx.clearRect(0, 0, canvas.width, canvas.height)
            cfg.fn(t, color)
            if (t < 1) requestAnimationFrame(frame)
            else canvas.style.display = 'none'
        }
        requestAnimationFrame(frame)
    }

    document.addEventListener('click', function (e) {
        const card = e.target.closest('[data-kpi-href]')
        if (!card) return
        e.preventDefault()
        const rect = card.getBoundingClientRect()
        card.style.transition = 'filter 120ms'
        card.style.filter     = 'blur(3px)'
        run(card.dataset.kpiType, card.dataset.kpiColor, card.dataset.kpiHref, rect)
    })

})()
