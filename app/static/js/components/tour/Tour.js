/**
 * Tour — a step-by-step guided tour over the page: the current element is lit, everything else
 * dimmed, and a card explains it (title, text, progress, Back / Next / Close; ← → Esc).
 * No dependency, no Vue: works on every page, including pages rendered later by Vue (each step
 * waits a moment for its target to appear).
 *
 *   import Tour from '/static/js/components/tour/Tour.js'
 *   const tour = new Tour(steps, { startAt: 0, labels, onEnd(reason, index), onStep(index) })
 *   tour.start()
 *
 * A step: { target: CSS selector | Element | "@page" (the whole page: shown first on a new page)
 *           | null (null or not found = centred card),
 *           title, text (plain text: blank line = new paragraph, **bold**, `code`),
 *           badge (small label above the title), demo: HTML shown in the card (an example when
 *           the target is missing), nextLabel (text of the Next button),
 *           open: CSS selector clicked first when the target is hidden — a collapsed panel, a closed
 *           filter box, another tab — so the step shows what it talks about,
 *           href: the Next button goes to this address (and ends the tour), e.g. the login page,
 *           keep: true to show the card even when the target is missing (by default such a step is
 *           skipped: a button only some users have, a tab only some bundles have) }
 * onEnd(reason): 'done' (last step), 'closed' (Close / Esc). Return false from onNext(index)
 * to take over the move yourself (e.g. go to another page).
 */
const WAIT_MS = 1500
const GAP = 14

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
}

export function formatText(text) {
    return escapeHtml(text).split(/\n{2,}/).map(p =>
        '<p>' + p.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/`(.+?)`/g, '<code>$1</code>')
                  .replace(/\n/g, '<br>') + '</p>').join('')
}

function visible(el) {
    if (!el || !el.isConnected) return false
    const r = el.getBoundingClientRect()
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'
}

const sleep = ms => new Promise(r => setTimeout(r, ms))

function rawFind(target) {
    if (!target || target === '@page') return null
    if (target instanceof Element) return target
    try { return document.querySelector(target) } catch { return null }
}

/** Opens what hides the target: a collapsed h-card (its header is clicked), a Bootstrap collapse,
 *  a closed <details>. Returns true when something was opened. */
async function reveal(target) {
    const raw = rawFind(target)
    if (!raw) return false
    let opened = false
    const card = raw.closest('.h-card')
    const body = card?.querySelector(':scope > .h-card__body')
    if (body && getComputedStyle(body).display === 'none') {
        card.querySelector(':scope > .h-card__header')?.click()
        opened = true
    }
    const collapse = raw.closest('.collapse:not(.show)')
    if (collapse && window.bootstrap?.Collapse) {
        window.bootstrap.Collapse.getOrCreateInstance(collapse, { toggle: false }).show()
        opened = true
    }
    const details = raw.closest('details:not([open])')
    if (details) { details.open = true; opened = true }
    if (opened) await sleep(350)
    return opened
}

function resolve(target) {
    if (target === '@page') return document.querySelector('main') || document.body
    if (!target) return null
    if (target instanceof Element) return visible(target) ? target : null
    try {
        return [...document.querySelectorAll(target)].find(visible) || null
    } catch { return null }                     // invalid selector in a setting: centred card
}

export default class Tour {
    constructor(steps, options = {}) {
        this.steps = (steps || []).filter(Boolean)
        this.opts = options
        this.index = options.startAt || 0
        this.labels = { next: 'Next', back: 'Back', done: 'Finish', close: 'Close tour', ...(options.labels || {}) }
        this._onKey = this._onKey.bind(this)
        this._place = this._place.bind(this)
        this._token = 0
    }

    start() {
        if (!this.steps.length) return
        this._build()
        document.addEventListener('keydown', this._onKey, true)
        window.addEventListener('resize', this._place)
        window.addEventListener('scroll', this._place, true)
        this.go(Math.min(this.index, this.steps.length - 1))
    }

    end(reason = 'closed') {
        document.removeEventListener('keydown', this._onKey, true)
        window.removeEventListener('resize', this._place)
        window.removeEventListener('scroll', this._place, true)
        this.root?.remove()
        this.root = null
        this.opts.onEnd?.(reason, this.index)
    }

    async go(i, dir = 1) {
        if (i < 0) return
        if (i >= this.steps.length) {                   // the last steps were skipped: same as Finish
            if (this.opts.onNext && this.opts.onNext(this.steps.length - 1) === false) return
            return this.end('done')
        }
        this.index = i
        const token = ++this._token
        const step = this.steps[i]
        this.card.classList.add('rz-tour-card--busy')
        // Vue pages render after load: wait for the target, opening on the way what hides it — the
        // step's own opener (a Filters button, a tab) once it exists, then collapsed cards / sections
        let el = null, openerClicked = false, revealed = false
        const until = Date.now() + (step.target ? WAIT_MS : 0)
        while (true) {
            el = resolve(step.target)
            if (!el && step.open && !openerClicked) {
                const opener = resolve(step.open)
                if (opener) { opener.click(); openerClicked = true; await sleep(300); el = resolve(step.target) }
            }
            if (!revealed && step.target && step.target !== '@page') {
                revealed = true
                if (await reveal(step.target)) el = resolve(step.target)
            }
            if (el || Date.now() >= until) break
            await sleep(100)
            if (token !== this._token) return
            revealed = false                            // the target may have just been rendered
        }
        if (token !== this._token || !this.root) return
        if (!el && step.target && !step.demo && !step.keep) {     // not on this page for this user: skip
            if (i + dir < 0) return this.go(i + 1, 1)
            return this.go(i + dir, dir)
        }
        this.el = el
        this.whole = step.target === '@page'
        if (this.whole) window.scrollTo({ top: 0, behavior: 'smooth' })
        else if (el) el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' })
        this._render(step)
        this.card.classList.remove('rz-tour-card--busy')
        this.opts.onStep?.(i)
        this._place()
        setTimeout(this._place, 350)                    // after the smooth scroll
        this.card.focus({ preventScroll: true })
    }

    next() {
        const href = this.steps[this.index]?.href
        if (href) { this.end('link'); location.href = href; return }
        if (this.opts.onNext && this.opts.onNext(this.index) === false) return
        if (this.index >= this.steps.length - 1) return this.end('done')
        this.go(this.index + 1)
    }

    back() { this.go(this.index - 1, -1) }

    // ── DOM ────────────────────────────────────────────────────────────────────
    _build() {
        this.root = document.createElement('div')
        this.root.className = 'rz-tour'
        this.root.innerHTML = `
            <div class="rz-tour-blocker"></div>
            <div class="rz-tour-spot"></div>
            <div class="rz-tour-card" role="dialog" aria-modal="true" aria-labelledby="rz-tour-title" tabindex="-1">
                <button type="button" class="rz-tour-x" aria-label="${escapeHtml(this.labels.close)}"><i class="fa-solid fa-xmark"></i></button>
                <div class="rz-tour-badge"></div>
                <h3 class="rz-tour-title" id="rz-tour-title"></h3>
                <div class="rz-tour-text"></div>
                <div class="rz-tour-demo"></div>
                <div class="rz-tour-foot">
                    <div class="rz-tour-progress"><div class="rz-tour-bar"></div></div>
                    <span class="rz-tour-count"></span>
                    <button type="button" class="rz-tour-btn rz-tour-btn--ghost rz-tour-back"></button>
                    <button type="button" class="rz-tour-btn rz-tour-next"></button>
                </div>
            </div>`
        document.body.appendChild(this.root)
        this.spot = this.root.querySelector('.rz-tour-spot')
        this.card = this.root.querySelector('.rz-tour-card')
        this.root.querySelector('.rz-tour-x').onclick = () => this.end('closed')
        this.root.querySelector('.rz-tour-back').onclick = () => this.back()
        this.root.querySelector('.rz-tour-next').onclick = () => this.next()
        this.root.querySelector('.rz-tour-blocker').onclick = () => this.card.classList.add('rz-tour-card--nudge')
        this.card.addEventListener('animationend', () => this.card.classList.remove('rz-tour-card--nudge'))
    }

    _render(step) {
        const last = this.index === this.steps.length - 1
        const q = s => this.root.querySelector(s)
        q('.rz-tour-badge').textContent = step.badge || ''
        q('.rz-tour-badge').hidden = !step.badge
        q('.rz-tour-title').textContent = step.title || ''
        q('.rz-tour-text').innerHTML = formatText(step.text)
        const showDemo = step.demo && (!this.el || step.demoAlways)
        q('.rz-tour-demo').innerHTML = showDemo ? step.demo : ''
        q('.rz-tour-demo').hidden = !showDemo
        q('.rz-tour-count').textContent = `${this.index + 1} / ${this.steps.length}`
        q('.rz-tour-bar').style.width = `${((this.index + 1) / this.steps.length) * 100}%`
        q('.rz-tour-back').textContent = this.labels.back
        q('.rz-tour-back').hidden = this.index === 0
        q('.rz-tour-next').textContent = step.nextLabel || (last ? this.labels.done : this.labels.next)
        this.root.classList.toggle('rz-tour--centred', !this.el)
    }

    _place() {
        if (!this.root) return
        const vw = window.innerWidth, vh = window.innerHeight
        const card = this.card.getBoundingClientRect()
        if (!this.el || !visible(this.el)) {
            this.spot.style.cssText = 'opacity:0'
            this.card.style.left = `${Math.max(12, (vw - card.width) / 2)}px`
            this.card.style.top = `${Math.max(12, (vh - card.height) / 2)}px`
            return
        }
        const box = this.el.getBoundingClientRect()
        // a target taller than the screen (a whole page, a long section): light only its visible part
        const r = { left: box.left, right: box.right, width: box.width,
                    top: Math.max(box.top, 8), bottom: Math.min(box.bottom, vh - 8) }
        r.height = Math.max(0, r.bottom - r.top)
        const pad = 6
        Object.assign(this.spot.style, {
            opacity: '1', left: `${r.left - pad}px`, top: `${r.top - pad}px`,
            width: `${r.width + pad * 2}px`, height: `${r.height + pad * 2}px`,
        })
        if (this.whole || r.height > vh * .7) {          // big area: the card sits in its lower right
            this.card.style.left = `${Math.max(12, Math.min(r.right - card.width - 24, vw - card.width - 12))}px`
            this.card.style.top = `${Math.max(12, vh - card.height - 24)}px`
            return
        }
        // below, else above, else beside, else over the bottom of the screen
        let top
        if (r.bottom + GAP + card.height <= vh) top = r.bottom + GAP
        else if (r.top - GAP - card.height >= 0) top = r.top - GAP - card.height
        else top = Math.max(12, vh - card.height - 12)
        let left = r.left + r.width / 2 - card.width / 2
        if (top === Math.max(12, vh - card.height - 12) && r.right + GAP + card.width <= vw) {
            left = r.right + GAP
            top = Math.min(Math.max(12, r.top), vh - card.height - 12)
        }
        this.card.style.left = `${Math.min(Math.max(12, left), vw - card.width - 12)}px`
        this.card.style.top = `${Math.max(12, top)}px`
    }

    _onKey(e) {
        if (!this.root) return
        if (e.key === 'Escape') { e.preventDefault(); this.end('closed') }
        else if (e.key === 'ArrowRight') { e.preventDefault(); this.next() }
        else if (e.key === 'ArrowLeft') { e.preventDefault(); this.back() }
        else if (e.key === 'Tab') {                     // keep the focus in the card
            const items = [...this.card.querySelectorAll('button:not([hidden]), a[href]')]
            if (!items.length) return
            const first = items[0], lastItem = items[items.length - 1]
            if (e.shiftKey && document.activeElement === first) { e.preventDefault(); lastItem.focus() }
            else if (!e.shiftKey && document.activeElement === lastItem) { e.preventDefault(); first.focus() }
        }
    }
}
