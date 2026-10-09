// Pivograph maps on blog posts (BlogPost.graph). Pivograph — the submodule
// app/modules/pivograph, built into static/pivograph by `manage.py pivograph` —
// runs in an iframe and talks with the page through postMessage:
//   app → page  pivograph:ready, pivograph:loaded, pivograph:error,
//               pivograph:changed { data }   (editable maps only)
//               pivograph:document { data }  (answer to pivograph:get)
//   page → app  pivograph:load { data, name }, pivograph:get
// The editor (templates/blog/create_edit.html) uses useBlogGraph(); the post
// page (detail_blog.html) uses mountGraphViewer().

const { ref, computed, nextTick } = Vue

export const PIVOGRAPH_URL = '/static/pivograph/index.html'

// The current Rulezet theme, for Pivograph: light / dark and the background
// the graph sits on (the card's own colour), so it blends with any theme.
export function currentTheme(surface = document.body) {
    const dark = document.documentElement.classList.contains('dark-mode')
    const bg = getComputedStyle(surface).getPropertyValue('--card-bg-color').trim()
    return { scheme: dark ? 'dark' : 'light', background: /^#[0-9a-f]{3,8}$/i.test(bg) ? bg : null }
}

function themeParams(theme) {
    const p = new URLSearchParams({ theme: theme.scheme })
    if (theme.background) p.set('bg', theme.background)
    return p.toString()
}

// Keep the frame in step when the user switches theme (theme.js changes <html>).
function followTheme(frame, surface) {
    const observer = new MutationObserver(() => {
        if (!frame.contentWindow) return
        frame.contentWindow.postMessage({ type: 'pivograph:theme', ...currentTheme(surface) }, window.location.origin)
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-theme'] })
    return () => observer.disconnect()
}

// Load `doc` into the Pivograph frame once it says it's ready (or right away
// if it already did). Returns a function that stops listening.
function connect(frame, getDoc, onMessage = () => {}) {
    const handler = (event) => {
        if (event.source !== frame.contentWindow) return
        const msg = event.data || {}
        if (msg.type === 'pivograph:ready') {
            frame.contentWindow.postMessage({ type: 'pivograph:load', data: getDoc(), name: 'blog-graph.json' },
                                            window.location.origin)
        }
        onMessage(msg)
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
}

// Ask the frame for its current document (positions included).
function requestDocument(frame, timeoutMs = 1500) {
    return new Promise((resolve) => {
        const timer = setTimeout(() => { window.removeEventListener('message', handler); resolve(null) }, timeoutMs)
        const handler = (event) => {
            if (event.source !== frame.contentWindow || event.data?.type !== 'pivograph:document') return
            clearTimeout(timer)
            window.removeEventListener('message', handler)
            resolve(event.data.data)
        }
        window.addEventListener('message', handler)
        frame.contentWindow.postMessage({ type: 'pivograph:get' }, window.location.origin)
    })
}

// An imported or bundled document, made editable: Pivograph locks maps with
// meta.readOnly, and its own examples (meta.source.format === 'example').
function editable(doc) {
    const meta = { ...(doc.meta || {}) }
    if (meta.source?.format === 'example') delete meta.source
    meta.readOnly = false
    return { ...doc, meta }
}

export function graphStats(doc) {
    return { nodes: (doc?.nodes || []).length, edges: (doc?.edges || []).length, title: doc?.meta?.title || 'Untitled graph' }
}

// ── Editor ──────────────────────────────────────────────────────────────────
export function useBlogGraph({ editUuid, hasGraph, postTitle, notify }) {
    const graph      = ref(null)      // the post's map (null = none)
    const graphDirty = ref(false)     // changed since the last save → sent with the post
    const loading    = ref(false)
    const editorOpen = ref(false)
    const editorFrame = ref(null)
    let draft = null                  // last document reported by the open editor
    let disconnect = null

    const stats = computed(() => graph.value ? graphStats(graph.value) : null)

    async function loadExisting() {
        if (!editUuid || !hasGraph) return
        loading.value = true
        try {
            const res = await fetch(`/blog/post/${editUuid}/graph.json`)
            if (res.ok) graph.value = await res.json()
        } catch { notify('Could not load the graph', 'danger-subtle') }
        finally { loading.value = false }
    }

    function setGraph(doc) { graph.value = doc; graphDirty.value = true }

    function createBlank() {
        setGraph({ version: 1, meta: { title: postTitle() || 'Graph', readOnly: false }, nodes: [], edges: [] })
        openEditor()
    }

    async function startFromTemplate(name) {
        try {
            const res = await fetch(`/blog/admin/graph_template/${name}`)
            const data = await res.json()
            if (!data.success) return notify(data.message || 'Template not available', 'danger-subtle')
            setGraph(data.graph)
            openEditor()
        } catch { notify('Could not load the template', 'danger-subtle') }
    }

    function importFile(event) {
        const file = event.target.files[0]
        event.target.value = ''
        if (!file) return
        if (file.size > 5 * 1024 * 1024) return notify('This file is too big (max 5 MB).', 'danger-subtle')
        const reader = new FileReader()
        reader.onload = () => {
            try {
                const doc = JSON.parse(reader.result)
                if (!doc || typeof doc !== 'object' || Array.isArray(doc)) throw new Error()
                setGraph(editable(doc))
                notify(`Graph imported: ${graphStats(doc).nodes} nodes. Save the post to keep it.`, 'success-subtle')
            } catch { notify('This file is not a Pivograph JSON document.', 'danger-subtle') }
        }
        reader.readAsText(file)
    }

    function removeGraph() {
        if (!confirm('Remove the graph from this post?')) return
        graph.value = null
        graphDirty.value = true
    }

    function download() {
        if (!graph.value) return
        const blob = new Blob([JSON.stringify(graph.value, null, 2)], { type: 'application/json' })
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `${(graphStats(graph.value).title || 'graph').replace(/[^\w-]+/g, '-').toLowerCase()}.json`
        a.click()
        URL.revokeObjectURL(a.href)
    }

    function openEditor() {
        draft = null
        editorOpen.value = true
        nextTick(() => {
            const frame = editorFrame.value
            if (!frame) return
            disconnect?.()
            disconnect = connect(frame, () => editable(graph.value), (msg) => {
                if (msg.type === 'pivograph:changed') draft = msg.data
                if (msg.type === 'pivograph:error') notify(`Graph error: ${msg.message}`, 'danger-subtle')
            })
            const stopTheme = followTheme(frame, document.body)
            const stopLoad = disconnect
            disconnect = () => { stopLoad(); stopTheme() }
            frame.src = `${PIVOGRAPH_URL}?embed=1&toolbar=1&${themeParams(currentTheme(document.body))}`
        })
    }

    async function applyEditor() {
        const frame = editorFrame.value
        const doc = (frame && await requestDocument(frame)) || draft
        if (doc) setGraph(editable(doc))
        closeEditor()
        notify('Graph updated — save the post to keep it.', 'success-subtle')
    }

    function closeEditor() {
        disconnect?.(); disconnect = null
        if (editorFrame.value) editorFrame.value.src = 'about:blank'
        editorOpen.value = false
    }

    // What savePost sends: the graph only when it changed (null removes it).
    function payloadPart() { return graphDirty.value ? { graph: graph.value } : {} }
    function markSaved() { graphDirty.value = false }

    return {
        graph, graphDirty, graphStats: stats, graphLoading: loading, graphEditorOpen: editorOpen, graphEditorFrame: editorFrame,
        loadGraph: loadExisting, createBlankGraph: createBlank, startGraphFromTemplate: startFromTemplate,
        importGraphFile: importFile, removeGraph, downloadGraph: download,
        openGraphEditor: openEditor, applyGraphEditor: applyEditor, closeGraphEditor: closeEditor,
        graphPayload: payloadPart, graphSaved: markSaved,
    }
}

// ── Viewer (post page) ──────────────────────────────────────────────────────
// Fetch the post's map and show it read-only in `frame`: 'full' (Pivograph with
// its side panel and tools) or 'simple' (just the graph). Follows the theme of
// `surface` (the card around the frame).
export async function mountGraphViewer(frame, graphUrl, { view = 'full', surface = frame.parentElement, onError = () => {} } = {}) {
    let doc
    try {
        const res = await fetch(graphUrl)
        if (!res.ok) throw new Error()
        doc = await res.json()
    } catch { onError('Could not load the graph'); return }
    const readOnly = { ...doc, meta: { ...(doc.meta || {}), readOnly: true } }
    connect(frame, () => readOnly, (msg) => { if (msg.type === 'pivograph:error') onError(msg.message) })
    followTheme(frame, surface)
    const simple = view === 'simple' ? '&sidebar=0&mode=viewer' : ''
    frame.src = `${PIVOGRAPH_URL}?embed=1${simple}&${themeParams(currentTheme(surface))}`
}
