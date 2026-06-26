/**
 * key-value.js — Recursive JSON/object inspector.
 *
 * Props:
 *   data       any      Value to display (object, array, primitive, null)
 *   label      String   Root label
 *   depth      Number   Internal recursion depth
 *   collapsed  Boolean  Start collapsed
 *   max-depth  Number   Auto-collapse beyond this depth (default: 3)
 *
 * Root-only features (depth === 0):
 *   - Search bar (filters keys + primitive values recursively)
 *   - Collapse all / Expand all buttons
 *
 * Usage:
 *   import KeyValue from '/static/js/components/key-value.js'
 *   <key-value :data="obj" label="Result"></key-value>
 */

const { ref, computed, watch, provide, inject } = Vue

// ── Type helpers ───────────────────────────────────────────────────────────────

function type_of(v) {
    if (v === null)        return 'null'
    if (Array.isArray(v)) return 'array'
    return typeof v
}

function type_label(v) {
    const t = type_of(v)
    if (t === 'object') return `{${Object.keys(v).length}}`
    if (t === 'array')  return `[${v.length}]`
    return t
}

function is_complex(v) {
    const t = type_of(v)
    return (t === 'object' || t === 'array') && v !== null
}

function display_primitive(v) {
    if (v === null || v === undefined) return String(v)
    if (typeof v === 'string') return JSON.stringify(v)
    return String(v)
}

function matches_query(data, q) {
    if (!q) return true
    const t = type_of(data)
    if (t === 'object') {
        return Object.entries(data).some(([k, v]) =>
            k.toLowerCase().includes(q) || matches_query(v, q)
        )
    }
    if (t === 'array') {
        return data.some(v => matches_query(v, q))
    }
    return String(data).toLowerCase().includes(q)
}

// ── Component ──────────────────────────────────────────────────────────────────

export default {
    name: 'KeyValue',

    props: {
        data:      { default: null },
        label:     { type: String,  default: null },
        depth:     { type: Number,  default: 0 },
        maxDepth:  { type: Number,  default: 3 },
        collapsed: { type: Boolean, default: false },
    },

    setup(props) {
        // ── Provide/inject force-state and search (root provides, children inject) ──
        let force_state, search_query

        if (props.depth === 0) {
            force_state  = ref(null)  // 'collapse' | 'expand' | null
            search_query = ref('')
            provide('kv_force',  force_state)
            provide('kv_search', search_query)
        } else {
            force_state  = inject('kv_force',  ref(null))
            search_query = inject('kv_search', ref(''))
        }

        const open = ref(!props.collapsed && props.depth < props.maxDepth)

        watch(force_state, (val) => {
            if (val === 'collapse') open.value = false
            if (val === 'expand')   open.value = true
        })

        // ── Entries (filtered by search) ─────────────────────────────────────────
        const all_entries = computed(() => {
            if (!is_complex(props.data)) return []
            if (Array.isArray(props.data)) {
                return props.data.map((v, i) => ({ key: String(i), value: v }))
            }
            return Object.entries(props.data).map(([k, v]) => ({ key: k, value: v }))
        })

        const entries = computed(() => {
            const q = (search_query.value || '').toLowerCase().trim()
            if (!q) return all_entries.value
            return all_entries.value.filter(({ key, value }) =>
                key.toLowerCase().includes(q) || matches_query(value, q)
            )
        })

        const data_type   = computed(() => type_of(props.data))
        const data_label  = computed(() => type_label(props.data))
        const complex     = computed(() => is_complex(props.data))
        const search_active = computed(() => !!(search_query.value?.trim()))

        function toggle() { open.value = !open.value }

        function collapse_all() {
            force_state.value = 'collapse'
            setTimeout(() => { force_state.value = null }, 50)
        }

        function expand_all() {
            force_state.value = 'expand'
            setTimeout(() => { force_state.value = null }, 50)
        }

        function copy_val(v) {
            const text = typeof v === 'string' ? v : JSON.stringify(v, null, 2)
            navigator.clipboard?.writeText(text)
        }

        return {
            open, entries, data_type, data_label, complex, search_active,
            search_query, force_state,
            toggle, collapse_all, expand_all, copy_val,
            type_of, display_primitive, is_complex,
        }
    },

    template: `
<div class="kv" :class="'kv--depth-' + depth">

    <!-- ── Root toolbar (search + collapse/expand) ── -->
    <div v-if="depth === 0" class="kv-toolbar">
        <div class="kv-search-wrap">
            <i class="fas fa-magnifying-glass kv-search-icon"></i>
            <input
                v-model="search_query"
                class="kv-search-input"
                type="text"
                placeholder="Search keys or values…"
                spellcheck="false">
            <button v-if="search_query" class="kv-search-clear" @click="search_query = ''" title="Clear">
                <i class="fas fa-xmark"></i>
            </button>
        </div>
        <div class="kv-toolbar-actions">
            <button class="kv-toolbar-btn" title="Expand all" @click="expand_all">
                <i class="fas fa-chevron-down"></i> Expand
            </button>
            <button class="kv-toolbar-btn" title="Collapse all" @click="collapse_all">
                <i class="fas fa-chevron-right"></i> Collapse
            </button>
        </div>
    </div>

    <!-- ── Root label ── -->
    <div v-if="depth === 0 && label" class="kv-root-label">{{ label }}</div>

    <!-- ── No search results ── -->
    <div v-if="depth === 0 && search_active && !entries.length && complex" class="kv-no-results">
        <i class="fas fa-magnifying-glass"></i>
        No matches for <code>{{ search_query }}</code>
    </div>

    <!-- ── Null / undefined ── -->
    <span v-else-if="data === null || data === undefined" class="kv-primitive kv-null">
        {{ data === null ? 'null' : 'undefined' }}
    </span>

    <!-- ── Primitive ── -->
    <span v-else-if="!complex" :class="['kv-primitive', 'kv-' + data_type]">
        {{ display_primitive(data) }}
    </span>

    <!-- ── Object / Array ── -->
    <div v-else class="kv-block">
        <div class="kv-block-header" @click="toggle">
            <i :class="['fas', open ? 'fa-chevron-down' : 'fa-chevron-right', 'kv-toggle-icon']"></i>
            <span class="kv-type-badge">{{ data_label }}</span>
            <span v-if="!open" class="kv-preview">
                {{ Array.isArray(data) ? '[…]' : '{…}' }}
            </span>
        </div>

        <div v-if="open" class="kv-children">
            <div
                v-for="entry in entries"
                :key="entry.key"
                class="kv-row"
                :class="{ 'kv-row--complex': is_complex(entry.value) }">

                <span class="kv-key">{{ entry.key }}</span>
                <span class="kv-colon">:</span>

                <key-value
                    v-if="is_complex(entry.value)"
                    :data="entry.value"
                    :depth="depth + 1"
                    :max-depth="maxDepth"
                    :collapsed="depth + 1 >= maxDepth">
                </key-value>

                <span v-else :class="['kv-primitive', 'kv-' + type_of(entry.value)]">
                    {{ display_primitive(entry.value) }}
                    <button class="kv-copy-btn" title="Copy" @click.stop="copy_val(entry.value)">
                        <i class="fas fa-copy"></i>
                    </button>
                </span>

            </div>

            <div v-if="search_active && !entries.length" class="kv-no-match-inner">
                no matches
            </div>
        </div>
    </div>

</div>
    `,
}
