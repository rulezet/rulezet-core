/*
  graph-viewer.js — Vue 3 component wrapping Pivotick graph visualization library.

  Props:
    config    Object | String   JSON config object, raw JSON string, or URL to fetch
    data      Object | String   JSON data  object, raw JSON string, or URL to fetch
    mode      'simple' | 'dev' simple = viewer only; dev = full Pivotick UI + filter bar
    height    String            CSS height of the component root (default '520px')
    editable  Boolean           Show "Edit JSON" button that opens a config/data modal

  Config JSON schema:
  {
    "graph": { "directed": true },
    "nodes": {
      "id_field": "id", "label_field": "label", "type_field": "type",
      "default": { "color": "#888", "shape": "circle", "size": 16 },
      "types": {
        "person": { "color": "#4e79a7", "shape": "circle", "size": 20, "label_field": "name" }
      }
    },
    "edges": {
      "from_field": "from", "to_field": "to", "label_field": "label", "type_field": "type",
      "default": { "color": "#aaa", "dashed": false },
      "types": { "works_at": { "color": "#e25c4a", "dashed": false } }
    }
  }

  Data JSON schema:
  {
    "nodes": [{ "id": "1", "type": "person", "name": "Alice" }],
    "edges": [{ "from": "1", "to": "2", "type": "works_at", "label": "Employee" }]
  }
*/

const { ref, watch, onMounted, onBeforeUnmount, nextTick } = Vue

let _pvt_p = null

function load_pivotick() {
    if (_pvt_p) return _pvt_p
    _pvt_p = new Promise((resolve, reject) => {
        if (window.Pivotick) { resolve(window.Pivotick); return }
        const s = document.createElement('script')
        s.src = '/static/js/pivotick.iife.js'
        s.onload  = () => resolve(window.Pivotick)
        s.onerror = () => reject(new Error('Failed to load Pivotick'))
        document.head.appendChild(s)
    })
    return _pvt_p
}

async function parse_input(val) {
    if (val === null || val === undefined) return null
    if (typeof val === 'object') return val
    if (typeof val === 'string') {
        const t = val.trim()
        if (t.startsWith('{') || t.startsWith('[')) {
            try { return JSON.parse(val) } catch (e) {
                throw new Error(`Invalid JSON: ${e.message}`)
            }
        }
        const r = await fetch(val)
        if (!r.ok) throw new Error(`HTTP ${r.status} fetching ${val}`)
        return r.json()
    }
    throw new Error('config/data must be an Object or a JSON/URL string')
}

function detect_theme() {
    return document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light'
}

function fmt_json(obj) {
    return JSON.stringify(obj, null, 2)
}

export default {
    name: 'GraphViewer',
    props: {
        config:   { default: null },
        data:     { default: null },
        mode:     { type: String,  default: 'simple' },
        height:   { type: String,  default: '520px'  },
        editable: { type: Boolean, default: false     },
    },

    template: `
<div class="gv-root" :style="{ height: height }">

    <!-- ── Header: filter bar (dev) + edit button (editable) ─ -->
    <div v-if="mode === 'dev' || editable" class="gv-header" :class="{ 'gv-header--simple': mode !== 'dev' }">
        <template v-if="mode === 'dev' && !loading">
            <div class="gv-filters" v-if="node_types.length > 1">
                <span class="gv-filters-label"><i class="fas fa-circle-dot"></i></span>
                <button
                    v-for="t in node_types" :key="t.key"
                    class="gv-type-chip"
                    :class="{ 'is-hidden': hidden_types.has(t.key) }"
                    :style="{ '--chip-color': t.color }"
                    @click="toggle_type(t.key)"
                    :title="(hidden_types.has(t.key) ? 'Show ' : 'Hide ') + t.key"
                ><span class="gv-chip-dot"></span>{{ t.key }}<span class="gv-chip-count">{{ t.count }}</span></button>
            </div>
            <div class="gv-header-right">
                <div class="gv-search-wrap">
                    <i class="fas fa-search"></i>
                    <input class="gv-search-input" v-model="search_q" placeholder="Search…" @input="on_filter_change">
                    <button v-if="search_q" class="gv-search-clear" @click="search_q = ''; on_filter_change()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <span class="gv-stat" v-if="graph_stats.nodes > 0">
                    {{ graph_stats.nodes }}N · {{ graph_stats.edges }}E
                    <span v-if="graph_stats.filtered" class="gv-stat-f"> (f)</span>
                </span>
                <button v-if="editable" class="gv-edit-open-btn" @click="open_modal" title="Edit config & data JSON">
                    <i class="fas fa-code"></i>
                </button>
            </div>
        </template>
        <template v-else-if="editable">
            <span class="gv-header-spacer"></span>
            <button class="gv-edit-open-btn gv-edit-open-btn--label" @click="open_modal">
                <i class="fas fa-code"></i> Edit JSON
            </button>
        </template>
    </div>

    <!-- ── Graph canvas ──────────────────────────────────────── -->
    <div class="gv-canvas">
        <div ref="pvt_ref" class="gv-pvt-inner"></div>
        <div v-if="loading" class="gv-overlay">
            <i class="fas fa-circle-notch fa-spin"></i>
            <span>Loading graph…</span>
        </div>
        <div v-else-if="error_msg" class="gv-overlay gv-overlay--error">
            <i class="fas fa-triangle-exclamation"></i>
            <span>{{ error_msg }}</span>
        </div>
    </div>

    <!-- ── JSON editor modal (Teleport to body so overflow doesn't clip it) ── -->
    <teleport to="body">
        <div v-if="edit_modal_open" class="gv-modal-backdrop" @click.self="close_modal">
            <div class="gv-modal" role="dialog" aria-modal="true">

                <div class="gv-modal-header">
                    <div class="gv-modal-title">
                        <i class="fas fa-code"></i>
                        <span>Edit Graph JSON</span>
                    </div>
                    <button class="gv-modal-close" @click="close_modal" title="Close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>

                <div class="gv-modal-tabs">
                    <button class="gv-modal-tab" :class="{ 'is-active': edit_tab === 'config' }" @click="edit_tab = 'config'">
                        <i class="fas fa-sliders"></i> Config
                    </button>
                    <button class="gv-modal-tab" :class="{ 'is-active': edit_tab === 'data' }" @click="edit_tab = 'data'">
                        <i class="fas fa-database"></i> Data
                    </button>
                    <span class="gv-modal-tab-hint">JSON — edit then click Apply</span>
                </div>

                <div class="gv-modal-body">
                    <textarea
                        class="gv-edit-ta"
                        v-if="edit_tab === 'config'"
                        v-model="edit_cfg_str"
                        spellcheck="false"
                        autocomplete="off"
                    ></textarea>
                    <textarea
                        class="gv-edit-ta"
                        v-if="edit_tab === 'data'"
                        v-model="edit_dat_str"
                        spellcheck="false"
                        autocomplete="off"
                    ></textarea>
                </div>

                <div class="gv-modal-footer">
                    <span v-if="edit_error" class="gv-edit-error">
                        <i class="fas fa-circle-exclamation"></i> {{ edit_error }}
                    </span>
                    <div class="gv-modal-actions">
                        <button class="gv-edit-btn gv-edit-btn--reset" @click="reset_edits">
                            <i class="fas fa-rotate-left"></i> Reset
                        </button>
                        <button class="gv-edit-btn gv-edit-btn--apply" @click="apply_edits">
                            <i class="fas fa-play"></i> Apply
                        </button>
                    </div>
                </div>

            </div>
        </div>
    </teleport>

</div>
    `,

    setup(props) {
        const pvt_ref        = ref(null)
        const loading        = ref(true)
        const error_msg      = ref('')
        const node_types     = ref([])
        const hidden_types   = ref(new Set())
        const search_q       = ref('')
        const graph_stats    = ref({ nodes: 0, edges: 0, filtered: false })

        const edit_modal_open = ref(false)
        const edit_tab        = ref('config')
        const edit_cfg_str    = ref('')
        const edit_dat_str    = ref('')
        const edit_error      = ref('')

        let pvt_instance    = null
        let theme_observer  = null
        let _raw_data       = null
        let _raw_cfg        = null
        let _debounce_timer = null

        // ── Pivotick lifecycle ────────────────────────────────────

        function destroy_instance() {
            if (pvt_instance) {
                try { pvt_instance.destroy?.() } catch {}
                pvt_instance = null
            }
            if (pvt_ref.value) pvt_ref.value.innerHTML = ''
        }

        // ── Data helpers ─────────────────────────────────────────

        function build_pvt_nodes(dat, n_cfg) {
            const id_f  = n_cfg.id_field    || 'id'
            const lbl_f = n_cfg.label_field || 'label'
            const typ_f = n_cfg.type_field  || 'type'
            const types = n_cfg.types       || {}

            return (dat.nodes || [])
                .filter(n => {
                    const t = n[typ_f] || '__default__'
                    if (hidden_types.value.has(t)) return false
                    if (search_q.value) {
                        const lbl = String(n[lbl_f] || n[id_f] || '').toLowerCase()
                        return lbl.includes(search_q.value.toLowerCase())
                    }
                    return true
                })
                .map(n => {
                    const t       = n[typ_f] || '__default__'
                    const t_cfg   = types[t] || {}
                    const lbl_key = t_cfg.label_field || lbl_f
                    return {
                        id:   String(n[id_f]),
                        data: { ...n, label: n[lbl_key] ?? String(n[id_f]), type: t },
                    }
                })
        }

        function build_pvt_edges(dat, e_cfg, vis_ids) {
            const frm_f = e_cfg.from_field  || 'from'
            const to_f  = e_cfg.to_field    || 'to'
            const lbl_f = e_cfg.label_field || 'label'
            const typ_f = e_cfg.type_field  || 'type'
            const types = e_cfg.types       || {}
            const def   = e_cfg.default     || {}

            return (dat.edges || [])
                .filter(e => vis_ids.has(String(e[frm_f])) && vis_ids.has(String(e[to_f])))
                .map((e, i) => {
                    const t   = e[typ_f] || '__default__'
                    const cfg = types[t] || def
                    const edge = {
                        id:   String(e.id ?? i),
                        from: String(e[frm_f]),
                        to:   String(e[to_f]),
                        data: { label: e[lbl_f] || '' },
                    }
                    if (cfg.color || cfg.dashed !== undefined || cfg.stroke_width) {
                        edge.style = {
                            strokeColor: cfg.color        || undefined,
                            dashed:      cfg.dashed       ?? undefined,
                            strokeWidth: cfg.stroke_width || undefined,
                        }
                    }
                    return edge
                })
        }

        function build_node_style_map(n_cfg) {
            const map = {}
            for (const [k, v] of Object.entries(n_cfg.types || {})) {
                map[k] = {
                    color:       v.color,
                    shape:       v.shape,
                    size:        v.size,
                    strokeColor: v.stroke_color,
                }
            }
            return map
        }

        function compute_node_types(dat, n_cfg) {
            const typ_f  = n_cfg.type_field || 'type'
            const types  = n_cfg.types      || {}
            const n_def  = n_cfg.default    || {}
            const counts = {}
            for (const n of dat.nodes || []) {
                const t = n[typ_f] || '__default__'
                counts[t] = (counts[t] || 0) + 1
            }
            node_types.value = Object.entries(counts).map(([key, count]) => ({
                key, count,
                color: (types[key] || n_def).color || '#888',
            }))
        }

        // ── Render ────────────────────────────────────────────────

        async function render_graph() {
            if (!pvt_ref.value || !_raw_cfg || !_raw_data) return

            destroy_instance()

            const cfg   = _raw_cfg
            const dat   = _raw_data
            const n_cfg = cfg.nodes || {}
            const e_cfg = cfg.edges || {}
            const g_cfg = cfg.graph || {}

            const pvt_nodes = build_pvt_nodes(dat, n_cfg)
            const vis_ids   = new Set(pvt_nodes.map(n => n.id))
            const pvt_edges = build_pvt_edges(dat, e_cfg, vis_ids)

            graph_stats.value = {
                nodes:    pvt_nodes.length,
                edges:    pvt_edges.length,
                filtered: hidden_types.value.size > 0 || !!search_q.value,
            }

            const n_default = n_cfg.default || { color: '#888', shape: 'circle', size: 16 }

            pvt_instance = new window.Pivotick(
                pvt_ref.value,
                { nodes: pvt_nodes, edges: pvt_edges },
                {
                    isDirected: g_cfg.directed !== false,
                    renderer: {
                        nodeTypeAccessor: (node) => node.getData()?.type,
                        nodeStyleMap:     build_node_style_map(n_cfg),
                        defaultNodeStyle: {
                            color: n_default.color || '#888',
                            shape: n_default.shape || 'circle',
                            size:  n_default.size  || 16,
                        },
                    },
                    UI: {
                        mode:  props.mode === 'dev' ? 'full' : 'viewer',
                        theme: detect_theme(),
                    },
                }
            )
        }

        // ── Load ──────────────────────────────────────────────────

        async function build_graph() {
            loading.value   = true
            error_msg.value = ''
            try {
                const [, cfg, dat] = await Promise.all([
                    load_pivotick(),
                    parse_input(props.config),
                    parse_input(props.data),
                ])
                if (!cfg || !dat) { loading.value = false; return }

                _raw_cfg  = cfg
                _raw_data = dat
                compute_node_types(dat, cfg.nodes || {})
                edit_cfg_str.value = fmt_json(cfg)
                edit_dat_str.value = fmt_json(dat)

                await nextTick()
                await render_graph()
            } catch (e) {
                error_msg.value = e.message
            } finally {
                loading.value = false
            }
        }

        // ── Filters ───────────────────────────────────────────────

        function toggle_type(key) {
            const s = new Set(hidden_types.value)
            s.has(key) ? s.delete(key) : s.add(key)
            hidden_types.value = s
            schedule_render()
        }

        function on_filter_change() { schedule_render() }

        function schedule_render() {
            if (_debounce_timer) clearTimeout(_debounce_timer)
            _debounce_timer = setTimeout(() => render_graph(), 250)
        }

        // ── Modal ─────────────────────────────────────────────────

        function open_modal() {
            edit_error.value = ''
            edit_modal_open.value = true
        }

        function close_modal() {
            edit_modal_open.value = false
        }

        function apply_edits() {
            edit_error.value = ''
            try {
                const new_cfg = JSON.parse(edit_cfg_str.value)
                const new_dat = JSON.parse(edit_dat_str.value)
                _raw_cfg  = new_cfg
                _raw_data = new_dat
                compute_node_types(new_dat, new_cfg.nodes || {})
                hidden_types.value = new Set()
                search_q.value     = ''
                render_graph()
                close_modal()
            } catch (e) {
                edit_error.value = e.message
            }
        }

        function reset_edits() {
            edit_error.value   = ''
            edit_cfg_str.value = fmt_json(_raw_cfg  || {})
            edit_dat_str.value = fmt_json(_raw_data || {})
        }

        // ── Theme ─────────────────────────────────────────────────

        function on_theme_change() {
            if (_raw_cfg && _raw_data) render_graph()
        }

        function on_keydown(e) {
            if (e.key === 'Escape' && edit_modal_open.value) close_modal()
        }

        // ── Lifecycle ─────────────────────────────────────────────

        onMounted(() => {
            build_graph()

            theme_observer = new MutationObserver(muts => {
                for (const m of muts) {
                    if (m.attributeName === 'data-bs-theme') { on_theme_change(); break }
                }
            })
            theme_observer.observe(document.documentElement, { attributes: true })
            document.addEventListener('keydown', on_keydown)
        })

        onBeforeUnmount(() => {
            destroy_instance()
            theme_observer?.disconnect()
            document.removeEventListener('keydown', on_keydown)
            if (_debounce_timer) clearTimeout(_debounce_timer)
        })

        watch(() => [props.config, props.data, props.mode], () => {
            hidden_types.value = new Set()
            search_q.value     = ''
            build_graph()
        })

        return {
            pvt_ref,
            loading, error_msg,
            node_types, hidden_types, search_q, graph_stats,
            edit_modal_open, edit_tab, edit_cfg_str, edit_dat_str, edit_error,
            toggle_type, on_filter_change,
            open_modal, close_modal, apply_edits, reset_edits,
        }
    },
}
