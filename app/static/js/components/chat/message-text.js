/**
 * message-text.js — renders a message: Markdown (marked + DOMPurify, sanitize.js) with
 *   @[Name](12)          → a chip to the user's profile
 *   #[Label](kind:key)   → a chip to that rule / bundle / blog post / CVE / ATT&CK technique / git source / channel,
 *                          through /messages/ref/<kind>/<key> (the server checks the reader may see it)
 * Used by the Messages page; any page can render chat text with it.
 *
 *   import MessageText, { renderMessage, plainMessage } from '/static/js/components/chat/message-text.js'
 *   <message-text :text="m.content"></message-text>
 */
import { renderMarkdown } from '/static/js/sanitize.js'

const { ref, watch, onMounted } = Vue

export const REF_ICONS = {
    rule: 'fa-solid fa-shield-halved', bundle: 'fa-solid fa-box-archive', blog: 'fa-solid fa-newspaper',
    cve: 'fa-solid fa-bug', attack: 'fa-solid fa-crosshairs', repo: 'fa-brands fa-git-alt', channel: 'fa-solid fa-hashtag',
}
const MENTION = /@\[([^\]]{1,80})\]\((\d+)\)/g
const REFERENCE = /#\[([^\]]{1,120})\]\(([a-z]+):([^)\s]{1,120})\)/g

const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))

export async function renderMessage(text) {
    if (!text) return ''
    const pre = String(text)
        .replace(MENTION, (m, name, id) =>
            `<a href="/account/detail_user/${id}" class="chat-chip chat-chip--user"><i class="fa-solid fa-at"></i>${esc(name)}</a>`)
        .replace(REFERENCE, (m, label, kind, key) => REF_ICONS[kind]
            ? `<a href="/messages/ref/${kind}/${encodeURIComponent(key)}" class="chat-chip chat-chip--${kind}"><i class="${REF_ICONS[kind]}"></i>${esc(label)}</a>`
            : esc(m))
    return keepOwnImages(await renderMarkdown(pre))
}

// Images: only the conversation's own uploads (/messages/files/…) are loaded — an outside image would tell its
// server who reads the message. They open full size in a new tab; any other image becomes a plain link.
function keepOwnImages(html) {
    if (!html.includes('<img')) return html
    const doc = new DOMParser().parseFromString(`<div>${html}</div>`, 'text/html')
    doc.querySelectorAll('img').forEach(img => {
        const src = img.getAttribute('src') || ''
        if (/^\/messages\/files\/[\w-]+\/[0-9a-f]{32}\.(png|jpg)$/.test(src)) {
            img.setAttribute('loading', 'lazy')
            img.classList.add('chat-img')
            if (img.parentElement.tagName !== 'A') {
                const a = doc.createElement('a'); a.href = src; a.target = '_blank'; a.rel = 'noopener'
                img.replaceWith(a); a.appendChild(img)
            }
        } else {
            const a = doc.createElement('a'); a.href = src; a.rel = 'noopener noreferrer'; a.target = '_blank'
            a.textContent = `[image: ${img.getAttribute('alt') || src}]`
            img.replaceWith(a)
        }
    })
    return doc.body.firstChild.innerHTML
}

// One line, no Markdown — previews, notifications, reply quotes
export function plainMessage(text) {
    return String(text || '').replace(/!\[([^\]]*)\]\([^)]*\)/g, '🖼 $1').replace(MENTION, '@$1').replace(REFERENCE, '#$1')
        .replace(/[*_`>#~]+/g, '').replace(/\s+/g, ' ').trim()
}

// ── Link previews: a card under the message for each link to a Rulezet page (rule, bundle, proposal, merge request,
// blog post, CVE, technique, profile, channel). One request for all the links seen in the same moment, every answer
// kept for the page's life — a list of messages never asks twice for the same link.
const _cache = new Map()
let _queue = [], _timer = null
function _flush() {
    const urls = [...new Set(_queue.map(q => q.url))]
    const waiting = _queue
    _queue = []; _timer = null
    const csrf = document.getElementById('csrf_token')?.value || ''
    fetch('/messages/api/previews', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                                      body: JSON.stringify({ urls }) })
        .then(r => r.ok ? r.json() : { previews: {} }).catch(() => ({ previews: {} }))
        .then(d => waiting.forEach(q => q.resolve((d.previews || {})[q.url] || null)))
}
export function linkPreview(url) {
    if (!_cache.has(url)) _cache.set(url, new Promise(resolve => {
        _queue.push({ url, resolve })
        if (!_timer) _timer = setTimeout(_flush, 60)
    }))
    return _cache.get(url)
}
function ownLinks(html) {
    const doc = new DOMParser().parseFromString(`<div>${html}</div>`, 'text/html')
    const out = []
    doc.querySelectorAll('a[href]:not(.chat-chip)').forEach(a => {
        let u
        try { u = new URL(a.getAttribute('href'), location.origin) } catch { return }
        if (u.origin === location.origin && u.pathname !== '/' && !u.pathname.startsWith('/messages/files/')) out.push(u.pathname + u.search)
    })
    return [...new Set(out)].slice(0, 3)
}

export default {
    name: 'MessageText',
    delimiters: ['[[', ']]'],
    props: { text: { type: String, default: '' }, previews: { type: Boolean, default: true } },
    setup(props) {
        const html = ref('')
        const cards = ref([])
        const render = async () => {
            html.value = await renderMessage(props.text)
            if (!props.previews) return
            const urls = ownLinks(html.value)
            cards.value = urls.length ? (await Promise.all(urls.map(linkPreview))).filter(Boolean) : []
        }
        watch(() => props.text, render)
        onMounted(render)
        return { html, cards }
    },
    template: `
    <div class="chat-text" v-html="html"></div>
    <div v-if="cards.length" class="chat-cards">
        <a v-for="c in cards" :key="c.url" :href="c.url" class="chat-card" :style="{ '--c': c.color }">
            <span class="chat-card__media">
                <img v-if="c.image" :src="c.image" alt="" loading="lazy">
                <i v-else :class="c.icon"></i>
            </span>
            <span class="chat-card__body">
                <span class="chat-card__kind"><i :class="c.icon"></i>[[ c.kind_label ]]</span>
                <span class="chat-card__title">[[ c.title ]]</span>
                <span v-if="c.description" class="chat-card__desc">[[ c.description ]]</span>
                <span v-if="c.meta.length" class="chat-card__meta"><span v-for="m in c.meta" :key="m">[[ m ]]</span></span>
            </span>
        </a>
    </div>`,
}
