/**
 * tourLauncher.js — the "Tutorial" icon of the top bar, on every page (base.html, data from
 * app/features/tour/tour_core.py, already filtered for who is browsing):
 *   - Tour of this page: who you are browsing as, then the page's own tour (setting
 *     tour.page.<endpoint>) or, when the page has none, a generic tour read from the page itself
 *     (banner title and description, its sections, the navigation);
 *   - Full tour of Rulezet: the main features page after page (setting tour.full), carried from
 *     one page to the next in sessionStorage; on an instance with no rule or bundle the server
 *     sends the demo pages (/tour/demo/...) and the steps show an example instead.
 */
import Tour from '/static/js/components/tour/Tour.js'
import confetti from '/static/js/components/tour/confetti.js'

const STATE_KEY = 'rz-full-tour'
const data = JSON.parse(document.getElementById('rz-tour-data')?.textContent || 'null')

function readState() {
    try { return JSON.parse(sessionStorage.getItem(STATE_KEY) || 'null') } catch { return null }
}
function writeState(state) {
    try { state ? sessionStorage.setItem(STATE_KEY, JSON.stringify(state)) : sessionStorage.removeItem(STATE_KEY) } catch { /* private mode */ }
}
const pathOf = url => { try { return new URL(url, location.origin).pathname.replace(/\/+$/, '') || '/' } catch { return url } }
const here = () => location.pathname.replace(/\/+$/, '') || '/'

// ── example shown in a step when the page has nothing to point at (empty instance) ──
function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])) }
function demoHtml(kind, demo) {
    const d = demo?.[kind]
    if (!d) return ''
    const chips = (d.tags || []).slice(0, 4).map(t => `<span>${esc(t)}</span>`).join('')
    const meta = kind === 'rule' ? `${esc(d.format)} · by ${esc(d.author)}` : `${(d.rules || []).length} rules · by ${esc(d.author)}`
    return `<div class="rz-tour-example"><span class="rz-tour-example__tag">Example</span>
        <div class="rz-tour-example__title">${esc(d.title)}</div>
        <div class="rz-tour-example__meta">${meta}</div>
        <div>${esc(d.description)}</div>
        <div class="rz-tour-example__chips mt-1">${chips}</div></div>`
}
function withDemo(steps, demo) {
    return steps.map(s => s.demo && typeof s.demo === 'string' && !s.demo.startsWith('<')
        ? { ...s, demo: demoHtml(s.demo, demo) } : s)
}

// ── generic tour: read from the page itself ──
// Every page gets one: its banner, then each section, tab bar, form part, table and action button,
// with the text the page itself gives them (subtitles, field names, column names, button tooltips).
// A page with a hand-written tour gets these too, after its own steps, for what those do not cover.
function textOf(el, max = 220) {
    const t = (el?.textContent || '').replace(/\s+/g, ' ').trim()
    return t.length > max ? t.slice(0, max - 1) + '…' : t
}
function shown(el) {
    if (!el || el.closest('.rz-tour, .modal, [hidden], .dropdown-menu, .main-navbar, footer')) return false
    const r = el.getBoundingClientRect()
    return r.width > 4 && r.height > 4
}
const labelOf = el => (el.getAttribute('title') || el.getAttribute('aria-label') || textOf(el, 60)).trim()
const listOf = (items, max = 8) => {
    const names = [...new Set(items.map(x => x.trim()).filter(x => x && x.length < 60))]
    return names.slice(0, max).join(', ') + (names.length > max ? `… (${names.length} in all)` : '')
}

function genericSteps(covered = []) {
    const main = document.querySelector('main') || document.body
    const taken = [...covered]
    const overlaps = el => taken.some(c => c === el || c.contains(el) || el.contains(c))
    const steps = []
    const add = (el, title, text) => {
        if (!el || !shown(el) || overlaps(el) || !title) return
        taken.push(el)
        steps.push({ target: el, title, text })
    }

    const banner = main.querySelector('.explorer-banner')
    if (banner) add(banner, textOf(banner.querySelector('h1, h2'), 80) || 'This page',
                    textOf(banner.querySelector('p')) || 'What this page is about.')

    for (const el of main.querySelectorAll('.dr-nav, [role="tablist"], .nav-tabs, .nav-pills')) {
        const tabs = [...el.querySelectorAll('.dr-nav__item, [role="tab"], .nav-link')].filter(shown).map(t => labelOf(t))
        if (tabs.length > 1) add(el, 'Tabs', `This page is split into tabs: **${listOf(tabs)}**. Click one to switch; the rest of the page follows it.`)
    }

    const sections = main.querySelectorAll('.h-card, .ud-section-header, .card, section, fieldset')
    for (const box of sections) {
        if (steps.length >= 28) break
        const head = box.querySelector(':scope > .h-card__header .h-card__title, :scope .h-card__title, :scope > .card-header, '
            + ':scope > .card-body > h5, :scope > .card-body > h4, :scope > .card-body > h6, :scope > h5, :scope > h4, :scope > legend, .ud-section-title')
        const title = textOf(head || (box.matches('.ud-section-header') ? box : null), 70)
        if (!title || title.length < 3) continue
        const sub = textOf(box.querySelector('.ud-section-sub, .h-card__sub, .card-text, p.text-muted, small.text-muted, p'), 200)
        const fields = [...box.querySelectorAll('label.form-label, label')].filter(shown).map(l => textOf(l, 50).replace(/\*$/, ''))
        const cols = [...box.querySelectorAll('thead th')].filter(shown).map(th => textOf(th, 40))
        const actions = [...box.querySelectorAll('button[title], a.btn[title], button.btn')].filter(shown).map(labelOf)
        let text = sub && sub !== title ? sub : `The “${title}” part of the page.`
        if (fields.length) text += `\n\nFields: **${listOf(fields)}**.`
        if (cols.length) text += `\n\nColumns: **${listOf(cols)}** — click a column name to sort when it is sortable.`
        if (actions.length) text += `\n\nActions here: ${listOf(actions, 6)}.`
        add(box, title, text)
    }

    for (const el of main.querySelectorAll('.form-section-title')) {
        if (steps.length >= 32) break
        const part = el.parentElement
        const fields = [...(part?.querySelectorAll('label') || [])].filter(shown).map(l => textOf(l, 50).replace(/\*$/, ''))
        add(el, textOf(el, 60), fields.length ? `Fields of this part: **${listOf(fields)}**.` : 'A part of the form.')
    }

    for (const table of main.querySelectorAll('table')) {
        if (steps.length >= 34) break
        const cols = [...table.querySelectorAll('thead th')].filter(shown).map(th => textOf(th, 40))
        if (cols.length > 1) add(table, 'The table', `Columns: **${listOf(cols, 10)}**. Rows can usually be clicked to open them.`)
    }

    const buttons = [...main.querySelectorAll('button[title], a.btn[title], .btn-primary, .dt-toolbar-btn')].filter(shown)
    for (const btn of buttons.slice(0, 8)) {
        const name = labelOf(btn)
        if (name && name.length > 1) add(btn, name, btn.getAttribute('title') && btn.getAttribute('title') !== name
            ? btn.getAttribute('title') : `“${name}” — one of the main actions of this page.`)
    }

    const nav = document.querySelector('.main-navbar .navbar-nav')
    if (!covered.length && nav) steps.push({ target: nav, title: 'Navigation',
        text: 'The menus at the top lead to every part of Rulezet: rules, bundles, the community, your account. The **Tutorial** icon (graduation cap, next to the settings gear) is on every page.' })
    return steps
}

// ── page tour ──
function pageSteps() {
    const steps = []
    if (data.intro) steps.push({ title: data.intro.title, text: data.intro.text, badge: data.intro.role_badge })
    if (!data.tour) { steps.push(...genericSteps()); return steps }
    const own = withDemo(data.tour.steps, data.demo)
    // the hand-written steps first, then what the page shows that they do not talk about
    const covered = own.map(st => { try { return st.target && st.target !== '@page' ? document.querySelector(st.target) : null } catch { return null } }).filter(Boolean)
    steps.push(...own, ...genericSteps(covered).map(st => ({ ...st, badge: 'More on this page' })))
    return steps
}
function startPageTour() {
    writeState(null)
    new Tour(pageSteps(), { onEnd: () => {} }).start()
}

// ── full tour, across pages ──
async function startFullTour(onboarding = false) {
    let payload
    try {
        const res = await fetch(data.full_url + (onboarding ? '?onboarding=1' : ''), { headers: { Accept: 'application/json' } })
        payload = await res.json()
    } catch { return }
    if (!payload?.pages?.length) return
    const state = { pages: payload.pages, intro: payload.intro, demo: payload.demo || data.demo, page: 0, step: 0 }
    writeState(state)
    if (pathOf(state.pages[0].url) === here()) runFullTourPage(state)
    else location.href = state.pages[0].url
}

function runFullTourPage(state) {
    const page = state.pages[state.page]
    const lastPage = state.page === state.pages.length - 1
    let steps = withDemo(page.steps, state.demo).map(s => ({ ...s, badge: s.badge || `${page.title} · ${state.page + 1}/${state.pages.length}` }))
    if (state.page === 0 && state.intro) steps = [{ title: state.intro.title, text: state.intro.text, badge: state.intro.role_badge }, ...steps]
    if (!lastPage) {
        const nextTitle = state.pages[state.page + 1].title
        steps[steps.length - 1] = { ...steps[steps.length - 1], nextLabel: `Next: ${nextTitle} →` }
    }
    const tour = new Tour(steps, {
        startAt: Math.min(state.step || 0, steps.length - 1),
        onStep: i => writeState({ ...state, step: i }),
        onNext: i => {
            if (i < steps.length - 1 || lastPage) return true
            writeState({ ...state, page: state.page + 1, step: 0 })
            location.href = state.pages[state.page + 1].url
            return false
        },
        onEnd: () => writeState(null),
    })
    tour.start()
}

// ── the button (top bar, next to the settings gear: sidebar.html) ──
function mountButton() {
    const wrap = document.getElementById('rz-tour-launch')
    if (!wrap) return
    const state = readState()
    const menu = document.createElement('div')
    menu.className = 'rz-tour-launch__menu'
    menu.setAttribute('role', 'menu')
    menu.hidden = true
    menu.innerHTML = `
        <div class="rz-tour-launch__role">${esc(data.intro?.role_badge ? 'Browsing as: ' + data.intro.role_badge : 'Tutorial')}</div>
        <button type="button" class="rz-tour-launch__item" role="menuitem" data-act="page">
            <i class="fa-solid fa-location-crosshairs"></i><span><strong>Tour of this page</strong><small>What everything here does</small></span></button>
        <button type="button" class="rz-tour-launch__item" role="menuitem" data-act="full">
            <i class="fa-solid fa-route"></i><span><strong>Full tour of Rulezet</strong><small>The main features, page after page</small></span></button>
        ${state ? `<button type="button" class="rz-tour-launch__item" role="menuitem" data-act="resume">
            <i class="fa-solid fa-play"></i><span><strong>Resume the full tour</strong><small>${esc(state.pages[state.page]?.title || '')}</small></span></button>` : ''}`
    wrap.appendChild(menu)
    const btn = wrap.querySelector('.rz-tour-launch__btn')
    const toggle = open => { menu.hidden = !open; btn.setAttribute('aria-expanded', String(open)); if (open) menu.querySelector('button')?.focus() }
    btn.addEventListener('click', e => { e.stopPropagation(); toggle(menu.hidden) })
    document.addEventListener('click', e => { if (!wrap.contains(e.target)) toggle(false) })
    menu.addEventListener('keydown', e => { if (e.key === 'Escape') { toggle(false); btn.focus() } })
    menu.addEventListener('click', e => {
        const act = e.target.closest('[data-act]')?.dataset.act
        if (!act) return
        toggle(false)
        if (act === 'page') startPageTour()
        else if (act === 'full') startFullTour()
        else if (act === 'resume') {
            const s = readState()
            if (!s) return
            if (pathOf(s.pages[s.page].url) === here()) runFullTourPage(s)
            else location.href = s.pages[s.page].url
        }
    })
}

if (data) {
    mountButton()
    // A fresh, empty Rulezet — after the Rulezet logo has built itself (home page):
    //  - nobody has set up the first admin yet: a thank-you card that sends to the admin login
    //    (the email and password are set right after, then the tour starts — no tour before that);
    //  - the admin has just set the account up: confetti, then the full tour at once;
    //  - otherwise (empty instance, set up already): the welcome card, until the instance has a rule.
    const pending = readState()
    const tourHere = pending && pending.pages?.[pending.page] && pathOf(pending.pages[pending.page].url) === here()
    const afterLogo = () => new Promise(r => setTimeout(r, document.querySelector('.hv2-stage__logo') ? 3800 : 600))
    const createStarter = async () => {
        const csrf = document.getElementById('csrf_token')?.value || ''
        try { await fetch(data.starter_url, { method: 'POST', headers: { 'X-CSRFToken': csrf, Accept: 'application/json' } }) } catch { /* the tour still runs on the demo pages */ }
    }
    if (data.just_setup) {
        ;(async () => {
            await new Promise(r => setTimeout(r, 400))
            await Promise.all([confetti(), createStarter()])
            startFullTour(true)
        })()
    } else if (data.setup_pending && !tourHere) {
        ;(async () => {
            await afterLogo()
            new Tour([{
                badge: 'First start', title: 'Thank you for installing Rulezet! 🎉',
                text: 'Your instance is up and running. One thing before the tour: **log in as the administrator** and choose '
                    + 'your own email and password.\n\nThe login is `admin@admin.admin`; its password is printed in the '
                    + 'terminal where you started Rulezet (the yellow **First login** box).',
                nextLabel: 'Log in as administrator →', href: '/account/login',
            }], { labels: { close: 'Later' } }).start()
        })()
    } else if (data.autostart && !tourHere) {
        ;(async () => {
            await afterLogo()
            if (data.logged_in) await createStarter()
            new Tour([{
                badge: 'Welcome', title: 'Welcome to Rulezet 👋',
                text: data.logged_in
                    ? 'This Rulezet is brand new. A short tour shows how to fill it — connectors, Git imports, your own rules — and then every main feature.'
                    : 'This Rulezet is brand new. A short tour shows what it is and how to fill it.',
                nextLabel: 'Start the tour →',
            }], { labels: { close: 'Not now' }, onNext: () => { startFullTour(true); return false }, onEnd: () => {} }).start()
        })()
    }
    const state = readState()                       // the full tour continues on this page
    if (state && state.pages?.[state.page] && pathOf(state.pages[state.page].url) === here()) runFullTourPage(state)
}
