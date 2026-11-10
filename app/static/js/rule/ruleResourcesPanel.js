/**
 * ruleResourcesPanel.js — the rule's Resources tab (issue #77): Markdown notes and external links
 * attached by the rule's owner or an admin. CSS: css/rule/base/detail_rule_resources.css (rr-*).
 *
 *   <rule-resources-panel :rule-id="1" :can-manage="true" csrf-token="…" />
 *
 * Files: text files from the user's computer, only the types of the setting rule.resources
 * (file_extensions, sizes) — shown in the code viewer, downloaded as plain text.
 * Links: the server reads the page once (safe_fetch.py) to show its title / description / site.
 *
 * Everything shown here is user content: notes go through renderMarkdown + hardenUserHtml
 * (sanitize.js: no images, no same-site links, external links in a new tab, noopener/noreferrer/
 * nofollow), and every external link opens only after a "You are leaving Rulezet" confirmation
 * that shows the real address.
 */
import { renderMarkdown, hardenUserHtml } from '/static/js/sanitize.js'
import { create_message } from '/static/js/toaster.js'
import SmartEditor from '/static/js/components/smart-editor.js'
import UserChip from '/static/js/components/UserChip.js'
import BundleFileViewer from '/static/js/bundle/BundleFileViewer.js'

const { ref, reactive, computed, onMounted, nextTick } = Vue

const EMPTY = { id: null, kind: 'note', title: '', url: '', content: '' }

const extOf = n => (String(n || '').includes('.') ? String(n).split('.').pop().toLowerCase() : '')
const FILE_ICONS = { pdf: 'fa-solid fa-file-pdf', markdown: 'fa-brands fa-markdown', txt: 'fa-solid fa-file-lines', md: 'fa-brands fa-markdown', json: 'fa-solid fa-file-code', yaml: 'fa-solid fa-file-code', yml: 'fa-solid fa-file-code',
                     csv: 'fa-solid fa-file-csv', tsv: 'fa-solid fa-file-csv', py: 'fa-brands fa-python', sh: 'fa-solid fa-terminal',
                     ps1: 'fa-solid fa-terminal', log: 'fa-solid fa-file-waveform', xml: 'fa-solid fa-file-code' }

function fmtSize(b) {
    if (b == null) return ''
    if (b < 1024) return b + ' B'
    if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB'
    return (b / 1024 / 1024).toFixed(1) + ' MB'
}

function hostOf(url) {
    try { return new URL(url).host } catch { return '' }
}

export default {
    name: 'RuleResourcesPanel',
    delimiters: ['[[', ']]'],
    components: { 'smart-editor': SmartEditor, 'user-chip': UserChip, 'file-viewer': BundleFileViewer },
    props: {
        ruleId:    { type: Number, required: true },
        canManage: { type: Boolean, default: false },
        csrfToken: { type: String, default: '' },
    },
    emits: ['count'],
    setup(props, { emit }) {
        const loading   = ref(true)
        const items     = ref([])
        const rendered  = reactive({})           // id -> sanitized HTML
        const filter    = ref('all')
        const editing   = ref(false)
        const saving    = ref(false)
        const form      = reactive({ ...EMPTY })
        const confirmDelete = ref(null)
        const leaving   = ref(null)              // the link the user is about to open
        let leaveModal  = null
        const cfg       = ref({ file_extensions: [], max_file_bytes: 0, max_total_bytes: 0, link_preview: false })
        const fileInput = ref(null)
        const uploading = ref(null)              // { done, total }
        const dragOver  = ref(false)
        const viewer    = ref(null)              // the file open in the viewer: { id, name, content, loading, isRule: false }
        const downloadAsk = ref(null)            // the file the user is about to download
        let downloadModal = null
        const refreshing = ref(null)
        const accept    = computed(() => cfg.value.file_extensions.map(e => '.' + e).join(','))
        const files     = computed(() => items.value.filter(r => r.kind === 'file'))
        const filesTotal = computed(() => files.value.reduce((n, f) => n + (f.size || 0), 0))

        const notes = computed(() => items.value.filter(r => r.kind === 'note'))
        const links = computed(() => items.value.filter(r => r.kind === 'link'))
        const shown = computed(() => filter.value === 'all' ? items.value : items.value.filter(r => r.kind === filter.value))

        async function render(r) {
            if (!r.content) { rendered[r.id] = ''; return }
            try { rendered[r.id] = hardenUserHtml(await renderMarkdown(r.content)) }
            catch { rendered[r.id] = '<p><em>Could not render this note.</em></p>' }
        }

        async function load() {
            loading.value = true
            try {
                const res = await fetch(`/rule/${props.ruleId}/resources`)
                const data = await res.json()
                items.value = data.resources || []
                if (data.config) cfg.value = data.config
                await Promise.all(items.value.map(render))
                emit('count', items.value.length)
            } catch {
                create_message('Could not load the resources.', 'danger-subtle')
            } finally {
                loading.value = false
            }
        }

        function startNew(kind) {
            Object.assign(form, EMPTY, { kind })
            editing.value = true
            nextTick(() => document.getElementById('rr-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
        }

        function startEdit(r) {
            Object.assign(form, { id: r.id, kind: r.kind, title: r.title, url: r.url || '', content: r.content || '' })
            editing.value = true
            nextTick(() => document.getElementById('rr-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
        }

        function cancel() { editing.value = false; Object.assign(form, EMPTY) }

        // 'circl.lu' is a link too: an address without a scheme gets https:// (as the server does)
        function normalizeUrl(u) {
            u = (u || '').trim()
            if (u && !/^[a-z][a-z0-9+-]*:/i.test(u)) u = 'https://' + u.replace(/^\/+/, '')
            return u
        }
        const urlOk = computed(() => {
            const u = normalizeUrl(form.url)
            if (!/^https?:\/\//i.test(u) || /\s/.test(u)) return false
            try { const h = new URL(u).hostname; return h.includes('.') || h === 'localhost' } catch { return false }
        })
        function onUrlBlur() { if (urlOk.value) form.url = normalizeUrl(form.url) }
        const urlPreview = computed(() => (form.url && urlOk.value && normalizeUrl(form.url) !== form.url.trim() ? normalizeUrl(form.url) : ''))
        // a link's title is optional: the server takes the page's title, or its site
        const canSave = computed(() => form.kind === 'link' ? urlOk.value : (form.title.trim() && form.content.trim()))

        async function save() {
            if (!canSave.value || saving.value) return
            saving.value = true
            try {
                const res = await fetch(form.id ? `/rule/${props.ruleId}/resources/${form.id}` : `/rule/${props.ruleId}/resources`, {
                    method: form.id ? 'PUT' : 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ kind: form.kind, title: form.title, url: normalizeUrl(form.url), content: form.content }),
                })
                const data = await res.json().catch(() => ({}))
                create_message(data.message || (data.success ? 'Saved.' : 'Request failed.'), data.toast_class || (data.success ? 'success-subtle' : 'danger-subtle'))
                if (data.success) { cancel(); await load() }
            } finally {
                saving.value = false
            }
        }

        async function remove(r) {
            if (confirmDelete.value !== r.id) { confirmDelete.value = r.id; return }
            confirmDelete.value = null
            const res = await fetch(`/rule/${props.ruleId}/resources/${r.id}`, {
                method: 'DELETE', headers: { 'X-CSRFToken': props.csrfToken },
            })
            const data = await res.json().catch(() => ({}))
            create_message(data.message || 'Request failed.', data.toast_class || 'danger-subtle')
            if (data.success) await load()
        }

        // every external link (link cards and links inside notes) goes through this confirmation
        function askLeave(url) {
            leaving.value = { url, host: hostOf(url) }
            leaveModal = leaveModal || bootstrap.Modal.getOrCreateInstance(document.getElementById('rr-leave-modal'))
            leaveModal.show()
        }
        function onNoteClick(e) {
            const a = e.target.closest('a[href]')
            if (!a) return
            e.preventDefault()
            askLeave(a.getAttribute('href'))
        }
        function goLeave() {
            if (leaving.value) window.open(leaving.value.url, '_blank', 'noopener,noreferrer')
            leaveModal?.hide()
        }

        // ── files ─────────────────────────────────────────────────────────────
        function pickFiles() { fileInput.value?.click() }

        function readFile(file, asDataUrl) {
            return new Promise((resolve, reject) => {
                const r = new FileReader()
                r.onload = () => resolve(r.result)
                r.onerror = () => reject(r.error)
                if (asDataUrl) r.readAsDataURL(file); else r.readAsText(file)
            })
        }
        const isPdfName = n => extOf(n) === 'pdf'

        async function uploadFiles(list) {
            const chosen = [...(list || [])]
            if (!chosen.length) return
            const allowed = new Set(cfg.value.file_extensions)
            const ok = []
            for (const f of chosen) {
                if (!allowed.has(extOf(f.name))) { create_message(`'${f.name}': this type of file can't be added.`, 'warning-subtle'); continue }
                const max = isPdfName(f.name) ? cfg.value.max_pdf_bytes : cfg.value.max_file_bytes
                if (f.size > max) { create_message(`'${f.name}' is too large (max ${fmtSize(max)}).`, 'warning-subtle'); continue }
                ok.push(f)
            }
            if (!ok.length) return
            uploading.value = { done: 0, total: ok.length }
            let added = 0
            for (const f of ok) {
                try {
                    const pdf = isPdfName(f.name)
                    const read = await readFile(f, pdf)
                    const payload = pdf ? { kind: 'file', filename: f.name, content_b64: read }
                                        : { kind: 'file', filename: f.name, content: read }
                    const res = await fetch(`/rule/${props.ruleId}/resources`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                        body: JSON.stringify(payload),
                    })
                    const data = await res.json().catch(() => ({}))
                    if (data.success) added++
                    else create_message(data.message || `'${f.name}' could not be added.`, 'danger-subtle')
                } catch {
                    create_message(`'${f.name}' could not be read.`, 'danger-subtle')
                }
                uploading.value.done++
            }
            uploading.value = null
            if (fileInput.value) fileInput.value.value = ''
            if (added) create_message(`${added} file${added > 1 ? 's' : ''} added.`, 'success-subtle')
            await load()
        }

        function onDrop(e) {
            dragOver.value = false
            if (props.canManage) uploadFiles(e.dataTransfer?.files)
        }

        // View: the bundle file viewer (full-screen, its own "not reviewed by Rulezet" warning)
        async function openFile(r) {
            if (r.is_pdf) { askDownload(r, 'view'); return }     // PDF: the browser's own viewer, new tab, after the warning
            viewer.value = { id: r.id, name: r.filename, content: '', loading: true, isRule: false }
            try {
                const res = await fetch(`/rule/${props.ruleId}/resources/${r.id}/text`)
                const data = await res.json()
                if (viewer.value?.id === r.id) viewer.value = { ...viewer.value, content: data.content || '', loading: false }
            } catch {
                if (viewer.value?.id === r.id) viewer.value = { ...viewer.value, content: 'Could not load this file.', loading: false }
            }
        }
        const textFiles = computed(() => files.value.filter(f => !f.is_pdf))
        const viewerIndex = computed(() => (viewer.value ? textFiles.value.findIndex(f => f.id === viewer.value.id) : -1))
        function viewerStep(d) {
            const f = textFiles.value[viewerIndex.value + d]
            if (f) openFile(f)
        }

        // Download: always confirmed first — Rulezet doesn't check what is inside a file
        function askDownload(r, mode = 'download') {
            downloadAsk.value = { ...r, mode }
            downloadModal = downloadModal || bootstrap.Modal.getOrCreateInstance(document.getElementById('rr-download-modal'))
            downloadModal.show()
        }
        function onViewerDownload(file) {
            const r = files.value.find(f => f.id === file.id)
            viewer.value = null                 // the viewer sits above Bootstrap modals: close it first
            if (r) nextTick(() => askDownload(r))
        }
        function goDownload() {
            const r = downloadAsk.value
            if (r && r.mode === 'view') window.open(`/rule/${props.ruleId}/resources/${r.id}/pdf`, '_blank', 'noopener,noreferrer')
            else if (r) window.location.href = downloadUrl(r)
            downloadModal?.hide()
        }

        const fileIcon = r => FILE_ICONS[extOf(r.filename)] || 'fa-solid fa-file-lines'
        const downloadUrl = r => `/rule/${props.ruleId}/resources/${r.id}/download`

        async function refreshPreview(r) {
            refreshing.value = r.id
            try {
                const res = await fetch(`/rule/${props.ruleId}/resources/${r.id}/refresh_preview`, {
                    method: 'POST', headers: { 'X-CSRFToken': props.csrfToken },
                })
                const data = await res.json().catch(() => ({}))
                create_message(data.message || 'Request failed.', data.toast_class || 'danger-subtle')
                if (data.resource) Object.assign(r, data.resource)
            } finally {
                refreshing.value = null
            }
        }

        const fmtDate = s => (s ? new Date(s).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '')

        onMounted(load)

        return {
            loading, items, rendered, filter, notes, links, shown, editing, saving, form, urlOk, urlPreview, normalizeUrl, onUrlBlur, canSave,
            confirmDelete, leaving, hostOf, fmtDate, fmtSize,
            cfg, fileInput, uploading, dragOver, viewer, viewerIndex, textFiles, downloadAsk, refreshing, accept, files, filesTotal,
            pickFiles, uploadFiles, onDrop, openFile, viewerStep, askDownload, onViewerDownload, goDownload,
            fileIcon, downloadUrl, refreshPreview,
            startNew, startEdit, cancel, save, remove, askLeave, onNoteClick, goLeave,
        }
    },
    template: `
<div>
    <!-- Warning: user content -->
    <div class="rr-warning mb-3" role="note">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <div>
            <strong>Not checked by Rulezet.</strong>
            These notes, links and files are added by the rule's owner or an administrator. Links can lead to
            malicious or phishing sites: check the address before opening it, never enter credentials,
            and never run a script or code from a note or a file without reading it first.
        </div>
    </div>

    <div class="h-card">
        <div class="h-card__header">
            <div class="h-card__accent"></div>
            <span class="h-card__title"><i class="fa-solid fa-book-bookmark me-1"></i>Notes, links &amp; files</span>
            <div class="d-flex flex-wrap align-items-center gap-2 ms-auto">
                <span class="h-filter-chip" :class="{ active: filter === 'all' }" @click="filter = 'all'">All <b>[[ items.length ]]</b></span>
                <span class="h-filter-chip" :class="{ active: filter === 'note' }" @click="filter = 'note'"><i class="fa-solid fa-file-lines"></i>Notes <b>[[ notes.length ]]</b></span>
                <span class="h-filter-chip" :class="{ active: filter === 'link' }" @click="filter = 'link'"><i class="fa-solid fa-link"></i>Links <b>[[ links.length ]]</b></span>
                <span class="h-filter-chip" :class="{ active: filter === 'file' }" @click="filter = 'file'"><i class="fa-solid fa-paperclip"></i>Files <b>[[ files.length ]]</b></span>
                <template v-if="canManage">
                    <button type="button" class="btn btn-sm btn-primary rounded-pill px-3" @click="startNew('note')">
                        <i class="fa-solid fa-file-circle-plus me-1"></i>Add a note
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3" @click="startNew('link')">
                        <i class="fa-solid fa-link me-1"></i>Add a link
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3" :disabled="!!uploading" @click="pickFiles">
                        <i class="fa-solid fa-paperclip me-1"></i>Add files
                    </button>
                    <input ref="fileInput" type="file" multiple :accept="accept" hidden @change="uploadFiles($event.target.files)">
                </template>
            </div>
        </div>

        <div class="h-card__body" @dragover.prevent="dragOver = canManage" @dragleave.prevent="dragOver = false" @drop.prevent="onDrop">
            <!-- Upload (owner / admin): drop zone, allowed types, progress -->
            <div v-if="canManage" class="rr-drop mb-3" :class="{ 'rr-drop--over': dragOver }" @click="pickFiles">
                <i class="fa-solid fa-cloud-arrow-up"></i>
                <div class="flex-grow-1">
                    <div v-if="uploading" class="fw-semibold">Adding files… [[ uploading.done ]] / [[ uploading.total ]]</div>
                    <div v-else class="fw-semibold">Drop documents here (Markdown, text, PDF…), or click to choose them</div>
                    <div class="rr-drop__types">
                        <span v-for="e in cfg.file_extensions" :key="e">.[[ e ]]</span>
                    </div>
                    <div class="small text-muted mt-1">
                        Documents only (no scripts) · text [[ fmtSize(cfg.max_file_bytes) ]], PDF [[ fmtSize(cfg.max_pdf_bytes) ]] per file ·
                        [[ fmtSize(filesTotal) ]] of [[ fmtSize(cfg.max_total_bytes) ]] used for this rule
                    </div>
                </div>
                <div v-if="uploading" class="spinner-border spinner-border-sm text-primary"></div>
            </div>

            <!-- Form (owner / admin) -->
            <div v-if="editing" id="rr-form" class="rr-form mb-4">
                <div class="rr-form__head">
                    <i class="fa-solid" :class="form.kind === 'link' ? 'fa-link' : 'fa-file-lines'"></i>
                    [[ form.id ? 'Edit' : 'New' ]] [[ form.kind === 'link' ? 'external link' : 'note' ]]
                </div>
                <label class="rr-label">Title <span v-if="form.kind === 'link'" class="text-muted fw-normal">(optional — the page's own title is used)</span></label>
                <input v-model="form.title" class="form-control mb-3" maxlength="200"
                       :placeholder="form.kind === 'link' ? 'e.g. Vendor advisory, analysis blog post…' : 'e.g. Deployment notes, tuning, false positives…'">
                <template v-if="form.kind === 'link'">
                    <label class="rr-label">Address</label>
                    <input v-model="form.url" type="text" inputmode="url" class="form-control mb-1" maxlength="2000"
                           placeholder="circl.lu or https://…" :class="{ 'is-invalid': form.url && !urlOk }"
                           @blur="onUrlBlur">
                    <div class="small mb-3" :class="form.url && !urlOk ? 'text-danger' : 'text-muted'">
                        <template v-if="form.url && !urlOk">Not a web address — e.g. <code>circl.lu</code> or <code>https://www.circl.lu/services/</code>.</template>
                        <template v-else-if="urlPreview">Will be saved as <code>[[ urlPreview ]]</code></template>
                        <template v-else>A web address: <code>circl.lu</code> works, <code>https://</code> is added for you.</template>
                    </div>
                    <label class="rr-label">Description <span class="text-muted fw-normal">(optional, Markdown)</span></label>
                    <smart-editor v-model="form.content" mode="markdown" placeholder="What this link is about…"
                                  min-height="90px" max-height="240px" :hardened-preview="true"></smart-editor>
                </template>
                <template v-else>
                    <label class="rr-label">Note <span class="text-muted fw-normal">(Markdown)</span></label>
                    <smart-editor v-model="form.content" mode="markdown"
                                  placeholder="Analysis, deployment notes, known false positives, references… Images are not loaded."
                                  min-height="220px" max-height="560px" :hardened-preview="true"></smart-editor>
                </template>
                <div class="d-flex justify-content-end gap-2 mt-3">
                    <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3" @click="cancel">Cancel</button>
                    <button type="button" class="btn btn-sm btn-primary rounded-pill px-4" :disabled="!canSave || saving" @click="save">
                        <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
                        <i v-else class="fa-solid fa-check me-1"></i>[[ form.id ? 'Save' : 'Add' ]]
                    </button>
                </div>
            </div>

            <div v-if="loading" class="text-center py-4"><div class="spinner-border text-primary"></div></div>

            <div v-else-if="!shown.length" class="rr-empty">
                <i class="fa-solid fa-book-bookmark"></i>
                <div class="fw-semibold">No [[ filter === 'link' ? 'links' : filter === 'note' ? 'notes' : filter === 'file' ? 'files' : 'resources' ]] yet</div>
                <div class="small text-muted">
                    <template v-if="canManage">Add an analysis, deployment notes, files or links to reports and advisories about this rule.</template>
                    <template v-else>The rule's owner hasn't added notes, links or files.</template>
                </div>
            </div>

            <div v-else class="rr-list">
                <div v-for="r in shown" :key="r.id" class="rr-item" :class="'rr-item--' + r.kind">
                    <div class="rr-item__icon"><i :class="r.kind === 'file' ? fileIcon(r) : (r.kind === 'link' ? 'fa-solid fa-link' : 'fa-solid fa-file-lines')"></i></div>
                    <div class="rr-item__main">
                        <div class="rr-item__head">
                            <span class="rr-item__title">[[ r.title ]]</span>
                            <span class="rr-kind">[[ r.kind ]]</span>
                        </div>
                        <button v-if="r.kind === 'link'" type="button" class="rr-url" @click="askLeave(r.url)" :title="r.url">
                            <i class="fa-solid fa-arrow-up-right-from-square"></i><b>[[ hostOf(r.url) ]]</b><span>[[ r.url ]]</span>
                        </button>
                        <!-- what the server read from the page (text only, no image) -->
                        <button v-if="r.kind === 'link' && r.preview" type="button" class="rr-preview" @click="askLeave(r.url)">
                            <span class="rr-preview__site"><i class="fa-solid fa-globe me-1"></i>[[ r.preview.site_name || hostOf(r.url) ]]</span>
                            <span v-if="r.preview.title && r.preview.title !== r.title" class="rr-preview__title">[[ r.preview.title ]]</span>
                            <span v-if="r.preview.description" class="rr-preview__desc">[[ r.preview.description ]]</span>
                        </button>
                        <!-- file: name, size, view / download -->
                        <div v-if="r.kind === 'file'" class="rr-file">
                            <code>[[ r.filename ]]</code><span>[[ fmtSize(r.size) ]]</span>
                            <button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3 py-0" @click="openFile(r)">
                                <i class="fa-solid fa-eye me-1"></i>View
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3 py-0" @click="askDownload(r)">
                                <i class="fa-solid fa-download me-1"></i>Download
                            </button>
                        </div>
                        <div v-if="r.kind !== 'file' && rendered[r.id]" class="rr-md" v-html="rendered[r.id]" @click="onNoteClick"></div>
                        <div class="rr-item__meta">
                            <user-chip v-if="r.user_id" :user-id="r.user_id" :username="r.user_name" :avatar="r.user_avatar" size="xs"></user-chip>
                            <span><i class="fa-regular fa-clock me-1"></i>[[ fmtDate(r.created_at) ]]</span>
                            <span v-if="r.updated_at && r.updated_at !== r.created_at" class="text-muted">· edited [[ fmtDate(r.updated_at) ]]</span>
                        </div>
                    </div>
                    <div v-if="canManage" class="dt-actions rr-item__actions">
                        <button v-if="r.kind === 'link' && cfg.link_preview" class="dt-action-btn" title="Read the page again"
                                :disabled="refreshing === r.id" @click="refreshPreview(r)">
                            <i class="fas fa-rotate" :class="{ 'fa-spin': refreshing === r.id }"></i>
                        </button>
                        <button v-if="r.kind !== 'file'" class="dt-action-btn" title="Edit" @click="startEdit(r)"><i class="fas fa-pencil"></i></button>
                        <button class="dt-action-btn dt-action-btn--danger" :title="confirmDelete === r.id ? 'Click again to delete' : 'Delete'"
                                @click="remove(r)" @blur="confirmDelete = null">
                            <i class="fas" :class="confirmDelete === r.id ? 'fa-check' : 'fa-trash'"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- File viewer (same as the bundle files) -->
    <file-viewer :file="viewer" :show-locate="false" :external-download="true"
                 :has-prev="viewerIndex > 0" :has-next="viewerIndex >= 0 && viewerIndex < textFiles.length - 1"
                 @close="viewer = null" @prev="viewerStep(-1)" @next="viewerStep(1)" @download="onViewerDownload"></file-viewer>

    <!-- Download confirmation -->
    <div class="modal fade" id="rr-download-modal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content border-0 shadow-lg rounded-4">
                <div class="modal-body p-4">
                    <div class="d-flex align-items-center gap-3 mb-3">
                        <div class="rr-leave__icon"><i class="fa-solid fa-download"></i></div>
                        <div>
                            <div class="fw-bold">[[ downloadAsk && downloadAsk.mode === 'view' ? 'Open a user PDF' : 'Download a user file' ]]</div>
                            <div class="small text-muted">Rulezet does not check whether this file is safe.</div>
                        </div>
                    </div>
                    <div v-if="downloadAsk" class="rr-leave__url">
                        <div class="rr-label mb-1">File</div>
                        <div class="fw-bold mb-1"><code>[[ downloadAsk.filename ]]</code></div>
                        <div class="small text-muted">[[ fmtSize(downloadAsk.size) ]] · added by [[ downloadAsk.user_name || 'a user' ]]</div>
                    </div>
                    <div class="rr-warning mt-3">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                        <div>
                            It was uploaded by the rule's owner or an administrator and is <strong>not scanned or reviewed</strong>.
                            Read it before using it, and never run a script from it without understanding what it does.
                            <template v-if="downloadAsk && downloadAsk.mode === 'view'">The PDF opens in your browser's own viewer, in a new tab, with scripts and forms blocked.</template>
                            <template v-else-if="downloadAsk && !downloadAsk.is_pdf">Prefer <strong>View</strong> to read it in the browser.</template>
                            <template v-else>Open it with an up-to-date PDF reader, and don't click links or enable anything it asks for.</template>
                        </div>
                    </div>
                    <div class="d-flex justify-content-end gap-2 mt-4">
                        <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-sm btn-primary rounded-pill px-4" @click="goDownload">
                            <i class="fa-solid me-2" :class="downloadAsk && downloadAsk.mode === 'view' ? 'fa-up-right-from-square' : 'fa-download'"></i>[[ downloadAsk && downloadAsk.mode === 'view' ? 'Open anyway' : 'Download anyway' ]]
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Leaving Rulezet -->
    <div class="modal fade" id="rr-leave-modal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content border-0 shadow-lg rounded-4">
                <div class="modal-body p-4">
                    <div class="d-flex align-items-center gap-3 mb-3">
                        <div class="rr-leave__icon"><i class="fa-solid fa-arrow-up-right-from-square"></i></div>
                        <div>
                            <div class="fw-bold">You are leaving Rulezet</div>
                            <div class="small text-muted">This link was added by a user, Rulezet has not checked it.</div>
                        </div>
                    </div>
                    <div v-if="leaving" class="rr-leave__url">
                        <div class="rr-label mb-1">Site</div>
                        <div class="fw-bold mb-2">[[ leaving.host ]]</div>
                        <div class="rr-label mb-1">Full address</div>
                        <code>[[ leaving.url ]]</code>
                    </div>
                    <div class="d-flex justify-content-end gap-2 mt-4">
                        <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3" data-bs-dismiss="modal">Stay here</button>
                        <button type="button" class="btn btn-sm btn-primary rounded-pill px-4" @click="goLeave">
                            Open the link<i class="fa-solid fa-arrow-right ms-2"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>`,
}
