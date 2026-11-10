/**
 * history_lightbox.js — the story page (macros/history_logo.html): click a logo or a screenshot of the
 * timeline (.hl-zoom, data-full / data-caption) to see it big in a modal. Esc / click outside / ×
 * close it, ← → go to the previous / next image. CSS: css/history/history_logo.css (hl-lb-*).
 */
const items = [...document.querySelectorAll('.hl-zoom')]
let index = -1
let box = null
let lastFocus = null

function build() {
    box = document.createElement('div')
    box.className = 'hl-lb'
    box.setAttribute('role', 'dialog')
    box.setAttribute('aria-modal', 'true')
    box.innerHTML = `
        <button type="button" class="hl-lb__btn hl-lb__close" aria-label="Close"><i class="fa-solid fa-xmark"></i></button>
        <button type="button" class="hl-lb__btn hl-lb__prev" aria-label="Previous image"><i class="fa-solid fa-chevron-left"></i></button>
        <figure class="hl-lb__figure">
            <div class="hl-lb__frame"><img alt=""></div>
            <figcaption class="hl-lb__caption"></figcaption>
        </figure>
        <button type="button" class="hl-lb__btn hl-lb__next" aria-label="Next image"><i class="fa-solid fa-chevron-right"></i></button>`
    document.body.appendChild(box)
    box.querySelector('.hl-lb__close').addEventListener('click', close)
    box.querySelector('.hl-lb__prev').addEventListener('click', () => show(index - 1))
    box.querySelector('.hl-lb__next').addEventListener('click', () => show(index + 1))
    box.addEventListener('mousedown', e => { if (e.target === box || e.target.classList.contains('hl-lb__figure')) close() })
}

function show(i) {
    index = (i + items.length) % items.length
    const el = items[index]
    const img = box.querySelector('img')
    img.src = el.dataset.full
    img.alt = el.dataset.caption || ''
    box.querySelector('.hl-lb__caption').textContent = `${el.dataset.caption || ''}  ·  ${index + 1} / ${items.length}`
    box.querySelector('.hl-lb__frame').classList.toggle('hl-lb__frame--shot', el.classList.contains('hl-card__media--shot'))
}

function open(i) {
    if (!box) build()
    lastFocus = document.activeElement
    show(i)
    box.classList.add('hl-lb--open')
    document.body.style.overflow = 'hidden'
    box.querySelector('.hl-lb__close').focus()
    document.addEventListener('keydown', onKey)
}

function close() {
    box.classList.remove('hl-lb--open')
    document.body.style.overflow = ''
    document.removeEventListener('keydown', onKey)
    lastFocus?.focus?.()
}

function onKey(e) {
    if (e.key === 'Escape') close()
    else if (e.key === 'ArrowLeft') show(index - 1)
    else if (e.key === 'ArrowRight') show(index + 1)
}

items.forEach((el, i) => el.addEventListener('click', () => open(i)))
