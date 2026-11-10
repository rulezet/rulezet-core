/**
 * confirm-dialog.js — Rulezet's own confirmation / input dialogs, instead of the browser's
 * confirm() / prompt() grey boxes. CSS: css/components/confirm-dialog.css (rzd-*).
 *
 *   if (!(await rzConfirm('Delete this tag?'))) return
 *   const ok = await rzConfirm({ title: 'Regenerate the key?', message: 'The current link stops working.',
 *                                confirmText: 'Regenerate', danger: true })
 *   const name = await rzPrompt({ title: 'Rename', value: 'old name' })      // string, or null if cancelled
 *
 * Both return a Promise. Loaded once by base.html, which also sets window.rzConfirm / window.rzPrompt,
 * so any page script can call them without importing.
 *
 * A plain-text message: "\n" are kept as line breaks, never rendered as HTML. Danger style (red
 * button) is picked automatically for deleting / irreversible actions unless `danger` is given.
 * Esc / click outside = cancel, Enter = confirm.
 */

const DANGER = /\b(delete|remove|permanently|irreversible|cannot be undone|can't be undone|revoke|purge|wipe|erase|discard|reject|ban|disable|reset|stops working|overwrite)\b/i

function verbOf(text) {
    const m = /^\s*(delete|remove|revoke|purge|reset|regenerate|discard|reject|disable|enable|restore|archive|publish|accept|approve|merge|close|reopen|cancel|stop|run|start|leave|make|give|renew|send|import|apply|replace|overwrite|clear|unlink|unfollow|block|unblock)\b/i.exec(text || '')
    return m ? m[1][0].toUpperCase() + m[1].slice(1).toLowerCase() : null
}

function splitTitle(text) {
    // "Delete this rule?\nThis cannot be undone." → title "Delete this rule?", message the rest
    const t = String(text ?? '').trim()
    const nl = t.indexOf('\n')
    if (nl > 0 && nl < 140) return { title: t.slice(0, nl).trim(), message: t.slice(nl + 1).trim() }
    const q = t.indexOf('?')
    if (q > 0 && q < 140 && q < t.length - 1) return { title: t.slice(0, q + 1), message: t.slice(q + 1).trim() }
    if (t.length <= 120) return { title: t, message: '' }
    return { title: 'Are you sure?', message: t }
}

function normalise(opts, kind) {
    if (typeof opts === 'string' || opts == null) opts = { ...splitTitle(opts) }
    else if (!opts.title) opts = { ...opts, ...splitTitle(opts.message) }
    const all = `${opts.title || ''} ${opts.message || ''}`
    const danger = opts.danger ?? (kind === 'confirm' && DANGER.test(all))
    return {
        title: opts.title || (kind === 'prompt' ? 'Enter a value' : 'Are you sure?'),
        message: opts.message || '',
        confirmText: opts.confirmText || (kind === 'prompt' ? 'OK' : (verbOf(opts.title) || (danger ? 'Delete' : 'Confirm'))),
        cancelText: opts.cancelText || 'Cancel',
        danger,
        value: opts.value ?? '',
        placeholder: opts.placeholder || '',
        icon: opts.icon || (danger ? 'fa-triangle-exclamation' : kind === 'prompt' ? 'fa-pen' : 'fa-circle-question'),
    }
}

function el(tag, cls, text) {
    const e = document.createElement(tag)
    if (cls) e.className = cls
    if (text != null) e.textContent = text
    return e
}

let queue = Promise.resolve()          // one dialog at a time

function open(kind, rawOpts) {
    const run = () => new Promise(resolve => {
        const o = normalise(rawOpts, kind)
        const lastFocus = document.activeElement
        const back = el('div', 'rzd-backdrop')
        const box = el('div', 'rzd-dialog' + (o.danger ? ' rzd-dialog--danger' : ''))
        box.setAttribute('role', 'dialog')
        box.setAttribute('aria-modal', 'true')

        const head = el('div', 'rzd-head')
        const ic = el('div', 'rzd-icon'); ic.appendChild(el('i', `fa-solid ${o.icon}`))
        const titles = el('div', 'rzd-titles')
        const h = el('div', 'rzd-title', o.title); h.id = 'rzd-title-' + Date.now()
        box.setAttribute('aria-labelledby', h.id)
        titles.appendChild(h)
        if (o.message) titles.appendChild(el('div', 'rzd-message', o.message))
        head.append(ic, titles)
        box.appendChild(head)

        let input = null
        if (kind === 'prompt') {
            input = el('input', 'form-control rzd-input')
            input.type = 'text'
            input.value = o.value
            input.placeholder = o.placeholder
            box.appendChild(input)
        }

        const actions = el('div', 'rzd-actions')
        const cancel = el('button', 'btn btn-sm btn-outline-secondary rounded-pill px-3', o.cancelText)
        const ok = el('button', `btn btn-sm rounded-pill px-4 ${o.danger ? 'btn-danger' : 'btn-primary'}`, o.confirmText)
        cancel.type = ok.type = 'button'
        actions.append(cancel, ok)
        box.appendChild(actions)
        back.appendChild(box)
        document.body.appendChild(back)
        document.body.classList.add('rzd-open')
        requestAnimationFrame(() => back.classList.add('rzd-show'))
        ;(input || ok).focus()
        if (input) input.select()

        function close(result) {
            document.removeEventListener('keydown', onKey, true)
            back.classList.remove('rzd-show')
            document.body.classList.remove('rzd-open')
            setTimeout(() => back.remove(), 150)
            try { lastFocus?.focus?.() } catch {}
            resolve(result)
        }
        const yes = () => close(kind === 'prompt' ? input.value : true)
        const no = () => close(kind === 'prompt' ? null : false)
        function onKey(e) {
            if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); no() }
            else if (e.key === 'Enter' && (e.target === input || e.target === ok || !box.contains(e.target))) { e.preventDefault(); yes() }
            else if (e.key === 'Tab') {                    // keep the focus inside the dialog
                const f = [input, cancel, ok].filter(Boolean)
                const i = f.indexOf(document.activeElement)
                e.preventDefault()
                f[(i + (e.shiftKey ? f.length - 1 : 1)) % f.length].focus()
            }
        }
        document.addEventListener('keydown', onKey, true)
        ok.addEventListener('click', yes)
        cancel.addEventListener('click', no)
        back.addEventListener('mousedown', e => { if (e.target === back) no() })
    })
    const p = queue.then(run, run)
    queue = p.catch(() => {})
    return p
}

export function rzConfirm(opts) { return open('confirm', opts) }
export function rzPrompt(opts) { return open('prompt', opts) }
