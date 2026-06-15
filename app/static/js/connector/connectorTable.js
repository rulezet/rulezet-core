/**
 * connectorTable.js — Connector management table/card component
 *
 * Props:
 *   isAdmin      Boolean  — show Pull button and bulk-pull action
 *   csrfToken    String   — CSRF token for POST requests
 *
 * Emits:
 *   create       — user clicked "Add"
 *   edit(c)      — user clicked Edit on a connector
 *   deleted      — after a connector is deleted (refetch signal)
 *
 * Exposed:
 *   refresh()    — re-fetch connectors (call via template ref)
 */

import PaginationComponent from '/static/js/rule/paginationComponent.js'
import { create_message } from '/static/js/toaster.js'

const { ref, reactive, computed, onMounted, watch } = Vue

// ─── helpers ──────────────────────────────────────────────────────────────────

function statusClass(c) {
    if (!c.is_active)  return 'cnt-status--inactive'
    if (c.last_error)  return 'cnt-status--error'
    if (c.is_verified) return 'cnt-status--ok'
    return 'cnt-status--pending'
}
function statusLabel(c) {
    if (!c.is_active)  return 'Inactive'
    if (c.last_error)  return 'Error'
    if (c.is_verified) return 'Verified'
    return 'Pending'
}
function statusIcon(c) {
    if (!c.is_active)  return 'fa-solid fa-pause'
    if (c.last_error)  return 'fa-solid fa-circle-exclamation'
    if (c.is_verified) return 'fa-solid fa-circle-check'
    return 'fa-solid fa-circle-question'
}
function actionBadgeClass(action) {
    if (!action) return 'bg-secondary'
    if (action.includes('pull_done'))    return 'bg-success'
    if (action.includes('pull_trigger')) return 'bg-primary'
    if (action.includes('test_ok'))      return 'bg-info text-dark'
    if (action.includes('create'))       return 'bg-secondary'
    if (action.includes('delete'))       return 'bg-danger'
    if (action.includes('update'))       return 'bg-warning text-dark'
    return 'bg-secondary'
}
function actionIcon(action) {
    if (!action) return 'fa-solid fa-circle-dot'
    if (action.includes('pull_done'))    return 'fa-solid fa-cloud-arrow-down'
    if (action.includes('pull_trigger')) return 'fa-solid fa-play'
    if (action.includes('test'))         return 'fa-solid fa-wifi'
    if (action.includes('create'))       return 'fa-solid fa-plus'
    if (action.includes('delete'))       return 'fa-solid fa-trash'
    if (action.includes('update'))       return 'fa-solid fa-pen'
    return 'fa-solid fa-circle-dot'
}
function dotClass(action) {
    if (!action) return 'neutral'
    if (action.includes('pull_done'))    return 'success'
    if (action.includes('pull_trigger')) return 'primary'
    if (action.includes('test_ok'))      return 'info'
    if (action.includes('error'))        return 'danger'
    if (action.includes('delete'))       return 'danger'
    if (action.includes('update'))       return 'warning'
    return 'neutral'
}
function _computeStats(items) {
    const pulls         = items.filter(e => e.action?.includes('pull_done')).length
    const tests         = items.filter(e => e.action?.includes('test')).length
    const errors        = items.filter(e => e.action?.includes('error')).length
    const rulesAdded    = items.reduce((s, e) => s + (e.extra?.rules_added    || 0), 0)
    const rulesUpdated  = items.reduce((s, e) => s + (e.extra?.rules_updated  || 0), 0)
    const rulesSkipped  = items.reduce((s, e) => s + (e.extra?.rules_skipped  || 0), 0)
    const bundlesAdded  = items.reduce((s, e) => s + (e.extra?.bundles_added  || 0), 0)
    const lastSync      = items.length ? items[0].timestamp : null

    const dayCounts = {}
    items.forEach(e => {
        const day = (e.timestamp || '').split(' ')[0]
        if (day) dayCounts[day] = (dayCounts[day] || 0) + 1
    })
    const sparkline = []
    for (let i = 29; i >= 0; i--) {
        const d = new Date()
        d.setDate(d.getDate() - i)
        sparkline.push(dayCounts[d.toISOString().split('T')[0]] || 0)
    }
    const maxCount = Math.max(...sparkline, 1)
    return { pulls, tests, errors, rulesAdded, rulesUpdated, rulesSkipped, bundlesAdded, lastSync, sparkline, maxCount }
}

// ─── ConnectorRow (table expanded detail) ─────────────────────────────────────

const _dropdownFixed = {
    mounted(el) {
        if (window.bootstrap?.Dropdown) {
            new window.bootstrap.Dropdown(el, { popperConfig: { strategy: 'fixed' } })
        }
    }
}

const ConnectorRow = {
    delimiters: ['[[', ']]'],
    directives: { dropdownFixed: _dropdownFixed },
    props: {
        c:         { type: Object,  required: true },
        isAdmin:   { type: Boolean, default: false },
        csrfToken: { type: String,  required: true },
        selected:  { type: Boolean, default: false },
    },
    emits: ['toggle-select', 'edit', 'deleted', 'pull-requested'],
    setup(props, { emit }) {
        const expanded       = ref(false)
        const historyLoaded  = ref(false)
        const historyItems   = ref([])
        const historyLoading = ref(false)
        const actionBusy     = ref(null)
        const historyPage    = ref(2)   // number of items currently visible

        const historyStats   = computed(() => _computeStats(historyItems.value))
        const visibleHistory = computed(() => historyItems.value.slice(0, historyPage.value))
        const hasMoreHistory = computed(() => historyPage.value < historyItems.value.length)

        // Missing tag families from the last pull_done entry
        const missingFamilies = computed(() => {
            const last = historyItems.value.find(e => e.action?.includes('pull_done'))
            return (last?.extra?.missing_tag_families || [])
        })
        const selectedFamilies = ref([])
        const importBusy       = ref(false)

        watch(missingFamilies, (families) => { selectedFamilies.value = [...families] }, { immediate: true })

        function loadMoreHistory() { historyPage.value += 5 }

        async function doPost(url, body = {}) {
            return fetch(url, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                body:    JSON.stringify(body),
            })
        }

        async function importFamilies() {
            if (!selectedFamilies.value.length) return
            importBusy.value = true
            try {
                const r    = await doPost('/connector/import_tag_families', { families: selectedFamilies.value })
                const data = await r.json()
                if (data.success) {
                    const ok  = data.results.filter(x => x.ok).map(x => x.family)
                    const err = data.results.filter(x => !x.ok).map(x => x.family)
                    if (ok.length)  create_message(`Imported: ${ok.join(', ')}`, 'success')
                    if (err.length) create_message(`Failed: ${err.join(', ')}`, 'warning')
                    // Remove successfully imported families from the list
                    selectedFamilies.value = err
                } else {
                    create_message(data.error || 'Import failed.', 'danger')
                }
            } finally { importBusy.value = false }
        }

        function toggleFamily(f) {
            const idx = selectedFamilies.value.indexOf(f)
            if (idx >= 0) selectedFamilies.value.splice(idx, 1)
            else selectedFamilies.value.push(f)
        }

        async function testConn() {
            actionBusy.value = 'test'
            try {
                const r    = await doPost(`/connector/test/${props.c.uuid}`)
                const data = await r.json()
                if (data.success && data.stats) {
                    if (data.stats.rules   != null) props.c.rules_count   = data.stats.rules
                    if (data.stats.bundles != null) props.c.bundles_count = data.stats.bundles
                }
                create_message(data.message || (data.success ? 'OK' : 'Failed'), data.success ? 'success' : 'danger')
            } finally { actionBusy.value = null }
        }

        async function deleteConn() {
            if (!confirm(`Delete connector "${props.c.name}"?`)) return
            const r    = await doPost(`/connector/delete/${props.c.uuid}`)
            const data = await r.json()
            if (data.success) {
                create_message('Connector deleted.', 'success')
                emit('deleted')
            } else {
                create_message(data.error || 'Delete failed.', 'danger')
            }
        }

        async function toggleHistory() {
            expanded.value = !expanded.value
            if (expanded.value && !historyLoaded.value) {
                historyLoading.value = true
                try {
                    const r = await fetch(`/connector/history/${props.c.uuid}`)
                    historyItems.value  = await r.json()
                    historyLoaded.value = true
                } catch { historyItems.value = [] }
                finally { historyLoading.value = false }
            }
        }

        return {
            expanded, historyItems, historyLoading, actionBusy, historyStats,
            visibleHistory, hasMoreHistory, loadMoreHistory,
            missingFamilies, selectedFamilies, importBusy,
            toggleFamily, importFamilies,
            statusClass, statusLabel, statusIcon,
            actionBadgeClass, actionIcon, dotClass,
            testConn, deleteConn, toggleHistory,
        }
    },
    template: `
<tbody>
  <!-- main row -->
  <tr class="cnt-tr" :class="{ 'cnt-tr--selected': selected }">
    <td class="cnt-td cnt-td--chk">
      <input v-if="!c.is_system" type="checkbox" class="cnt-checkbox"
             :checked="selected" @change="$emit('toggle-select', c.uuid)" />
    </td>
    <td class="cnt-td">
      <div class="d-flex align-items-center gap-2">
        <div class="cnt-icon-sm" :class="c.is_verified ? 'cnt-icon-sm--ok' : c.last_error ? 'cnt-icon-sm--err' : ''">
          <i :class="c.icon || 'fa-solid fa-plug'"></i>
        </div>
        <div>
          <div class="fw-semibold d-flex align-items-center gap-1" style="font-size:.88rem;">
            [[ c.name ]]
            <i v-if="c.is_system" class="fa-solid fa-lock text-muted" style="font-size:.65rem;" title="System — read only"></i>
            <span v-if="c.is_self" class="badge bg-warning text-dark" style="font-size:.58rem;" title="This is the current instance — pull disabled."><i class="fa-solid fa-house me-1"></i>self</span>
          </div>
          <div style="font-size:.72rem;color:var(--subtle-text-color);">[[ c.instance_url ]]</div>
        </div>
      </div>
    </td>
    <td class="cnt-td">
      <span :class="['cnt-status', statusClass(c)]">
        <i :class="statusIcon(c)"></i> [[ statusLabel(c) ]]
      </span>
    </td>
    <td class="cnt-td d-none d-lg-table-cell">
      <span class="cnt-type-pill">[[ c.connector_type ]]</span>
    </td>
    <td class="cnt-td d-none d-md-table-cell" style="font-size:.82rem;">
      <span class="badge bg-secondary" style="font-size:.65rem;" v-if="c.owner_mode==='self'">
        <i class="fa-solid fa-user me-1"></i>owner
      </span>
      <span class="badge bg-secondary" style="font-size:.65rem;" v-else>
        <i class="fa-solid fa-ghost me-1"></i>shadow
      </span>
    </td>
    <td class="cnt-td d-none d-md-table-cell" style="font-size:.82rem;">
      [[ c.rules_count ]] / [[ c.bundles_count ]]
    </td>
    <td class="cnt-td d-none d-xl-table-cell" style="font-size:.75rem;color:var(--subtle-text-color);">
      [[ c.last_sync_at || '—' ]]
    </td>
    <td class="cnt-td cnt-td--actions">
      <div class="cnt-actions">
        <button v-if="!c.is_system" class="cnt-btn" title="Edit" @click="$emit('edit', c)">
          <i class="fa-solid fa-pen-to-square"></i>
        </button>
        <button class="cnt-btn" title="Test" @click="testConn" :disabled="actionBusy==='test'">
          <span v-if="actionBusy==='test'" class="spinner-border spinner-border-sm"></span>
          <i v-else class="fa-solid fa-wifi"></i>
        </button>
        <template v-if="c.is_active && isAdmin">
          <div v-if="c.is_self" class="cnt-btn" title="Cannot pull from this instance (self)" style="opacity:.4;cursor:not-allowed;">
            <i class="fa-solid fa-cloud-arrow-down"></i>
          </div>
          <button v-else class="cnt-btn cnt-btn--success" title="Pull rules from this connector"
                  @click="$emit('pull-requested', c)">
            <i class="fa-solid fa-cloud-arrow-down"></i>
          </button>
        </template>
        <button v-if="!c.is_system" class="cnt-btn cnt-btn--danger" title="Delete" @click="deleteConn">
          <i class="fa-solid fa-trash"></i>
        </button>
        <button class="cnt-btn cnt-btn--expand" :class="{ 'is-open': expanded }" title="History" @click="toggleHistory">
          <i class="fa-solid fa-clock-rotate-left" style="font-size:.75rem;"></i>
          <i class="fa-solid fa-chevron-down cnt-expand-chevron" style="font-size:.6rem;margin-left:2px;"></i>
        </button>
      </div>
    </td>
  </tr>

  <!-- expanded history panel -->
  <tr v-if="expanded" class="cnt-tr-expand">
    <td :colspan="8" class="cnt-td-expand">
      <div v-if="historyLoading" class="text-center py-3">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>
      <template v-else-if="historyItems.length === 0">
        <div class="cnt-hist-empty">
          <i class="fa-solid fa-clock-rotate-left"></i>
          <span>No history yet — test or pull to record interactions.</span>
        </div>
      </template>
      <template v-else>
        <!-- Stats row -->
        <div class="cnt-hist-stats">
          <div class="cnt-hist-stat">
            <span class="cnt-hist-stat__icon" style="color:#198754;"><i class="fa-solid fa-cloud-arrow-down"></i></span>
            <span class="cnt-hist-stat__value">[[ historyStats.pulls ]]</span>
            <span class="cnt-hist-stat__label">Pulls</span>
          </div>
          <div class="cnt-hist-stat">
            <span class="cnt-hist-stat__icon" style="color:#0d6efd;"><i class="fa-solid fa-wifi"></i></span>
            <span class="cnt-hist-stat__value">[[ historyStats.tests ]]</span>
            <span class="cnt-hist-stat__label">Tests</span>
          </div>
          <div class="cnt-hist-stat">
            <span class="cnt-hist-stat__icon" style="color:#0dcaf0;"><i class="fa-solid fa-shield-halved"></i></span>
            <span class="cnt-hist-stat__value">+[[ historyStats.rulesAdded.toLocaleString() ]]</span>
            <span class="cnt-hist-stat__label">Rules synced</span>
          </div>
          <div class="cnt-hist-stat">
            <span class="cnt-hist-stat__icon" style="color:#6f42c1;"><i class="fa-solid fa-box"></i></span>
            <span class="cnt-hist-stat__value">+[[ historyStats.bundlesAdded ]]</span>
            <span class="cnt-hist-stat__label">Bundles synced</span>
          </div>
          <div class="cnt-hist-stat" v-if="historyStats.errors > 0">
            <span class="cnt-hist-stat__icon" style="color:#dc3545;"><i class="fa-solid fa-triangle-exclamation"></i></span>
            <span class="cnt-hist-stat__value">[[ historyStats.errors ]]</span>
            <span class="cnt-hist-stat__label">Errors</span>
          </div>
          <div class="cnt-hist-stat ms-auto" v-if="historyStats.lastSync">
            <span class="cnt-hist-stat__icon" style="color:var(--subtle-text-color);"><i class="fa-solid fa-rotate"></i></span>
            <span class="cnt-hist-stat__value" style="font-size:.75rem;">[[ historyStats.lastSync ]]</span>
            <span class="cnt-hist-stat__label">Last sync</span>
          </div>
        </div>

        <!-- Sparkline -->
        <div class="cnt-sparkline-wrap">
          <span class="cnt-sparkline-label">Activity — last 30 days</span>
          <svg viewBox="0 0 300 32" preserveAspectRatio="none" class="cnt-sparkline">
            <rect v-for="(v, i) in historyStats.sparkline" :key="i"
                  :x="i * 10 + 1"
                  y="0"
                  :width="8"
                  :height="32"
                  :fill="v > 0 ? 'rgba(13,110,253,.08)' : 'transparent'"
                  rx="2"/>
            <rect v-for="(v, i) in historyStats.sparkline" :key="'b'+i"
                  :x="i * 10 + 1"
                  :y="v > 0 ? (1 - v/historyStats.maxCount) * 28 + 2 : 30"
                  :width="8"
                  :height="v > 0 ? Math.max((v/historyStats.maxCount) * 28, 3) : 2"
                  :fill="v > 0 ? '#0d6efd' : 'var(--border-color)'"
                  rx="2"/>
          </svg>
        </div>

        <!-- Error banner -->
        <div v-if="c.last_error" class="cnt-hist-error-banner">
          <i class="fa-solid fa-triangle-exclamation me-2"></i>[[ c.last_error ]]
        </div>

        <!-- Missing tag families banner -->
        <div v-if="missingFamilies.length" class="cnt-missing-tags-banner">
          <div class="cnt-missing-tags-banner__header">
            <i class="fa-solid fa-tags me-2 text-warning"></i>
            <strong style="font-size:.8rem;">Tags not installed locally</strong>
            <span class="text-muted ms-1" style="font-size:.75rem;">(from last pull)</span>
          </div>
          <div class="cnt-missing-tags-banner__body">
            <label v-for="f in missingFamilies" :key="f" class="cnt-family-check">
              <input type="checkbox"
                     :value="f"
                     :checked="selectedFamilies.includes(f)"
                     @change="toggleFamily(f)"
                     class="me-1" />
              <code style="font-size:.72rem;">[[ f ]]</code>
            </label>
          </div>
          <button class="btn btn-sm btn-warning rounded-pill mt-2"
                  style="font-size:.72rem;"
                  :disabled="importBusy || !selectedFamilies.length"
                  @click="importFamilies">
            <span v-if="importBusy" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else class="fa-solid fa-download me-1"></i>
            Import selected
          </button>
        </div>

        <!-- Timeline -->
        <div class="cnt-timeline">
          <div v-for="(e, idx) in visibleHistory" :key="e.timestamp+e.action+idx" class="cnt-timeline-item">
            <div class="cnt-timeline-dot" :class="'cnt-timeline-dot--'+dotClass(e.action)"></div>
            <div class="cnt-timeline-content">
              <div class="cnt-timeline-header">
                <span :class="['badge', 'me-1', actionBadgeClass(e.action)]" style="font-size:.6rem;">
                  <i :class="actionIcon(e.action)"></i> [[ e.action ? e.action.split('.').pop() : '?' ]]
                </span>
                <span class="cnt-timeline-ts">[[ e.timestamp ]]</span>
              </div>
              <div class="cnt-timeline-desc">[[ e.description ]]</div>
              <div v-if="e.extra && e.extra.rules_added !== undefined" class="cnt-timeline-meta">
                <span title="Rules added"><i class="fa-solid fa-shield-halved me-1 text-primary"></i>+[[ e.extra.rules_added ]]</span>
                <span v-if="e.extra.rules_skipped" title="Rules skipped"><i class="fa-solid fa-forward me-1 text-secondary"></i>=[[ e.extra.rules_skipped ]]</span>
                <span title="Bundles added"><i class="fa-solid fa-box me-1 text-secondary"></i>+[[ e.extra.bundles_added ]]</span>
                <span v-if="e.extra.rules_errors" title="Errors" class="text-danger"><i class="fa-solid fa-triangle-exclamation me-1"></i>[[ e.extra.rules_errors ]] err</span>
                <span v-if="e.extra.duration_s" title="Duration" class="text-muted"><i class="fa-solid fa-stopwatch me-1"></i>[[ e.extra.duration_s ]]s</span>
              </div>
            </div>
          </div>
        </div>
        <!-- Show more -->
        <div v-if="hasMoreHistory" class="text-center pt-2">
          <button class="btn btn-sm btn-outline-secondary rounded-pill px-3" style="font-size:.75rem;" @click="loadMoreHistory">
            <i class="fa-solid fa-chevron-down me-1"></i>Show more
            <span class="text-muted ms-1">([[ historyItems.length - visibleHistory.length ]] hidden)</span>
          </button>
        </div>
      </template>
    </td>
  </tr>
</tbody>
`
}

// ─── ConnectorCard (card view) ────────────────────────────────────────────────

const ConnectorCard = {
    delimiters: ['[[', ']]'],
    directives: { dropdownFixed: _dropdownFixed },
    props: {
        c:         { type: Object,  required: true },
        isAdmin:   { type: Boolean, default: false },
        csrfToken: { type: String,  required: true },
        selected:  { type: Boolean, default: false },
    },
    emits: ['toggle-select', 'edit', 'deleted', 'pull-requested'],
    setup(props, { emit }) {
        const expanded       = ref(false)
        const historyLoaded  = ref(false)
        const historyItems   = ref([])
        const historyLoading = ref(false)
        const actionBusy     = ref(null)
        const historyPage    = ref(2)

        const historyStats   = computed(() => _computeStats(historyItems.value))
        const visibleHistory = computed(() => historyItems.value.slice(0, historyPage.value))
        const hasMoreHistory = computed(() => historyPage.value < historyItems.value.length)

        const missingFamilies  = computed(() => {
            const last = historyItems.value.find(e => e.action?.includes('pull_done'))
            return (last?.extra?.missing_tag_families || [])
        })
        const selectedFamilies = ref([])
        const importBusy       = ref(false)

        watch(missingFamilies, (families) => { selectedFamilies.value = [...families] }, { immediate: true })

        function loadMoreHistory() { historyPage.value += 5 }

        async function doPost(url, body = {}) {
            return fetch(url, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                body:    JSON.stringify(body),
            })
        }

        async function importFamilies() {
            if (!selectedFamilies.value.length) return
            importBusy.value = true
            try {
                const r    = await doPost('/connector/import_tag_families', { families: selectedFamilies.value })
                const data = await r.json()
                if (data.success) {
                    const ok  = data.results.filter(x => x.ok).map(x => x.family)
                    const err = data.results.filter(x => !x.ok).map(x => x.family)
                    if (ok.length)  create_message(`Imported: ${ok.join(', ')}`, 'success')
                    if (err.length) create_message(`Failed: ${err.join(', ')}`, 'warning')
                    selectedFamilies.value = err
                } else {
                    create_message(data.error || 'Import failed.', 'danger')
                }
            } finally { importBusy.value = false }
        }

        function toggleFamily(f) {
            const idx = selectedFamilies.value.indexOf(f)
            if (idx >= 0) selectedFamilies.value.splice(idx, 1)
            else selectedFamilies.value.push(f)
        }

        async function testConn() {
            actionBusy.value = 'test'
            try {
                const r    = await doPost(`/connector/test/${props.c.uuid}`)
                const data = await r.json()
                if (data.success && data.stats) {
                    if (data.stats.rules   != null) props.c.rules_count   = data.stats.rules
                    if (data.stats.bundles != null) props.c.bundles_count = data.stats.bundles
                }
                create_message(data.message || (data.success ? 'OK' : 'Failed'), data.success ? 'success' : 'danger')
            } finally { actionBusy.value = null }
        }

        async function deleteConn() {
            if (!confirm(`Delete connector "${props.c.name}"?`)) return
            const r    = await doPost(`/connector/delete/${props.c.uuid}`)
            const data = await r.json()
            if (data.success) {
                create_message('Connector deleted.', 'success')
                emit('deleted')
            } else {
                create_message(data.error || 'Delete failed.', 'danger')
            }
        }

        async function toggleHistory() {
            expanded.value = !expanded.value
            if (expanded.value && !historyLoaded.value) {
                historyLoading.value = true
                try {
                    const r = await fetch(`/connector/history/${props.c.uuid}`)
                    historyItems.value  = await r.json()
                    historyLoaded.value = true
                } catch { historyItems.value = [] }
                finally { historyLoading.value = false }
            }
        }

        return {
            expanded, historyItems, historyLoading, actionBusy, historyStats,
            visibleHistory, hasMoreHistory, loadMoreHistory,
            missingFamilies, selectedFamilies, importBusy,
            toggleFamily, importFamilies,
            statusClass, statusLabel, statusIcon,
            actionBadgeClass, actionIcon, dotClass,
            testConn, deleteConn, toggleHistory,
        }
    },
    template: `
<div :class="['connector-card', !c.is_active && 'connector-card--inactive', selected && 'connector-card--selected']">

  <!-- select -->
  <div v-if="!c.is_system" class="cnt-card-check">
    <input type="checkbox" class="cnt-checkbox" :checked="selected" @change="$emit('toggle-select', c.uuid)" />
  </div>

  <!-- header -->
  <div class="connector-card__header">
    <div :class="['connector-card__icon', c.is_verified ? 'connector-card__icon--verified' : c.last_error ? 'connector-card__icon--error' : '']">
      <i :class="c.icon || 'fa-solid fa-plug'"></i>
    </div>
    <div class="flex-grow-1 min-w-0">
      <div class="d-flex align-items-center justify-content-between gap-2">
        <p class="connector-card__name">
          [[ c.name ]]
          <i v-if="c.is_system" class="fa-solid fa-lock text-muted ms-1" style="font-size:.65rem;"></i>
          <span v-if="c.is_self" class="badge bg-warning text-dark ms-1" style="font-size:.58rem;" title="This is the current instance — pull disabled."><i class="fa-solid fa-house me-1"></i>self</span>
        </p>
        <span :class="['connector-status', statusClass(c)]">
          <i :class="statusIcon(c)"></i> [[ statusLabel(c) ]]
        </span>
      </div>
      <div class="connector-card__url">[[ c.instance_url ]]</div>
    </div>
  </div>

  <!-- description -->
  <p v-if="c.description" class="text-muted mb-2" style="font-size:.8rem;">[[ c.description ]]</p>

  <!-- pills -->
  <div class="d-flex gap-1 flex-wrap mb-2">
    <span class="connector-type-pill">[[ c.connector_type ]]</span>
    <span class="badge bg-secondary" style="font-size:.65rem;" v-if="c.owner_mode==='self'"><i class="fa-solid fa-user me-1"></i>owner</span>
    <span class="badge bg-secondary" style="font-size:.65rem;" v-else><i class="fa-solid fa-ghost me-1"></i>shadow</span>
    <span v-if="!c.is_active" class="badge bg-secondary" style="font-size:.65rem;">inactive</span>
  </div>

  <!-- stats -->
  <div class="connector-stats">
    <div class="connector-stat">
      <span class="connector-stat__value">[[ c.rules_count ]]</span>
      <span class="connector-stat__label">Rules</span>
    </div>
    <div class="connector-stat">
      <span class="connector-stat__value">[[ c.bundles_count ]]</span>
      <span class="connector-stat__label">Bundles</span>
    </div>
    <div class="connector-stat">
      <span class="connector-stat__value" style="font-size:.75rem;">
        <i v-if="c.sync_rules"   class="fa-solid fa-shield-halved text-primary me-1"></i>
        <i v-if="c.sync_bundles" class="fa-solid fa-box text-primary"></i>
      </span>
      <span class="connector-stat__label">Syncing</span>
    </div>
  </div>

  <div v-if="c.last_sync_at" class="connector-last-sync"><i class="fa-solid fa-rotate me-1"></i>[[ c.last_sync_at ]]</div>

  <!-- actions -->
  <div class="connector-actions">
    <button v-if="!c.is_system" class="btn btn-sm btn-outline-secondary rounded-pill" @click="$emit('edit', c)">
      <i class="fa-solid fa-pen-to-square me-1"></i>Edit
    </button>
    <button class="btn btn-sm btn-outline-primary rounded-pill" @click="testConn" :disabled="actionBusy==='test'">
      <span v-if="actionBusy==='test'" class="spinner-border spinner-border-sm me-1"></span>
      <i v-else class="fa-solid fa-wifi me-1"></i>Test
    </button>
    <template v-if="c.is_active && isAdmin">
      <button v-if="c.is_self" class="btn btn-sm btn-outline-secondary rounded-pill" disabled title="Cannot pull from this instance (self)">
        <i class="fa-solid fa-cloud-arrow-down me-1"></i>Pull
      </button>
      <button v-else class="btn btn-sm btn-outline-success rounded-pill"
              title="Pull rules from this connector"
              @click="$emit('pull-requested', c)">
        <i class="fa-solid fa-cloud-arrow-down me-1"></i>Pull
      </button>
    </template>
    <button class="btn btn-sm btn-outline-secondary rounded-pill" @click="toggleHistory">
      <i :class="['fa-solid', expanded ? 'fa-chevron-up' : 'fa-clock-rotate-left', 'me-1']"></i>History
    </button>
    <button v-if="!c.is_system" class="btn btn-sm btn-outline-danger rounded-pill ms-auto" @click="deleteConn">
      <i class="fa-solid fa-trash"></i>
    </button>
  </div>

  <!-- inline history panel -->
  <div v-if="expanded" class="cnt-card-history">
    <div v-if="historyLoading" class="text-center py-3">
      <div class="spinner-border spinner-border-sm text-primary"></div>
    </div>
    <template v-else-if="historyItems.length === 0">
      <div class="cnt-hist-empty">
        <i class="fa-solid fa-clock-rotate-left"></i>
        <span>No history yet — test or pull to record interactions.</span>
      </div>
    </template>
    <template v-else>
      <!-- Stats -->
      <div class="cnt-hist-stats">
        <div class="cnt-hist-stat">
          <span class="cnt-hist-stat__icon" style="color:#198754;"><i class="fa-solid fa-cloud-arrow-down"></i></span>
          <span class="cnt-hist-stat__value">[[ historyStats.pulls ]]</span>
          <span class="cnt-hist-stat__label">Pulls</span>
        </div>
        <div class="cnt-hist-stat">
          <span class="cnt-hist-stat__icon" style="color:#0d6efd;"><i class="fa-solid fa-wifi"></i></span>
          <span class="cnt-hist-stat__value">[[ historyStats.tests ]]</span>
          <span class="cnt-hist-stat__label">Tests</span>
        </div>
        <div class="cnt-hist-stat">
          <span class="cnt-hist-stat__icon" style="color:#0dcaf0;"><i class="fa-solid fa-shield-halved"></i></span>
          <span class="cnt-hist-stat__value">+[[ historyStats.rulesAdded.toLocaleString() ]]</span>
          <span class="cnt-hist-stat__label">Rules</span>
        </div>
        <div class="cnt-hist-stat">
          <span class="cnt-hist-stat__icon" style="color:#6f42c1;"><i class="fa-solid fa-box"></i></span>
          <span class="cnt-hist-stat__value">+[[ historyStats.bundlesAdded ]]</span>
          <span class="cnt-hist-stat__label">Bundles</span>
        </div>
        <div class="cnt-hist-stat" v-if="historyStats.errors > 0">
          <span class="cnt-hist-stat__icon" style="color:#dc3545;"><i class="fa-solid fa-triangle-exclamation"></i></span>
          <span class="cnt-hist-stat__value">[[ historyStats.errors ]]</span>
          <span class="cnt-hist-stat__label">Errors</span>
        </div>
      </div>
      <!-- Sparkline -->
      <div class="cnt-sparkline-wrap">
        <span class="cnt-sparkline-label">Activity — last 30 days</span>
        <svg viewBox="0 0 300 32" preserveAspectRatio="none" class="cnt-sparkline">
          <rect v-for="(v, i) in historyStats.sparkline" :key="i"
                :x="i * 10 + 1" y="0" :width="8" :height="32"
                :fill="v > 0 ? 'rgba(13,110,253,.08)' : 'transparent'" rx="2"/>
          <rect v-for="(v, i) in historyStats.sparkline" :key="'b'+i"
                :x="i * 10 + 1"
                :y="v > 0 ? (1 - v/historyStats.maxCount) * 28 + 2 : 30"
                :width="8"
                :height="v > 0 ? Math.max((v/historyStats.maxCount) * 28, 3) : 2"
                :fill="v > 0 ? '#0d6efd' : 'var(--border-color)'" rx="2"/>
        </svg>
      </div>
      <!-- Error banner -->
      <div v-if="c.last_error" class="cnt-hist-error-banner">
        <i class="fa-solid fa-triangle-exclamation me-2"></i>[[ c.last_error ]]
      </div>
      <!-- Missing tag families banner -->
      <div v-if="missingFamilies.length" class="cnt-missing-tags-banner">
        <div class="cnt-missing-tags-banner__header">
          <i class="fa-solid fa-tags me-2 text-warning"></i>
          <strong style="font-size:.8rem;">Tags not installed locally</strong>
          <span class="text-muted ms-1" style="font-size:.75rem;">(from last pull)</span>
        </div>
        <div class="cnt-missing-tags-banner__body">
          <label v-for="f in missingFamilies" :key="f" class="cnt-family-check">
            <input type="checkbox"
                   :value="f"
                   :checked="selectedFamilies.includes(f)"
                   @change="toggleFamily(f)"
                   class="me-1" />
            <code style="font-size:.72rem;">[[ f ]]</code>
          </label>
        </div>
        <button class="btn btn-sm btn-warning rounded-pill mt-2"
                style="font-size:.72rem;"
                :disabled="importBusy || !selectedFamilies.length"
                @click="importFamilies">
          <span v-if="importBusy" class="spinner-border spinner-border-sm me-1"></span>
          <i v-else class="fa-solid fa-download me-1"></i>
          Import selected
        </button>
      </div>
      <!-- Timeline -->
      <div class="cnt-timeline">
        <div v-for="(e, idx) in visibleHistory" :key="e.timestamp+e.action+idx" class="cnt-timeline-item">
          <div class="cnt-timeline-dot" :class="'cnt-timeline-dot--'+dotClass(e.action)"></div>
          <div class="cnt-timeline-content">
            <div class="cnt-timeline-header">
              <span :class="['badge', 'me-1', actionBadgeClass(e.action)]" style="font-size:.6rem;">
                <i :class="actionIcon(e.action)"></i> [[ e.action ? e.action.split('.').pop() : '?' ]]
              </span>
              <span class="cnt-timeline-ts">[[ e.timestamp ]]</span>
            </div>
            <div class="cnt-timeline-desc">[[ e.description ]]</div>
            <div v-if="e.extra && e.extra.rules_added !== undefined" class="cnt-timeline-meta">
              <span v-if="e.extra.mode" :class="['badge', 'me-1', e.extra.mode==='hard' ? 'bg-warning text-dark' : 'bg-success']" style="font-size:.58rem;">
                <i :class="e.extra.mode==='hard' ? 'fa-solid fa-bolt' : 'fa-solid fa-feather'" class="me-1"></i>[[ e.extra.mode ]]
              </span>
              <span title="Rules added"><i class="fa-solid fa-shield-halved me-1 text-primary"></i>+[[ e.extra.rules_added ]]</span>
              <span v-if="e.extra.rules_skipped" title="Rules skipped"><i class="fa-solid fa-forward me-1 text-secondary"></i>=[[ e.extra.rules_skipped ]]</span>
              <span title="Bundles added"><i class="fa-solid fa-box me-1 text-secondary"></i>+[[ e.extra.bundles_added ]]</span>
              <span v-if="e.extra.rules_errors" title="Errors" class="text-danger"><i class="fa-solid fa-triangle-exclamation me-1"></i>[[ e.extra.rules_errors ]] err</span>
              <span v-if="e.extra.duration_s" title="Duration" class="text-muted"><i class="fa-solid fa-stopwatch me-1"></i>[[ e.extra.duration_s ]]s</span>
            </div>
          </div>
        </div>
      </div>
      <!-- Show more -->
      <div v-if="hasMoreHistory" class="text-center pt-2">
        <button class="btn btn-sm btn-outline-secondary rounded-pill px-3" style="font-size:.75rem;" @click="loadMoreHistory">
          <i class="fa-solid fa-chevron-down me-1"></i>Show more
          <span class="text-muted ms-1">([[ historyItems.length - visibleHistory.length ]] hidden)</span>
        </button>
      </div>
    </template>
  </div>
</div>
`
}

// ─── ConnectorTable (main export) ─────────────────────────────────────────────

export default {
    name: 'ConnectorTable',
    delimiters: ['[[', ']]'],
    directives: { dropdownFixed: _dropdownFixed },
    components: {
        ConnectorRow,
        ConnectorCard,
        PaginationComponent,
    },
    props: {
        isAdmin:   { type: Boolean, default: false },
        csrfToken: { type: String,  required: true },
        section:   { type: String,  default: 'rulezet' },  // 'rulezet' | 'other'
    },
    emits: ['create', 'edit', 'count', 'pull-requested'],

    expose: ['refresh'],

    setup(props, { emit }) {
        const allConnectors = ref([])
        const loading       = ref(true)

        // View / search / pagination
        const viewMode  = ref('table')  // 'table' | 'card'
        const search    = ref('')
        const page      = ref(1)
        const perPage   = ref(12)

        // Selection
        const selectedUuids = reactive(new Set())

        // Bulk state
        const bulkBusy = ref(false)

        // ── Derived ──────────────────────────────────────────────────────
        const filtered = computed(() => {
            const q = search.value.toLowerCase()
            return allConnectors.value.filter(c => {
                const matchSection = props.section === 'rulezet'
                    ? c.connector_type === 'rulezet'
                    : c.connector_type !== 'rulezet'
                if (!matchSection) return false
                if (!q) return true
                return (c.name + c.instance_url + (c.description || '')).toLowerCase().includes(q)
            })
        })

        const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / perPage.value)))

        const paginated = computed(() => {
            const start = (page.value - 1) * perPage.value
            return filtered.value.slice(start, start + perPage.value)
        })

        const allPageSelected = computed(() =>
            paginated.value.length > 0 &&
            paginated.value.filter(c => !c.is_system).every(c => selectedUuids.has(c.uuid))
        )
        const somePageSelected = computed(() =>
            paginated.value.some(c => selectedUuids.has(c.uuid))
        )

        const selectableOnPage = computed(() => paginated.value.filter(c => !c.is_system))

        // ── Data ─────────────────────────────────────────────────────────
        async function refresh() {
            loading.value = true
            try {
                const r = await fetch('/connector/get')
                allConnectors.value = await r.json()
                emit('count', filtered.value.length)
            } catch { create_message('Failed to load connectors.', 'danger') }
            finally { loading.value = false }
        }

        // ── Search ───────────────────────────────────────────────────────
        let searchTimer = null
        function onSearch() {
            clearTimeout(searchTimer)
            searchTimer = setTimeout(() => { page.value = 1 }, 250)
        }

        // ── Selection ────────────────────────────────────────────────────
        function toggleSelect(uuid) {
            if (selectedUuids.has(uuid)) selectedUuids.delete(uuid)
            else selectedUuids.add(uuid)
        }

        function togglePageAll() {
            if (allPageSelected.value) {
                selectableOnPage.value.forEach(c => selectedUuids.delete(c.uuid))
            } else {
                selectableOnPage.value.forEach(c => selectedUuids.add(c.uuid))
            }
        }

        function clearSelection() { selectedUuids.clear() }

        // ── Bulk actions ─────────────────────────────────────────────────
        async function bulkTest() {
            bulkBusy.value = true
            const uuids = [...selectedUuids]
            let ok = 0
            for (const uuid of uuids) {
                try {
                    const r = await fetch(`/connector/test/${uuid}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                        body: '{}',
                    })
                    const d = await r.json()
                    if (d.success) ok++
                } catch {}
            }
            create_message(`Tested ${uuids.length} connector(s): ${ok} OK.`, 'info')
            await refresh()
            bulkBusy.value = false
        }

        async function bulkPull() {
            if (!props.isAdmin) return
            bulkBusy.value = true
            const connectors = paginated.value.filter(c => selectedUuids.has(c.uuid) && !c.is_self)
            let queued = 0
            for (const c of connectors) {
                try {
                    const r = await fetch(`/connector/pull/${c.uuid}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    })
                    const d = await r.json()
                    if (d.success) queued++
                } catch {}
            }
            const skipped = selectedUuids.size - connectors.length
            const note = skipped > 0 ? ` (${skipped} skipped — self)` : ''
            if (queued > 0) window.dispatchEvent(new Event('rz:job-created'))
            create_message(`${queued} pull job(s) queued${note}.`, 'success')
            clearSelection()
            bulkBusy.value = false
        }

        async function bulkDelete() {
            if (!confirm(`Delete ${selectedUuids.size} connector(s)? Imported rules will remain.`)) return
            bulkBusy.value = true
            const uuids = [...selectedUuids]
            for (const uuid of uuids) {
                try {
                    await fetch(`/connector/delete/${uuid}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                        body: '{}',
                    })
                } catch {}
            }
            create_message(`${uuids.length} connector(s) deleted.`, 'success')
            clearSelection()
            await refresh()
            bulkBusy.value = false
        }

        onMounted(refresh)

        return {
            allConnectors, loading,
            viewMode, search, page, perPage, totalPages,
            filtered, paginated,
            selectedUuids, allPageSelected, somePageSelected, selectableOnPage,
            bulkBusy,
            refresh, onSearch,
            toggleSelect, togglePageAll, clearSelection,
            bulkTest, bulkPull, bulkDelete,
        }
    },

    template: `
<div class="cnt-wrapper">

  <!-- Toolbar -->
  <div class="cnt-toolbar">
    <div class="cnt-toolbar-left">
      <!-- Search -->
      <div class="cnt-search-wrap">
        <i class="fa-solid fa-magnifying-glass cnt-search-icon"></i>
        <input class="cnt-search-input" type="text" placeholder="Search connectors…"
               v-model="search" @input="onSearch" />
        <button v-if="search" class="cnt-search-clear" @click="search=''; page=1">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <span class="cnt-count">[[ filtered.length ]] connector[[ filtered.length!==1?'s':'' ]]</span>
    </div>
    <div class="cnt-toolbar-right">
      <!-- View toggle -->
      <div class="cnt-view-toggle">
        <button :class="['cnt-view-btn', viewMode==='table' && 'cnt-view-btn--active']"
                @click="viewMode='table'" title="Table view">
          <i class="fa-solid fa-table-cells-large"></i>
        </button>
        <button :class="['cnt-view-btn', viewMode==='card' && 'cnt-view-btn--active']"
                @click="viewMode='card'" title="Card view">
          <i class="fa-solid fa-grip"></i>
        </button>
      </div>
      <!-- Add button -->
      <button class="btn btn-primary btn-sm rounded-pill px-3" @click="$emit('create')">
        <i class="fa-solid fa-plus me-1"></i>Add
      </button>
    </div>
  </div>

  <!-- Loading -->
  <div v-if="loading" class="text-center py-5">
    <div class="spinner-border text-primary"></div>
  </div>

  <!-- Empty -->
  <div v-else-if="filtered.length === 0" class="connector-empty">
    <div class="connector-empty__icon"><i class="fa-solid fa-plug-circle-xmark"></i></div>
    <p class="mb-0">No connectors found.</p>
  </div>

  <template v-else>

    <!-- ── TABLE VIEW ──────────────────────────────────────────── -->
    <div v-if="viewMode === 'table'" class="cnt-table-wrap">
      <table class="cnt-table">
        <thead class="cnt-thead">
          <tr>
            <th class="cnt-th cnt-th--chk">
              <input type="checkbox" class="cnt-checkbox"
                     :checked="allPageSelected"
                     :indeterminate="somePageSelected && !allPageSelected"
                     @change="togglePageAll" />
            </th>
            <th class="cnt-th">Connector</th>
            <th class="cnt-th">Status</th>
            <th class="cnt-th d-none d-lg-table-cell">Type</th>
            <th class="cnt-th d-none d-md-table-cell">Ownership</th>
            <th class="cnt-th d-none d-md-table-cell">Rules / Bundles</th>
            <th class="cnt-th d-none d-xl-table-cell">Last sync</th>
            <th class="cnt-th cnt-th--actions">Actions</th>
          </tr>
        </thead>
        <connector-row
          v-for="c in paginated" :key="c.uuid"
          :c="c" :is-admin="isAdmin" :csrf-token="csrfToken"
          :selected="selectedUuids.has(c.uuid)"
          @toggle-select="toggleSelect"
          @edit="$emit('edit', $event)"
          @pull-requested="$emit('pull-requested', $event)"
          @deleted="refresh">
        </connector-row>
      </table>
    </div>

    <!-- ── CARD VIEW ───────────────────────────────────────────── -->
    <div v-else class="row g-3">
      <div v-for="c in paginated" :key="c.uuid" class="col-12 col-md-6 col-xl-4">
        <connector-card
          :c="c" :is-admin="isAdmin" :csrf-token="csrfToken"
          :selected="selectedUuids.has(c.uuid)"
          @toggle-select="toggleSelect"
          @edit="$emit('edit', $event)"
          @pull-requested="$emit('pull-requested', $event)"
          @deleted="refresh">
        </connector-card>
      </div>
    </div>

    <!-- Footer -->
    <div class="cnt-footer">
      <div class="cnt-per-page">
        <span>Per page</span>
        <select v-model="perPage" @change="page=1">
          <option v-for="n in [6,12,24,48]" :key="n" :value="n">[[ n ]]</option>
        </select>
      </div>
      <pagination-component :current-page="page" :total-pages="totalPages"
                            @change-page="page=$event" />
      <div class="cnt-footer-info">
        [[ (page-1)*perPage+1 ]]–[[ Math.min(page*perPage, filtered.length) ]] of [[ filtered.length ]]
      </div>
    </div>

  </template>

  <!-- Bulk bar -->
  <transition name="cnt-bulk-slide">
    <div v-if="selectedUuids.size > 0" class="cnt-bulk-bar">
      <span class="cnt-bulk-count">[[ selectedUuids.size ]] selected</span>
      <div class="d-flex gap-2">
        <button class="cnt-bulk-btn" @click="bulkTest" :disabled="bulkBusy">
          <i class="fa-solid fa-wifi me-1"></i>Test all
        </button>
        <button v-if="isAdmin" class="cnt-bulk-btn cnt-bulk-btn--success" @click="bulkPull" :disabled="bulkBusy">
          <i class="fa-solid fa-cloud-arrow-down me-1"></i>Pull all
        </button>
        <button class="cnt-bulk-btn cnt-bulk-btn--danger" @click="bulkDelete" :disabled="bulkBusy">
          <i class="fa-solid fa-trash me-1"></i>Delete
        </button>
      </div>
      <button class="cnt-bulk-clear" @click="clearSelection">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>
  </transition>

</div>
`
}
