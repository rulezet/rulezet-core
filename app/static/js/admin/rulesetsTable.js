/**
 * rulesetsTable.js — Rulesets (Rule Git Mirror) config management table.
 *
 * Mirrors app/static/js/misp/mispTable.js's structure — search + table +
 * per-row actions + expandable activity history — adapted for
 * RuleMirrorConfig rows instead of MISP server connections. "Run now" is
 * only enabled once a "Test connection" has passed (RuleMirrorConfig.is_verified) —
 * changing the repo URL/branch/token resets that and requires a re-test.
 *
 * Props:
 *   csrfToken    String   — CSRF token for POST requests
 *
 * Emits:
 *   create       — user clicked "Add repository"
 *   edit         — user clicked "Edit" on a config row (passes the config object)
 *
 * Exposed:
 *   refresh()    — re-fetch configs (call via template ref)
 */

import { create_message } from '/static/js/toaster.js'

const { ref, computed, onMounted } = Vue

// ── History timeline helpers ─────────────────────────────────────────────────
function actionBadgeClass(e) {
  if (!e || !e.action) return 'bg-secondary'
  if (e.action.includes('test_failed'))        return 'bg-danger'
  if (e.action.includes('test_ok'))            return 'bg-info text-dark'
  if (e.action.includes('sync_failed'))        return 'bg-danger'
  if (e.action.includes('sync'))               return 'bg-success'
  if (e.action.includes('run_triggered'))      return 'bg-primary'
  if (e.action.includes('config_created'))     return 'bg-secondary'
  if (e.action.includes('config_deleted'))     return 'bg-danger'
  if (e.action.includes('config_changed'))     return 'bg-warning text-dark'
  return 'bg-secondary'
}
function actionIcon(e) {
  if (!e || !e.action) return 'fa-solid fa-circle'
  if (e.action.includes('test_failed'))        return 'fa-solid fa-triangle-exclamation'
  if (e.action.includes('test_ok'))            return 'fa-solid fa-wifi'
  if (e.action.includes('sync_failed'))        return 'fa-solid fa-triangle-exclamation'
  if (e.action.includes('sync'))               return 'fa-solid fa-flag-checkered'
  if (e.action.includes('run_triggered'))      return 'fa-solid fa-play'
  if (e.action.includes('config_created'))     return 'fa-solid fa-plus'
  if (e.action.includes('config_deleted'))     return 'fa-solid fa-trash'
  if (e.action.includes('config_changed'))     return 'fa-solid fa-pen'
  return 'fa-solid fa-circle'
}
function dotClass(e) {
  if (!e || !e.action) return 'neutral'
  if (e.action.includes('test_failed'))        return 'danger'
  if (e.action.includes('test_ok'))            return 'info'
  if (e.action.includes('sync_failed'))        return 'danger'
  if (e.action.includes('sync'))               return 'success'
  if (e.action.includes('run_triggered'))      return 'primary'
  if (e.action.includes('config_deleted'))     return 'danger'
  if (e.action.includes('config_changed'))     return 'warning'
  return 'neutral'
}

const RulesetRow = {
  name: 'RulesetRow',
  delimiters: ['[[', ']]'],
  props: {
    c: { type: Object, required: true },
    csrfToken: { type: String, required: true },
  },
  emits: ['edit', 'refresh'],
  setup(props, { emit }) {
    const actionBusy = ref(false)
    const testing     = ref(false)

    const expanded       = ref(false)
    const historyLoaded  = ref(false)
    const historyItems   = ref([])
    const historyLoading = ref(false)
    const historyPage    = ref(2)

    const visibleHistory = computed(() => historyItems.value.slice(0, historyPage.value))
    const hasMoreHistory = computed(() => historyPage.value < historyItems.value.length)
    function loadMoreHistory() { historyPage.value += 5 }

    async function toggleHistory() {
      expanded.value = !expanded.value
      if (expanded.value && !historyLoaded.value) {
        historyLoading.value = true
        try {
          const r = await fetch(`/admin/rule_mirror/history/${props.c.uuid}`)
          historyItems.value  = await r.json()
          historyLoaded.value = true
        } catch { historyItems.value = [] }
        finally { historyLoading.value = false }
      }
    }

    async function doPost(url, body) {
      return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      })
    }

    async function testConnection() {
      testing.value = true
      try {
        const r = await doPost(`/admin/rule_mirror/test/${props.c.uuid}`)
        const data = await r.json()
        if (data.config) Object.assign(props.c, data.config)
        create_message(data.message || (data.success ? 'Connection OK.' : 'Test failed.'), data.success ? 'success-subtle' : 'danger-subtle')
        historyLoaded.value = false   // a new test just wrote a history entry — refetch on next expand
        emit('refresh')
      } finally {
        testing.value = false
      }
    }

    async function toggleEnabled() {
      actionBusy.value = true
      try {
        const r = await doPost(`/admin/rule_mirror/update/${props.c.uuid}`, { enabled: !props.c.enabled })
        const data = await r.json()
        if (data.success) {
          props.c.enabled = data.config.enabled
        } else {
          create_message(data.message || 'Failed to update.', 'danger-subtle')
        }
      } finally {
        actionBusy.value = false
      }
    }

    async function runNow() {
      actionBusy.value = true
      try {
        // The server always re-tests the connection first — "Run now" can
        // never skip that check — so this row's status reflects that fresh
        // test result either way, success or failure.
        const r = await doPost(`/admin/rule_mirror/run_now/${props.c.uuid}`)
        const data = await r.json()
        if (data.config) Object.assign(props.c, data.config)
        if (data.success) {
          create_message('Connection OK — sync started, track it on the Jobs page.', 'success-subtle')
          window.location.href = '/jobs/detail/' + data.job_uuid
        } else {
          create_message(data.message || 'Could not start the sync.', 'danger-subtle')
        }
        historyLoaded.value = false
      } finally {
        actionBusy.value = false
      }
    }

    async function deleteConfig() {
      if (!confirm(`Delete the "${props.c.name}" mirror config? This only removes this instance's settings and local checkout — it never touches the remote GitHub repo.`)) return
      const r = await doPost(`/admin/rule_mirror/delete/${props.c.uuid}`)
      const data = await r.json()
      if (data.success) {
        create_message('Mirror config deleted.', 'success-subtle')
        emit('refresh')
      } else {
        create_message(data.message || 'Delete failed.', 'danger-subtle')
      }
    }

    return {
      actionBusy, testing, expanded, historyLoading, historyItems, visibleHistory, hasMoreHistory,
      actionBadgeClass, actionIcon, dotClass,
      toggleHistory, loadMoreHistory, testConnection, toggleEnabled, runNow, deleteConfig,
    }
  },
  template: `
<tr class="rms-tr">
  <td class="rms-td">
    <div class="d-flex align-items-center gap-2">
      <div class="rms-icon-sm">
        <img src="/static/image/rulezet_rulesets_logo.png" alt="" style="height:20px;width:20px;object-fit:contain;">
      </div>
      <div>
        <div class="fw-semibold" style="font-size:.88rem;">[[ c.name ]]</div>
        <div style="font-size:.72rem;color:var(--subtle-text-color);">[[ c.branch ]]</div>
      </div>
    </div>
  </td>
  <td class="rms-td">
    <span :class="['rms-status', c.enabled ? 'rms-status--on' : 'rms-status--off']">
      <i :class="c.enabled ? 'fa-solid fa-circle-check' : 'fa-solid fa-pause'"></i> [[ c.enabled ? 'Enabled' : 'Disabled' ]]
    </span>
    <div class="mt-1">
      <span v-if="c.is_verified" class="rms-status rms-status--verified">
        <i class="fa-solid fa-shield-check"></i> Tested OK
      </span>
      <span v-else class="rms-status rms-status--untested">
        <i class="fa-solid fa-circle-question"></i> Not tested
      </span>
    </div>
    <div v-if="c.last_error" class="text-danger text-truncate" style="font-size:.7rem;max-width:220px;" :title="c.last_error">
      [[ c.last_error ]]
    </div>
  </td>
  <td class="rms-td d-none d-md-table-cell" style="font-size:.8rem;">
    <span v-if="c.repo_url">[[ c.repo_url ]]</span>
    <span v-else class="text-muted">Not set</span>
  </td>
  <td class="rms-td d-none d-lg-table-cell" style="font-size:.78rem;">
    <span v-if="c.has_token" class="text-success"><i class="fa-solid fa-key me-1"></i>Set</span>
    <span v-else class="text-muted">Not set</span>
  </td>
  <td class="rms-td d-none d-xl-table-cell" style="font-size:.75rem;color:var(--subtle-text-color);">[[ c.last_synced_at || 'Never synced' ]]</td>
  <td class="rms-td rms-td--actions">
    <div class="rms-actions">
      <button class="rms-btn" title="History" @click="toggleHistory" :class="{ 'rms-btn--active': expanded }">
        <i class="fa-solid fa-clock-rotate-left"></i>
      </button>
      <button class="rms-btn" title="Test connection" @click="testConnection" :disabled="testing || !c.repo_url || !c.has_token">
        <span v-if="testing" class="spinner-border spinner-border-sm"></span>
        <i v-else class="fa-solid fa-wifi"></i>
      </button>
      <button class="rms-btn" title="Run now — tests the connection first" @click="runNow" :disabled="actionBusy || !c.enabled || !c.repo_url || !c.has_token">
        <span v-if="actionBusy" class="spinner-border spinner-border-sm"></span>
        <i v-else class="fa-solid fa-play"></i>
      </button>
      <button class="rms-btn" title="Edit" @click="$emit('edit', c)">
        <i class="fa-solid fa-pen-to-square"></i>
      </button>
      <button class="rms-btn" :title="c.enabled ? 'Disable' : 'Enable'" @click="toggleEnabled" :disabled="actionBusy">
        <i :class="c.enabled ? 'fa-solid fa-pause' : 'fa-solid fa-play'"></i>
      </button>
      <button class="rms-btn rms-btn--danger" title="Delete" @click="deleteConfig">
        <i class="fa-solid fa-trash"></i>
      </button>
    </div>
  </td>
</tr>
<tr v-if="expanded" class="rms-tr-expand">
  <td colspan="6">
    <div class="rms-history-panel">
      <div v-if="historyLoading" class="text-center py-3">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>
      <div v-else-if="!historyItems.length" class="text-muted text-center py-3" style="font-size:.82rem;">
        No activity recorded yet.
      </div>
      <template v-else>
        <div class="rms-timeline">
          <div v-for="(e, idx) in visibleHistory" :key="e.timestamp+e.action+idx" class="rms-timeline-item">
            <div class="rms-timeline-dot" :class="'rms-timeline-dot--'+dotClass(e)"></div>
            <div class="rms-timeline-content">
              <div class="rms-timeline-header">
                <span :class="['badge', 'me-1', actionBadgeClass(e)]" style="font-size:.6rem;">
                  <i :class="actionIcon(e)"></i> [[ e.action ? e.action.split('.').pop() : '?' ]]
                </span>
                <span class="rms-timeline-ts">[[ e.timestamp ]]</span>
              </div>
              <div class="rms-timeline-desc">[[ e.description ]]</div>
            </div>
          </div>
        </div>
        <div v-if="hasMoreHistory" class="text-center pt-2">
          <button class="btn btn-sm btn-outline-secondary rounded-pill px-3" style="font-size:.75rem;" @click="loadMoreHistory">
            <i class="fa-solid fa-chevron-down me-1"></i>Show more
            <span class="text-muted ms-1">([[ historyItems.length - visibleHistory.length ]] hidden)</span>
          </button>
        </div>
      </template>
    </div>
  </td>
</tr>
`,
}

export default {
  name: 'RulesetsTable',
  delimiters: ['[[', ']]'],
  components: { 'ruleset-row': RulesetRow },
  props: {
    csrfToken: { type: String, required: true },
  },
  emits: ['create', 'edit'],
  expose: ['refresh'],

  setup(props, { emit }) {
    const configs = ref([])
    const loading = ref(true)
    const search = ref('')

    const filtered = computed(() => {
      const q = search.value.toLowerCase()
      if (!q) return configs.value
      return configs.value.filter(c =>
        (c.name + (c.repo_url || '')).toLowerCase().includes(q)
      )
    })

    async function refresh() {
      loading.value = true
      try {
        const r = await fetch('/admin/rule_mirror/list')
        configs.value = await r.json()
      } catch {
        create_message('Failed to load Rulesets configs.', 'danger-subtle')
      } finally {
        loading.value = false
      }
    }

    onMounted(refresh)

    return { configs, loading, search, filtered, refresh }
  },

  template: `
<div class="rms-wrapper">

  <!-- Toolbar -->
  <div class="rms-toolbar">
    <div class="rms-toolbar-left">
      <div class="rms-search-wrap">
        <i class="fa-solid fa-magnifying-glass rms-search-icon"></i>
        <input class="rms-search-input" type="text" placeholder="Search repositories…" v-model="search" />
      </div>
      <span class="rms-count">[[ filtered.length ]] repositor[[ filtered.length!==1?'ies':'y' ]]</span>
    </div>
    <div class="rms-toolbar-right">
      <button class="btn btn-primary btn-sm rounded-pill px-3" @click="$emit('create')">
        <i class="fa-solid fa-plus me-1"></i>Add repository
      </button>
    </div>
  </div>

  <!-- Loading -->
  <div v-if="loading" class="text-center py-5">
    <div class="spinner-border text-primary"></div>
  </div>

  <!-- Empty -->
  <div v-else-if="filtered.length === 0" class="rms-empty">
    <div class="rms-empty__icon"><i class="fa-brands fa-git-alt"></i></div>
    <p class="mb-0">No mirror repositories configured yet.</p>
  </div>

  <!-- Table -->
  <div v-else class="rms-table-wrap">
    <table class="rms-table">
      <thead class="rms-thead">
        <tr>
          <th class="rms-th">Repository</th>
          <th class="rms-th">Status</th>
          <th class="rms-th d-none d-md-table-cell">URL</th>
          <th class="rms-th d-none d-lg-table-cell">Token</th>
          <th class="rms-th d-none d-xl-table-cell">Last synced</th>
          <th class="rms-th rms-th--actions">Actions</th>
        </tr>
      </thead>
      <tbody>
        <ruleset-row
          v-for="c in filtered" :key="c.uuid"
          :c="c" :csrf-token="csrfToken"
          @edit="$emit('edit', $event)"
          @refresh="refresh">
        </ruleset-row>
      </tbody>
    </table>
  </div>

</div>
`,
}
