/**
 * log-table.js — Activity log table with GitHub-style filter menus.
 *
 * Props:
 *   fetchUrl     String  (required) — API endpoint, e.g. "/admin/get_logs_page"
 *   facetsUrl    String  (default: '/admin/logs/facets') — options + counts of the
 *                filter menus (author, action, category, IP), fetched when a menu opens
 *   scope        String  (default: 'all') — 'all' | 'connections' | 'api', same pinning
 *                as fetchUrl so the menu counts match the table
 *   canDelete    Boolean (default: false) — show delete / bulk-delete controls
 *   canModerate  Boolean (default: false) — Visibility column, filter and bulk actions
 *   csrfToken    String  (default: '')
 *   hideCategoryFilter Boolean — hide the Category menu (listing pinned to one category)
 *
 * Events:
 *   delete(log), bulk-delete(uuids[]), edit(log), toggle-visibility(log),
 *   bulk-set-visibility(uuids[], isPublic)
 *
 * Exposed:
 *   fetchData() — re-fetch current page
 *
 * Clicking anywhere on a row opens its details (buttons, links and the checkbox
 * keep their own action).
 */

import PaginationComponent from '/static/js/rule/paginationComponent.js'
import CodeViewer         from '/static/js/components/code-viewer.js'
import IpAddress          from '/static/js/components/ip-address.js'
import UserChip           from '/static/js/components/UserChip.js'

const { ref, reactive, computed, watch, onMounted, onBeforeUnmount } = Vue

const CATEGORY_ICONS = {
    rule: 'fa-file-shield', bundle: 'fa-box', user: 'fa-user', admin: 'fa-crown',
    tag: 'fa-tag', job: 'fa-gears', github: 'fa-code-branch', connector: 'fa-plug',
    comment: 'fa-comment', blog: 'fa-newspaper', chatbot: 'fa-robot', api: 'fa-code',
    system: 'fa-gear',
}

const LEVELS = [
    { value: 'info',    label: 'Info'    },
    { value: 'success', label: 'Success' },
    { value: 'warning', label: 'Warning' },
    { value: 'error',   label: 'Error'   },
]

const SORTS = [
    { key: 'created_at', dir: 'desc', label: 'Newest' },
    { key: 'created_at', dir: 'asc',  label: 'Oldest' },
    { key: 'action',     dir: 'asc',  label: 'Action (A→Z)' },
    { key: 'category',   dir: 'asc',  label: 'Category (A→Z)' },
    { key: 'level',      dir: 'desc', label: 'Level' },
]

function getCategoryIcon(cat) { return CATEGORY_ICONS[cat] || 'fa-circle' }

// Page of a log's target, when it has one ('' otherwise).
function targetUrl(log) {
    const id = log.target_id, uuid = log.target_uuid
    switch (log.target_type) {
        case 'rule':      return (uuid || id) ? `/rule/detail_rule/${uuid || id}` : ''
        case 'bundle':    return (uuid || id) ? `/bundle/detail/${uuid || id}` : ''
        case 'user':      return id ? `/account/detail_user/${id}` : ''
        case 'job':       return uuid ? `/jobs/detail/${uuid}` : ''
        case 'blog_post': return uuid ? `/blog/post/${uuid}` : ''
        default:          return ''
    }
}

function targetLabel(type) {
    return (type || '').replace(/_/g, ' ').replace(/^./, c => c.toUpperCase())
}

function getInitials(name) {
    if (!name || name === 'System' || name === 'Anonymous') return '?'
    const parts = name.trim().split(/\s+/)
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function formatRelative(val) {
    if (!val) return '—'
    const diff = Math.floor((Date.now() - new Date(val).getTime()) / 1000)
    if (diff < 60)    return `${Math.max(diff, 0)}s ago`
    if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    if (diff < 86400 * 30) return `${Math.floor(diff / 86400)}d ago`
    return new Date(val).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatFull(val) {
    if (!val) return ''
    return new Date(val).toLocaleString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
    })
}

// ── Filter menu (GitHub "Author ▾" dropdown) ─────────────────────────────────
// Static options via `options`, or server options (with counts) via `load(q)`.
const FilterMenu = {
    name: 'LtFilterMenu',
    components: { 'user-chip': UserChip },
    props: {
        label:       { type: String, required: true },
        title:       { type: String, default: '' },
        options:     { type: Array,  default: null },   // [{value,label,count?,icon?}]
        load:        { type: Function, default: null }, // async (q, offset) => { items, has_more }
        modelValue:  { type: String, default: '' },
        searchable:  { type: Boolean, default: false },
        placeholder: { type: String, default: 'Filter…' },
        align:       { type: String, default: 'end' },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
        const open = ref(false), q = ref(''), loading = ref(false), remote = ref([]), hasMore = ref(false)
        const root = ref(null), input = ref(null)
        let timer = null, seq = 0

        async function fetchRemote(more = false) {
            if (!props.load) return
            const my = ++seq
            loading.value = true
            try {
                const r = await props.load(q.value, more ? remote.value.length : 0)
                if (my !== seq) return
                remote.value = more ? [...remote.value, ...r.items] : r.items
                hasMore.value = r.has_more
            } finally { if (my === seq) loading.value = false }
        }
        function loadMore() { fetchRemote(true) }
        const shown = computed(() => {
            if (props.load) return remote.value
            const t = q.value.toLowerCase()
            return (props.options || []).filter(o => !t || o.label.toLowerCase().includes(t))
        })
        function toggle() {
            open.value = !open.value
            if (open.value) {
                q.value = ''
                fetchRemote()
                setTimeout(() => input.value?.focus(), 0)
            }
        }
        function onInput() { clearTimeout(timer); timer = setTimeout(fetchRemote, 250) }
        function pick(v) { emit('update:modelValue', props.modelValue === v ? '' : v); open.value = false }
        function onDoc(e) { if (open.value && root.value && !root.value.contains(e.target)) open.value = false }
        function onKey(e) { if (e.key === 'Escape') open.value = false }
        onMounted(() => { document.addEventListener('mousedown', onDoc); document.addEventListener('keydown', onKey) })
        onBeforeUnmount(() => { document.removeEventListener('mousedown', onDoc); document.removeEventListener('keydown', onKey) })
        return { open, q, loading, hasMore, shown, root, input, toggle, onInput, pick, loadMore }
    },
    template: `
<div class="lt-menu" ref="root">
    <button type="button" class="lt-menu-btn" :class="{ 'is-set': modelValue, 'is-open': open }" @click="toggle">
        {{ label }} <i class="fas fa-caret-down"></i>
    </button>
    <div v-if="open" class="lt-menu-pop" :class="'lt-menu-pop--' + align">
        <div class="lt-menu-head">{{ title || ('Filter by ' + label.toLowerCase()) }}</div>
        <div v-if="searchable || load" class="lt-menu-search">
            <input ref="input" v-model="q" @input="onInput" :placeholder="placeholder" />
        </div>
        <div class="lt-menu-list">
            <slot name="before" :pick="pick"></slot>
            <div v-if="loading && !shown.length" class="lt-menu-empty"><i class="fas fa-spinner fa-spin"></i></div>
            <div v-else-if="!shown.length" class="lt-menu-empty">Nothing found</div>
            <button v-for="o in shown" :key="o.value" type="button" class="lt-menu-item"
                    :class="{ 'is-selected': modelValue === String(o.value) }" @click.prevent="pick(String(o.value))">
                <i class="fas fa-check lt-menu-check"></i>
                <i v-if="o.icon" :class="['fas', o.icon, 'lt-menu-icon']"></i>
                <span v-if="o.user_id" class="lt-menu-label">
                    <user-chip :user-id="o.user_id" :username="o.label" :avatar="o.avatar" size="xs"></user-chip>
                </span>
                <span v-else class="lt-menu-label" :title="o.label">{{ o.label }}</span>
                <span v-if="o.count != null" class="lt-menu-count">{{ o.count }}</span>
            </button>
            <button v-if="hasMore && shown.length" type="button" class="lt-menu-more" :disabled="loading" @click="loadMore">
                <i :class="['fas', loading ? 'fa-spinner fa-spin' : 'fa-angles-down']"></i> Load more
            </button>
        </div>
        <button v-if="modelValue" type="button" class="lt-menu-clear" @click="pick(modelValue)">
            <i class="fas fa-xmark"></i> Clear filter
        </button>
    </div>
</div>`,
}

// ── Component ─────────────────────────────────────────────────────────────────

export default {
    name: 'LogTable',
    components: {
        'pagination-component': PaginationComponent, 'code-viewer': CodeViewer,
        'ip-address': IpAddress, 'lt-filter-menu': FilterMenu, 'user-chip': UserChip,
    },

    props: {
        fetchUrl:    { type: String,  required: true },
        facetsUrl:   { type: String,  default: '/admin/logs/facets' },
        scope:       { type: String,  default: 'all' },
        canDelete:   { type: Boolean, default: false },
        canModerate: { type: Boolean, default: false },
        csrfToken:   { type: String,  default: '' },
        hideCategoryFilter: { type: Boolean, default: false },
    },

    emits: ['delete', 'bulk-delete', 'edit', 'toggle-visibility', 'bulk-set-visibility'],

    setup(props, { emit, expose }) {

        // ── State ─────────────────────────────────────────────────────────────
        const items        = ref([])
        const total        = ref(0)
        const total_pages  = ref(1)
        const loading      = ref(false)
        const page         = ref(1)
        const per_page     = ref(50)
        const rootEl       = ref(null)
        const sort_key     = ref('created_at')
        const sort_dir     = ref('desc')
        const search       = ref('')
        const expanded_id  = ref(null)
        const selected     = ref(new Set())
        const togglingUuid = ref(null)

        // Every server-side filter; '' = not set. `author` is a user id or
        // 'system' / 'anonymous'. `authorLabel` keeps the name for the chip.
        const filters = reactive({
            author: '', authorLabel: '', category: '', level: '', action: '',
            ip: '', visibility: '', date_from: '', date_to: '',
        })

        const colCount = computed(() => 9 + (props.canDelete ? 1 : 0) + (props.canModerate ? 1 : 0))

        function filterParams(skip = '') {
            const p = new URLSearchParams()
            if (search.value) p.set('search', search.value)
            if (filters.author && skip !== 'user') {
                if (filters.author === 'system' || filters.author === 'anonymous') p.set('actor', filters.author)
                else p.set('user_id', filters.author)
            }
            for (const k of ['category', 'level', 'action', 'ip', 'visibility', 'date_from', 'date_to']) {
                if (filters[k] && skip !== k) p.set(k, filters[k])
            }
            return p
        }

        // ── Fetch ─────────────────────────────────────────────────────────────
        let fetchSeq = 0
        async function fetchData() {
            const my = ++fetchSeq
            loading.value = true
            try {
                const params = filterParams()
                params.set('page', page.value)
                params.set('per_page', per_page.value)
                params.set('sort', sort_key.value)
                params.set('dir', sort_dir.value)
                const res  = await fetch(`${props.fetchUrl}?${params}`)
                const data = await res.json()
                if (my !== fetchSeq) return
                items.value       = data.items || data.logs || []
                total.value       = data.total       || 0
                total_pages.value = data.total_pages || 1
                const current = new Set(items.value.map(i => i.uuid))
                selected.value = new Set([...selected.value].filter(u => current.has(u)))
            } catch (e) {
                console.error('[LogTable] fetch error:', e)
            } finally {
                if (my === fetchSeq) { loading.value = false; togglingUuid.value = null }
            }
        }

        function refetch() { page.value = 1; fetchData() }

        // ── Filter menus (server options with counts) ─────────────────────────
        function facetLoader(facet) {
            return async (q, offset = 0) => {
                const p = filterParams(facet)
                p.set('facet', facet); p.set('scope', props.scope)
                p.set('offset', offset); p.set('limit', 50)
                if (q) p.set('q', q)
                try {
                    const res = await fetch(`${props.facetsUrl}?${p}`)
                    const data = await res.json()
                    const items = (data.items || []).map(o => facet === 'category'
                        ? { ...o, icon: getCategoryIcon(o.value) } : o)
                    return { items, has_more: !!data.has_more }
                } catch { return { items: [], has_more: false } }
            }
        }
        const loadUsers      = facetLoader('user')
        const loadActions    = facetLoader('action')
        const loadCategories = facetLoader('category')
        const loadIps        = facetLoader('ip')

        // The author menu emits the id; remember the name for the chip.
        const authorCache = {}
        async function loadUsersCached(q, offset) {
            const r = await loadUsers(q, offset)
            r.items.forEach(o => { authorCache[o.value] = o.label })
            return r
        }
        function setAuthor(v) {
            filters.author = v
            filters.authorLabel = v === 'system' ? 'System' : v === 'anonymous' ? 'Anonymous' : (authorCache[v] || `#${v}`)
        }

        // Clicking a value in the table filters on it (author, category, IP…).
        function filterBy(key, value, label) {
            if (!value) return
            if (key === 'author') { authorCache[value] = label; setAuthor(String(value)) }
            else filters[key] = String(value)
        }

        watch(() => [filters.author, filters.category, filters.level, filters.action,
                     filters.ip, filters.visibility, filters.date_from, filters.date_to], refetch)

        const visibilityOptions = [
            { value: 'public',  label: 'Public',     icon: 'fa-eye' },
            { value: 'private', label: 'Admin only', icon: 'fa-eye-slash' },
        ]
        const levelOptions = LEVELS.map(l => ({ ...l, icon: 'fa-circle' }))

        const chips = computed(() => {
            const c = []
            if (filters.author)     c.push({ key: 'author',     label: 'author',     value: filters.authorLabel })
            if (filters.category)   c.push({ key: 'category',   label: 'category',   value: filters.category })
            if (filters.level)      c.push({ key: 'level',      label: 'level',      value: filters.level })
            if (filters.action)     c.push({ key: 'action',     label: 'action',     value: filters.action })
            if (filters.ip)         c.push({ key: 'ip',         label: 'ip',         value: filters.ip })
            if (filters.visibility) c.push({ key: 'visibility', label: 'visibility', value: filters.visibility === 'public' ? 'public' : 'admin only' })
            if (filters.date_from)  c.push({ key: 'date_from',  label: 'from',       value: filters.date_from })
            if (filters.date_to)    c.push({ key: 'date_to',    label: 'to',         value: filters.date_to })
            return c
        })
        function removeChip(key) { filters[key] = ''; if (key === 'author') filters.authorLabel = '' }
        function clearAll() {
            Object.keys(filters).forEach(k => { filters[k] = '' })
            if (search.value) { search.value = ''; refetch() }
        }
        const hasFilters = computed(() => chips.value.length > 0 || !!search.value)

        // ── Sort ──────────────────────────────────────────────────────────────
        const sortValue = computed({
            get: () => `${sort_key.value}:${sort_dir.value}`,
            set: (v) => {
                const [k, d] = (v || 'created_at:desc').split(':')
                sort_key.value = k; sort_dir.value = d; refetch()
            },
        })
        const sortOptions = SORTS.map(s => ({ value: `${s.key}:${s.dir}`, label: s.label }))
        const sortLabel = computed(() => (SORTS.find(s => `${s.key}:${s.dir}` === sortValue.value) || SORTS[0]).label)
        function toggleDateSort() { sortValue.value = sort_dir.value === 'desc' && sort_key.value === 'created_at' ? 'created_at:asc' : 'created_at:desc' }

        // ── Search ────────────────────────────────────────────────────────────
        let _searchTimer = null
        function onSearch() { clearTimeout(_searchTimer); _searchTimer = setTimeout(refetch, 300) }
        function clearSearch() { search.value = ''; refetch() }

        function onPerPageChange() { refetch() }
        function scrollToTop() {
            const el = rootEl.value
            if (!el) return
            const top = el.getBoundingClientRect().top + window.scrollY - 80
            if (window.scrollY > top) window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
        }
        function handlePageChange(p) { page.value = p; fetchData(); scrollToTop() }

        function shortPath(url) {
            if (!url) return ''
            try { const u = new URL(url, location.origin); return u.pathname + u.search } catch { return url }
        }

        // ── Expand: a click anywhere on the row, except on its controls ───────
        function onRowClick(e, uuid) {
            if (e.target.closest('button, a, input, select, label, .ipa')) return
            if (window.getSelection && String(window.getSelection()).length) return  // selecting text
            expanded_id.value = expanded_id.value === uuid ? null : uuid
        }

        // ── Selection ─────────────────────────────────────────────────────────
        const all_page_selected = computed(() =>
            items.value.length > 0 && items.value.every(i => selected.value.has(i.uuid)))
        function toggleAll() {
            const next = new Set(selected.value)
            if (all_page_selected.value) items.value.forEach(i => next.delete(i.uuid))
            else items.value.forEach(i => next.add(i.uuid))
            selected.value = next
        }
        function toggleOne(uuid) {
            const next = new Set(selected.value)
            next.has(uuid) ? next.delete(uuid) : next.add(uuid)
            selected.value = next
        }
        function clearSelection() { selected.value = new Set() }

        // ── Emit events ───────────────────────────────────────────────────────
        function requestDelete(log) { emit('delete', log) }
        function requestBulkDelete() { emit('bulk-delete', [...selected.value]) }
        function requestEdit(log) { emit('edit', log) }
        function requestToggleVisibility(log) { togglingUuid.value = log.uuid; emit('toggle-visibility', log) }
        function requestBulkVisibility(isPublic) { emit('bulk-set-visibility', [...selected.value], isPublic) }

        onMounted(() => fetchData())
        expose({ fetchData })

        return {
            items, total, total_pages, loading, page, per_page, search, filters, rootEl, shortPath,
            expanded_id, selected, all_page_selected, togglingUuid, colCount,
            sort_key, sort_dir, sortValue, sortOptions, sortLabel, toggleDateSort,
            visibilityOptions, levelOptions, chips, hasFilters,
            loadUsersCached, loadActions, loadCategories, loadIps, setAuthor, filterBy,
            removeChip, clearAll,
            getCategoryIcon, getInitials, targetUrl, targetLabel, formatRelative, formatFull,
            fetchData, onSearch, clearSearch, onPerPageChange, handlePageChange, onRowClick,
            toggleAll, toggleOne, clearSelection,
            requestDelete, requestBulkDelete, requestEdit,
            requestToggleVisibility, requestBulkVisibility,
        }
    },

    template: `
<div class="lt-root" ref="rootEl">

    <!-- Search bar + date range (above the box, like GitHub) -->
    <div class="lt-topbar">
        <div class="lt-search">
            <i class="fas fa-magnifying-glass lt-search-icon"></i>
            <input class="lt-search-input" type="text" v-model="search" @input="onSearch"
                   placeholder="Search title, action, description, IP…" />
            <button v-if="search" class="lt-search-clear" @click="clearSearch" title="Clear search">
                <i class="fas fa-xmark"></i>
            </button>
        </div>
        <div class="lt-date-range" title="Date range">
            <i class="fas fa-calendar-days lt-date-icon"></i>
            <input type="date" class="lt-date-input" v-model="filters.date_from" title="From date" />
            <span class="lt-date-sep">→</span>
            <input type="date" class="lt-date-input" v-model="filters.date_to" title="To date" />
        </div>
    </div>

    <!-- Active filters -->
    <div v-if="hasFilters" class="lt-chips">
        <span v-for="c in chips" :key="c.key" class="lt-chip">
            <span class="lt-chip-key">{{ c.label }}:</span>{{ c.value }}
            <button type="button" @click="removeChip(c.key)" :title="'Remove ' + c.label"><i class="fas fa-xmark"></i></button>
        </span>
        <button type="button" class="lt-chips-clear" @click="clearAll">
            <i class="fas fa-circle-xmark"></i> Clear filters and search
        </button>
    </div>

    <div class="lt-wrapper">
        <div v-if="loading" class="lt-loading-bar"></div>

        <!-- Box header: count + filter menus, or bulk actions when rows are selected -->
        <div class="lt-boxhead">
            <label v-if="canDelete" class="lt-boxhead-check" title="Select the page">
                <input type="checkbox" class="lt-checkbox" :checked="all_page_selected" @change="toggleAll" />
            </label>

            <template v-if="selected.size === 0">
                <span class="lt-count"><i class="fas fa-scroll"></i> <strong>{{ total.toLocaleString() }}</strong> log{{ total !== 1 ? 's' : '' }}</span>
                <div class="lt-menus">
                    <lt-filter-menu label="Author" :model-value="filters.author" @update:model-value="setAuthor"
                                    :load="loadUsersCached" placeholder="Filter users">
                        <template #before="{ pick }">
                            <button type="button" class="lt-menu-item" :class="{ 'is-selected': filters.author === 'system' }" @click="pick('system')">
                                <i class="fas fa-check lt-menu-check"></i><i class="fas fa-gear lt-menu-icon"></i>
                                <span class="lt-menu-label">System</span>
                            </button>
                            <button type="button" class="lt-menu-item" :class="{ 'is-selected': filters.author === 'anonymous' }" @click="pick('anonymous')">
                                <i class="fas fa-check lt-menu-check"></i><i class="fas fa-user-secret lt-menu-icon"></i>
                                <span class="lt-menu-label">Anonymous</span>
                            </button>
                            <div class="lt-menu-divider"></div>
                        </template>
                    </lt-filter-menu>
                    <lt-filter-menu v-if="!hideCategoryFilter" label="Category" v-model="filters.category"
                                    :load="loadCategories" placeholder="Filter categories"></lt-filter-menu>
                    <lt-filter-menu label="Action" v-model="filters.action" :load="loadActions"
                                    placeholder="Filter actions (e.g. rule.)"></lt-filter-menu>
                    <lt-filter-menu label="Level" v-model="filters.level" :options="levelOptions"></lt-filter-menu>
                    <lt-filter-menu label="IP" v-model="filters.ip" :load="loadIps" placeholder="IP or prefix"
                                    title="Filter by IP address"></lt-filter-menu>
                    <lt-filter-menu v-if="canModerate" label="Visibility" v-model="filters.visibility"
                                    :options="visibilityOptions"></lt-filter-menu>
                    <lt-filter-menu :label="'Sort: ' + sortLabel" title="Sort by" v-model="sortValue"
                                    :options="sortOptions"></lt-filter-menu>
                </div>
            </template>

            <template v-else>
                <span class="lt-count"><strong>{{ selected.size }}</strong> selected</span>
                <div class="lt-menus">
                    <button v-if="canModerate" class="lt-bulk-btn" @click="requestBulkVisibility(true)">
                        <i class="fa-solid fa-eye"></i> Set public
                    </button>
                    <button v-if="canModerate" class="lt-bulk-btn" @click="requestBulkVisibility(false)">
                        <i class="fa-solid fa-eye-slash"></i> Set admin only
                    </button>
                    <button v-if="canDelete" class="lt-bulk-btn lt-bulk-btn--danger" @click="requestBulkDelete">
                        <i class="fas fa-trash-can"></i> Delete
                    </button>
                    <button class="lt-bulk-btn lt-bulk-btn--clear" @click="clearSelection">
                        <i class="fas fa-xmark"></i> Clear
                    </button>
                </div>
            </template>
        </div>

        <div class="lt-table-wrap">
            <table class="lt-table">
                <colgroup>
                    <col v-if="canDelete" style="width:38px">
                    <col style="width:4px">
                    <col>
                    <col style="width:118px">
                    <col style="width:150px">
                    <col style="width:175px">
                    <col style="width:170px">
                    <col style="width:190px">
                    <col v-if="canModerate" style="width:96px">
                    <col style="width:92px">
                    <col style="width:84px">
                </colgroup>
                <thead class="lt-thead">
                    <tr>
                        <th v-if="canDelete" class="lt-th"></th>
                        <th class="lt-th" style="padding:0"></th>
                        <th class="lt-th">Event</th>
                        <th class="lt-th">Category</th>
                        <th class="lt-th">Actor</th>
                        <th class="lt-th">IP address</th>
                        <th class="lt-th">Target</th>
                        <th class="lt-th">Request</th>
                        <th v-if="canModerate" class="lt-th">Visibility</th>
                        <th class="lt-th lt-th--sortable" :class="{ 'lt-th--sorted': sort_key === 'created_at' }" @click="toggleDateSort">
                            <span class="lt-th-inner">Date
                                <i :class="['fas', sort_key !== 'created_at' ? 'fa-sort' : (sort_dir === 'asc' ? 'fa-sort-up' : 'fa-sort-down'), 'lt-th-sort-icon']"></i>
                            </span>
                        </th>
                        <th class="lt-th"></th>
                    </tr>
                </thead>

                <tbody>
                    <tr v-if="!items.length && !loading">
                        <td :colspan="colCount" class="lt-empty">
                            <i class="fas fa-scroll lt-empty-icon"></i>
                            <div class="lt-empty-text">No logs match these filters</div>
                            <button v-if="hasFilters" class="btn btn-sm btn-link" @click="clearAll">Clear filters</button>
                        </td>
                    </tr>

                    <template v-for="log in items" :key="log.uuid">
                        <tr class="lt-row"
                            :class="{
                                'lt-row--selected': selected.has(log.uuid),
                                'lt-row--open':     expanded_id === log.uuid,
                                'lt-row--error':    log.level === 'error',
                                'lt-row--warning':  log.level === 'warning',
                            }"
                            @click="onRowClick($event, log.uuid)">

                            <td v-if="canDelete" class="lt-td lt-td--check">
                                <input type="checkbox" class="lt-checkbox" :checked="selected.has(log.uuid)" @change="toggleOne(log.uuid)" />
                            </td>

                            <td class="lt-td lt-td--level">
                                <span :class="['lt-level-bar', 'lt-level-bar--' + log.level]" :title="log.level"></span>
                            </td>

                            <td class="lt-td lt-td--event">
                                <span class="lt-event-title" :title="log.title || log.description">{{ log.title || log.action }}</span>
                                <button type="button" class="lt-event-action" @click="filterBy('action', log.action)" :title="'Only ' + log.action">{{ log.action }}</button>
                            </td>

                            <td class="lt-td lt-td--cat">
                                <button type="button" :class="['lt-category-badge', 'lt-category-badge--' + log.category]"
                                        @click="filterBy('category', log.category)" :title="'Only ' + log.category">
                                    <i :class="['fas', getCategoryIcon(log.category)]"></i>{{ log.category }}
                                </button>
                            </td>

                            <td class="lt-td lt-td--actor">
                                <span v-if="log.user_id" class="lt-actor-chip">
                                    <user-chip :user-id="log.user_id" :username="log.actor_name" :avatar="log.actor_avatar" size="xs"></user-chip>
                                    <button type="button" class="lt-ip-filter" @click="filterBy('author', log.user_id, log.actor_name)" title="Only this author">
                                        <i class="fas fa-filter"></i>
                                    </button>
                                </span>
                                <button v-else type="button" class="lt-actor"
                                        :title="'Only ' + (log.actor_name || 'System')"
                                        @click="log.user_id ? filterBy('author', log.user_id, log.actor_name) : filterBy('author', log.ip_address ? 'anonymous' : 'system', log.actor_name)">
                                    <span class="lt-actor-avatar" :class="{ 'lt-actor-avatar--none': !log.user_id }">
                                        <i v-if="!log.user_id" :class="['fas', log.ip_address ? 'fa-user-secret' : 'fa-gear']"></i>
                                        <template v-else>{{ getInitials(log.actor_name) }}</template>
                                    </span>
                                    <span class="lt-actor-name">{{ log.actor_name || 'System' }}</span>
                                </button>
                            </td>

                            <td class="lt-td lt-td--ip" data-label="IP">
                                <span v-if="log.ip_address" class="lt-ip">
                                    <ip-address :ip="log.ip_address"></ip-address>
                                    <button type="button" class="lt-ip-filter" @click="filterBy('ip', log.ip_address)" title="Only this IP">
                                        <i class="fas fa-filter"></i>
                                    </button>
                                </span>
                                <span v-else class="lt-muted">—</span>
                            </td>

                            <td class="lt-td lt-td--target" data-label="Target">
                                <span v-if="log.target_type" class="lt-target-cell">
                                    <span class="lt-target" :title="targetLabel(log.target_type) + (log.target_id ? ' #' + log.target_id : '')">
                                        <i :class="['fas', getCategoryIcon(log.target_type)]"></i>{{ targetLabel(log.target_type) }}<span v-if="log.target_id" class="lt-muted"> #{{ log.target_id }}</span>
                                    </span>
                                    <a v-if="targetUrl(log)" :href="targetUrl(log)" target="_blank" rel="noopener"
                                       class="lt-goto" :title="'Go to this ' + targetLabel(log.target_type).toLowerCase()">
                                        Go to <i class="fas fa-arrow-up-right-from-square"></i>
                                    </a>
                                </span>
                                <span v-else class="lt-muted">—</span>
                            </td>

                            <td class="lt-td lt-td--req" data-label="Request">
                                <span v-if="log.url" class="lt-req" :title="(log.method || '') + ' ' + log.url">
                                    <span v-if="log.method" :class="['lt-method', 'lt-method--' + log.method.toLowerCase()]">{{ log.method }}</span>{{ shortPath(log.url) }}
                                </span>
                                <span v-else class="lt-muted">—</span>
                            </td>

                            <td v-if="canModerate" class="lt-td lt-td--vis">
                                <button type="button" class="lt-vis-btn"
                                        :class="log.is_public ? 'lt-vis-btn--public' : 'lt-vis-btn--private'"
                                        :disabled="togglingUuid === log.uuid"
                                        :title="log.is_public ? 'Click to make admin-only' : 'Click to make public'"
                                        @click="requestToggleVisibility(log)">
                                    <i :class="log.is_public ? 'fa-solid fa-eye' : 'fa-solid fa-eye-slash'"></i>
                                    {{ log.is_public ? 'Public' : 'Private' }}
                                </button>
                            </td>

                            <td class="lt-td lt-td--date" :title="formatFull(log.created_at)">{{ formatRelative(log.created_at) }}</td>

                            <td class="lt-td lt-td--actions">
                                <button class="lt-icon-btn" @click="requestEdit(log)" title="Edit"><i class="fas fa-pen"></i></button>
                                <button v-if="canDelete" class="lt-icon-btn lt-icon-btn--danger" @click="requestDelete(log)" title="Delete"><i class="fas fa-trash-can"></i></button>
                                <i class="fas fa-chevron-right lt-chevron" :class="{ 'is-open': expanded_id === log.uuid }"></i>
                            </td>
                        </tr>

                        <tr v-if="expanded_id === log.uuid" class="lt-row-expand">
                            <td :colspan="colCount" class="lt-expand-cell">
                                <div class="lt-expand-content">
                                    <div class="lt-expand-grid">
                                        <div class="lt-expand-field">
                                            <span class="lt-expand-label">UUID</span>
                                            <span class="lt-expand-value lt-mono">{{ log.uuid }}</span>
                                        </div>
                                        <div class="lt-expand-field">
                                            <span class="lt-expand-label">Created at</span>
                                            <span class="lt-expand-value lt-mono">{{ formatFull(log.created_at) }}</span>
                                        </div>
                                        <div class="lt-expand-field">
                                            <span class="lt-expand-label">Level</span>
                                            <span class="lt-expand-value" style="text-transform:capitalize;">{{ log.level }}</span>
                                        </div>
                                        <div class="lt-expand-field" v-if="log.target_type">
                                            <span class="lt-expand-label">Target</span>
                                            <span class="lt-expand-value lt-mono">
                                                {{ targetLabel(log.target_type) }}<template v-if="log.target_id"> #{{ log.target_id }}</template>
                                                <a v-if="targetUrl(log)" :href="targetUrl(log)" target="_blank" rel="noopener" class="lt-goto ms-1">Go to <i class="fas fa-arrow-up-right-from-square"></i></a>
                                            </span>
                                        </div>
                                        <div class="lt-expand-field" v-if="log.user_id">
                                            <span class="lt-expand-label">Actor profile</span>
                                            <a class="lt-expand-value" :href="'/account/detail_user/' + log.user_id" target="_blank">{{ log.actor_name }} <i class="fas fa-arrow-up-right-from-square" style="font-size:.6rem"></i></a>
                                        </div>
                                        <div class="lt-expand-field">
                                            <span class="lt-expand-label">Visibility</span>
                                            <span class="lt-expand-value">{{ log.is_public ? 'Public' : 'Admin only' }}</span>
                                        </div>
                                    </div>

                                    <div v-if="log.description" class="lt-expand-field">
                                        <span class="lt-expand-label">Description</span>
                                        <p class="lt-expand-desc">{{ log.description }}</p>
                                    </div>
                                    <div v-if="log.url" class="lt-expand-field">
                                        <span class="lt-expand-label">Request</span>
                                        <p class="lt-expand-desc lt-mono">{{ log.method }} {{ log.url }}</p>
                                    </div>
                                    <div v-if="log.user_agent" class="lt-expand-field">
                                        <span class="lt-expand-label">User agent</span>
                                        <p class="lt-expand-desc lt-mono">{{ log.user_agent }}</p>
                                    </div>
                                    <div v-if="log.extra" class="lt-expand-field">
                                        <span class="lt-expand-label">Extra data</span>
                                        <code-viewer :code="JSON.stringify(log.extra, null, 2)" language="json"
                                                     max-height="320px" :show-lines="false"></code-viewer>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>

        <div class="lt-footer">
            <span class="lt-info">
                {{ total.toLocaleString() }} log{{ total !== 1 ? 's' : '' }}
                <template v-if="total > per_page"> — page {{ page }} / {{ total_pages }}</template>
            </span>
            <div class="lt-footer-right">
                <div class="lt-per-page">
                    <span>Per page</span>
                    <select class="lt-per-page-select" v-model.number="per_page" @change="onPerPageChange">
                        <option>10</option><option>25</option><option>50</option><option>100</option>
                    </select>
                </div>
                <pagination-component :current-page="page" :total-pages="total_pages" @change-page="handlePageChange"></pagination-component>
            </div>
        </div>
    </div>
</div>
    `,
}
