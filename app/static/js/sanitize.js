/**
 * sanitize.js — shared DOMPurify config for user-authored markdown/HTML.
 *
 * Comments, blog posts, and proposal/PR discussion messages are rendered
 * client-side via marked + DOMPurify and injected with v-html. DOMPurify's
 * default config still allows <form>/<input>/<style> and the style/action
 * attributes, which is enough to build a full-page phishing overlay (fixed
 * position, high z-index, opaque background) with a login form posting
 * credentials to an attacker-controlled host — no <script> tag required.
 * Forbid the tags/attributes that make that possible.
 */

export const SANITIZE_CONFIG = {
    FORBID_TAGS: ['form', 'input', 'button', 'select', 'textarea', 'option',
                  'fieldset', 'legend', 'datalist', 'output', 'label', 'style',
                  'base', 'meta', 'link'],
    FORBID_ATTR: ['style', 'action', 'method', 'formaction', 'target'],
    // DOMPurify's default allows http(s)/mailto/tel/sms/cid/xmpp/matrix/callto/ftp
    // in href/src. This is user-authored rule/comment content, not a chat app —
    // restrict to the schemes we actually render links/images for.
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z\d+.-]+(?:[^a-z\d+.\-:]|$))/i,
}

let _purify = null
export async function getPurify() {
    if (!_purify) {
        const m = await import('/static/js/purify.min.js')
        _purify = m.default || window.DOMPurify
    }
    return _purify
}

let _marked = null
async function getMarked() {
    if (!_marked) {
        const m = await import('/static/js/marked.min.js')
        _marked = m.marked || m.default || window.marked
    }
    return _marked
}

export async function sanitizeHtml(html) {
    const purify = await getPurify()
    return purify.sanitize(html, SANITIZE_CONFIG)
}

export async function renderMarkdown(text) {
    if (!text) return ''
    const mk = await getMarked()
    const html = mk.parse ? mk.parse(text) : mk(text)
    return sanitizeHtml(html)
}


// hardenUserHtml — extra hardening for user content shown to OTHER users
// (bundle files, descriptions, release notes, notes). Run it on HTML that
// already went through DOMPurify (sanitizeHtml / renderMarkdown). It:
//  - never load images / media: an <img src="/some/get/endpoint"> would fire
//    a same-origin request with the viewer's cookies, and remote images leak
//    the viewer's IP. They become a non-loading "[image: alt — host]" text.
//  - keep only absolute http(s) links to *other* hosts, opened in a new tab
//    with noopener/noreferrer; same-origin and relative links become text.
//  - drop id / name attributes (DOM clobbering: a note could otherwise add an
//    element the page looks up with getElementById, e.g. "bundle-info").
//  - drop every class that isn't ours: DOMPurify keeps `class`, and the
//    page's own CSS (e.g. .bfv-backdrop — position:fixed, z-index 1080)
//    would let a note draw a fake full-page overlay.
//  - drop svg / math (sizeable, hard to reason about, never needed here).
const SAFE_CLASS = /^(bn-mention|bn-ref|bn-ref--rule|bn-ref--file|bfv-img-ph|bfv-ext-link|fa-solid|fa-shield-halved|fa-file-lines|language-[\w-]{1,30}|hljs[\w-]*)$/

export function hardenUserHtml(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html')   // inert document
    const here = window.location.origin

    doc.querySelectorAll('svg, math').forEach(el => el.remove())
    doc.querySelectorAll('[id], [name]').forEach(el => { el.removeAttribute('id'); el.removeAttribute('name') })
    doc.querySelectorAll('[class]').forEach(el => {
        const keep = [...el.classList].filter(c => SAFE_CLASS.test(c))
        if (keep.length) el.setAttribute('class', keep.join(' '))
        else el.removeAttribute('class')
    })

    doc.querySelectorAll('img, picture, video, audio, source, iframe, object, embed').forEach(el => {
        const src = el.getAttribute('src') || ''
        let host = ''
        try { host = new URL(src, here).host } catch {}
        const ph = doc.createElement('span')
        ph.className = 'bfv-img-ph'
        ph.textContent = `[image${el.getAttribute('alt') ? ': ' + el.getAttribute('alt') : ''}${host ? ' — ' + host : ''}]`
        ph.title = 'Images are not loaded from bundle files'
        el.replaceWith(ph)
    })

    doc.querySelectorAll('a').forEach(a => {
        const href = a.getAttribute('href') || ''
        let url = null
        try { url = new URL(href, here) } catch {}
        const external = url && /^https?:$/.test(url.protocol) && url.origin !== here && /^https?:\/\//i.test(href)
        if (!external) {
            a.replaceWith(doc.createTextNode(a.textContent))
            return
        }
        a.setAttribute('target', '_blank')
        a.setAttribute('rel', 'noopener noreferrer nofollow')
        a.setAttribute('title', url.href)
        a.classList.add('bfv-ext-link')
    })
    return doc.body.innerHTML
}
