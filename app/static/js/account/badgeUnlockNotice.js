/**
 * badgeUnlockNotice.js — "Congratulations, you unlocked X" on any page.
 *
 * Loaded by base.html only when the user's points just moved (a contribution counted). Asks the
 * server (POST /account/badges/check) which badges were just unlocked — the server saves them,
 * so each one is announced once — and shows a Rulezy card bottom-left with a link to the profile.
 */
import { MASCOT_ENABLED } from '/static/js/components/mascot.js'

const LINES = ['Congratulations!', 'Well done!', 'New badge unlocked!', 'Nice work!']

function el(tag, cls, text) {
    const n = document.createElement(tag)
    if (cls) n.className = cls
    if (text) n.textContent = text
    return n
}

function show(badges, profileUrl) {
    const first = badges[0]
    const card = el('div', 'rz-badge-unlock')
    card.setAttribute('role', 'status')
    card.style.setProperty('--badge-color', first.color || '#0d6efd')

    if (MASCOT_ENABLED) {
        const img = el('img', 'rz-badge-unlock__rulezy')
        img.src = `/static/images/rulezy/${first.rulezy_pose || 'armcross'}.png`
        img.alt = 'Rulezy'
        card.append(img)
    } else {
        const icon = el('i', `rz-badge-unlock__icon fa-solid ${first.icon || 'fa-award'}`)
        card.append(icon)
    }

    const body = el('div', 'rz-badge-unlock__body')
    body.append(el('div', 'rz-badge-unlock__title', LINES[Math.floor(Math.random() * LINES.length)]))
    const what = el('div', 'rz-badge-unlock__text')
    what.append(badges.length > 1 ? 'You unlocked the badges ' : 'You unlocked the badge ')
    what.append(el('strong', null, badges.map(b => b.name).join(', ')))
    body.append(what)
    if (badges.length === 1 && first.description) body.append(el('div', 'rz-badge-unlock__desc', first.description))
    const link = el('a', 'rz-badge-unlock__link', 'See my badges')
    link.href = profileUrl
    body.append(link)
    card.append(body)

    const close = el('button', 'rz-badge-unlock__close')
    close.type = 'button'
    close.setAttribute('aria-label', 'Close')
    close.innerHTML = '<i class="fa-solid fa-xmark"></i>'
    const hide = () => { card.classList.add('is-leaving'); setTimeout(() => card.remove(), 300) }
    close.addEventListener('click', hide)
    card.append(close)

    document.body.append(card)
    requestAnimationFrame(() => card.classList.add('is-shown'))
    setTimeout(hide, 12000)
}

async function check() {
    const me = document.currentScript || document.querySelector('script[src*="badgeUnlockNotice.js"]')
    const profileUrl = me?.dataset.profile || '/account/'
    try {
        const res = await fetch('/account/badges/check', {
            method: 'POST',
            headers: { 'X-CSRFToken': document.getElementById('csrf_token')?.value || '' },
        })
        if (!res.ok) return
        const data = await res.json()
        if (data.new_badges?.length) show(data.new_badges, profileUrl)
    } catch { /* never in the way of the page */ }
}

check()
