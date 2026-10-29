/**
 * badge-popover.js — a small card on hover for badges (organisation, "Verified by an admin"…),
 * instead of a browser title: icon + name, a line of text, and a link with a Copy button.
 * It stays open while the mouse is on it, so the link can be selected, opened or copied.
 *
 * Any element, rendered by Jinja or by Vue, gets it with data attributes (no import needed,
 * the listener is on the document):
 *   data-rz-pop-title   the card's title (required)
 *   data-rz-pop-text    a line under it (optional)
 *   data-rz-pop-url     a link, shown with Copy (optional, http(s) only)
 *   data-rz-pop-icon    Font Awesome name, e.g. fa-building (optional)
 *   data-rz-pop-color   accent colour, hex (optional)
 * Loaded once by base.html; CSS in css/components/badge-popover.css.
 */

const SHOW_DELAY = 150
const HIDE_DELAY = 220

let card = null
let current = null
let showTimer = null
let hideTimer = null

function el(tag, cls, text) {
    const n = document.createElement(tag)
    if (cls) n.className = cls
    if (text) n.textContent = text
    return n
}

function build(target) {
    const d = target.dataset
    const color = /^#[0-9a-fA-F]{3,8}$/.test(d.rzPopColor || '') ? d.rzPopColor : '#0d6efd'
    const icon = /^fa-[a-z0-9-]+$/.test(d.rzPopIcon || '') ? d.rzPopIcon : null

    const c = el('div', 'rz-badge-pop')
    c.style.setProperty('--pop-color', color)
    c.setAttribute('role', 'tooltip')

    const head = el('div', 'rz-badge-pop__head')
    if (icon) {
        const i = el('span', 'rz-badge-pop__icon')
        i.append(el('i', `fa-solid ${icon}`))
        head.append(i)
    }
    head.append(el('span', 'rz-badge-pop__title', d.rzPopTitle))
    c.append(head)

    if (d.rzPopText) c.append(el('div', 'rz-badge-pop__text', d.rzPopText))

    const url = d.rzPopUrl || ''
    if (/^https?:\/\//i.test(url)) {
        const row = el('div', 'rz-badge-pop__url')
        const a = el('a', null, url.replace(/^https?:\/\//i, '').replace(/\/$/, ''))
        a.href = url
        a.target = '_blank'
        a.rel = 'noopener noreferrer'
        const copy = el('button', 'rz-badge-pop__copy')
        copy.type = 'button'
        copy.innerHTML = '<i class="fa-regular fa-copy"></i>'
        copy.title = 'Copy the link'
        copy.addEventListener('click', async (e) => {
            e.preventDefault()
            e.stopPropagation()
            try {
                await navigator.clipboard.writeText(url)
                copy.innerHTML = '<i class="fa-solid fa-check"></i>'
                copy.classList.add('is-done')
                setTimeout(() => { copy.innerHTML = '<i class="fa-regular fa-copy"></i>'; copy.classList.remove('is-done') }, 1400)
            } catch { /* clipboard refused: the link stays selectable */ }
        })
        row.append(el('i', 'fa-solid fa-link rz-badge-pop__link-icon'), a, copy)
        c.append(row)
    }

    c.addEventListener('mouseenter', () => clearTimeout(hideTimer))
    c.addEventListener('mouseleave', scheduleHide)
    return c
}

function place(target) {
    const r = target.getBoundingClientRect()
    const w = card.offsetWidth
    const h = card.offsetHeight
    let top = r.bottom + 8
    if (top + h > window.innerHeight - 8) top = Math.max(8, r.top - h - 8)
    let left = r.left + r.width / 2 - w / 2
    left = Math.min(Math.max(8, left), window.innerWidth - w - 8)
    card.style.top = `${top}px`
    card.style.left = `${left}px`
}

function show(target) {
    hide()
    current = target
    card = build(target)
    document.body.append(card)
    place(target)
    requestAnimationFrame(() => card && card.classList.add('is-shown'))
}

function hide() {
    clearTimeout(hideTimer)
    if (card) card.remove()
    card = null
    current = null
}

function scheduleHide() {
    clearTimeout(showTimer)
    clearTimeout(hideTimer)
    hideTimer = setTimeout(hide, HIDE_DELAY)
}

document.addEventListener('mouseover', (e) => {
    const target = e.target.closest?.('[data-rz-pop-title]')
    if (!target) return
    if (target === current) { clearTimeout(hideTimer); return }
    clearTimeout(showTimer)
    showTimer = setTimeout(() => show(target), SHOW_DELAY)
})

document.addEventListener('mouseout', (e) => {
    const target = e.target.closest?.('[data-rz-pop-title]')
    if (!target || target.contains(e.relatedTarget)) return
    if (card && card.contains(e.relatedTarget)) return
    scheduleHide()
})

// keyboard: a focused badge shows its card too
document.addEventListener('focusin', (e) => {
    const target = e.target.closest?.('[data-rz-pop-title]')
    if (target) show(target)
})
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hide() })
window.addEventListener('scroll', () => { if (card) hide() }, { passive: true })
