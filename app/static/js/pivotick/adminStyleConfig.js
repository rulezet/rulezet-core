// ─────────────────────────────────────────────────────────────────────────────
//  adminStyleConfig.js — Vue logic for the /admin/pivotick page.
//  The markup lives in app/templates/pivotick/admin_style.html (Vue mounts in
//  place, same convention as config/settings.html); this module only exports
//  the data/computed/methods used to build the app.
// ─────────────────────────────────────────────────────────────────────────────

import { create_message } from '/static/js/toaster.js'
import SmartEditor from '/static/js/components/smart-editor.js'

const { createApp, reactive } = Vue

const SECTION_META = [
    { key: 'rule',   label: 'Rule graph',   icon: 'fa-solid fa-shield-halved',
      hint: 'The "Graph" tab on a rule detail page — only used when this graph is drawn with the Rulezet mapping (pivotick-converters brings its own look).',
      offText: 'The Visualization card is hidden on rule pages.' },
    { key: 'bundle', label: 'Bundle graph', icon: 'fa-solid fa-box-archive',
      hint: 'The "Graph" view of a bundle\'s MISP tab — only used when this graph is drawn with the Rulezet mapping (pivotick-converters brings its own look).',
      offText: 'The bundle MISP tab shows only the JSON, without the Graph view.' },
    { key: 'attack', label: 'ATT&CK graph', icon: 'fa-solid fa-crosshairs',
      hint: 'The "Graph" view of the MITRE ATT&CK heatmap (attackGraph.js). Technique/sub-technique color is always inherited from their parent tactic.',
      offText: 'The ATT&CK page offers only the Matrix and Charts views.' },
]

const SHAPES = ['circle', 'square', 'triangle', 'hexagon']

function newNodeTypeRow(graphKey) {
    if (graphKey === 'attack') {
        return { shape: 'circle', icon: '', size_min: 10, size_max: 24 }
    }
    return { shape: 'circle', color: '#64748b', dark_color: '#94a3b8', size: 16, icon: '' }
}

function newEdgeTypeRow() {
    return { color: '#94a3b8', dark_color: '#475569', width: 2, dashed: false }
}

function paletteToText(arr) {
    return (arr || []).join(', ')
}

function textToPalette(text) {
    return String(text || '')
        .split(',')
        .map(s => s.trim())
        .filter(Boolean)
}

function csrfHeader() {
    const el = document.getElementById('csrf_token')
    return { 'X-CSRFToken': el ? el.value : '' }
}

export const RENDERERS = [
    { id: 'converters', label: 'pivotick-converters', icon: 'fa-solid fa-wand-magic-sparkles',
      title: 'MISP event drawn by pivotick-converters (cards, legend, grouped tags/attributes)' },
    { id: 'rulezet',    label: 'Rulezet mapping',     icon: 'fa-solid fa-sitemap',
      title: "Rulezet's own MISP mapping, styled with the settings below" },
]

export function createPivotickAdminApp(initialConfigs, defaultConfigs, initialEnabled = {}, initialRenderers = {}) {
    return createApp({
        delimiters: ['[[', ']]'],

        components: { 'smart-editor': SmartEditor },

        data() {
            return {
                shapes: SHAPES,
                renderers: RENDERERS,
                graphs: SECTION_META.map(meta => reactive({
                    key: meta.key, label: meta.label, icon: meta.icon, offText: meta.offText,
                    enabled: initialEnabled[meta.key] !== false,
                    renderer: initialRenderers[meta.key] || null,   // null for attack (no choice)
                    busy: false,
                })),
                activeTab: SECTION_META[0].key,
                sections: SECTION_META.map(meta => reactive({
                    ...meta,
                    mode: 'form',            // 'form' | 'json'
                    config: initialConfigs[meta.key],
                    defaultConfig: defaultConfigs[meta.key],
                    jsonText: JSON.stringify(initialConfigs[meta.key], null, 2),
                    jsonError: '',
                    newNodeTypeName: '',
                    newEdgeTypeName: '',
                    saving: false,
                    savedAt: null,
                })),
            }
        },

        methods: {
            isAttack(section) { return section.key === 'attack' },

            async _postGraphSetting(graph, path, body, okMsg) {
                graph.busy = true
                try {
                    const res = await fetch(`/admin/pivotick/${graph.key}/${path}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', ...csrfHeader() },
                        body: JSON.stringify(body),
                    })
                    const data = await res.json()
                    if (data.success) { create_message(okMsg, 'success'); return true }
                    create_message(data.message || 'Error saving', 'danger')
                } catch (e) {
                    create_message('Network error: ' + e.message, 'danger')
                } finally {
                    graph.busy = false
                }
                return false
            },

            async toggleGraph(graph) {
                const wanted = !graph.enabled
                if (await this._postGraphSetting(graph, 'enabled', { enabled: wanted },
                        `${graph.label} ${wanted ? 'enabled' : 'disabled'}`)) {
                    graph.enabled = wanted
                }
            },

            async setRenderer(graph, renderer) {
                if (graph.renderer === renderer) return
                const label = RENDERERS.find(r => r.id === renderer)?.label || renderer
                if (await this._postGraphSetting(graph, 'renderer', { renderer },
                        `${graph.label}: drawn with ${label}`)) {
                    graph.renderer = renderer
                }
            },

            setMode(section, mode) {
                if (mode === 'json') {
                    section.jsonText = JSON.stringify(section.config, null, 2)
                    section.jsonError = ''
                } else {
                    if (!this._applyJsonText(section)) return
                }
                section.mode = mode
            },

            addNodeType(section) {
                const name = section.newNodeTypeName.trim()
                if (!name) return
                if (section.config.nodes.types[name]) {
                    create_message(`Node type "${name}" already exists`, 'warning')
                    return
                }
                section.config.nodes.types[name] = newNodeTypeRow(section.key)
                section.newNodeTypeName = ''
            },

            removeNodeType(section, key) {
                delete section.config.nodes.types[key]
            },

            addEdgeType(section) {
                const name = section.newEdgeTypeName.trim()
                if (!name) return
                if (section.config.edges.types[name]) {
                    create_message(`Relation type "${name}" already exists`, 'warning')
                    return
                }
                section.config.edges.types[name] = newEdgeTypeRow()
                section.newEdgeTypeName = ''
            },

            removeEdgeType(section, key) {
                delete section.config.edges.types[key]
            },

            paletteText(type, field) {
                return paletteToText(type[field])
            },

            setPaletteText(type, field, text) {
                type[field] = textToPalette(text)
            },

            _applyJsonText(section) {
                try {
                    const parsed = JSON.parse(section.jsonText)
                    if (!parsed || typeof parsed !== 'object' || !parsed.nodes || !parsed.edges) {
                        throw new Error('JSON must contain "nodes" and "edges" keys')
                    }
                    section.config = parsed
                    section.jsonError = ''
                    return true
                } catch (e) {
                    section.jsonError = e.message
                    return false
                }
            },

            async save(section) {
                if (section.mode === 'json' && !this._applyJsonText(section)) {
                    create_message('Invalid JSON: ' + section.jsonError, 'danger')
                    return
                }
                section.saving = true
                try {
                    const res = await fetch(`/admin/pivotick/style/${section.key}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', ...csrfHeader() },
                        body: JSON.stringify(section.config),
                    })
                    const data = await res.json()
                    if (data.success) {
                        section.config = data.config
                        section.jsonText = JSON.stringify(data.config, null, 2)
                        section.savedAt = new Date().toLocaleTimeString()
                        create_message(`${section.label}: style saved`, 'success')
                    } else {
                        create_message(data.message || 'Error saving style', 'danger')
                    }
                } catch (e) {
                    create_message('Network error: ' + e.message, 'danger')
                } finally {
                    section.saving = false
                }
            },

            async reset(section) {
                if (!confirm(`Reset the "${section.label}" render to its default values?`)) return
                section.saving = true
                try {
                    const res = await fetch(`/admin/pivotick/style/${section.key}/reset`, {
                        method: 'POST',
                        headers: csrfHeader(),
                    })
                    const data = await res.json()
                    if (data.success) {
                        section.config = data.config
                        section.jsonText = JSON.stringify(data.config, null, 2)
                        section.jsonError = ''
                        create_message(`${section.label}: reset to default`, 'success')
                    } else {
                        create_message(data.message || 'Error resetting style', 'danger')
                    }
                } catch (e) {
                    create_message('Network error: ' + e.message, 'danger')
                } finally {
                    section.saving = false
                }
            },
        },
    })
}

export { SHAPES }
