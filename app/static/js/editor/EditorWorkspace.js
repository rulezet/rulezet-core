/**
 * EditorWorkspace.js — the editor as a full page (/editor): folders and files of YARA rules,
 * like a code editor, turned into Rulezet rules and a bundle.
 *
 *   Explorer (left)   the bundle tree component (TreeItem from BundleStructureEditor): folders,
 *                     files, drag & drop, rename. .yar / .yara files are YARA documents, any other
 *                     file (README.md…) is plain text and becomes a text file of the bundle.
 *   Tabs + editor     one RulezetEditor, one document per file (own undo history, locks, results).
 *   Actions           Create rules / Create bundle / Save bundle: a modal shows what will happen
 *                     to each rule, then the background job (editor_yara_import) checks every rule
 *                     and only then writes the rules and the bundle. Errors go back to their file
 *                     and line; nothing is written while one rule has an error.
 *
 * ?bundle=<id> opens a bundle: its rules come as files, locked when the user may not edit them
 * (unlocking one the user may edit makes the save update it). Drafts are kept in the browser.
 *
 * Props: csrfToken, author, bundleId (Number|null)
 * Server: /editor-api (app/features/editor), see app/modules/rulezet-editor/docs/rulezet/workspace.md
 */
import { TreeItem } from '/static/js/bundle/BundleStructureEditor.js'
import EditorImportModal from '/static/js/editor/EditorImportModal.js'

const { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } = Vue

const EDITOR_JS = '/editor-api/assets/rulezet-editor.js'
const EDITOR_CSS = '/editor-api/assets/rulezet-editor.css'
const POLL_MS = 700
const DRAFT_DELAY = 800

const isYara = (name) => /\.(yar|yara)$/i.test(name || '')
let nextId = 1
const newId = () => `n_${Date.now().toString(36)}_${nextId++}`

const STATUS_TEXT = {
    exists: 'Already in Rulezet, unchanged: reused',
    update: 'Already in Rulezet and changed: it will be UPDATED (new version)',
    proposal: 'Not yours: an edit proposal will be sent to its owner',
}
const BADGES = {
    new: { badge: 'New', tone: 'info' }, exists: { badge: 'In Rulezet', tone: 'ok' },
    update: { badge: 'Will be updated', tone: 'warning' }, proposal: { badge: 'Edit proposal', tone: 'info' },
    created: { badge: 'Created', tone: 'ok' }, updated: { badge: 'Updated', tone: 'ok' }, proposed: { badge: 'Proposal sent', tone: 'ok' },
    error: { badge: 'Error', tone: 'error' }, blocked: { badge: 'Blocked', tone: 'warning' },
}

function loadCss() {
    if (document.querySelector(`link[href^="${EDITOR_CSS}"]`)) return
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = EDITOR_CSS
    document.head.appendChild(link)
}

function readDraft(key) {
    try { return JSON.parse(window.localStorage.getItem(key) || 'null') } catch { return null }
}
function writeDraft(key, value) {
    try {
        if (value == null) window.localStorage.removeItem(key)
        else window.localStorage.setItem(key, JSON.stringify(value))
    } catch { /* storage blocked: drafts are a convenience */ }
}

/** server workspace / draft -> reactive nodes with ids */
function withIds(nodes) {
    return (nodes || []).map(n => n.type === 'folder'
        ? { id: n.id || newId(), name: n.name, type: 'folder', children: withIds(n.children) }
        : { id: n.id || newId(), name: n.name, type: 'file', content: n.content || '', rule: n.rule || null, locks: n.locks || [], children: [] })
}

function walk(nodes, fn, path = []) {
    for (const n of nodes) {
        const p = [...path, n.name]
        fn(n, p)
        if (n.type === 'folder') walk(n.children, fn, p)
    }
}

/**
 * What the bundle will look like, as rows to draw: same mapping as the server
 * (app/features/editor/editor_bundle.to_bundle_structure): a YARA file with one rule -> a rule
 * file, with several -> a folder named after the file, other files -> text files.
 */
function bundleRows(tree) {
    const rows = []
    const stem = (name) => name.replace(/\.[^.]*$/, '')
    const visit = (nodes, depth) => {
        for (const n of nodes) {
            if (n.type === 'folder') {
                rows.push({ depth, kind: 'folder', name: n.name })
                visit(n.children || [], depth + 1)
            } else if (!isYara(n.name)) {
                rows.push({ depth, kind: 'text', name: n.name })
            } else if ((n.rules || []).length === 1) {
                rows.push({ depth, kind: 'rule', name: `${n.rules[0]}.yar`, note: `from ${n.name}` })
            } else if ((n.rules || []).length > 1) {
                rows.push({ depth, kind: 'folder', name: stem(n.name), note: `${n.name}: ${n.rules.length} rules, one file each`, split: true })
                for (const r of n.rules) rows.push({ depth: depth + 1, kind: 'rule', name: `${r}.yar` })
            } else {
                rows.push({ depth, kind: 'empty', name: n.name, note: 'no rule: not in the bundle' })
            }
        }
    }
    visit(tree, 0)
    return rows
}

export default {
    name: 'EditorWorkspace',
    delimiters: ['[[', ']]'],
    components: { 'tree-item': TreeItem, draggable: window.vuedraggable, 'editor-import-modal': EditorImportModal },
    props: {
        csrfToken: { type: String, default: '' },
        author:    { type: String, default: '' },
        bundleId:  { type: Number, default: null },
        showScenarios: { type: Boolean, default: false },   // test cases menu (admins, development)
    },
    setup(props) {
        const host = ref(null)
        const loading = ref(true)
        const loadError = ref('')
        const tree = ref([])
        const bundle = ref(null)               // the bundle this workspace was opened from
        const selectedId = ref(null)
        const renamingId = ref(null)
        const tabs = ref([])                   // file ids, in tab order
        const activeId = ref(null)
        const problems = reactive({})          // file id -> errors count from the last check
        const tick = ref(0)                    // bumps when rules / errors change (for computed)
        const modal = ref(null)
        const bundleForm = reactive({ name: '', description: '', public: true })
        const scenarios = ref(null)            // test cases, loaded when the menu opens
        const scenario = ref(null)             // the one loaded: its title and what to expect

        let lib = null
        let editor = null
        let pollTimer = null
        let draftTimer = null
        const opened = new Set()               // documents already created in the editor
        const draftKey = props.bundleId ? `rulezet-editor-workspace-bundle-${props.bundleId}` : 'rulezet-editor-workspace'

        const files = () => { const out = []; walk(tree.value, (n, p) => { if (n.type === 'file') out.push({ node: n, path: p.join('/') }) }); return out }
        const nodeById = (id) => { let found = null; walk(tree.value, n => { if (n.id === id) found = n }); return found }
        const activeNode = computed(() => { tick.value; return activeId.value ? nodeById(activeId.value) : null })
        const fileCount = computed(() => { tick.value; return files().length })
        const ruleCount = computed(() => { tick.value; return lib ? collectRules().length : 0 })
        const errorCount = computed(() => { tick.value; return Object.values(problems).reduce((a, b) => a + b, 0) })
        const activeRules = computed(() => {
            tick.value
            const node = activeNode.value
            if (!node || !isYara(node.name) || !lib) return []
            try { return lib.yara.splitRules(lib.yara.parse(textOf(node))).map(r => r.name) } catch { return [] }
        })
        const canSaveBundle = computed(() => !!(bundle.value && bundle.value.can_edit))

        // ── text of files ──
        const textOf = (node) => (editor && opened.has(node.id) ? editor.getDocumentText(node.id) : node.content) || ''

        function syncActive() {
            if (!editor || !activeId.value) return
            const node = nodeById(activeId.value)
            if (node) node.content = editor.getValue()
        }

        function saveDraftSoon() {
            clearTimeout(draftTimer)
            draftTimer = setTimeout(() => {
                syncActive()
                const strip = (nodes) => nodes.map(n => n.type === 'folder'
                    ? { id: n.id, name: n.name, type: 'folder', children: strip(n.children) }
                    : { id: n.id, name: n.name, type: 'file', content: textOf(n), rule: n.rule || null })
                writeDraft(draftKey, { savedAt: Date.now(), tree: strip(tree.value), bundle: bundle.value })
            }, DRAFT_DELAY)
        }

        // ── rules of the workspace (all YARA files) ──
        function collectRules() {
            const out = []
            for (const { node, path } of files()) {
                if (!isYara(node.name)) continue
                const text = textOf(node)
                let model
                try { model = lib.yara.parse(text) } catch { continue }
                const imports = (model.imports || []).map(i => i.name)
                for (const r of lib.yara.splitRules(model)) {
                    out.push({ name: r.name, text: r.text, path, imports, fileId: node.id,
                               line: text.slice(0, r.from).split('\n').length })
                }
            }
            return out
        }

        function jobTree() {
            const convert = (nodes) => nodes.map(n => {
                if (n.type === 'folder') return { type: 'folder', name: n.name, children: convert(n.children) }
                if (!isYara(n.name)) return { type: 'file', name: n.name, content: textOf(n) }
                let names = []
                try { names = lib.yara.splitRules(lib.yara.parse(textOf(n))).map(r => r.name) } catch { names = [] }
                return { type: 'file', name: n.name, rules: names }
            })
            return convert(tree.value)
        }

        // ── explorer ──
        function select(node) {
            selectedId.value = node.id
            if (node.type === 'file') openFile(node)
        }

        function openFile(node) {
            if (!editor) return
            syncActive()
            if (!tabs.value.includes(node.id)) tabs.value.push(node.id)
            const first = !opened.has(node.id)
            editor.openDocument(node.id, { text: node.content || '' })
            opened.add(node.id)
            activeId.value = node.id
            selectedId.value = node.id
            editor.setLanguage(isYara(node.name) ? 'yara' : 'plain')
            if (first) for (const lock of node.locks || []) editor.lockRule(lock.name, { label: 'Rulezet', canUnlock: !!lock.canUnlock, url: lock.url })
            if (first && node.rule) {
                // a rule of the bundle: locked unless the user may edit it (then "unlock" = update)
                editor.lockRule(node.rule.name, { label: 'Rulezet', canUnlock: !!node.rule.can_edit, url: node.rule.url })
            }
            if (first && isYara(node.name) && !(node.content || '').trim()) editor.newRule()
            editor.focus()
            tick.value++
        }

        function closeTab(id) {
            const i = tabs.value.indexOf(id)
            if (i < 0) return
            syncActive()
            tabs.value.splice(i, 1)
            if (activeId.value === id) {
                const next = tabs.value[Math.min(i, tabs.value.length - 1)]
                if (next) openFile(nodeById(next))
                else activeId.value = null
            }
        }

        function uniqueName(siblings, base) {
            const names = new Set(siblings.map(n => n.name))
            if (!names.has(base)) return base
            const dot = base.lastIndexOf('.')
            const stem = dot > 0 ? base.slice(0, dot) : base
            const ext = dot > 0 ? base.slice(dot) : ''
            for (let k = 2; ; k++) if (!names.has(`${stem}_${k}${ext}`)) return `${stem}_${k}${ext}`
        }

        function targetChildren() {
            const sel = selectedId.value && nodeById(selectedId.value)
            if (sel && sel.type === 'folder') return sel.children
            // the folder of the selected file, else the first root folder, else the root list
            let parent = null
            if (sel) walk(tree.value, n => { if (n.type === 'folder' && n.children.includes(sel)) parent = n })
            if (parent) return parent.children
            const root = tree.value.find(n => n.type === 'folder')
            return root ? root.children : tree.value
        }

        function addNode(children, kind) {
            const node = kind === 'folder'
                ? { id: newId(), name: uniqueName(children, 'folder'), type: 'folder', children: [] }
                : { id: newId(), name: uniqueName(children, 'rules.yar'), type: 'file', content: '', rule: null, children: [] }
            children.push(node)
            renamingId.value = node.id
            if (kind === 'file') nextTick(() => openFile(node))
            saveDraftSoon()
        }

        function confirmRename(node, value) {
            if (renamingId.value !== node.id) return
            renamingId.value = null
            let name = String(value || '').trim().replace(/[\\/]/g, '_')
            if (!name) return
            if (node.type === 'file') {
                const dot = node.name.lastIndexOf('.')
                const ext = dot > 0 ? node.name.slice(dot) : ''
                if (ext && !name.toLowerCase().endsWith(ext.toLowerCase())) name += ext
            }
            node.name = name
            if (activeId.value === node.id && editor) editor.setLanguage(isYara(name) ? 'yara' : 'plain')
            tick.value++
            saveDraftSoon()
        }

        function removeNode(node) {
            const ids = []
            walk([node], n => ids.push(n.id))
            const drop = (nodes) => {
                const i = nodes.indexOf(node)
                if (i >= 0) { nodes.splice(i, 1); return true }
                return nodes.some(n => n.type === 'folder' && drop(n.children))
            }
            drop(tree.value)
            for (const id of ids) {
                if (tabs.value.includes(id)) closeTab(id)
                if (editor && id !== editor.activeDocument()) editor.closeDocument(id)
                opened.delete(id)
                delete problems[id]
            }
            tick.value++
            saveDraftSoon()
        }

        // ── create rules / bundle ──
        async function post(path, body) {
            const res = await fetch(`/editor-api/yara/${path}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                body: JSON.stringify(body),
            })
            const data = await res.json().catch(() => ({}))
            if (!res.ok && !Array.isArray(data.rules) && !data.uuid) throw new Error(data.error || `HTTP ${res.status}`)
            return data
        }

        function annotate(report, rules) {
            // results per file, at each rule's line in that file
            const byName = Object.fromEntries(rules.map(r => [r.name, r]))
            const perFile = {}
            for (const k of Object.keys(problems)) delete problems[k]
            for (const r of report.rules || []) {
                const src = byName[r.name]
                if (!src) continue
                const ann = perFile[src.fileId] || (perFile[src.fileId] = { rules: {}, diagnostics: [], source: 'Rulezet' })
                const notes = (r.errors || []).map(e => e.message)
                const links = []
                if (r.existing) {
                    if (STATUS_TEXT[r.status]) notes.push(STATUS_TEXT[r.status])
                    links.push({ label: `Open "${r.existing.title}"`, url: r.existing.url })
                }
                for (const d of r.depends_on || []) if (d.url) links.push({ label: `Needs ${d.name} (Rulezet)`, url: d.url })
                if (r.created) links.push({ label: 'Open in Rulezet', url: r.created.url })
                if (r.proposal) links.push({ label: 'See the proposal', url: r.proposal.url })
                ann.rules[r.name] = { ...(BADGES[r.status] || {}), notes, links }
                for (const e of r.errors || []) {
                    ann.diagnostics.push({ line: e.line ? src.line + e.line - 1 : src.line, severity: r.status === 'blocked' ? 'warning' : 'error', message: e.message })
                }
                if (r.status === 'error' || r.status === 'blocked') problems[src.fileId] = (problems[src.fileId] || 0) + 1
            }
            for (const [fileId, ann] of Object.entries(perFile)) {
                if (!opened.has(fileId)) { const node = nodeById(fileId); if (node) { editor.openDocument(fileId, { text: node.content || '' }); opened.add(fileId); editor.setLanguage('yara') } }
            }
            // back to the file the user was on, then put the results on every file
            if (activeId.value && editor.activeDocument() !== activeId.value) editor.openDocument(activeId.value)
            for (const [fileId, ann] of Object.entries(perFile)) editor.setAnnotations(ann, { document: fileId })
            tick.value++
        }

        async function openCreate(kind) {
            if (!editor) return
            syncActive()
            const rules = collectRules()
            if (!rules.length) { editor.notify('No YARA rule in the workspace'); return }
            if (kind === 'create-bundle' && !bundleForm.name) bundleForm.name = (tree.value[0] && tree.value[0].name) || 'New bundle'
            modal.value = { phase: 'planning', kind, rules: [], job: null, sent: rules }
            try {
                const plan = await post('plan', { rules: rules.map(r => ({ name: r.name, text: r.text, path: r.path, imports: r.imports })) })
                if (plan.error) throw new Error(plan.error)
                const byName = Object.fromEntries(rules.map(r => [r.name, r]))
                const list = plan.rules.map(r => ({ ...r, path: (byName[r.name] || {}).path, fileId: (byName[r.name] || {}).fileId, line: (byName[r.name] || {}).line }))
                if (!plan.ok) {
                    annotate(plan, rules)
                    modal.value = { phase: 'failed', kind, rules: list, job: { steps: [], rules: plan.rules }, sent: rules }
                    return
                }
                modal.value = { phase: 'confirm', kind, rules: list, job: null, sent: rules,
                                rows: kind === 'rules' ? null : bundleRows(jobTree()) }
            } catch (e) {
                modal.value = null
                editor.notify(`Rulezet: ${e.message || e}`)
            }
        }

        async function confirm() {
            const m = modal.value
            const rules = m.sent
            const body = { rules: rules.map(r => ({ name: r.name, text: r.text, path: r.path, imports: r.imports })) }
            if (m.kind === 'create-bundle') {
                body.bundle = { mode: 'create', name: bundleForm.name.trim(), description: bundleForm.description, public: bundleForm.public }
                body.tree = jobTree()
            } else if (m.kind === 'save-bundle') {
                body.bundle = { mode: 'update', bundle_id: bundle.value.id }
                body.tree = jobTree()
            }
            editor.setReadOnly(true)
            modal.value = { ...m, phase: 'running' }
            try {
                const state = await post('jobs', body)
                modal.value = { ...modal.value, job: state }
                poll(state.uuid, rules)
            } catch (e) {
                finish({ status: 'failed', error: e.message || String(e), steps: [] }, rules)
            }
        }

        function poll(uuid, rules) {
            clearTimeout(pollTimer)
            pollTimer = setTimeout(async () => {
                try {
                    const res = await fetch(`/editor-api/yara/jobs/${uuid}`)
                    const state = await res.json()
                    if (!res.ok) throw new Error(state.error || `HTTP ${res.status}`)
                    modal.value = { ...modal.value, job: state }
                    if (['done', 'failed', 'cancelled'].includes(state.status)) finish(state, rules)
                    else poll(uuid, rules)
                } catch (e) {
                    finish({ status: 'failed', error: e.message || String(e), steps: (modal.value.job || {}).steps || [] }, rules)
                }
            }, POLL_MS)
        }

        function finish(state, rules) {
            editor.setReadOnly(false)
            const ok = state.status === 'done' && state.ok
            modal.value = { ...modal.value, job: state, phase: ok ? 'done' : 'failed' }
            if (state.rules && state.rules.length) annotate(state, rules)
            if (ok && state.bundle) {
                bundle.value = { id: state.bundle.id, name: state.bundle.name, can_edit: true, url: state.bundle.url }
            }
            if (ok) saveDraftSoon()
        }

        function fixErrors() {
            const bad = ((modal.value.job && modal.value.job.rules) || modal.value.rules || []).find(r => r.status === 'error' || r.status === 'blocked')
            const src = bad && modal.value.sent.find(r => r.name === bad.name)
            modal.value = null
            if (src) {
                openFile(nodeById(src.fileId))
                const err = (bad.errors || [])[0]
                editor.goTo({ line: src.line + (err && err.line ? err.line - 1 : 0) })
            }
        }

        function closeModal() {
            if (modal.value && ['running', 'planning'].includes(modal.value.phase)) return
            modal.value = null
            if (editor) editor.focus()
        }

        const job = computed(() => (modal.value && modal.value.job) || null)

        // ── bundle preview ──
        function openPreview() {
            syncActive()
            modal.value = { phase: 'preview', kind: 'create-bundle', rules: [], job: null, rows: bundleRows(jobTree()) }
        }

        // ── test scenarios ──
        async function loadScenarios() {
            if (scenarios.value) return
            try {
                const res = await fetch('/editor-api/yara/scenarios')
                const data = await res.json()
                if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
                scenarios.value = data.scenarios
            } catch (e) {
                scenarios.value = []
                editor && editor.notify(`Scenarios: ${e.message || e}`)
            }
        }

        /** Replaces the workspace with a scenario's files (paths -> folders). */
        function useScenario(sc) {
            if (!sc || !sc.available) return
            if (!window.confirm(`Replace the workspace with the test "${sc.title}"?`)) return
            const root = []
            for (const f of sc.files) {
                const parts = f.path.split('/')
                let level = root
                for (const folder of parts.slice(0, -1)) {
                    let node = level.find(n => n.type === 'folder' && n.name === folder)
                    if (!node) { node = { name: folder, type: 'folder', children: [] }; level.push(node) }
                    level = node.children
                }
                level.push({ name: parts[parts.length - 1], type: 'file', content: f.content, locks: f.locks || [] })
            }
            // forget every document of the previous workspace
            const old = editor.documentIds()
            for (const k of Object.keys(problems)) delete problems[k]
            tabs.value = []
            activeId.value = null
            opened.clear()
            bundle.value = null
            modal.value = null
            tree.value = withIds(root)
            scenario.value = sc
            const first = files()[0]
            if (first) openFile(first.node)
            for (const id of old) editor.closeDocument(id)
            saveDraftSoon()
        }

        // ── start ──
        async function load() {
            try {
                loadCss()
                lib = await import(EDITOR_JS)
            } catch (e) {
                loadError.value = `${EDITOR_JS} could not be loaded (${e.message || e}): is app/modules/rulezet-editor installed?`
                loading.value = false
                return
            }
            let initial = null
            if (props.bundleId) {
                try {
                    const res = await fetch(`/editor-api/bundles/${props.bundleId}`)
                    const data = await res.json()
                    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
                    bundle.value = data.bundle
                    bundleForm.name = data.bundle.name
                    bundleForm.description = data.bundle.description
                    bundleForm.public = data.bundle.public
                    initial = data.tree
                } catch (e) {
                    loadError.value = `The bundle could not be opened: ${e.message || e}`
                }
            }
            const draft = readDraft(draftKey)
            if (!props.bundleId && draft && draft.tree) {
                initial = draft.tree
                if (draft.bundle) bundle.value = draft.bundle
            }
            tree.value = withIds(initial && initial.length ? initial
                : [{ name: 'Workspace', type: 'folder', children: [{ name: 'rules.yar', type: 'file', content: '' }] }])
            loading.value = false
            await nextTick()
            editor = new lib.RulezetEditor(host.value, {
                language: 'yara', theme: 'auto', height: 'calc(100vh - 230px)', outline: 'auto',
                author: props.author || null,
                host: new lib.EditorServerHost({ baseUrl: '/editor-api', csrfToken: props.csrfToken, name: 'Rulezet' }),
                lineWrapping: null,
            })
            editor.on('change', () => { tick.value++; saveDraftSoon() })
            editor.on('locks', saveDraftSoon)
            editor.on('save', () => openCreate(canSaveBundle.value ? 'save-bundle' : 'rules'))
            const first = files().find(f => isYara(f.node.name)) || files()[0]
            if (first) openFile(first.node)
        }

        onMounted(load)
        onBeforeUnmount(() => { clearTimeout(pollTimer); clearTimeout(draftTimer); if (editor) editor.destroy() })

        function discardDraft() {
            if (!window.confirm('Forget this workspace and start again?')) return
            writeDraft(draftKey, null)
            window.location.reload()
        }

        return {
            scenarios, scenario, loadScenarios, useScenario, openPreview, activeRules,
            stemOf: (name) => String(name || '').replace(/\.[^.]*$/, ''),
            host, loading, loadError, tree, bundle, selectedId, renamingId, tabs, activeId, activeNode, problems,
            fileCount, ruleCount, errorCount, canSaveBundle, modal, bundleForm, job,
            nodeById, select, openFile,
            addNodeHere: (kind) => addNode(targetChildren(), kind),
            isYaraId: (id) => isYara((nodeById(id) || {}).name), closeTab, addNode, confirmRename, removeNode, saveDraftSoon,
            openCreate, confirm, fixErrors, closeModal, discardDraft,
            onTreeChange: () => { tick.value++; saveDraftSoon() },
        }
    },
    template: `
    <div class="ew">
        <!-- header: like the detail pages' banner -->
        <div class="ew-head">
            <div class="ew-head__icon"><i class="fas fa-laptop-code"></i></div>
            <div class="ew-head__text">
                <div class="d-flex align-items-center gap-2 flex-wrap">
                    <h4 class="ew-head__title">Editor</h4>
                    <span class="ed-pill ed-pill--update">BETA</span>
                    <a v-if="bundle" :href="bundle.url || ('/bundle/detail/' + bundle.id)" target="_blank" class="ew-head__bundle">
                        <i class="fas fa-box-archive"></i>[[ bundle.name ]]
                    </a>
                    <span v-if="bundle && !bundle.can_edit" class="ed-pill ed-pill--exists">read-only · save as a new bundle</span>
                </div>
                <div class="ew-head__meta">
                    <span><i class="fas fa-file-code"></i>[[ fileCount ]] file[[ fileCount === 1 ? '' : 's' ]]</span>
                    <span><i class="fas fa-shield-halved"></i>[[ ruleCount ]] rule[[ ruleCount === 1 ? '' : 's' ]]</span>
                    <span v-if="errorCount" class="ew-head__bad"><i class="fas fa-circle-exclamation"></i>[[ errorCount ]] to fix</span>
                </div>
            </div>
            <div class="ew-head__actions">
                <div v-if="showScenarios" class="dropdown">
                    <button type="button" class="ed-btn ed-btn--ghost" data-bs-toggle="dropdown" @click="loadScenarios" title="Fill the workspace with a test case">
                        <i class="fas fa-vial"></i>Test scenarios
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end ew-scenarios">
                        <li v-if="!scenarios" class="dropdown-item-text small text-muted"><i class="fas fa-spinner fa-spin me-1"></i>Loading…</li>
                        <li v-for="sc in scenarios || []" :key="sc.id">
                            <a href="#" class="dropdown-item" :class="{ disabled: !sc.available }" @click.prevent="useScenario(sc)">
                                <div class="fw-semibold small">[[ sc.title ]]</div>
                                <div class="small text-muted text-wrap">[[ sc.available ? sc.expect : sc.missing ]]</div>
                            </a>
                        </li>
                    </ul>
                </div>
                <button type="button" class="ed-btn ed-btn--ghost ed-btn--icon" title="Forget this workspace and start again" @click="discardDraft"><i class="fas fa-rotate-left"></i></button>
                <button type="button" class="ed-btn ed-btn--ghost" :disabled="!fileCount" @click="openPreview" title="How the bundle will be organised">
                    <i class="fas fa-folder-tree"></i>Preview bundle
                </button>
                <button type="button" class="ed-btn" :disabled="!ruleCount || !!modal" @click="openCreate('rules')">
                    <i class="fas fa-file-circle-plus"></i>Create rules
                </button>
                <button v-if="canSaveBundle" type="button" class="ed-btn ed-btn--success ed-btn--lg" :disabled="!ruleCount || !!modal" @click="openCreate('save-bundle')">
                    <i class="fas fa-floppy-disk"></i>Save bundle
                </button>
                <button type="button" class="ed-btn ed-btn--lg" :class="canSaveBundle ? '' : 'ed-btn--success'" :disabled="!ruleCount || !!modal" @click="openCreate('create-bundle')">
                    <i class="fas fa-box-archive"></i>[[ bundle ? 'Save as new bundle' : 'Create bundle' ]]
                </button>
            </div>
        </div>

        <div v-if="loadError" class="ed-note ed-note--danger mb-0"><i class="fas fa-circle-exclamation"></i><span>[[ loadError ]]</span></div>
        <div v-if="scenario" class="ed-note ed-note--info mb-0">
            <i class="fas fa-vial"></i>
            <span><b>Test: [[ scenario.title ]]</b><br>Expected: [[ scenario.expect ]]</span>
            <button type="button" class="ed-modal__close" aria-label="Close" @click="scenario = null"><i class="fas fa-xmark"></i></button>
        </div>

        <div class="ew-body">
            <!-- explorer -->
            <aside class="ed-card ew-explorer">
                <div class="ed-card__header">
                    <span class="ed-card__accent"></span><span class="ed-card__title">Explorer</span>
                    <span class="ms-auto d-flex gap-1">
                        <button type="button" class="ew-icon-btn" title="New YARA file" @click="addNodeHere('file')"><i class="fas fa-file-circle-plus"></i></button>
                        <button type="button" class="ew-icon-btn" title="New folder" @click="addNodeHere('folder')"><i class="fas fa-folder-plus"></i></button>
                    </span>
                </div>
                <draggable v-model="tree" group="bse-tree" :item-key="n => n.id" tag="ul" class="ps-0 mb-0 ew-tree"
                           :animation="150" ghost-class="bse-ghost" @end="onTreeChange">
                    <template #item="{ element }">
                        <tree-item :node="element" :selected-id="selectedId" :multi-set="null" :renaming-id="renamingId"
                            @select="select"
                            @rename="n => renamingId = n.id"
                            @rename-confirm="confirmRename"
                            @rename-cancel="renamingId = null"
                            @add-sub="addNode"
                            @remove="removeNode"
                            @sort-end="onTreeChange" />
                    </template>
                </draggable>
                <div class="ew-explorer__foot">
                    <i class="fas fa-circle-info"></i><span><b>.yar</b> files hold YARA rules; other files (README.md…) go to the bundle as text.</span>
                </div>
            </aside>

            <!-- tabs + editor -->
            <section class="ed-card ew-main">
                <div class="ew-tabs">
                    <div v-for="id in tabs" :key="id" class="ew-tab" :class="{ 'ew-tab--active': id === activeId }" @click="openFile(nodeById(id))">
                        <i class="fas" :class="isYaraId(id) ? 'fa-shield-halved ew-tab__yara' : 'fa-file-lines'"></i>
                        <span>[[ (nodeById(id) || {}).name ]]</span>
                        <span v-if="problems[id]" class="ew-tab__dot" :title="problems[id] + ' to fix'"></span>
                        <button type="button" class="ew-tab__close" @click.stop="closeTab(id)" aria-label="Close"><i class="fas fa-xmark"></i></button>
                    </div>
                    <div v-if="!tabs.length" class="ew-tab-empty">Open a file from the explorer</div>
                </div>
                <div v-if="activeRules.length >= 2" class="ew-split">
                    <span class="ew-split__icon"><i class="fas fa-box-archive"></i></span>
                    <span class="ew-split__text">
                        This file has <b>[[ activeRules.length ]] rules</b>. In a bundle it becomes the folder
                        <code>[[ stemOf(activeNode.name) ]]/</code> with one file per rule.
                    </span>
                    <button type="button" class="ed-btn ed-btn--ghost" @click="openPreview"><i class="fas fa-folder-tree"></i>Preview bundle</button>
                </div>
                <div v-if="loading" class="ew-loading"><i class="fas fa-spinner fa-spin me-1"></i>Loading…</div>
                <div ref="host" class="ew-editor"></div>
            </section>
        </div>

        <editor-import-modal v-if="modal" :state="modal" :bundle-form="bundleForm" :bundle-name="bundle ? bundle.name : ''"
            @close="closeModal" @confirm="confirm" @fix="fixErrors"
            @create-bundle="openCreate(canSaveBundle ? 'save-bundle' : 'create-bundle')" />
    </div>`,
}
