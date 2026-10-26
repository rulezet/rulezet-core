/**
 * YaraEditorPanel.js — "YARA editor" tab of the create-rule page: the rule editor from
 * app/modules/rulezet-editor (completion, lint checked against libyara, quick fixes, rule
 * tools, several rules per document), backed by this Rulezet through /editor-api.
 *
 * Paste or write any number of YARA rules, then:
 *   Fields  (panel, open by default) the rule's Rulezet fields: title, CVE, ATT&CK, tags...; with
 *           an empty document, filling them builds the rule.
 *   Check   (Check & preview, editor toolbar, Ctrl+S) POST /editor-api/yara/plan — nothing written:
 *           a modal lists every rule, what will happen to it, and every field Rulezet will store
 *           for it (and where each value comes from); the result also shows in the editor.
 *   Create  (action bar) opens a modal listing the rules to import. Once confirmed, a
 *           background job (POST /editor-api/yara/jobs, polled) checks every rule — already in
 *           Rulezet?, syntax with its dependencies, samples (later) — and only when every check
 *           passes creates the rules and links them. The modal then lists the created rules
 *           (clickable) and the summary page. When a check fails nothing is created: the
 *           modal closes on "Fix the errors" and each error is put back on its line.
 *
 * Props:
 *   active     Boolean — the tab is shown; the editor is loaded the first time it is
 *   csrfToken  String
 *   author     String — offered by the "Set author" rule tool
 */
import EditorImportModal from '/static/js/editor/EditorImportModal.js'
import { create_message } from '/static/js/toaster.js'

const { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } = Vue

const EDITOR_JS = '/editor-api/assets/rulezet-editor.js'
const TOAST_CLASS = { info: 'info', success: 'success', warning: 'warning', error: 'danger' }
const EDITOR_CSS = '/editor-api/assets/rulezet-editor.css'
const POLL_MS = 700

const BADGES = {
    new:      { badge: 'New', tone: 'info' },
    exists:   { badge: 'In Rulezet', tone: 'ok' },
    update:   { badge: 'Will be updated', tone: 'warning' },
    proposal: { badge: 'Edit proposal', tone: 'info' },
    created:  { badge: 'Created', tone: 'ok' },
    updated:  { badge: 'Updated', tone: 'ok' },
    proposed: { badge: 'Proposal sent', tone: 'ok' },
    error:    { badge: 'Error', tone: 'error' },
    blocked:  { badge: 'Blocked', tone: 'warning' },
}

// what the confirm list says for a rule already in Rulezet
const STATUS_TEXT = {
    new:      'New rule',
    exists:   'Already in Rulezet, unchanged: not imported again, used for the links',
    update:   'Already in Rulezet and changed: this rule will be UPDATED (new version, history kept)',
    proposal: 'Already in Rulezet and changed, but it is not yours: an edit proposal will be sent to its owner',
}


function loadCss() {
    if (document.querySelector(`link[href^="${EDITOR_CSS}"]`)) return
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = EDITOR_CSS
    document.head.appendChild(link)
}

/** Server report -> editor annotations (rules panel + underlines). */
function annotations(report, lines) {
    const rules = {}
    const diagnostics = []
    for (const r of report.rules || []) {
        const notes = []
        const links = []
        for (const err of r.errors || []) {
            notes.push(err.message)
            const at = lines[r.name]
            if (at) diagnostics.push({ line: err.line ? at + err.line - 1 : at, severity: r.status === 'blocked' ? 'warning' : 'error', message: err.message })
        }
        if (r.existing) {
            if (STATUS_TEXT[r.status] && r.status !== 'new') notes.push(`${STATUS_TEXT[r.status]} (${r.existing.reason})`)
            links.push({ label: `Open "${r.existing.title}"`, url: r.existing.url })
        }
        if (r.open_proposal) links.push({ label: 'Your open proposal for this content', url: r.open_proposal.url })
        if (r.proposal) links.push({ label: 'See the proposal', url: r.proposal.url })
        for (const d of r.depends_on || []) {
            if (d.where === 'rulezet') links.push({ label: `Needs ${d.name} (Rulezet)`, url: d.url })
            else notes.push(`Needs ${d.name} (this document)`)
        }
        if (r.created) links.push({ label: r.status === 'updated' ? 'Open the updated rule' : 'Open the new rule', url: r.created.url })
        rules[r.name] = { ...BADGES[r.status], notes, links }
    }
    return { rules, diagnostics, source: 'Rulezet' }
}

export default {
    name: 'YaraEditorPanel',
    delimiters: ['[[', ']]'],
    components: { 'editor-import-modal': EditorImportModal },
    props: {
        active:    { type: Boolean, default: false },
        csrfToken: { type: String, default: '' },
        author:    { type: String, default: '' },
    },
    setup(props) {
        const host = ref(null)
        const loading = ref(false)
        const loadError = ref('')
        const ruleCount = ref(0)
        const editorErrors = ref(0)

        // modal: null | { phase: 'confirm' | 'running' | 'done' | 'failed', rules, job }
        const modal = ref(null)
        let editor = null
        let pollTimer = null
        let jobText = null          // document the job runs on
        let jobLines = {}

        const job = computed(() => (modal.value && modal.value.job) || null)
        const badRules = computed(() => ((job.value && job.value.rules) || []).filter(r => r.status === 'error' || r.status === 'blocked'))
        const canCreate = computed(() => ruleCount.value > 0 && !editorErrors.value && !modal.value)

        function refresh() {
            if (!editor) return
            ruleCount.value = editor.getRules().length
            editorErrors.value = editor.getDiagnostics().filter(d => d.severity === 'error').length
            editor.refreshToolbar()
        }

        function body() {
            const model = editor.getModel()
            const fields = editor.getAllFieldValues ? editor.getAllFieldValues() : {}
            return JSON.stringify({
                imports: (model.imports || []).map(i => i.name),
                // the Fields panel's values (title, CVE, tags, ATT&CK...) go with each rule
                rules: editor.getRules().map(r => ({ name: r.name, text: r.text, fields: (fields[r.name] || {}).values || null })),
            })
        }

        async function post(path) {
            const res = await fetch(`/editor-api/yara/${path}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                body: body(),
            })
            const data = await res.json().catch(() => ({}))
            if (!res.ok && !Array.isArray(data.rules) && !data.uuid) throw new Error(data.error || `HTTP ${res.status}`)
            return data
        }

        /** Create: first what will happen to each rule (quick check), then the user confirms */
        async function openCreate(force = false) {
            if (modal.value || !editor || !ruleCount.value) return
            if (!force && !canCreate.value) return
            const text = editor.getValue()
            const lines = Object.fromEntries(editor.getRules().map(r => [r.name, r.line]))
            modal.value = { phase: 'planning', rules: [], job: null }
            try {
                const plan = await post('plan')
                if (plan.error) throw new Error(plan.error)
                if (editor.getValue() !== text) { modal.value = null; editor.notify('The document changed: try again', 'warning'); return }
                const rules = plan.rules.map(r => ({ ...r, line: lines[r.name] }))
                if (!plan.ok) {
                    // nothing can be written: straight to the errors
                    jobText = text
                    jobLines = lines
                    editor.setAnnotations(annotations(plan, lines))
                    modal.value = { phase: 'failed', rules, job: { steps: [], rules: plan.rules } }
                    return
                }
                editor.setAnnotations(annotations(plan, lines))
                modal.value = { phase: 'confirm', rules, job: null }
            } catch (e) {
                modal.value = null
                editor.notify(`Rulezet: ${e.message || e}`, 'error')
            }
        }

        async function confirmCreate() {
            jobText = editor.getValue()
            jobLines = Object.fromEntries(editor.getRules().map(r => [r.name, r.line]))
            editor.setReadOnly(true)        // the job checks this exact text
            modal.value = { ...modal.value, phase: 'running' }
            try {
                const state = await post('jobs')
                modal.value = { ...modal.value, job: state }
                poll(state.uuid)
            } catch (e) {
                finish({ status: 'failed', error: e.message || String(e), steps: [] })
            }
        }

        function poll(uuid) {
            clearTimeout(pollTimer)
            pollTimer = setTimeout(async () => {
                try {
                    const res = await fetch(`/editor-api/yara/jobs/${uuid}`)
                    const state = await res.json()
                    if (!res.ok) throw new Error(state.error || `HTTP ${res.status}`)
                    modal.value = { ...modal.value, job: state }
                    if (state.status === 'done' || state.status === 'failed' || state.status === 'cancelled') finish(state)
                    else poll(uuid)
                } catch (e) {
                    finish({ status: 'failed', error: e.message || String(e), steps: (job.value && job.value.steps) || [] })
                }
            }, POLL_MS)
        }

        function finish(state) {
            editor.setReadOnly(false)
            const ok = state.status === 'done' && state.ok
            modal.value = { ...modal.value, job: state, phase: ok ? 'done' : 'failed' }
            if (state.rules && state.rules.length && editor.getValue() === jobText) {
                editor.setAnnotations(annotations(state, jobLines))
            }
            if (ok) editor.clearDraft()
        }

        /** failed: close, and go to the first error in the editor */
        function fixErrors() {
            const first = badRules.value[0]
            modal.value = null
            if (first && jobLines[first.name]) {
                const err = (first.errors || [])[0]
                editor.goTo({ line: jobLines[first.name] + (err && err.line ? err.line - 1 : 0) })
            }
            editor.focus()
            refresh()
        }

        function closeModal() {
            if (modal.value && (modal.value.phase === 'running' || modal.value.phase === 'planning')) return
            modal.value = null
            if (editor) { editor.focus(); refresh() }
        }

        async function load() {
            if (editor || loading.value) return
            loading.value = true
            loadError.value = ''
            try {
                loadCss()
                let lib
                try {
                    lib = await import(EDITOR_JS)
                } catch (e) {
                    throw new Error(`${EDITOR_JS} could not be loaded (${e.message || e}): is app/modules/rulezet-editor installed?`)
                }
                await nextTick()
                editor = new lib.RulezetEditor(host.value, {
                    language: 'yara',
                    theme: 'auto',
                    height: '75vh',
                    outline: true,
                    author: props.author || null,
                    host: new lib.EditorServerHost({ baseUrl: '/editor-api', csrfToken: props.csrfToken, name: 'Rulezet' }),
                    draftKey: 'rulezet-create-yara',
                    lockPasted: true,          // a pasted rule keeps its text; unlock it to edit
                    toast: (message, tone) => create_message(message, TOAST_CLASS[tone] || 'info'),   // Rulezet's own toasts
                    buttons: [{
                        id: 'check', label: 'Check', icon: 'ok',
                        title: 'Check every rule with Rulezet, nothing is created (Ctrl+S)',
                        disabled: (ed) => !!modal.value || !ed.getRules().length,
                        run: () => openCreate(true),
                    }],
                })
                editor.on('save', () => openCreate(true))
                editor.on('change', refresh)
                editor.on('diagnostics', refresh)
                editor.on('annotationsCleared', refresh)
                // an empty document: the Fields panel (open) builds the rule as the fields are filled
                refresh()
            } catch (e) {
                loadError.value = `The editor could not start: ${e.message || e}`
            } finally {
                loading.value = false
            }
        }

        watch(() => props.active, (on) => { if (on) load() })
        onMounted(() => { if (props.active) load() })
        onBeforeUnmount(() => { clearTimeout(pollTimer); if (editor) editor.destroy() })

        return {
            host, loading, loadError, ruleCount, editorErrors, canCreate,
            modal, job, badRules,
            openCreate, confirmCreate, fixErrors, closeModal,
        }
    },
    template: `
    <div>
        <div class="d-flex align-items-center gap-3 mb-3 flex-wrap">
            <div class="ed-icon-badge"><i class="fas fa-laptop-code"></i></div>
            <div class="flex-grow-1">
                <div class="d-flex align-items-center gap-2">
                    <h5 class="fw-bold mb-0">YARA editor</h5>
                    <span class="ed-pill ed-pill--update">BETA</span>
                </div>
                <div class="small text-muted">
                    Write or paste as many rules as you want. Each one is checked with the rules it needs, from this document or
                    already in Rulezet; nothing is written until every check passes. <kbd>Ctrl+Shift+R</kbd>: rule tools.
                </div>
            </div>
        </div>

        <div v-if="loadError" class="ed-note ed-note--danger"><i class="fas fa-circle-exclamation"></i><span>[[ loadError ]]</span></div>
        <div v-if="loading" class="ed-note ed-note--info"><i class="fas fa-spinner fa-spin"></i><span>Loading the editor…</span></div>
        <div ref="host" style="min-height: 75vh;"></div>

        <div class="ed-actionbar">
            <div class="ed-actionbar__stats">
                <span class="ed-stat"><i class="fas fa-file-code"></i><b>[[ ruleCount ]]</b> rule[[ ruleCount === 1 ? '' : 's' ]]</span>
                <span v-if="editorErrors" class="ed-stat ed-stat--error"><i class="fas fa-circle-xmark"></i><b>[[ editorErrors ]]</b> error[[ editorErrors === 1 ? '' : 's' ]] to fix</span>
                <span v-else-if="ruleCount" class="ed-stat ed-stat--ok"><i class="fas fa-circle-check"></i>No error</span>
                <span v-else class="ed-stat ed-stat--muted"><i class="fas fa-pen"></i>Fill the fields or write a rule</span>
            </div>
            <div class="ed-actionbar__buttons">
                <button type="button" class="ed-btn ed-btn--ghost" :disabled="!ruleCount || !!modal" @click="openCreate(true)"
                        title="See every rule and every field Rulezet will store, nothing is written (Ctrl+S)">
                    <i class="fas fa-list-check"></i>Check &amp; preview
                </button>
                <button type="button" class="ed-btn ed-btn--success ed-btn--lg" :disabled="!canCreate" @click="openCreate()"
                        :title="editorErrors ? 'Fix the errors in the editor first' : ''">
                    <i class="fas fa-floppy-disk"></i>Create [[ ruleCount ]] rule[[ ruleCount === 1 ? '' : 's' ]]
                </button>
            </div>
        </div>

        <editor-import-modal v-if="modal" :state="modal" @close="closeModal" @confirm="confirmCreate" @fix="fixErrors" />
    </div>`,
}
