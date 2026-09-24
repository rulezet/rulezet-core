/**
 * file-tree.js — Collapsible interactive file/directory tree.
 *
 * Props:
 *   nodes         Array    Tree nodes: [{ name, type: 'file'|'dir', path, ext, children }]
 *                          Optional per node: icon / color (override the ext icon),
 *                          badge (small label after the name), variant (adds
 *                          .ft-row--<variant>), defaultOpen (dirs; else open if depth < 2)
 *   loading       Boolean  Show skeleton
 *   mode          String   'read' (select only) | 'read-plus' (select + inline preview)
 *   fetch-content Function Async (node) => string — called in read-plus when a file is clicked
 *
 *   row-actions   Array    Optional buttons shown on file rows (on hover; always on touch):
 *                          [{ key, label, icon }] — clicking one emits row-action({ action: key, node })
 *
 * Events:
 *   select(node)  — emitted when user clicks a file or directory
 *   row-action({ action, node })
 *
 * Expose:
 *   reveal(path)  — unfold every folder above the node with that `path`,
 *                   mark it selected and scroll it into view (briefly flashed)
 */

const { ref, computed, watch, provide, inject, nextTick } = Vue

// ── Icon mapping ───────────────────────────────────────────────────────────────

const EXT_ICONS = {
    py:   { icon: 'fa-file-code',   color: '#3b82f6' },
    js:   { icon: 'fa-file-code',   color: '#f59e0b' },
    ts:   { icon: 'fa-file-code',   color: '#3b82f6' },
    jsx:  { icon: 'fa-file-code',   color: '#06b6d4' },
    tsx:  { icon: 'fa-file-code',   color: '#06b6d4' },
    json: { icon: 'fa-file-code',   color: '#a855f7' },
    yaml: { icon: 'fa-file-code',   color: '#f97316' },
    yml:  { icon: 'fa-file-code',   color: '#f97316' },
    toml: { icon: 'fa-file-code',   color: '#f97316' },
    html: { icon: 'fa-file-code',   color: '#ef4444' },
    css:  { icon: 'fa-file-code',   color: '#22c55e' },
    scss: { icon: 'fa-file-code',   color: '#ec4899' },
    md:   { icon: 'fa-file-lines',  color: '#9ca3af' },
    txt:  { icon: 'fa-file-lines',  color: '#9ca3af' },
    rst:  { icon: 'fa-file-lines',  color: '#9ca3af' },
    sql:  { icon: 'fa-database',    color: '#f59e0b' },
    db:   { icon: 'fa-database',    color: '#3b82f6' },
    csv:  { icon: 'fa-table',       color: '#22c55e' },
    png:  { icon: 'fa-file-image',  color: '#a855f7' },
    jpg:  { icon: 'fa-file-image',  color: '#a855f7' },
    jpeg: { icon: 'fa-file-image',  color: '#a855f7' },
    gif:  { icon: 'fa-file-image',  color: '#a855f7' },
    svg:  { icon: 'fa-file-image',  color: '#f59e0b' },
    zip:  { icon: 'fa-file-zipper', color: '#f97316' },
    gz:   { icon: 'fa-file-zipper', color: '#f97316' },
    tar:  { icon: 'fa-file-zipper', color: '#f97316' },
    sh:   { icon: 'fa-terminal',    color: '#22c55e' },
    env:  { icon: 'fa-gear',        color: '#6b7280' },
    cfg:  { icon: 'fa-gear',        color: '#6b7280' },
    ini:  { icon: 'fa-gear',        color: '#6b7280' },
    pdf:  { icon: 'fa-file-pdf',    color: '#ef4444' },
}

const BINARY_EXTS = new Set(['png','jpg','jpeg','gif','svg','pdf','zip','gz','tar','db'])

function file_icon(ext) {
    return EXT_ICONS[ext?.toLowerCase()] || { icon: 'fa-file', color: '#9ca3af' }
}

// ── Single tree node (recursive) ──────────────────────────────────────────────

const FtNode = {
    name: 'FtNode',

    props: {
        node:  { type: Object, required: true },
        depth: { type: Number, default: 0 },
    },

    setup(props) {
        const ft_force        = inject('ft_force',         ref(null))
        const ft_search       = inject('ft_search',        ref(''))
        const ft_selected     = inject('ft_selected',      ref(null))
        const ft_on_select    = inject('ft_on_select',     () => {})
        const ft_row_actions  = inject('ft_row_actions',   ref([]))
        const ft_on_action    = inject('ft_on_action',     () => {})
        const ft_reveal       = inject('ft_reveal',        ref(null))

        // ft_force = { mode: 'expand' | 'collapse', keep } set by the toolbar
        // toggle. Persistent (not a one-shot pulse): folders mounted later —
        // children of a folder that just opened — follow it too.
        function forced(val) {
            if (!val || props.node.type !== 'dir') return null
            if (val.mode === 'expand') return true
            if (val.mode === 'collapse') return props.node.path === val.keep
            return null
        }
        const open = ref(forced(ft_force.value) ?? props.node.defaultOpen ?? props.depth < 2)

        watch(ft_force, (val) => {
            const f = forced(val)
            if (f !== null) open.value = f
        })

        watch(ft_search, (f) => {
            if (f) open.value = true
        })

        // reveal(): open this folder if it's an ancestor of the target
        // immediate: sub-folders are only mounted once their parent opens,
        // i.e. *after* reveal() ran — they must check the target on mount.
        watch(ft_reveal, (r) => {
            if (r && props.node.type === 'dir' && r.ancestors.has(props.node.path)) open.value = true
        }, { immediate: true })

        const icon_info = computed(() => {
            if (props.node.type === 'dir') {
                return { icon: open.value ? 'fa-folder-open' : 'fa-folder', color: '#f59e0b' }
            }
            if (props.node.icon) return { icon: props.node.icon, color: props.node.color || '#9ca3af' }
            return file_icon(props.node.ext)
        })

        const is_selected = computed(() =>
            ft_selected.value?.path === props.node.path
        )

        function matches_filter(node, f) {
            if (node.name.toLowerCase().includes(f)) return true
            return node.children?.some(c => matches_filter(c, f)) ?? false
        }

        const visible_children = computed(() => {
            const children = props.node.children || []
            const f = ft_search.value.toLowerCase().trim()
            if (!f) return children
            return children.filter(c => matches_filter(c, f))
        })

        function on_click() {
            if (props.node.type === 'dir') {
                open.value = !open.value
            }
            ft_on_select(props.node)
        }

        return {
            open, icon_info, is_selected, visible_children, on_click,
            ft_search, ft_row_actions, ft_on_action,
        }
    },

    template: `
<div class="ft-node">
    <div
        :class="['ft-row',
                 node.type === 'dir'  ? 'ft-row--dir'  : 'ft-row--file',
                 is_selected          ? 'ft-row--selected' : '',
                 node.variant         ? 'ft-row--' + node.variant : '']"
        :style="{ paddingLeft: (depth * 14 + 8) + 'px' }"
        :data-ft-path="node.path"
        @click="on_click">
        <i v-if="node.type === 'dir'"
           :class="['fas', 'ft-chevron', open ? 'fa-chevron-down' : 'fa-chevron-right']"></i>
        <span v-else class="ft-chevron"></span>
        <i :class="(icon_info.icon.includes(' ') ? '' : 'fas ') + icon_info.icon + ' ft-icon'" :style="{ color: icon_info.color }"></i>
        <span class="ft-name">{{ node.name }}</span>
        <span v-if="node.badge" class="ft-badge" :style="node.color ? { color: node.color, borderColor: node.color + '55', background: node.color + '14' } : null">{{ node.badge }}</span>
        <span v-if="node.type === 'dir' && node.children" class="ft-count">
            {{ node.children.length }}
        </span>
        <span v-if="node.type !== 'dir' && ft_row_actions.length" class="ft-row-actions">
            <button v-for="a in ft_row_actions" :key="a.key" type="button" class="ft-row-action"
                    :title="a.label" @click.stop="ft_on_action({ action: a.key, node })">
                <i :class="a.icon"></i><span>{{ a.label }}</span>
            </button>
        </span>
    </div>

    <div v-if="node.type === 'dir' && open">
        <template v-if="visible_children.length">
            <ft-node
                v-for="child in visible_children"
                :key="child.path || child.name"
                :node="child"
                :depth="depth + 1">
            </ft-node>
        </template>
        <div v-else-if="ft_search"
             class="ft-no-match"
             :style="{ paddingLeft: ((depth + 1) * 14 + 8) + 'px' }">
            no matches
        </div>
    </div>
</div>
    `,
}

// ── Root component ─────────────────────────────────────────────────────────────

export default {
    name: 'FileTree',
    components: { FtNode },

    props: {
        nodes:        { type: Array,    default: () => [] },
        loading:      { type: Boolean,  default: false },
        mode:         { type: String,   default: 'read' },    // 'read' | 'read-plus'
        fetchContent: { type: Function, default: null },
        rowActions:   { type: Array,    default: () => [] },
    },

    emits: ['select', 'row-action'],

    setup(props, { emit }) {
        const search          = ref('')
        const ft_force        = ref(null)
        const selected_node   = ref(null)
        const preview_content = ref('')
        const preview_loading = ref(false)
        const preview_error   = ref('')

        provide('ft_force',     ft_force)
        provide('ft_search',    search)
        provide('ft_selected',  selected_node)
        provide('ft_on_select', on_select)
        provide('ft_row_actions', computed(() => props.rowActions || []))
        provide('ft_on_action', (payload) => emit('row-action', payload))

        const ft_reveal = ref(null)
        const root_el   = ref(null)
        provide('ft_reveal', ft_reveal)

        function _ancestors(nodes, path, trail = []) {
            for (const n of nodes || []) {
                if (n.path === path) return { node: n, trail }
                if (n.children) {
                    const hit = _ancestors(n.children, path, [...trail, n.path])
                    if (hit) return hit
                }
            }
            return null
        }

        async function reveal(path) {
            const hit = _ancestors(props.nodes, path)
            if (!hit) return false
            search.value = ''
            ft_reveal.value = { ancestors: new Set(hit.trail), at: Date.now() }
            selected_node.value = hit.node
            // each level mounts on its parent's render — wait until the row exists
            let row = null
            for (let i = 0; i < 25 && !row; i++) {
                await nextTick()
                row = root_el.value?.querySelector(`[data-ft-path="${CSS.escape(path)}"]`)
            }
            row = row || root_el.value?.querySelector(`[data-ft-path="${CSS.escape(path)}"]`)
            if (row) {
                row.scrollIntoView({ behavior: 'smooth', block: 'center' })
                row.classList.remove('ft-row--flash')
                void row.offsetWidth
                row.classList.add('ft-row--flash')
            }
            return true
        }

        const can_preview = computed(() =>
            selected_node.value && !BINARY_EXTS.has(selected_node.value.ext?.toLowerCase())
        )

        async function on_select(node) {
            emit('select', node)

            if (props.mode !== 'read-plus' || node.type !== 'file') return

            // Toggle off if same file clicked again
            if (selected_node.value?.path === node.path) {
                selected_node.value   = null
                preview_content.value = ''
                preview_error.value   = ''
                return
            }

            selected_node.value   = node
            preview_content.value = ''
            preview_error.value   = ''

            if (!props.fetchContent) return
            if (BINARY_EXTS.has(node.ext?.toLowerCase())) {
                preview_error.value = 'Binary file — preview not supported.'
                return
            }

            preview_loading.value = true
            try {
                const result = await props.fetchContent(node)
                preview_content.value = typeof result === 'string' ? result : (result?.content ?? '')
                if (result?.error) preview_error.value = result.error
            } catch (e) {
                preview_error.value = String(e)
            }
            preview_loading.value = false
        }

        // Single toggle: expand everything / collapse everything except the
        // first root folder (so the tree never collapses to a bare line).
        const all_expanded = ref(false)
        function toggle_all() {
            if (all_expanded.value) {
                const first = (props.nodes || []).find(n => n.type === 'dir')
                ft_force.value = { mode: 'collapse', keep: first ? first.path : null }
            } else {
                ft_force.value = { mode: 'expand' }
            }
            all_expanded.value = !all_expanded.value
        }
        function collapse_all() { all_expanded.value = true;  toggle_all() }
        function expand_all()   { all_expanded.value = false; toggle_all() }

        function close_preview() {
            selected_node.value   = null
            preview_content.value = ''
            preview_error.value   = ''
        }

        function download_file() {
            if (!selected_node.value || !preview_content.value) return
            const blob = new Blob([preview_content.value], { type: 'text/plain' })
            const url  = URL.createObjectURL(blob)
            const a    = document.createElement('a')
            a.href     = url
            a.download = selected_node.value.name
            a.click()
            URL.revokeObjectURL(url)
        }

        return {
            search, selected_node, preview_content, preview_loading, preview_error,
            can_preview, reveal, root_el,
            collapse_all, expand_all, toggle_all, all_expanded, close_preview, download_file,
        }
    },

    expose: ['reveal'],

    template: `
<div class="ft" ref="root_el">

    <!-- ── Toolbar ─────────────────────────────────────────────── -->
    <div class="ft-toolbar">
        <div class="ft-search-wrap">
            <i class="fas fa-magnifying-glass ft-search-icon"></i>
            <input
                v-model="search"
                class="ft-search-input"
                type="text"
                placeholder="Search files…"
                spellcheck="false">
            <button v-if="search" class="ft-search-clear" @click="search = ''" title="Clear">
                <i class="fas fa-xmark"></i>
            </button>
        </div>
        <div class="ft-toolbar-actions">
            <button class="ft-toolbar-btn ft-toolbar-btn--toggle" @click="toggle_all"
                    :title="all_expanded ? 'Collapse every folder except the first one' : 'Open every folder'">
                <i :class="all_expanded ? 'fas fa-down-left-and-up-right-to-center' : 'fas fa-up-right-and-down-left-from-center'"></i>
                <span>{{ all_expanded ? 'Collapse all' : 'Expand all' }}</span>
            </button>
            <button
                v-if="mode === 'read-plus' && selected_node && preview_content"
                class="ft-toolbar-btn ft-toolbar-btn--download"
                title="Download file"
                @click="download_file">
                <i class="fas fa-download"></i>
            </button>
        </div>
    </div>

    <!-- ── Tree body ───────────────────────────────────────────── -->
    <div class="ft-body">
        <template v-if="loading">
            <div class="ft-skeleton" v-for="i in 6" :key="i"
                 :style="{ marginLeft: (i % 3 * 12) + 'px', width: (40 + (i * 13) % 40) + '%' }">
            </div>
        </template>

        <div v-else-if="!nodes.length" class="ft-empty">
            <i class="fas fa-folder-open"></i>
            <span>Empty directory</span>
        </div>

        <template v-else>
            <ft-node
                v-for="node in nodes"
                :key="node.path || node.name"
                :node="node"
                :depth="0">
            </ft-node>
        </template>
    </div>

    <!-- ── Preview panel (read-plus mode) ──────────────────────── -->
    <div v-if="mode === 'read-plus' && selected_node && selected_node.type === 'file'" class="ft-preview">
        <div class="ft-preview-header">
            <i class="fas fa-file-lines ft-preview-icon"></i>
            <span class="ft-preview-name">{{ selected_node.name }}</span>
            <span v-if="selected_node.path" class="ft-preview-path">{{ selected_node.path }}</span>
            <div class="ft-preview-actions">
                <button
                    v-if="preview_content"
                    class="ft-preview-btn"
                    title="Download"
                    @click="download_file">
                    <i class="fas fa-download"></i>
                </button>
                <button class="ft-preview-btn" title="Close preview" @click="close_preview">
                    <i class="fas fa-xmark"></i>
                </button>
            </div>
        </div>
        <div class="ft-preview-body">
            <div v-if="preview_loading" class="ft-preview-loading">
                <i class="fas fa-spinner fa-spin"></i> Loading…
            </div>
            <div v-else-if="preview_error" class="ft-preview-error">
                <i class="fas fa-circle-exclamation"></i> {{ preview_error }}
            </div>
            <div v-else-if="!fetchContent" class="ft-preview-no-fn">
                <i class="fas fa-info-circle"></i> No content loader configured.
            </div>
            <pre v-else class="ft-preview-code">{{ preview_content }}</pre>
        </div>
    </div>

</div>
    `,
}
