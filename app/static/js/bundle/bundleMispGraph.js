// ─────────────────────────────────────────────────────────────────────────────
//  bundleMispGraph.js — MISP event graph for Rulezet bundle/rule detail pages.
//
//  The MISP → graph conversion is pivotick-converters' MispEventImporter
//  (submodule app/modules/pivotick-converters, compiled to
//  /static/js/pivotick/pivotick-converters.js by `python3 manage.py pivotick`),
//  rendered with Pivotick (/static/js/pivotick.iife.js) using the same setup
//  as the converters' own demo — HTML cards, type/relationship legend,
//  properties panel, expand/collapse — but strictly read-only: every Pivotick
//  editing affordance (create/edit/delete nodes and edges, notes) is off.
//
//  Call initBundleGraph(containerId, jsonText, { renderer, graphType }) once the
//  container is visible. renderer 'rulezet' (admin choice, /admin/pivotick)
//  hands off to Rulezet's own mapping instead (mispGraphRulezet.js).
// ─────────────────────────────────────────────────────────────────────────────

import { isDarkMode } from '../pivotick/pivotickStyle.js'

const CONVERTERS_URL = '/static/js/pivotick/pivotick-converters.js'
const PIVOTICK_URL   = '/static/js/pivotick.iife.js'

// Always the converter's simplified view: tags and attributes folded behind
// expandable summary nodes (the user expands what they need).
const VIEW_MODE = 'grouped'

const NODE_TYPE_LABELS = {
    'misp-event': 'Event',
    'misp-attribute': 'Attribute',
    'misp-attribute-group': 'Attributes',
    'misp-object': 'Object',
    'misp-galaxy-group': 'Galaxy clusters',
    'misp-galaxy': 'Galaxy',
    'misp-galaxy-cluster': 'Galaxy cluster',
    'misp-sighting-summary': 'Sightings',
    'misp-sighting-type': 'Sighting type',
    'misp-tag': 'Tag',
    'misp-tag-group': 'Tags',
    'misp-correlation': 'Correlated indicator',
}

// Pivotick editing is on by default (even in "viewer" mode the context menu
// offers Delete Node / Connect to…): switch every write affordance off, and
// veto at the hook level too in case a future Pivotick adds a new entry point.
const READ_ONLY_UI = {
    editors: {
        nodeCreator: { enabled: false },
        edgeCreator: { enabled: false },
        nodeEditor:  { enabled: false },
        edgeEditor:  { enabled: false },
        deletion:    { enabled: false },
    },
    notes:   { enabled: false },
    history: { enabled: false },
}
const READ_ONLY_CALLBACKS = {
    onBeforeNodeCreate:     () => false,
    onBeforeEdgeCreate:     () => false,
    onBeforeDelete:         () => false,
    onBeforeNodeEditCommit: () => false,
    onBeforeEdgeEditCommit: () => false,
}

const _instances = new Map()   // containerId → Pivotick instance
let _themeObserver = null
let _convertersPromise = null
let _pivotickPromise = null

// ─────────────────────────────────────────────────────────────────────────────
//  Loading
// ─────────────────────────────────────────────────────────────────────────────

function _loadConverters() {
    if (!_convertersPromise) {
        _convertersPromise = import(CONVERTERS_URL).then(mod => {
            // Converter's own CSS fixes (collapsed "+" nodes, shadow edges) — once per page.
            if (mod.PIVOTICK_STYLE_OVERRIDES && !document.getElementById('pivotick-converters-overrides')) {
                const style = document.createElement('style')
                style.id = 'pivotick-converters-overrides'
                style.textContent = mod.PIVOTICK_STYLE_OVERRIDES
                document.head.append(style)
            }
            return mod
        })
    }
    return _convertersPromise
}

function _loadPivotick() {
    if (typeof window.Pivotick === 'function') return Promise.resolve(window.Pivotick)
    if (!_pivotickPromise) {
        _pivotickPromise = new Promise((resolve, reject) => {
            const s = document.createElement('script')
            s.src = PIVOTICK_URL
            s.dataset.pivotick = '1'
            s.onload  = () => typeof window.Pivotick === 'function' ? resolve(window.Pivotick) : reject(new Error('Pivotick global missing'))
            s.onerror = () => reject(new Error('Could not load Pivotick'))
            document.head.appendChild(s)
        })
    }
    return _pivotickPromise
}

// ─────────────────────────────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────────────────────────────

function _message(container, text, spinner = false) {
    container.replaceChildren()
    const box = document.createElement('div')
    box.style.cssText = 'display:flex;align-items:center;justify-content:center;height:100%;gap:.75rem;' +
                        'color:var(--subtle-text-color,#6c757d);font-size:.875rem;padding:2rem;text-align:center;'
    if (spinner) {
        const sp = document.createElement('div')
        sp.className = 'spinner-border spinner-border-sm text-primary'
        sp.setAttribute('role', 'status')
        box.append(sp)
    }
    const span = document.createElement('span')
    span.textContent = text
    box.append(span)
    container.append(box)
}

// Rulezet exports the MISP event without the {"Event": …} wrapper that MISP's
// own API (and the converter) use — accept both.
function _asMispInput(json) {
    if (json && typeof json === 'object' && json.Event && typeof json.Event === 'object') return json
    return { Event: json }
}

function _nodePropertiesMap(node) {
    const data = typeof node.getData === 'function' ? node.getData() : (node.data ?? {})
    return Object.entries(data)
        .filter(([key, value]) => key && key !== 'label' && value !== undefined && value !== null && value !== '' && typeof value !== 'object')
        .map(([name, value]) => ({ name, value: String(value) }))
}

function _legendEntries(NODE_DEFAULTS) {
    const catalog = Object.entries(NODE_DEFAULTS)
        .filter(([, style]) => style.accentColor)
        .map(([type, style]) => ({ id: type, label: NODE_TYPE_LABELS[type] ?? type, color: style.accentColor }))
        .concat({ id: 'misp-tag', label: NODE_TYPE_LABELS['misp-tag'], color: '#DB6A47' })
    return (graph) => {
        const present = new Set(graph.getNodes().map(n => n.getData()?.type))
        return catalog.filter(entry => present.has(entry.id))
    }
}

function _destroy(containerId) {
    const prev = _instances.get(containerId)
    if (prev?.destroy) { try { prev.destroy() } catch {} }
    _instances.delete(containerId)
}

// ─────────────────────────────────────────────────────────────────────────────
//  Public: initBundleGraph
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Render a MISP event graph inside `containerId`.
 * Must be called when the container is visible (tab shown).
 *
 * @param {string} containerId  DOM id of the target div
 * @param {string} jsonText     Raw JSON string of the MISP event (with or without the Event wrapper)
 * @param {object} [opts]       { renderer: 'converters' (default) | 'rulezet', graphType: 'rule' | 'bundle' }
 */
export function initBundleGraph(containerId, jsonText, opts = {}) {
    if (opts.renderer === 'rulezet') {
        import('./mispGraphRulezet.js').then(mod => mod.initRulezetMispGraph(containerId, jsonText, opts))
        return
    }
    const container = document.getElementById(containerId)
    if (!container) return

    _destroy(containerId)
    if (_themeObserver) { _themeObserver.disconnect(); _themeObserver = null }

    _message(container, 'Loading graph…', true)

    let input
    try {
        input = _asMispInput(JSON.parse(jsonText))
    } catch {
        _message(container, 'Could not parse the MISP event.')
        return
    }

    Promise.all([_loadConverters(), _loadPivotick()]).then(([conv, Pivotick]) => {
        const importer = conv.GraphRegistry.getImporter('misp')
        if (!importer.detect(input)) {
            _message(container, 'This is not a MISP event.')
            return
        }

        const theme = isDarkMode() ? 'dark' : 'light'
        const data = importer.convert(input, { theme, viewMode: VIEW_MODE })

        container.replaceChildren()
        const instance = new Pivotick(container, data, {
            isDirected: true,
            layout: { type: 'force' },
            render: {
                type: 'svg',
                enableFocusMode: true,
                enableNodeExpansion: true,   // needed by the grouped view's expandable summaries
                zoomEnabled: true,
                zoomAnimation: true,
                dragEnabled: true,
                interactionEnabled: true,
                selectionBox: { enabled: true },
            },
            simulation: {
                enabled: true,
                useWorker: true,
                ...conv.RECOMMENDED_PIVOTICK_SIMULATION_OPTIONS,
            },
            callbacks: READ_ONLY_CALLBACKS,
            UI: {
                theme,
                mode: 'full',
                sidebar: { collapsed: 'auto' },
                tooltip: { enabled: true, allowPinning: true, nodePropertiesMap: _nodePropertiesMap },
                propertiesPanel: { nodePropertiesMap: _nodePropertiesMap },
                contextMenu: {
                    enabled: true,
                    menuNode: {
                        topbar: [{
                            text: 'Copy label',
                            iconClass: 'fas fa-copy',
                            onclick: (_evt, node) => {
                                navigator.clipboard?.writeText(String(node.getData()?.label ?? '')).catch(() => {})
                            },
                        }],
                    },
                },
                navigation: { enabled: true },
                legend: {
                    position: 'bottom-left',
                    sections: [
                        { key: 'type', title: 'Node type', entries: _legendEntries(conv.NODE_DEFAULTS) },
                        { scope: 'edge', key: 'label', title: 'Relationship' },
                    ],
                },
                ...READ_ONLY_UI,
            },
        })
        _instances.set(containerId, instance)

        // The converter's cards are pre-built DOM for one theme — re-convert on toggle.
        _themeObserver = new MutationObserver(() => {
            _themeObserver.disconnect()
            _themeObserver = null
            initBundleGraph(containerId, jsonText)
        })
        _themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    }).catch(err => {
        console.error('[bundleMispGraph]', err)
        _message(container, 'Could not load the graph.')
    })
}
