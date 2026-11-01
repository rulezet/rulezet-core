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

export default {
    name: 'MessageText',
    delimiters: ['[[', ']]'],
    props: { text: { type: String, default: '' } },
    setup(props) {
        const html = ref('')
        const render = async () => { html.value = await renderMessage(props.text) }
        watch(() => props.text, render)
        onMounted(render)
        return { html }
    },
    template: `<div class="chat-text" v-html="html"></div>`,
}
