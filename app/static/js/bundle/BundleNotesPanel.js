/**
 * BundleNotesPanel.js — "Notes" tab: community notes / known issues on a
 * bundle ("⚠ this bundle doesn't work if…"), written in Markdown.
 *
 * Who can do what is decided server-side (/bundle/<id>/notes): anyone who
 * can view the bundle reads; logged-in users write while the bundle is
 * public; authors edit/delete their own notes; owner/admin resolve.
 *
 * Props:  bundleId, csrfToken, isAuthenticated,
 *         refs  [{ kind: 'rule', id, label } | { kind: 'file', path, label }] — what "#" can reference
 * Emits:  loaded({ open, notes }), open-ref({ kind, ref })
 *
 * Tokens (inserted by the pickers, rendered as chips):
 *   @[Name](12)                 a user — notified if they can see the bundle
 *   #[Rule title](rule:345)     a rule of the bundle
 *   #[docs/README.md](file:…)   a file of the bundle (path, URI-encoded)
 */

import { create_message } from '/static/js/toaster.js'
import { renderSafeMarkdown } from '/static/js/bundle/bundleFileTypes.js'
import PaginationComponent from '/static/js/rule/paginationComponent.js'

const { ref, reactive, computed, nextTick, watch } = Vue

const esc = (t) => String(t ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

// Tokens → chips, before markdown rendering (the result still goes through
// the sanitiser; everything user-typed is escaped here).
function preprocessNote(text) {
    return String(text || '')
        .replace(/@\[([^\]]+)\]\((\d+)\)/g, (m, name, id) =>
            `<span class="bn-mention" data-user="${id}" role="button" tabindex="0">@${esc(name)}</span>`)
        .replace(/#\[([^\]]+)\]\((rule|file):([^)\s]+)\)/g, (m, label, kind, ref) =>
            `<span class="bn-ref bn-ref--${kind}" data-ref-kind="${kind}" data-ref="${esc(ref)}" role="button" tabindex="0">` +
            `<i class="fa-solid ${kind === 'rule' ? 'fa-shield-halved' : 'fa-file-lines'}"></i>${esc(label)}</span>`)
}
const renderNote = (text) => renderSafeMarkdown(preprocessNote(text))

const SEVERITY = {
    critical: { label: 'Critical', icon: 'fa-solid fa-circle-exclamation' },
    warning:  { label: 'Warning',  icon: 'fa-solid fa-triangle-exclamation' },
    info:     { label: 'Info',     icon: 'fa-solid fa-circle-info' },
}

export default {
    name: 'BundleNotesPanel',

    props: {
        bundleId:        { type: [Number, String], required: true },
        csrfToken:       { type: String, default: '' },
        isAuthenticated: { type: Boolean, default: false },
        refs:            { type: Array, default: () => [] },
    },

    emits: ['loaded', 'open-ref'],
    components: { PaginationComponent },

    template: `
    <div class="bn-root">
        <!-- Write -->
        <div v-if="canCreate && !form.open" class="bn-new">
            <button type="button" class="bd-btn bd-btn--primary" @click="openForm()">
                <i class="fa-solid fa-plus"></i><span>Add a note</span>
            </button>
            <span class="bn-hint">Known issue, deployment caveat, false positive… visible to everyone who can see the bundle.</span>
        </div>
        <div v-else-if="!canCreate && loaded && !loadError" class="bn-blocked">
            <i class="fa-solid fa-lock"></i>
            <span v-if="!isAuthenticated">Log in to add a note.</span>
            <span v-else>{{ blockedReason || 'You cannot add notes to this bundle.' }}</span>
        </div>

        <div v-if="form.open" class="bn-form">
            <div class="br-form-row">
                <label class="br-field br-field--grow">
                    <span>Title</span>
                    <input type="text" v-model="form.title" maxlength="200" placeholder="e.g. Suricata rules need the HTTP app-layer enabled">
                </label>
                <label class="br-field">
                    <span>Severity</span>
                    <select v-model="form.severity" class="bn-select">
                        <option value="info">Info</option>
                        <option value="warning">Warning</option>
                        <option value="critical">Critical</option>
                    </select>
                </label>
            </div>
            <div class="br-field">
                <span>Tags <em>(false positives, detection verdicts, priority, confidence… — curated taxonomies only)</em></span>
                <div class="bn-tags-field">
                    <span v-for="t in form.tags" :key="t.id" class="bn-tag" :title="t.description || t.name">
                        {{ shortTag(t.name) }}
                        <button type="button" @click="removeTag(t)" aria-label="Remove tag"><i class="fa-solid fa-xmark"></i></button>
                    </span>
                    <input type="text" v-model="tagQuery" class="bn-tag-input" placeholder="Search a tag…"
                           @input="searchTags" @focus="searchTags" @blur="closeTagsSoon" @keydown.enter.prevent="addFirstTag"
                           :disabled="form.tags.length >= 8">
                    <ul v-if="tagOpen && tagResults.length" class="bn-picker bn-tag-picker">
                        <li v-for="t in tagResults" :key="t.id" class="bn-picker-item" @mousedown.prevent="addTag(t)" :title="t.description || ''">
                            <i class="fa-solid fa-tag"></i><span>{{ t.name }}</span>
                        </li>
                    </ul>
                </div>
                <div class="bn-quick-tags">
                    <button v-for="t in quickTags" :key="t.id" type="button" class="bn-quick-tag"
                            :class="{ active: form.tags.some(x => x.id === t.id) }" @click="toggleTag(t)" :title="t.description || t.name">
                        <i class="fa-solid fa-bug-slash"></i>{{ shortTag(t.name) }}
                    </button>
                </div>
            </div>
            <div class="br-field">
                <span>Note <em>(Markdown — type <b>@</b> to mention someone, <b>#</b> to reference a rule or file of the bundle)</em></span>
                <div class="bn-composer">
                    <div class="bn-composer-tabs">
                        <button type="button" :class="{ active: !preview }" @click="preview = false"><i class="fa-solid fa-pen"></i>Write</button>
                        <button type="button" :class="{ active: preview }" @click="showPreview"><i class="fa-solid fa-eye"></i>Preview</button>
                    </div>
                    <div v-show="!preview" class="bn-composer-body">
                        <textarea ref="ta" v-model="form.content" class="bn-textarea" rows="7"
                            placeholder="Explain what doesn't work, in which setup, and any workaround."
                            @input="onInput" @keydown="onKeydown" @click="onInput" @blur="closePickerSoon"></textarea>
                        <ul v-if="picker.mode" class="bn-picker" role="listbox">
                            <li v-if="picker.loading" class="bn-picker-empty"><i class="fas fa-spinner fa-spin me-1"></i>Searching…</li>
                            <li v-else-if="!picker.items.length" class="bn-picker-empty">
                                {{ picker.mode === 'user' ? 'No user found' : 'No rule or file matches' }}
                            </li>
                            <li v-for="(it, i) in picker.items" :key="i" class="bn-picker-item"
                                :class="{ active: i === picker.index }" @mousedown.prevent="choose(it)" role="option">
                                <i :class="it.icon"></i><span>{{ it.label }}</span><small v-if="it.sub">{{ it.sub }}</small>
                            </li>
                        </ul>
                    </div>
                    <div v-show="preview" class="bfv-md bn-body bn-preview" v-html="previewHtml" @click="onBodyClick"></div>
                </div>
            </div>
            <div class="br-form-actions">
                <button type="button" class="bd-btn bd-btn--ghost" @click="form.open = false">Cancel</button>
                <button type="button" class="bd-btn bd-btn--primary" @click="save" :disabled="busy">
                    <i :class="busy ? 'fas fa-spinner fa-spin' : 'fa-solid fa-paper-plane'"></i>
                    <span>{{ form.id ? 'Save changes' : 'Publish note' }}</span>
                </button>
            </div>
        </div>

        <!-- List -->
        <div v-if="loading && !loaded" class="bh-loading"><i class="fas fa-spinner fa-spin me-2"></i>Loading notes…</div>
        <div v-else-if="loadError && !notes.length" class="bn-blocked">
            <i class="fa-regular fa-note-sticky"></i><span>Notes are not available right now.</span>
        </div>
        <div v-else-if="!notes.length && !form.open" class="br-empty">
            <i class="fa-regular fa-note-sticky"></i>
            <div><strong>No notes yet.</strong><span>Nobody reported a known issue on this bundle.</span></div>
        </div>

        <!-- Search + status filter (built for bundles with many notes) -->
        <div v-if="notes.length" class="bn-toolbar">
            <div class="bfp-search">
                <i class="fa-solid fa-magnifying-glass"></i>
                <input type="text" v-model="query" placeholder="Search notes — title, text, author, tag…">
                <button v-if="query" type="button" class="bfp-search-clear" @click="query = ''"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="bfp-chips mb-0">
                <button v-for="f in statusFilters" :key="f.key" type="button" class="bfp-chip"
                        :class="{ active: statusFilter === f.key }" @click="statusFilter = f.key">
                    {{ f.label }} <span class="bfp-chip-count">{{ f.count }}</span>
                </button>
            </div>
        </div>
        <div v-if="tagFilter" class="bd-focus-bar">
            <i class="fa-solid fa-filter"></i>
            <span>Notes tagged <strong>{{ tagFilter }}</strong></span>
            <button type="button" class="bd-btn bd-btn--ghost ms-auto" @click="tagFilter = ''"><i class="fa-solid fa-xmark"></i><span>Show all</span></button>
        </div>
        <div class="bn-list">
            <div v-if="notes.length && !shownNotes.length" class="bfp-empty">
                <i class="fa-regular fa-note-sticky"></i> No note matches.
            </div>
            <article v-for="n in pageNotes" :key="n.id" class="bn-note" :class="['bn-note--' + n.severity, { 'bn-note--resolved': n.status === 'resolved' }]">
                <header class="bn-head">
                    <i :class="SEVERITY[n.severity].icon + ' bn-sev-icon'"></i>
                    <div class="bn-head-main">
                        <div class="bn-title">{{ n.title }}</div>
                        <div class="bn-meta">
                            <span class="bn-sev">{{ SEVERITY[n.severity].label }}</span>
                            <span v-if="n.status === 'resolved'" class="bn-resolved"><i class="fa-solid fa-check"></i>Resolved<template v-if="n.resolved_by"> by {{ n.resolved_by }}</template></span>
                            <span>{{ n.user_name || 'Deleted user' }} · {{ fmt(n.created_at) }}<template v-if="n.updated_at !== n.created_at"> · edited</template></span>
                        </div>
                    </div>
                    <div class="bn-actions">
                        <button v-if="n.can_resolve" type="button" class="bfv-btn" :title="n.status === 'open' ? 'Mark as resolved' : 'Reopen'" @click="setStatus(n)">
                            <i :class="n.status === 'open' ? 'fa-solid fa-check' : 'fa-solid fa-rotate-left'"></i>
                        </button>
                        <button v-if="n.can_edit" type="button" class="bfv-btn" title="Edit" @click="openForm(n)"><i class="fa-solid fa-pen"></i></button>
                        <button v-if="n.can_delete" type="button" class="bfv-btn bfv-btn--close" :class="{ 'bn-armed': armed === n.id }"
                                :title="armed === n.id ? 'Click again to delete' : 'Delete'" @click="remove(n)"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </header>
                <div v-if="n.tags && n.tags.length" class="bn-note-tags">
                    <button v-for="t in n.tags" :key="t.id" type="button" class="bn-tag bn-tag--view"
                            :class="{ active: tagFilter === t.name }" :title="(t.description || t.name) + ' — click to filter'"
                            @click="tagFilter = tagFilter === t.name ? '' : t.name">{{ shortTag(t.name) }}</button>
                </div>
                <div class="bfv-md bn-body" v-html="html[n.id] || ''" @click="onBodyClick" @keydown.enter="onBodyClick"></div>
            </article>
        </div>
        <div v-if="totalPages > 1" class="bfp-footer">
            <pagination-component :current-page="page" :total-pages="totalPages" @change-page="p => page = p"></pagination-component>
            <span class="bfp-range">{{ (page - 1) * PER_PAGE + 1 }}–{{ Math.min(page * PER_PAGE, shownNotes.length) }} of {{ shownNotes.length }}</span>
        </div>
    </div>
    `,

    setup(props, { emit }) {
        const notes = ref([])
        const html = reactive({})
        const loading = ref(false)
        const loaded = ref(false)
        const busy = ref(false)
        const canCreate = ref(false)
        const blockedReason = ref('')
        const armed = ref(null)
        const loadError = ref('')
        // ── tags (curated taxonomies, see NOTE_TAG_PREFIXES server-side) ──
        const tagQuery = ref('')
        const tagResults = ref([])
        const tagOpen = ref(false)
        const quickTags = ref([])
        const tagFilter = ref('')
        let tagT = null, tagBlurT = null
        const shortTag = (n) => String(n).replace(/^([a-z-]+):/i, '$1 ').replace(/"/g, '').replace(/=/, ': ')
        // ── search / status filter / pagination ──
        const PER_PAGE = 10
        const query = ref('')
        const statusFilter = ref('all')
        const page = ref(1)
        const statusFilters = computed(() => [
            { key: 'all',      label: 'All',      count: notes.value.length },
            { key: 'open',     label: 'Open',     count: notes.value.filter(n => n.status === 'open').length },
            { key: 'resolved', label: 'Resolved', count: notes.value.filter(n => n.status === 'resolved').length },
        ])
        const shownNotes = computed(() => {
            const q = query.value.trim().toLowerCase()
            return notes.value.filter(n =>
                (statusFilter.value === 'all' || n.status === statusFilter.value) &&
                (!tagFilter.value || (n.tags || []).some(t => t.name === tagFilter.value)) &&
                (!q || [n.title, n.content, n.user_name, n.severity, ...(n.tags || []).map(t => t.name)]
                        .some(v => String(v || '').toLowerCase().includes(q))))
        })
        const totalPages = computed(() => Math.max(1, Math.ceil(shownNotes.value.length / PER_PAGE)))
        const pageNotes = computed(() => shownNotes.value.slice((page.value - 1) * PER_PAGE, page.value * PER_PAGE))
        watch([query, statusFilter, tagFilter], () => { page.value = 1 })
        watch(totalPages, (t) => { if (page.value > t) page.value = t })
        async function fetchTags(q) {
            const d = await fetch('/bundle/note_tags?' + new URLSearchParams({ q })).then(r => r.json()).catch(() => ({ tags: [] }))
            return d.tags || []
        }
        function searchTags() {
            clearTimeout(tagT)
            tagOpen.value = true
            tagT = setTimeout(async () => {
                const picked = new Set(form.tags.map(t => t.id))
                tagResults.value = (await fetchTags(tagQuery.value.trim())).filter(t => !picked.has(t.id)).slice(0, 12)
            }, 180)
        }
        function closeTagsSoon() { clearTimeout(tagBlurT); tagBlurT = setTimeout(() => { tagOpen.value = false }, 150) }
        function addTag(t) {
            if (form.tags.length >= 8 || form.tags.some(x => x.id === t.id)) return
            form.tags.push(t); tagQuery.value = ''; tagResults.value = tagResults.value.filter(x => x.id !== t.id)
        }
        function addFirstTag() { if (tagResults.value[0]) addTag(tagResults.value[0]) }
        function removeTag(t) { form.tags = form.tags.filter(x => x.id !== t.id) }
        function toggleTag(t) { form.tags.some(x => x.id === t.id) ? removeTag(t) : addTag(t) }
        const form = reactive({ open: false, id: null, title: '', content: '', severity: 'warning', key: 0, tags: [] })
        let armT = null

        const fmt = (iso) => window.dayjs ? dayjs(iso).format('MMM D, YYYY HH:mm') : iso
        const json = async (res) => {
            const d = await res.json().catch(() => null)
            if (!res.ok || !d || d.success === false) throw new Error((d && d.message) || `HTTP ${res.status}`)
            return d
        }
        const H = () => ({ 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken })

        async function load() {
            loading.value = true
            try {
                const d = await json(await fetch(`/bundle/${props.bundleId}/notes`))
                loadError.value = ''
                notes.value = d.notes
                canCreate.value = d.can_create
                blockedReason.value = d.create_blocked_reason || ''
                for (const n of d.notes) html[n.id] = await renderNote(n.content)
                loaded.value = true
                emit('loaded', { open: d.open, notes: d.notes })
            } catch (e) {
                // No toast for the list itself — an empty / unavailable list is
                // not an error the user can act on; show it inline instead.
                loadError.value = String(e.message || e)
                loaded.value = true
            } finally {
                loading.value = false
            }
        }

        // ── Write / Preview + @ / # pickers ───────────────────────────
        const ta = ref(null)
        const preview = ref(false)
        const previewHtml = ref('')
        const picker = reactive({ mode: null, items: [], index: 0, loading: false, start: 0 })
        let searchT = null, reqId = 0, blurT = null

        async function showPreview() {
            previewHtml.value = form.content ? await renderNote(form.content) : '<p><em>Nothing to preview.</em></p>'
            preview.value = true
        }
        function closePicker() { picker.mode = null; picker.items = []; picker.index = 0; picker.loading = false }
        function closePickerSoon() { clearTimeout(blurT); blurT = setTimeout(closePicker, 150) }

        function onInput() {
            const el = ta.value
            if (!el) return
            const before = form.content.slice(0, el.selectionStart)
            const u = before.match(/(^|\s)@([\w.\-]{0,30})$/)
            const h = before.match(/(^|\s)#([^\s#@\[\]()]{0,40})$/)
            if (u) {
                picker.start = el.selectionStart - u[2].length - 1
                const q = u[2]
                picker.mode = 'user'
                picker.index = 0
                if (q.length < 2) { picker.items = []; picker.loading = false; return }
                picker.loading = true
                clearTimeout(searchT)
                const my = ++reqId
                searchT = setTimeout(async () => {
                    try {
                        const d = await fetch('/account/search_mentionable_users?q=' + encodeURIComponent(q)).then(r => r.json())
                        if (my !== reqId) return
                        picker.items = (d.users || []).map(x => ({ kind: 'user', id: x.id, label: x.username || x.first_name || 'User',
                                                                   sub: x.first_name && x.username ? x.first_name : '', icon: 'fa-solid fa-at' }))
                    } catch { if (my === reqId) picker.items = [] }
                    finally { if (my === reqId) picker.loading = false }
                }, 200)
            } else if (h) {
                picker.start = el.selectionStart - h[2].length - 1
                const q = h[2].toLowerCase()
                picker.mode = 'ref'
                picker.index = 0
                picker.loading = false
                picker.items = props.refs
                    .filter(r => !q || r.label.toLowerCase().includes(q) || String(r.id || '').startsWith(q))
                    .slice(0, 12)
                    .map(r => ({ ...r, icon: r.kind === 'rule' ? 'fa-solid fa-shield-halved' : 'fa-solid fa-file-lines',
                                 sub: r.kind === 'rule' ? '#' + r.id : 'file' }))
            } else {
                closePicker()
            }
        }

        function choose(it) {
            clearTimeout(blurT)
            const el = ta.value
            const end = el ? el.selectionStart : picker.start
            const clean = (t) => String(t).replace(/[\[\]()]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 80)
            const token = it.kind === 'user' ? `@[${clean(it.label)}](${it.id}) `
                        : it.kind === 'rule' ? `#[${clean(it.label)}](rule:${it.id}) `
                        : `#[${clean(it.label)}](file:${encodeURIComponent(it.path)}) `
            form.content = form.content.slice(0, picker.start) + token + form.content.slice(end)
            closePicker()
            nextTick(() => { if (el) { el.focus(); const p = picker.start + token.length; el.setSelectionRange(p, p) } })
        }

        function onKeydown(e) {
            if (!picker.mode || !picker.items.length) { if (e.key === 'Escape') closePicker(); return }
            if (e.key === 'ArrowDown') { e.preventDefault(); picker.index = (picker.index + 1) % picker.items.length }
            else if (e.key === 'ArrowUp') { e.preventDefault(); picker.index = (picker.index - 1 + picker.items.length) % picker.items.length }
            else if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); choose(picker.items[picker.index]) }
            else if (e.key === 'Escape') closePicker()
        }

        // Chips in rendered notes
        function onBodyClick(e) {
            const refEl = e.target.closest('[data-ref-kind]')
            if (refEl) {
                const kind = refEl.dataset.refKind
                let refVal = refEl.dataset.ref
                if (kind === 'file') { try { refVal = decodeURIComponent(refVal) } catch {} }
                emit('open-ref', { kind, ref: refVal })
                return
            }
            const userEl = e.target.closest('[data-user]')
            if (userEl) window.location.href = '/account/detail_user/' + encodeURIComponent(userEl.dataset.user)
        }

        function openForm(n = null) {
            Object.assign(form, n
                ? { open: true, id: n.id, title: n.title, content: n.content, severity: n.severity, tags: [...(n.tags || [])] }
                : { open: true, id: null, title: '', content: '', severity: 'warning', tags: [] })
            // One-click picks: false positives first, then the detection verdicts
            if (!quickTags.value.length)
                Promise.all([fetchTags('false-positive:'), fetchTags('use-case-applicability:')]).then(([fp, uc]) => {
                    const verdicts = uc.filter(t => /rule-pattern|rule-configuration|test-alert/.test(t.name))
                    quickTags.value = [...fp.slice(0, 6), ...verdicts.slice(0, 3)]
                })
            form.key++
            preview.value = false
            closePicker()
        }

        async function save() {
            busy.value = true
            try {
                const url = form.id ? `/bundle/${props.bundleId}/notes/${form.id}` : `/bundle/${props.bundleId}/notes`
                const d = await json(await fetch(url, {
                    method: form.id ? 'PUT' : 'POST', headers: H(),
                    body: JSON.stringify({ title: form.title, content: form.content, severity: form.severity,
                                           tag_ids: form.tags.map(t => t.id) }),
                }))
                create_message(d.message, d.not_notified && d.not_notified.length ? 'warning-subtle' : 'success-subtle')
                form.open = false
                await load()
            } catch (e) {
                create_message(e.message, 'danger-subtle')
            } finally {
                busy.value = false
            }
        }

        async function setStatus(n) {
            try {
                const d = await json(await fetch(`/bundle/${props.bundleId}/notes/${n.id}/status`, {
                    method: 'POST', headers: H(), body: JSON.stringify({ status: n.status === 'open' ? 'resolved' : 'open' }),
                }))
                create_message(d.message, 'success-subtle')
                await load()
            } catch (e) { create_message(e.message, 'danger-subtle') }
        }

        async function remove(n) {
            if (armed.value !== n.id) {
                armed.value = n.id
                clearTimeout(armT)
                armT = setTimeout(() => { armed.value = null }, 3500)
                return
            }
            armed.value = null
            try {
                const d = await json(await fetch(`/bundle/${props.bundleId}/notes/${n.id}`, { method: 'DELETE', headers: H() }))
                create_message(d.message, 'success-subtle')
                await load()
            } catch (e) { create_message(e.message, 'danger-subtle') }
        }

        load()
        return { query, statusFilter, statusFilters, page, totalPages, pageNotes, PER_PAGE,
                 tagQuery, tagResults, tagOpen, quickTags, tagFilter, shownNotes, shortTag,
                 searchTags, closeTagsSoon, addTag, addFirstTag, removeTag, toggleTag,
                 ta, preview, previewHtml, picker, showPreview, closePickerSoon, onInput, onKeydown, choose, onBodyClick,
                 notes, html, loading, loaded, loadError, busy, canCreate, blockedReason, armed, form, fmt, openForm, save, setStatus, remove, SEVERITY }
    },
}
