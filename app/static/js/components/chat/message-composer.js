/**
 * message-composer.js — the box to write a message: Markdown with Write / Preview, a toolbar,
 *   @  → pick a user  (inserts @[Name](id))
 *   #  → pick a rule, bundle, blog post, CVE, ATT&CK technique, git source or channel (inserts #[Label](kind:key))
 * Images (when upload-url is given): the image button, paste (Ctrl+V) or drop a file — uploaded, then inserted as ![name](url).
 * Enter sends, Shift+Enter makes a new line, Esc cancels a reply / an edit, ↑ in an empty box edits your last message.
 *
 *   import MessageComposer from '/static/js/components/chat/message-composer.js'
 *   <message-composer :disabled="…" :reply-to="m" :editing="m" placeholder="…"
 *                     @send="text => …" @cancel="…" @edit-last="…"></message-composer>
 */
import MessageText from '/static/js/components/chat/message-text.js'
import { REF_ICONS } from '/static/js/components/chat/message-text.js'

const { ref, computed, watch, nextTick } = Vue

export default {
    name: 'MessageComposer',
    delimiters: ['[[', ']]'],
    components: { MessageText },
    props: {
        placeholder: { type: String, default: 'Write a message…' },
        disabled: { type: Boolean, default: false },
        replyTo: { type: Object, default: null },
        editing: { type: Object, default: null },
        maxLength: { type: Number, default: 8000 },
        draftKey: { type: String, default: '' },
        uploadUrl: { type: String, default: '' },          // POST image → { url, name }
    },
    emits: ['send', 'cancel', 'edit-last', 'typing'],
    setup(props, { emit }) {
        const text = ref('')
        const preview = ref(false)
        const box = ref(null)
        const sending = ref(false)

        // ── drafts, kept per conversation in this browser ──
        const loadDraft = () => {
            if (props.editing) { text.value = props.editing.content; return }
            try { text.value = props.draftKey ? (localStorage.getItem('rz-draft:' + props.draftKey) || '') : '' } catch { text.value = '' }
        }
        const saveDraft = () => {
            if (props.editing || !props.draftKey) return
            try { text.value ? localStorage.setItem('rz-draft:' + props.draftKey, text.value) : localStorage.removeItem('rz-draft:' + props.draftKey) } catch { }
        }
        watch(() => [props.draftKey, props.editing && props.editing.id], () => { loadDraft(); preview.value = false; nextTick(autosize) }, { immediate: true })
        watch(() => props.replyTo, v => { if (v) focus() })

        function autosize() {
            const el = box.value
            if (!el) return
            el.style.height = 'auto'
            el.style.height = Math.min(el.scrollHeight, 260) + 'px'
        }
        function focus() { nextTick(() => box.value && box.value.focus()) }

        // ── @ and # pickers ──
        const picker = ref(null)          // null | 'user' | 'ref'
        const pickKind = ref(null)        // the "Attach" menu: search one kind only
        const ATTACH = [
            { kind: 'rule', label: 'Rule' }, { kind: 'bundle', label: 'Bundle' }, { kind: 'blog', label: 'Blog post' },
            { kind: 'cve', label: 'Vulnerability (CVE…)' }, { kind: 'attack', label: 'ATT&CK technique' },
            { kind: 'repo', label: 'Git source' }, { kind: 'channel', label: 'Channel' },
        ]
        const attachOpen = ref(false)
        const results = ref([])
        const active = ref(0)
        const loading = ref(false)
        let start = 0, timer = null, seq = 0

        function closePicker() { picker.value = null; pickKind.value = null; results.value = []; active.value = 0 }

        function onInput() {
            autosize(); saveDraft(); emit('typing')
            const el = box.value
            const before = text.value.slice(0, el.selectionStart)
            const um = before.match(/(?:^|\s)@([\w.\- ]{0,30})$/)
            const rm = before.match(/(?:^|\s)#([^#\[\]()\n]{0,60})$/)
            const m = um || rm
            if (!m) return closePicker()
            const q = m[1]
            // "#" followed by words: keep searching while it finds something, a sentence goes on normally
            if (!um && /^\s/.test(q)) return closePicker()          // "# title" in Markdown
            if (!um && /\s/.test(q) && !pickKind.value && picker.value === 'ref' && !loading.value && !results.value.length) return closePicker()
            if (!um && picker.value !== 'ref') pickKind.value = null
            picker.value = um ? 'user' : 'ref'
            start = before.length - q.length - 1
            if (picker.value === 'user' && q.length < 2) { results.value = []; loading.value = false; return }
            if (picker.value === 'ref' && q.length < 1 && !pickKind.value) { results.value = []; loading.value = false; return }
            loading.value = true
            clearTimeout(timer)
            const my = ++seq
            timer = setTimeout(async () => {
                try {
                    const url = picker.value === 'user' ? '/account/search_mentionable_users?q=' + encodeURIComponent(q)
                                                        : '/messages/api/refs?q=' + encodeURIComponent(q) + (pickKind.value ? '&kinds=' + pickKind.value : '')
                    const data = await (await fetch(url)).json()
                    if (my !== seq) return
                    results.value = picker.value === 'user' ? (data.users || []) : (data.items || [])
                    active.value = 0
                } catch { if (my === seq) results.value = [] } finally { if (my === seq) loading.value = false }
            }, 220)
        }

        function insert(token) {
            const el = box.value
            const end = el.selectionStart
            text.value = text.value.slice(0, start) + token + ' ' + text.value.slice(end)
            closePicker()
            nextTick(() => { const p = start + token.length + 1; el.focus(); el.setSelectionRange(p, p); autosize(); saveDraft() })
        }
        const clean = s => String(s).replace(/[\[\]()]/g, ' ').replace(/\s+/g, ' ').trim()
        function pick(item) {
            if (!item) return
            if (picker.value === 'user') insert(`@[${clean(item.username)}](${item.id})`)
            else insert(`#[${clean(item.label)}](${item.kind}:${item.key})`)
        }

        // ── toolbar ──
        function wrap(before, after = before, placeholder = 'text') {
            const el = box.value
            const s = el.selectionStart, e = el.selectionEnd
            const sel = text.value.slice(s, e) || placeholder
            text.value = text.value.slice(0, s) + before + sel + after + text.value.slice(e)
            nextTick(() => { el.focus(); el.setSelectionRange(s + before.length, s + before.length + sel.length); autosize(); saveDraft() })
        }
        const attachMenu = ref(null)
        function openAttach() {
            attachOpen.value = !attachOpen.value
            if (attachOpen.value) nextTick(() => attachMenu.value && attachMenu.value.querySelector('button').focus())
        }
        function onAttachKey(e) {
            const items = [...attachMenu.value.querySelectorAll('button')], i = items.indexOf(document.activeElement)
            if (e.key === 'ArrowDown') { e.preventDefault(); items[(i + 1) % items.length].focus() }
            else if (e.key === 'ArrowUp') { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus() }
            else if (e.key === 'Home') { e.preventDefault(); items[0].focus() }
            else if (e.key === 'End') { e.preventDefault(); items[items.length - 1].focus() }
            else if (e.key === 'Escape' || e.key === 'Tab') { if (e.key === 'Escape') e.preventDefault(); attachOpen.value = false; if (e.key === 'Escape') focus() }
        }
        function attach(kind) {
            attachOpen.value = false
            picker.value = 'ref'          // set first: onInput keeps the kind while the "#" picker is open
            pickKind.value = kind
            trigger('#')
        }
        function trigger(ch) {
            const el = box.value
            const s = el.selectionStart
            const pad = s > 0 && !/\s/.test(text.value[s - 1]) ? ' ' : ''
            text.value = text.value.slice(0, s) + pad + ch + text.value.slice(s)
            nextTick(() => { el.focus(); el.setSelectionRange(s + pad.length + 1, s + pad.length + 1); onInput() })
        }

        // ── images: button, paste, drop ──
        const uploading = ref(0)
        const dragging = ref(false)
        const fileInput = ref(null)
        const csrf = () => document.getElementById('csrf_token')?.value || ''
        async function uploadImages(files) {
            if (!props.uploadUrl) return
            for (const f of [...files].filter(f => /^image\//.test(f.type)).slice(0, 6)) {
                if (f.size > 5 * 1024 * 1024) { window.create_message ? window.create_message('The image is larger than 5 MB.', 'danger-subtle') : alert('The image is larger than 5 MB.'); continue }
                uploading.value++
                try {
                    const fd = new FormData(); fd.append('image', f, f.name || 'pasted.png')
                    const res = await fetch(props.uploadUrl, { method: 'POST', headers: { 'X-CSRFToken': csrf() }, body: fd })
                    const data = await res.json().catch(() => null)
                    if (!res.ok || !data) { import('/static/js/toaster.js').then(m => m.create_message((data && data.message) || 'Upload failed.', 'danger-subtle')); continue }
                    const el = box.value, at = el ? el.selectionStart : text.value.length
                    const md = `![${(data.name || 'image').replace(/[\[\]]/g, '')}](${data.url})`
                    const pad = at > 0 && text.value[at - 1] !== '\n' ? '\n' : ''
                    text.value = text.value.slice(0, at) + pad + md + '\n' + text.value.slice(at)
                    saveDraft(); nextTick(autosize)
                } finally { uploading.value-- }
            }
            focus()
        }
        function onPaste(e) {
            const files = [...(e.clipboardData?.files || [])]
            if (files.length && props.uploadUrl) { e.preventDefault(); uploadImages(files) }
        }
        function onDrop(e) { dragging.value = false; if (e.dataTransfer?.files?.length) uploadImages(e.dataTransfer.files) }
        function onDragOver(e) { if (props.uploadUrl && [...(e.dataTransfer?.items || [])].some(i => i.kind === 'file')) dragging.value = true }

        // ── sending ──
        const tooLong = computed(() => text.value.length > props.maxLength)
        const canSend = computed(() => !props.disabled && !sending.value && !uploading.value && text.value.trim() && !tooLong.value)
        async function send() {
            if (!canSend.value) return
            sending.value = true
            const value = text.value.trim()
            try {
                const ok = await new Promise(resolve => emit('send', value, resolve))
                if (ok !== false) { text.value = ''; preview.value = false; saveDraft(); nextTick(autosize) }
            } finally { sending.value = false; focus() }
        }

        function onKey(e) {
            if (picker.value && results.value.length) {
                if (e.key === 'ArrowDown') { e.preventDefault(); active.value = (active.value + 1) % results.value.length; return }
                if (e.key === 'ArrowUp') { e.preventDefault(); active.value = (active.value - 1 + results.value.length) % results.value.length; return }
                if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); pick(results.value[active.value]); return }
            }
            if (e.key === 'Escape') { if (picker.value) closePicker(); else emit('cancel'); return }
            if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); return }
            if (e.key === 'ArrowUp' && !text.value && !props.editing) { e.preventDefault(); emit('edit-last') }
            if ((e.ctrlKey || e.metaKey) && e.key === 'b') { e.preventDefault(); wrap('**') }
            if ((e.ctrlKey || e.metaKey) && e.key === 'i') { e.preventDefault(); wrap('_') }
        }

        return { text, preview, box, sending, picker, results, active, loading, tooLong, canSend, REF_ICONS,
                 onInput, onKey, pick, wrap, trigger, send, focus, closePicker, uploading, dragging, fileInput, uploadImages, onPaste, onDrop, onDragOver, pickKind, ATTACH, attachOpen, attach, attachMenu, openAttach, onAttachKey }
    },
    template: `
    <div class="chat-composer" :class="{ 'is-disabled': disabled, 'is-editing': editing }">
        <div v-if="replyTo || editing" class="chat-composer__context">
            <i :class="editing ? 'fa-solid fa-pen' : 'fa-solid fa-reply'"></i>
            <span v-if="editing">Editing your message</span>
            <span v-else>Replying to <b>[[ replyTo.author ? replyTo.author.name : '' ]]</b></span>
            <button type="button" class="chat-composer__x" title="Cancel (Esc)" @click="$emit('cancel')"><i class="fa-solid fa-xmark"></i></button>
        </div>

        <div v-if="picker" class="chat-picker">
            <div class="chat-picker__head">[[ picker === 'user' ? 'Mention someone' : (pickKind ? 'Attach a ' + ATTACH.find(a => a.kind === pickKind).label.toLowerCase() + ' — type to search' : 'Link a rule, bundle, blog post, CVE, technique, git source or channel') ]]
                <button v-if="pickKind" type="button" class="chat-picker__close" @mousedown.prevent="closePicker" title="Close"><i class="fa-solid fa-xmark"></i></button></div>
            <div v-if="loading" class="chat-picker__empty"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
            <div v-else-if="!results.length" class="chat-picker__empty">[[ picker === 'user' ? 'Type 2 letters of a name' : (pickKind ? 'Nothing found' : 'Type a title, an id, CVE-…, T1059…') ]]</div>
            <button v-for="(it, i) in results" :key="i" type="button" class="chat-picker__row" :class="{ 'is-active': i === active }"
                    @mousedown.prevent="pick(it)" @mouseenter="active = i">
                <template v-if="picker === 'user'">
                    <img v-if="it.avatar" :src="it.avatar" class="chat-avatar chat-avatar--xs" alt="">
                    <span class="chat-picker__label">[[ it.username ]]</span>
                </template>
                <template v-else>
                    <i :class="REF_ICONS[it.kind]" class="chat-picker__icon"></i>
                    <span class="chat-picker__label">[[ it.label ]]</span>
                    <span class="chat-picker__kind">[[ it.kind_label ]]<template v-if="it.sub"> · [[ it.sub ]]</template></span>
                </template>
            </button>
        </div>

        <div class="chat-composer__box" :class="{ 'is-dragging': dragging }"
             @dragover.prevent="onDragOver" @dragleave.self="dragging = false" @drop.prevent="onDrop">
            <div v-if="dragging" class="chat-composer__drop"><i class="fa-solid fa-image me-2"></i>Drop the image to add it</div>
            <message-text v-if="preview" class="chat-composer__preview" :text="text || '_Nothing to preview_'"></message-text>
            <textarea v-show="!preview" ref="box" v-model="text" rows="1" :placeholder="disabled ? 'You can\\'t write here' : placeholder"
                      :disabled="disabled" @input="onInput" @keydown="onKey" @paste="onPaste" @blur="pickKind ? null : closePicker()"
                      aria-label="Message"></textarea>
            <div class="chat-composer__bar">
                <button type="button" class="chat-tool" title="Bold (Ctrl+B)" @click="wrap('**')" :disabled="preview"><i class="fa-solid fa-bold"></i></button>
                <button type="button" class="chat-tool" title="Italic (Ctrl+I)" @click="wrap('_')" :disabled="preview"><i class="fa-solid fa-italic"></i></button>
                <button type="button" class="chat-tool" title="Code" @click="wrap('\`')" :disabled="preview"><i class="fa-solid fa-code"></i></button>
                <button type="button" class="chat-tool" title="Code block" @click="wrap('\\n\`\`\`\\n', '\\n\`\`\`\\n', 'code')" :disabled="preview"><i class="fa-solid fa-file-code"></i></button>
                <button type="button" class="chat-tool" title="Quote" @click="wrap('\\n> ', '', 'quote')" :disabled="preview"><i class="fa-solid fa-quote-left"></i></button>
                <button type="button" class="chat-tool" title="Link" @click="wrap('[', '](https://)', 'link')" :disabled="preview"><i class="fa-solid fa-link"></i></button>
                <button v-if="uploadUrl" type="button" class="chat-tool" title="Add an image (or paste / drop it)" :disabled="preview || disabled" @click="fileInput.click()">
                    <i :class="uploading ? 'fa-solid fa-circle-notch fa-spin' : 'fa-regular fa-image'"></i></button>
                <input v-if="uploadUrl" ref="fileInput" type="file" accept="image/png,image/jpeg,image/gif,image/webp" multiple hidden
                       @change="uploadImages($event.target.files); $event.target.value = ''">
                <span class="chat-tool-sep"></span>
                <button type="button" class="chat-tool" title="Mention someone (@)" @click="trigger('@')" :disabled="preview"><i class="fa-solid fa-at"></i></button>
                <button type="button" class="chat-tool" title="Link a rule, bundle, CVE… (#)" @click="trigger('#')" :disabled="preview"><i class="fa-solid fa-hashtag"></i></button>
                <span class="chat-attach">
                    <button type="button" class="chat-tool chat-tool--attach" :class="{ 'is-on': attachOpen }" title="Attach a rule, bundle, blog post…" :disabled="preview || disabled"
                            @click="openAttach" aria-haspopup="menu" :aria-expanded="attachOpen"><i class="fa-solid fa-paperclip"></i><span>Attach</span></button>
                    <span v-if="attachOpen" class="chat-attach__menu" ref="attachMenu" role="menu" @keydown="onAttachKey" @mouseleave="attachOpen = false">
                        <button v-for="a in ATTACH" :key="a.kind" type="button" role="menuitem" @click="attach(a.kind)"><i :class="REF_ICONS[a.kind]"></i>[[ a.label ]]</button>
                    </span>
                </span>
                <button v-for="a in ATTACH.slice(0, 3)" :key="'q' + a.kind" type="button" class="chat-tool chat-tool--quick" :title="'Attach a ' + a.label.toLowerCase()"
                        :disabled="preview || disabled" @click="attach(a.kind)"><i :class="REF_ICONS[a.kind]"></i></button>
                <button type="button" class="chat-tool" :class="{ 'is-on': preview }" title="Preview" @click="preview = !preview"><i class="fa-solid fa-eye"></i></button>
                <span class="chat-composer__hint">
                    <span v-if="tooLong" class="text-danger">[[ text.length ]] / [[ maxLength ]]</span>
                    <template v-else><b>Enter</b> send · <b>Shift+Enter</b> new line · Markdown</template>
                </span>
                <button type="button" class="chat-send" :disabled="!canSend" @click="send" :title="editing ? 'Save' : 'Send'">
                    <i :class="sending ? 'fa-solid fa-circle-notch fa-spin' : (editing ? 'fa-solid fa-check' : 'fa-solid fa-paper-plane')"></i>
                </button>
            </div>
        </div>
    </div>`,
}
