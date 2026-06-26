/**
 * formatList.js — Admin rule format manager component.
 * Card + table view, search, create modal, rename section, delete confirm.
 * All-in-one, no external imports beyond PaginationComponent.
 *
 * Expose: fetchData()
 */
import PaginationComponent from '/static/js/rule/paginationComponent.js'

const { ref, computed, onMounted } = Vue

export default {
    name: 'FormatList',
    components: { PaginationComponent },
    expose: ['fetchData'],

    props: {
        csrfToken: { type: String, default: '' },
    },

    template: `
    <div class="fl-wrapper">

        <!-- ── Toolbar ── -->
        <div class="fl-toolbar">
            <div class="fl-toolbar-left">
                <div class="dt-search">
                    <i class="fas fa-search dt-search-icon"></i>
                    <input class="dt-search-input" type="text" v-model="search"
                           placeholder="Search formats…" @input="onSearchInput" />
                    <button v-if="search" class="dt-search-clear" @click="clearSearch">
                        <i class="fas fa-xmark"></i>
                    </button>
                </div>
                <span v-if="!loading" class="text-muted small ms-2 text-nowrap">
                    <strong>{{ total }}</strong> format<span v-if="total !== 1">s</span>
                </span>
            </div>
            <div class="fl-toolbar-right">
                <!-- View toggle -->
                <div class="dt-view-toggle">
                    <button class="dt-view-btn" :class="{ 'dt-view-btn--active': viewMode === 'card' }"
                            @click="viewMode = 'card'">
                        <i class="fas fa-grip"></i>
                    </button>
                    <button class="dt-view-btn" :class="{ 'dt-view-btn--active': viewMode === 'table' }"
                            @click="viewMode = 'table'">
                        <i class="fas fa-table-cells-large"></i>
                    </button>
                </div>
                <!-- Per page (table) -->
                <div v-if="viewMode === 'table'" class="rl-per-page">
                    <span>Rows</span>
                    <select v-model="perPageModel">
                        <option v-for="n in [10, 20, 50]" :key="n" :value="n">{{ n }}</option>
                    </select>
                </div>
                <!-- Create button -->
                <button class="btn btn-primary btn-sm rounded-pill px-3" @click="openCreate">
                    <i class="fas fa-plus me-1"></i>New Format
                </button>
            </div>
        </div>

        <!-- ── Loading ── -->
        <div v-if="loading" class="rl-loading">
            <div class="spinner-border text-primary"></div>
        </div>

        <!-- ── Empty ── -->
        <div v-else-if="items.length === 0" class="rl-empty">
            <div class="rl-empty-icon"><i class="fas fa-file-code"></i></div>
            <p class="mb-1">No formats found.</p>
            <button class="btn btn-sm btn-outline-primary rounded-pill" @click="openCreate">
                <i class="fas fa-plus me-1"></i>Create one
            </button>
        </div>

        <!-- ═══════ CARD VIEW ═══════ -->
        <div v-else-if="viewMode === 'card'" class="fl-cards">
            <div v-for="fmt in items" :key="fmt.id" class="fl-format-card">
                <div class="fl-card-accent"></div>
                <div class="fl-card-top">
                    <div class="fl-card-icon">
                        <i class="fas fa-file-code"></i>
                    </div>
                    <div class="fl-card-badges">
                        <span v-if="fmt.can_be_execute" class="badge bg-success-subtle text-success border border-success-subtle">
                            <i class="fas fa-play me-1"></i>Executable
                        </span>
                        <span v-else class="badge bg-secondary-subtle text-secondary border border-secondary-subtle">
                            <i class="fas fa-ban me-1"></i>Read-only
                        </span>
                    </div>
                </div>
                <div class="fl-card-name">{{ fmt.name }}</div>
                <div class="fl-card-meta">
                    <span class="fl-meta-item">
                        <i class="fas fa-file-shield"></i>
                        {{ fmt.number_of_rule_with_this_format }} rule<span v-if="fmt.number_of_rule_with_this_format !== 1">s</span>
                    </span>
                    <span class="fl-meta-item">
                        <i class="fas fa-calendar"></i>
                        {{ fmt.creation_date }}
                    </span>
                </div>
                <div class="fl-card-actions">
                    <button class="fl-action-delete" @click="askDelete(fmt)" title="Delete format">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>

        <!-- ═══════ TABLE VIEW ═══════ -->
        <div v-else class="dt-table-wrap">
            <table class="dt-table">
                <thead class="dt-thead">
                    <tr>
                        <th class="dt-th" style="width:50px;">
                            <div class="dt-th-inner dt-th--sortable"
                                 :class="{'dt-th--sorted': sortKey==='id'}" @click="setSort('id')">
                                ID <i class="fas dt-sort-icon" :class="sortIcon('id')"></i>
                            </div>
                        </th>
                        <th class="dt-th">
                            <div class="dt-th-inner dt-th--sortable"
                                 :class="{'dt-th--sorted': sortKey==='name'}" @click="setSort('name')">
                                Name <i class="fas dt-sort-icon" :class="sortIcon('name')"></i>
                            </div>
                        </th>
                        <th class="dt-th" style="width:120px;">Executable</th>
                        <th class="dt-th" style="width:100px;">Rules</th>
                        <th class="dt-th dt-th--sortable" style="width:155px;"
                            :class="{'dt-th--sorted': sortKey==='creation_date'}"
                            @click="setSort('creation_date')">
                            <div class="dt-th-inner">
                                Created <i class="fas dt-sort-icon" :class="sortIcon('creation_date')"></i>
                            </div>
                        </th>
                        <th class="dt-th dt-th--actions" style="width:80px;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="fmt in items" :key="fmt.id" class="dt-row">
                        <td class="dt-td" style="color:var(--subtle-text-color);font-size:.78rem;">{{ fmt.id }}</td>
                        <td class="dt-td">
                            <span class="fw-600" style="font-size:.9rem;">{{ fmt.name }}</span>
                        </td>
                        <td class="dt-td">
                            <span v-if="fmt.can_be_execute" class="badge bg-success-subtle text-success border border-success-subtle">
                                <i class="fas fa-play me-1"></i>Yes
                            </span>
                            <span v-else class="text-muted small">No</span>
                        </td>
                        <td class="dt-td" style="font-weight:600;font-size:.85rem;">
                            {{ fmt.number_of_rule_with_this_format }}
                        </td>
                        <td class="dt-td" style="font-size:.78rem;white-space:nowrap;color:var(--subtle-text-color);">
                            {{ fmt.creation_date }}
                        </td>
                        <td class="dt-td dt-td--actions">
                            <div class="dt-actions">
                                <button class="dt-action-btn dt-action-btn--danger"
                                        title="Delete" @click="askDelete(fmt)">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- ── Footer ── -->
        <div v-if="!loading && items.length > 0" class="rl-footer">
            <div v-if="viewMode === 'card'" class="rl-per-page">
                <span>Per page</span>
                <select v-model="perPageModel">
                    <option v-for="n in [8, 16, 32]" :key="n" :value="n">{{ n }}</option>
                </select>
            </div>
            <div v-else style="width:1px;"></div>
            <div style="flex-grow:1;display:flex;justify-content:center;">
                <pagination-component :current-page="page" :total-pages="totalPages"
                                      @change-page="goToPage"></pagination-component>
            </div>
            <div class="rl-footer-info">{{ footerInfo }}</div>
        </div>

        <!-- ═══════ RENAME SECTION ═══════ (hidden by default) -->
        <div class="fl-rename-section mt-4">
            <button class="fl-rename-toggle" @click="renameOpen = !renameOpen">
                <div class="fl-rename-toggle-left">
                    <i class="fas fa-pen-to-square me-2 text-warning"></i>
                    <span>Bulk rename a format</span>
                    <span class="fl-rename-badge">Advanced</span>
                </div>
                <i class="fas transition-icon" :class="renameOpen ? 'fa-chevron-up' : 'fa-chevron-down'" style="color:var(--subtle-text-color);"></i>
            </button>
            <div v-show="renameOpen" class="fl-rename-body">
                <p class="text-warning small mb-3">
                    <i class="fas fa-triangle-exclamation me-1"></i>
                    This renames the format on <strong>every matching rule</strong>. No undo — double-check the names.
                </p>
                <div class="row g-3 align-items-end">
                    <div class="col-md-5">
                        <label class="form-label small fw-600">Current format name</label>
                        <input type="text" class="form-control form-control-sm" v-model="renameCurrent"
                               placeholder="e.g. Sigma" />
                    </div>
                    <div class="col-md-1 text-center pb-1" style="font-size:1.2rem;color:var(--subtle-text-color);">
                        <i class="fas fa-arrow-right"></i>
                    </div>
                    <div class="col-md-5">
                        <label class="form-label small fw-600">New format name</label>
                        <input type="text" class="form-control form-control-sm" v-model="renameNew"
                               placeholder="e.g. sigma" />
                    </div>
                    <div class="col-md-1">
                        <button class="btn btn-warning btn-sm w-100" :disabled="renameWorking || !renameCurrent.trim() || !renameNew.trim()"
                                @click="doRename">
                            <span v-if="renameWorking" class="spinner-border spinner-border-sm"></span>
                            <i v-else class="fas fa-sync-alt"></i>
                        </button>
                    </div>
                </div>
                <div v-if="renameMsg" class="alert mt-2 py-2 small"
                     :class="renameOk ? 'alert-success' : 'alert-danger'">
                    {{ renameMsg }}
                </div>
            </div>
        </div>

        <!-- ═══════ CREATE MODAL ═══════ -->
        <teleport to="body">
            <div class="modal fade" id="fl-createModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-sm">
                    <div class="modal-content border-0 shadow-lg" style="border-radius:16px;">
                        <div class="modal-header border-0 pb-0">
                            <h6 class="modal-title fw-bold">
                                <i class="fas fa-plus-circle me-2 text-primary"></i>New Format
                            </h6>
                            <button class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body pb-2">
                            <div class="mb-3">
                                <label class="form-label small fw-600">Format name <span class="text-danger">*</span></label>
                                <input ref="createNameInput" type="text" class="form-control"
                                       v-model="createName" placeholder="e.g. yara"
                                       @keydown.enter="doCreate" />
                                <div v-if="createError" class="text-danger small mt-1">{{ createError }}</div>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="fl-canExec" v-model="createExec">
                                <label class="form-check-label small" for="fl-canExec">Can be executed</label>
                            </div>
                        </div>
                        <div class="modal-footer border-0 pt-0 justify-content-end gap-2">
                            <button class="btn btn-light rounded-pill px-4 btn-sm" data-bs-dismiss="modal">Cancel</button>
                            <button class="btn btn-primary rounded-pill px-4 btn-sm"
                                    :disabled="createWorking || !createName.trim()" @click="doCreate">
                                <span v-if="createWorking" class="spinner-border spinner-border-sm me-1"></span>
                                <i v-else class="fas fa-plus me-1"></i>Create
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </teleport>

        <!-- ═══════ DELETE CONFIRM MODAL ═══════ -->
        <teleport to="body">
            <div class="modal fade" id="fl-deleteModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-sm">
                    <div class="modal-content border-0 shadow-lg" style="border-radius:16px;">
                        <div class="modal-header border-0 pb-0">
                            <h6 class="modal-title fw-bold text-danger">
                                <i class="fas fa-triangle-exclamation me-2"></i>Delete Format
                            </h6>
                            <button class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center py-3">
                            <div class="text-danger mb-2" style="font-size:2rem;"><i class="fas fa-trash-can"></i></div>
                            <p class="mb-1">Delete format <strong>{{ deleteTarget?.name }}</strong>?</p>
                            <p v-if="deleteTarget?.number_of_rule_with_this_format > 0"
                               class="text-warning small mb-0">
                                <i class="fas fa-exclamation-circle me-1"></i>
                                {{ deleteTarget.number_of_rule_with_this_format }} rule<span v-if="deleteTarget.number_of_rule_with_this_format > 1">s</span>
                                will lose their format assignment.
                            </p>
                        </div>
                        <div class="modal-footer border-0 pt-0 justify-content-center gap-2">
                            <button class="btn btn-light rounded-pill px-4 btn-sm" data-bs-dismiss="modal">Cancel</button>
                            <button class="btn btn-danger rounded-pill px-4 btn-sm"
                                    :disabled="deleteWorking" @click="doDelete">
                                <span v-if="deleteWorking" class="spinner-border spinner-border-sm me-1"></span>
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </teleport>

    </div>
    `,

    setup(props) {
        // ── State ─────────────────────────────────────────────────────────
        const items      = ref([])
        const total      = ref(0)
        const totalPages = ref(1)
        const loading    = ref(false)
        const viewMode   = ref('table')
        const page       = ref(1)
        const sortKey    = ref('creation_date')
        const sortDir    = ref('desc')
        const cardPP     = ref(16)
        const tablePP    = ref(20)
        const perPage    = computed(() => viewMode.value === 'table' ? tablePP.value : cardPP.value)
        const perPageModel = computed({
            get: () => perPage.value,
            set: val => {
                if (viewMode.value === 'table') tablePP.value = Number(val)
                else                            cardPP.value  = Number(val)
                page.value = 1; fetchData()
            },
        })
        const search     = ref('')
        const footerInfo = computed(() => {
            if (total.value === 0) return ''
            const s = (page.value - 1) * perPage.value + 1
            const e = Math.min(page.value * perPage.value, total.value)
            return `${s}–${e} of ${total.value}`
        })

        // ── Fetch ─────────────────────────────────────────────────────────
        async function fetchData() {
            loading.value = true
            try {
                const p = new URLSearchParams({ page: page.value, per_page: perPage.value })
                if (search.value) p.set('search', search.value)
                if (sortKey.value) { p.set('sort', sortKey.value); p.set('dir', sortDir.value) }
                const res  = await fetch(`/rule/formats_data_table?${p}`)
                const data = await res.json()
                items.value      = data.items      ?? []
                total.value      = data.total      ?? 0
                totalPages.value = data.total_pages ?? 1
                if (page.value > totalPages.value && totalPages.value > 0)
                    page.value = totalPages.value
            } finally {
                loading.value = false
            }
        }

        // ── Search + sort ─────────────────────────────────────────────────
        let _st = null
        function onSearchInput() { clearTimeout(_st); _st = setTimeout(() => { page.value = 1; fetchData() }, 340) }
        function clearSearch()   { search.value = ''; page.value = 1; fetchData() }
        function setSort(key) {
            if (sortKey.value === key) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
            else { sortKey.value = key; sortDir.value = 'desc' }
            page.value = 1; fetchData()
        }
        function sortIcon(key) {
            if (sortKey.value !== key) return 'fa-sort'
            return sortDir.value === 'asc' ? 'fa-sort-up' : 'fa-sort-down'
        }
        function goToPage(p) { page.value = p; fetchData() }

        // ── Create ────────────────────────────────────────────────────────
        const createName  = ref('')
        const createExec  = ref(false)
        const createError = ref('')
        const createWorking = ref(false)
        const createNameInput = ref(null)
        let _createModal  = null

        function openCreate() {
            createName.value = ''; createExec.value = false; createError.value = ''
            _createModal = _createModal || new bootstrap.Modal(document.getElementById('fl-createModal'))
            _createModal.show()
            setTimeout(() => createNameInput.value?.focus(), 300)
        }

        async function doCreate() {
            if (!createName.value.trim()) return
            createWorking.value = true; createError.value = ''
            try {
                const res  = await fetch('/rule/create_format_json', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ name: createName.value.trim(), can_be_execute: createExec.value }),
                })
                const data = await res.json()
                if (data.success) {
                    _createModal?.hide()
                    fetchData()
                    if (window.create_message) window.create_message('Format created!', 'success-subtle')
                } else {
                    createError.value = data.message || 'Error creating format'
                }
            } catch { createError.value = 'Network error' }
            finally  { createWorking.value = false }
        }

        // ── Delete ────────────────────────────────────────────────────────
        const deleteTarget  = ref(null)
        const deleteWorking = ref(false)
        let   _deleteModal  = null

        function askDelete(fmt) {
            deleteTarget.value = fmt
            _deleteModal = _deleteModal || new bootstrap.Modal(document.getElementById('fl-deleteModal'))
            _deleteModal.show()
        }

        async function doDelete() {
            if (!deleteTarget.value) return
            deleteWorking.value = true
            try {
                const res  = await fetch(`/rule/delete_format_rule?id=${deleteTarget.value.id}`)
                const data = await res.json()
                if (window.create_message) window.create_message(data.message || 'Done', data.toast_class || 'success-subtle')
                if (res.ok && data.success) {
                    _deleteModal?.hide()
                    fetchData()
                }
            } catch { if (window.create_message) window.create_message('Network error', 'danger-subtle') }
            finally  { deleteWorking.value = false; deleteTarget.value = null }
        }

        // ── Rename ────────────────────────────────────────────────────────
        const renameOpen    = ref(false)
        const renameCurrent = ref('')
        const renameNew     = ref('')
        const renameWorking = ref(false)
        const renameMsg     = ref('')
        const renameOk      = ref(false)

        async function doRename() {
            renameWorking.value = true; renameMsg.value = ''
            try {
                const res  = await fetch('/rule/rename_format_json', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ current_format: renameCurrent.value.trim(), new_format: renameNew.value.trim() }),
                })
                const data = await res.json()
                renameOk.value  = data.success
                renameMsg.value = data.message || (data.success ? 'Done' : 'Error')
                if (data.success) { renameCurrent.value = ''; renameNew.value = ''; fetchData() }
            } catch { renameOk.value = false; renameMsg.value = 'Network error' }
            finally  { renameWorking.value = false }
        }

        onMounted(fetchData)

        return {
            items, total, totalPages, loading, viewMode, page,
            perPage, perPageModel, search, footerInfo, sortKey, sortDir,
            onSearchInput, clearSearch, setSort, sortIcon, goToPage,
            createName, createExec, createError, createWorking, createNameInput,
            openCreate, doCreate,
            deleteTarget, deleteWorking, askDelete, doDelete,
            renameOpen, renameCurrent, renameNew, renameWorking, renameMsg, renameOk, doRename,
            fetchData,
        }
    },
}
