/**
 * aiProvidersCard.js — the AI backends of this instance (Models & Security
 * page): Ollama (local or remote), Claude, ChatGPT, or any internal
 * OpenAI-compatible server. One table, an add/edit form, and a radio to pick
 * the ACTIVE one — every AI feature goes through it. Replaces the old
 * single-Ollama card; the first provider is seeded from those settings, so
 * the default stays Ollama.
 *
 * Security: the API key is write-only — the server only ever returns a
 * "••••last4" hint; leave the field empty to keep the stored key. Changing a
 * provider's URL drops its key server-side unless a new one is entered.
 *
 * Props:
 *   csrfToken  String (required)
 *
 * Emits:
 *   changed — after any save/activation, so the page can refresh model lists.
 */

import { create_message } from '/static/js/toaster.js'
import DataTable from '/static/js/components/table/data-table.js'

const { ref, reactive, computed, onMounted, onUnmounted, nextTick } = Vue

const PRIVATE_V4 = /^(127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/

function isLocalUrl(url) {
    let host = ''
    try { host = new URL(url).hostname.toLowerCase() } catch (e) { return false }
    return host === 'localhost' || host.endsWith('.local') || PRIVATE_V4.test(host)
}

const KIND_ICONS = {
    ollama: 'fa-server',
    anthropic: 'fa-robot',
    openai: 'fa-comments',
    openai_compatible: 'fa-building-shield',
}

function emptyForm() {
    return { id: null, name: '', kind: 'ollama', base_url: '', api_key: '', clear_api_key: false, workspace_id: '', monthly_budget_usd: '', price_input_per_mtok: '', price_output_per_mtok: '', block_over_budget: false,
             default_model: '', remote_allowed: false, has_api_key: false, api_key_hint: null }
}

export default {
    name: 'AiProvidersCard',
    delimiters: ['[[', ']]'],

    props: {
        csrfToken: { type: String, required: true },
    },

    emits: ['changed'],

    components: { 'data-table': DataTable },

    template: `
        <div class="card border-0 shadow-sm rounded-4 mb-4">
            <div class="card-body p-4">
                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-1">
                    <div class="d-flex align-items-center gap-2">
                        <div style="width:3px;height:14px;background:#0d6efd;border-radius:2px;flex-shrink:0;"></div>
                        <span class="fw-bold" style="font-size:.75rem;text-transform:uppercase;letter-spacing:.07em;color:var(--subtle-text-color);">
                            <i class="fa-solid fa-plug me-1"></i>AI providers
                        </span>
                    </div>
                </div>
                <small class="text-muted d-block mb-3">
                    Every AI feature (chatbot, rule &amp; bundle analysis, fixer, generator) runs on the <strong>active</strong>
                    provider. API keys are encrypted on the server and never shown again.
                </small>

                <div v-if="loading" class="text-center py-3 text-muted"><i class="fa-solid fa-spinner fa-spin"></i></div>

                <div v-else-if="loadError" class="alert alert-danger py-2 px-3 mb-0" style="font-size:.82rem;">
                    <i class="fa-solid fa-circle-xmark me-1"></i>[[ loadError ]]
                </div>

                <template v-else>
                    <data-table
                        ref="tableRef"
                        :key="fetchUrl"
                        :fetch-url="fetchUrl"
                        :columns="columns"
                        mode="read"
                        :can-create="canEdit"
                        :can-edit="canEdit"
                        :can-delete="canEdit"
                        :row-deletable="item => !item.is_active"
                        row-not-deletable-title="Activate another provider before deleting this one"
                        :allow-card-view="false"
                        initial-sort="created_at"
                        initial-dir="asc"
                        @create="startCreate"
                        @edit="startEdit"
                        @delete="remove">

                        <template #toolbar-start>
                            <select class="form-select form-select-sm" v-model="kindFilter" style="width:auto;" title="Filter by type">
                                <option value="">All types</option>
                                <option v-for="(k, key) in kinds" :key="key" :value="key">[[ k.label ]]</option>
                            </select>
                            <select class="form-select form-select-sm" v-model="testFilter" style="width:auto;" title="Filter by last test">
                                <option value="">Any test status</option>
                                <option value="ok">Test passed</option>
                                <option value="failed">Test failed</option>
                                <option value="never">Never tested</option>
                            </select>
                        </template>

                        <template #cell-is_active="{ item }">
                            <input class="form-check-input" type="radio" name="ai-active-provider"
                                   :checked="item.is_active" :disabled="!canEdit || activating"
                                   :title="item.is_active ? 'Active provider' : 'Make this the active provider'"
                                   @change="activate(item)">
                        </template>

                        <template #cell-name="{ item, highlight }">
                            <span class="ap-name" v-html="highlight(item.name)"></span>
                            <span v-if="item.is_active" class="ap-pill ap-pill--blue ms-1">active</span>
                        </template>

                        <template #cell-kind="{ item }">
                            <span class="ap-text"><i class="fa-solid" :class="kindIcon(item.kind)"></i>[[ kindLabel(item.kind) ]]</span>
                        </template>

                        <template #cell-base_url="{ item, highlight }">
                            <span class="ap-pill me-1" :class="item.is_local ? 'ap-pill--green' : 'ap-pill--orange'">
                                <i class="fa-solid" :class="item.is_local ? 'fa-house' : 'fa-globe'"></i>
                                [[ item.is_local ? 'local' : 'external' ]]
                            </span>
                            <span class="ap-url" v-html="highlight(item.base_url || kinds[item.kind]?.default_url || '')"></span>
                        </template>

                        <template #cell-default_model="{ item, highlight }">
                            <span class="ap-text" v-html="highlight(item.default_model || '—')"></span>
                        </template>

                        <template #cell-api_key_hint="{ item }">
                            <span v-if="item.has_api_key" class="ap-text" :title="item.api_key_hint"><i class="fa-solid fa-lock" style="color:#198754;"></i>[[ item.api_key_hint ]]</span>
                            <span v-else class="ap-text">—</span>
                        </template>

                        <template #cell-monthly_budget_usd="{ item }">
                            <div class="d-flex align-items-center gap-2">
                                <button class="ap-test-btn" :disabled="budgetLoading === item.id"
                                        :title="budgets[item.id] ? 'Refresh' : 'Show the spending of this month'" @click="loadBudget(item)">
                                    <i class="fa-solid" :class="budgetLoading === item.id ? 'fa-spinner fa-spin' : 'fa-gauge-high'"></i>
                                </button>
                                <template v-if="budgets[item.id]">
                                    <span v-if="budgets[item.id].free" class="ap-pill ap-pill--grey"><i class="fa-solid fa-house"></i>Free (local)</span>
                                    <div v-else-if="budgets[item.id].budget" class="ap-budget" :title="budgetTitle(budgets[item.id])">
                                        <div class="ap-budget__bar"><div :class="'ap-budget__fill ap-budget__fill--' + budgetLevel(budgets[item.id])"
                                             :style="{ width: budgets[item.id].remaining_pct + '%' }"></div></div>
                                        <span class="ap-text">[[ budgets[item.id].remaining_pct ]]% left</span>
                                    </div>
                                    <span v-else class="ap-text" :title="budgetTitle(budgets[item.id])">
                                        [[ budgets[item.id].priced ? fmtUsd(budgets[item.id].spent) + ' spent · no budget' : 'price unknown' ]]
                                    </span>
                                </template>
                                <span v-else-if="item.monthly_budget_usd" class="ap-text">[[ fmtUsd(item.monthly_budget_usd) ]]/mo</span>
                            </div>
                        </template>

                        <template #cell-last_test_at="{ item }">
                            <div class="d-flex align-items-center gap-2">
                                <span v-if="item.last_test_ok === true" class="ap-pill ap-pill--green"
                                      :title="item.last_test_message + ' — ' + fmtDate(item.last_test_at)">
                                    <i class="fa-solid fa-circle-check"></i>Tested · [[ fmtDate(item.last_test_at) ]]
                                </span>
                                <span v-else-if="item.last_test_ok === false" class="ap-pill ap-pill--red"
                                      :title="item.last_test_message">
                                    <i class="fa-solid fa-circle-xmark"></i>Failed · [[ fmtDate(item.last_test_at) ]]
                                </span>
                                <span v-else class="ap-pill ap-pill--grey">
                                    <i class="fa-solid fa-circle-question"></i>Never tested
                                </span>
                                <button v-if="canEdit" class="ap-test-btn"
                                        :disabled="testingId === item.id" title="Test the saved settings" @click="testSaved(item)">
                                    <i class="fa-solid" :class="testingId === item.id ? 'fa-spinner fa-spin' : 'fa-plug'"></i>
                                </button>
                            </div>
                        </template>

                        <template #expand="{ item }">
                            <div class="ap-text d-flex flex-column gap-1 p-2">
                                <div><strong>Last test:</strong> [[ item.last_test_message || 'never run' ]]</div>
                                <div><strong>Sending content outside the network:</strong>
                                    [[ item.is_local ? 'not needed (local)' : (item.remote_allowed ? 'allowed' : 'not allowed — cannot be activated') ]]</div>
                                <div v-if="item.workspace_id"><strong>Workspace:</strong> [[ item.workspace_id ]]</div>
                                <div><strong>Updated:</strong> [[ fmtDate(item.updated_at) || '—' ]]</div>
                            </div>
                        </template>
                    </data-table>

                    <div v-if="!canEdit" class="small text-muted mt-2">
                        <i class="fa-solid fa-lock me-1"></i>Only administrators can add, edit or activate providers.
                    </div>
                </template>
            </div>

                <!-- Add / edit modal -->
                <teleport to="body">
                    <div class="modal fade" id="ai-provider-modal" tabindex="-1" aria-hidden="true" ref="modalEl">
                        <div class="modal-dialog modal-dialog-centered modal-lg">
                            <div class="modal-content border-0 shadow-lg" style="border-radius:16px;background:var(--card-bg-color);color:var(--text-color);">
                                <div class="modal-header border-0 pb-0">
                                    <h6 class="modal-title fw-bold">
                                        <i class="fa-solid me-2 text-primary" :class="form && form.id ? 'fa-pen' : 'fa-plus-circle'"></i>
                                        [[ form && form.id ? 'Edit provider' : 'New AI provider' ]]
                                    </h6>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                </div>
                                <div class="modal-body" v-if="form">
                        <div class="row g-3">
                            <div class="col-md-4">
                                <label class="form-label small fw-semibold mb-1">Type</label>
                                <select class="form-select form-select-sm" v-model="form.kind" @change="onKindChange">
                                    <option v-for="(k, key) in kinds" :key="key" :value="key">[[ k.label ]]</option>
                                </select>
                            </div>
                            <div class="col-md-8">
                                <label class="form-label small fw-semibold mb-1">Name
                                    <span class="fw-normal text-muted ms-1" style="font-size:.72rem;"><kbd>Tab</kbd> in an empty field fills in the grey suggestion</span>
                                </label>
                                <input type="text" class="form-control form-control-sm" v-model.trim="form.name" maxlength="128"
                                       :placeholder="suggest.name" @keydown.tab="tabFill('name', $event)">
                            </div>
                            <div class="col-md-7">
                                <label class="form-label small fw-semibold mb-1">Endpoint URL</label>
                                <input type="text" class="form-control form-control-sm" v-model.trim="form.base_url"
                                       :placeholder="suggest.base_url" @keydown.tab="tabFill('base_url', $event)">
                                <div class="form-text" style="font-size:.72rem;">Empty = [[ kinds[form.kind]?.default_url ]]</div>
                            </div>
                            <div class="col-md-5">
                                <label class="form-label small fw-semibold mb-1">Default model</label>
                                <input type="text" class="form-control form-control-sm" v-model.trim="form.default_model"
                                       list="ai-provider-models" :placeholder="suggest.default_model" @keydown.tab="tabFill('default_model', $event)">
                                <datalist id="ai-provider-models">
                                    <option v-for="m in testedModels" :key="m" :value="m"></option>
                                </datalist>
                            </div>
                            <div class="col-md-7">
                                <label class="form-label small fw-semibold mb-1">
                                    API key <span v-if="!kinds[form.kind]?.needs_key" class="fw-normal text-muted">(optional)</span>
                                </label>
                                <input type="password" class="form-control form-control-sm" v-model="form.api_key"
                                       autocomplete="new-password" spellcheck="false"
                                       :placeholder="form.has_api_key ? 'A key is stored — leave empty to keep it' : 'Paste the key'">
                                <div v-if="form.has_api_key" class="form-check mt-1">
                                    <input class="form-check-input" type="checkbox" id="ai-provider-clear-key" v-model="form.clear_api_key">
                                    <label class="form-check-label small" for="ai-provider-clear-key">Remove the stored key</label>
                                </div>
                                <div v-if="urlChanged && form.has_api_key && !form.api_key" class="small text-warning mt-1">
                                    <i class="fa-solid fa-triangle-exclamation me-1"></i>
                                    The endpoint changed: the stored key will be deleted on save (it is never sent to a new host). Re-enter it.
                                </div>
                            </div>
                        </div>

                        <div v-if="form.kind === 'anthropic'" class="row g-3 mt-0">
                            <div class="col-md-7">
                                <label class="form-label small fw-semibold mb-1">Workspace ID <span class="fw-normal text-muted">(optional)</span></label>
                                <input type="text" class="form-control form-control-sm" v-model.trim="form.workspace_id" maxlength="128"
                                       placeholder="wrkspc_…" spellcheck="false">
                                <div class="form-text" style="font-size:.72rem;">
                                    Only for an organization-level key (error “not scoped to a workspace”). Found in the
                                    Claude console → Settings → Workspaces. A key created inside a workspace doesn't need it.
                                </div>
                            </div>
                        </div>

                        <div v-if="form.kind !== 'ollama'" class="rounded-3 border p-3 mt-3" style="background:var(--card-bg-color);">
                            <div class="small fw-semibold mb-2"><i class="fa-solid fa-gauge-high me-1"></i>Monthly budget</div>
                            <div class="row g-2">
                                <div class="col-md-4">
                                    <label class="form-label small mb-1">Budget (USD / month)</label>
                                    <input type="number" min="0" step="1" class="form-control form-control-sm" v-model="form.monthly_budget_usd" placeholder="e.g. 20">
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label small mb-1">Input price (USD / 1M tokens)</label>
                                    <input type="number" min="0" step="0.01" class="form-control form-control-sm" v-model="form.price_input_per_mtok"
                                           :placeholder="form.kind === 'anthropic' ? 'auto (Claude prices)' : 'required to count cost'">
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label small mb-1">Output price (USD / 1M tokens)</label>
                                    <input type="number" min="0" step="0.01" class="form-control form-control-sm" v-model="form.price_output_per_mtok"
                                           :placeholder="form.kind === 'anthropic' ? 'auto (Claude prices)' : 'required to count cost'">
                                </div>
                            </div>
                            <div class="form-check mt-2">
                                <input class="form-check-input" type="checkbox" id="ai-provider-block" v-model="form.block_over_budget">
                                <label class="form-check-label small" for="ai-provider-block">Stop AI calls once the budget is used up</label>
                            </div>
                            <div class="form-text" style="font-size:.72rem;">
                                Counted by Rulezet from the tokens of its own calls this month — the provider doesn't expose your
                                remaining credit, and other uses of the same key aren't included.
                            </div>
                        </div>

                        <div v-if="formIsExternal" class="rounded-3 border p-3 mt-3" style="background:var(--card-bg-color);">
                            <div class="form-check mb-1">
                                <input class="form-check-input" type="checkbox" id="ai-provider-remote" v-model="form.remote_allowed">
                                <label class="form-check-label small fw-semibold" for="ai-provider-remote">Allow sending content to this service</label>
                            </div>
                            <div class="small text-muted">
                                <i class="fa-solid fa-triangle-exclamation text-warning me-1"></i>
                                [[ externalHost ]] is outside this server's network. When this provider is active, rule content,
                                bundle material and chatbot messages are sent to it. Only enable this for a service you trust.
                            </div>
                        </div>

                        <div v-if="testResult" class="alert py-2 px-3 mt-3 mb-0" style="font-size:.82rem;"
                             :class="testResult.success ? 'alert-success' : 'alert-danger'">
                            <template v-if="testResult.success">
                                <i class="fa-solid fa-circle-check me-1"></i>Connected — [[ testResult.models.length ]] model(s):
                                <span>[[ testResult.models.slice(0, 15).join(', ') || '—' ]][[ testResult.models.length > 15 ? '…' : '' ]]</span>
                            </template>
                            <template v-else><i class="fa-solid fa-circle-xmark me-1"></i>[[ testResult.error ]]</template>
                        </div>

                                </div>
                                <div class="modal-footer border-0 pt-0 justify-content-end gap-2" v-if="form">
                                    <button class="btn btn-light rounded-pill px-4 btn-sm" data-bs-dismiss="modal">Cancel</button>
                                    <button class="btn btn-outline-secondary rounded-pill px-3 btn-sm" :disabled="testing || blockedByConsent" @click="test">
                                        <i class="fa-solid me-1" :class="testing ? 'fa-spinner fa-spin' : 'fa-plug'"></i>Test connection
                                    </button>
                                    <button class="btn btn-primary rounded-pill px-4 btn-sm" :disabled="saving || !form.name" @click="save">
                                        <i class="fa-solid me-1" :class="saving ? 'fa-spinner fa-spin' : 'fa-floppy-disk'"></i>Save
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </teleport>
        </div>
    `,

    setup(props, { emit }) {
        const loading    = ref(true)
        const saving     = ref(false)
        const testing    = ref(false)
        const activating = ref(false)
        const kinds      = ref({})
        const canEdit    = ref(false)
        const form       = ref(null)
        const original   = reactive({ kind: '', base_url: '' })
        const testResult = ref(null)
        const loadError  = ref('')
        const tableRef   = ref(null)
        const kindFilter = ref('')
        const testFilter = ref('')
        const testingId  = ref(null)
        const budgets    = reactive({})
        const budgetLoading = ref(null)
        const fmtUsd = v => '$' + Number(v || 0).toFixed(Number(v || 0) < 10 ? 2 : 0)
        const budgetLevel = b => b.remaining_pct > 50 ? 'ok' : (b.remaining_pct > 20 ? 'warn' : 'low')
        const budgetTitle = b => `${fmtUsd(b.spent)} spent this month` + (b.budget ? ` of ${fmtUsd(b.budget)}` : '')
            + ` · ${b.calls} call(s), ${b.input_tokens.toLocaleString()} in / ${b.output_tokens.toLocaleString()} out tokens`
            + (b.blocking ? ' · calls stop at 100%' : '')

        async function loadBudget(p) {
            budgetLoading.value = p.id
            try {
                const res = await fetch(`/ai/admin/providers/${p.id}/budget`)
                if (res.ok) budgets[p.id] = await res.json()
                else create_message('Could not load the budget', 'danger-subtle')
            } finally {
                budgetLoading.value = null
            }
        }
        const fetchUrl   = computed(() => {
            const q = new URLSearchParams()
            if (kindFilter.value) q.set('kind', kindFilter.value)
            if (testFilter.value) q.set('test', testFilter.value)
            const qs = q.toString()
            return '/ai/admin/providers/data' + (qs ? '?' + qs : '')
        })
        const columns = [
            { key: 'is_active',     label: 'Active',        sortable: true, width: '70px' },
            { key: 'name',          label: 'Name',          sortable: true },
            { key: 'kind',          label: 'Type',          sortable: true },
            { key: 'base_url',      label: 'Endpoint',      sortable: true },
            { key: 'default_model', label: 'Default model', sortable: true },
            { key: 'api_key_hint',  label: 'API key' },
            { key: 'monthly_budget_usd', label: 'Budget',   sortable: true },
            { key: 'last_test_at',  label: 'Last test',     sortable: true },
            { key: 'created_at',    label: 'Added',         sortable: true, type: 'date' },
        ]
        const fmtDate = iso => iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : ''
        const refresh = () => tableRef.value?.fetchData()
        const modalEl    = ref(null)
        let modal = null

        function openModal() {
            nextTick(() => {
                if (!modal && modalEl.value) {
                    modal = new bootstrap.Modal(modalEl.value)
                    // Closing the modal forgets the form — the typed API key included.
                    modalEl.value.addEventListener('hidden.bs.modal', () => { form.value = null; testResult.value = null })
                }
                modal?.show()
            })
        }

        const kindLabel = k => kinds.value[k]?.label || k
        const kindIcon  = k => KIND_ICONS[k] || 'fa-microchip'

        const effectiveUrl   = computed(() => form.value ? (form.value.base_url || kinds.value[form.value.kind]?.default_url || '') : '')
        const formIsExternal = computed(() => !!form.value && (kinds.value[form.value.kind]?.cloud || !isLocalUrl(effectiveUrl.value)))
        const blockedByConsent = computed(() => formIsExternal.value && !form.value.remote_allowed)
        const externalHost   = computed(() => { try { return new URL(effectiveUrl.value).host } catch (e) { return effectiveUrl.value } })
        const urlChanged     = computed(() => !!form.value?.id && (form.value.kind !== original.kind
                                   || (form.value.base_url || '') !== (original.base_url || '')))
        const testedModels   = computed(() => testResult.value?.success ? testResult.value.models : [])
        // Grey suggestions shown in empty fields — Tab fills them in (tabFill).
        const suggest = computed(() => {
            const f = form.value
            if (!f) return {}
            const k = kinds.value[f.kind] || {}
            let host = ''
            try { host = new URL(f.base_url || k.default_url).hostname } catch (e) { /* not a URL yet */ }
            const tested = testedModels.value
            const pick = prefs => prefs.find(m => tested.includes(m)) || tested[0] || prefs[0] || ''
            return {
                name: f.kind === 'ollama' || f.kind === 'openai_compatible'
                    ? `${f.kind === 'ollama' ? 'Ollama' : 'Internal AI'}${host && host !== 'localhost' ? ' — ' + host : ''}`
                    : (k.label || ''),
                base_url: k.default_url || '',
                default_model: {
                    ollama:            pick(['qwen2.5:7b', 'qwen2.5:1.5b']),
                    anthropic:         pick(['claude-opus-5-5', 'claude-sonnet-5-5']),
                    openai:            pick([]),
                    openai_compatible: pick([]),
                }[f.kind] || '',
            }
        })

        function tabFill(field, event) {
            // Only plain Tab on an empty field; Shift+Tab and a second Tab move focus as usual.
            if (event.shiftKey || !form.value || form.value[field] || !suggest.value[field]) return
            event.preventDefault()
            form.value[field] = suggest.value[field]
        }

        async function load() {
            loading.value = true
            loadError.value = ''
            try {
                const res = await fetch('/ai/admin/providers')
                let data = {}
                try { data = await res.json() } catch (e) { /* HTML error page */ }
                if (res.ok) {
                    kinds.value = data.kinds || {}
                    canEdit.value = !!data.can_edit
                } else {
                    loadError.value = data.error || `Could not load the AI providers (HTTP ${res.status}) — has the database been migrated (flask db upgrade)?`
                }
            } catch (e) {
                loadError.value = 'Could not load the AI providers: ' + e
            } finally {
                loading.value = false
            }
        }

        function startCreate() {
            form.value = emptyForm()
            original.kind = ''
            original.base_url = ''
            testResult.value = null
            openModal()
        }

        function startEdit(p) {
            form.value = { ...emptyForm(), ...p, api_key: '', clear_api_key: false, base_url: p.base_url || '',
                           workspace_id: p.workspace_id || '',
                           monthly_budget_usd: p.monthly_budget_usd ?? '', price_input_per_mtok: p.price_input_per_mtok ?? '',
                           price_output_per_mtok: p.price_output_per_mtok ?? '' }
            original.kind = p.kind
            original.base_url = p.base_url || ''
            testResult.value = null
            openModal()
        }

        function cancel() {
            modal?.hide()
        }

        function onKindChange() {
            // A URL typed for another type is almost never right for this one.
            if (!form.value.id) form.value.base_url = ''
            testResult.value = null
        }

        function body() {
            const f = form.value
            return {
                id: f.id, name: f.name, kind: f.kind, base_url: f.base_url, api_key: f.api_key,
                workspace_id: f.kind === 'anthropic' ? (f.workspace_id || '') : '',
                monthly_budget_usd: f.monthly_budget_usd === '' ? null : f.monthly_budget_usd,
                price_input_per_mtok: f.price_input_per_mtok === '' ? null : f.price_input_per_mtok,
                price_output_per_mtok: f.price_output_per_mtok === '' ? null : f.price_output_per_mtok,
                block_over_budget: !!f.block_over_budget,
                clear_api_key: f.clear_api_key, default_model: f.default_model,
                remote_allowed: formIsExternal.value ? f.remote_allowed : false,
            }
        }

        async function post(url, payload, method = 'POST') {
            const res = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                body: payload ? JSON.stringify(payload) : undefined,
            })
            let data = {}
            try { data = await res.json() } catch (e) { /* non-JSON error page */ }
            return { ok: res.ok, data }
        }

        async function test() {
            testing.value = true
            testResult.value = null
            try {
                const { data } = await post('/ai/admin/providers/test', body())
                testResult.value = data.success ? { success: true, models: data.models || [] }
                                                : { success: false, error: data.error || 'Connection failed.' }
                if (data.provider) refresh()   // result recorded on the saved provider
            } catch (e) {
                testResult.value = { success: false, error: String(e) }
            } finally {
                testing.value = false
            }
        }

        async function save() {
            saving.value = true
            try {
                const f = form.value
                const { ok, data } = await post(f.id ? `/ai/admin/providers/${f.id}` : '/ai/admin/providers', body())
                if (!ok) {
                    create_message(data.error || 'Failed to save the provider', 'danger-subtle')
                    return
                }
                create_message(data.key_removed ? 'Saved — the endpoint changed, so the stored API key was deleted.' : 'Provider saved',
                               data.key_removed ? 'warning-subtle' : 'success-subtle')
                form.value.api_key = ''   // never keep the key around in the page
                modal?.hide()
                refresh()
                emit('changed')
            } finally {
                saving.value = false
            }
        }

        async function activate(p) {
            if (p.is_active) return
            const external = !p.is_local
            const msg = external
                ? `Make "${p.name}" the active provider?\n\nEvery AI feature will then send rule content and messages to ${p.base_url || kindLabel(p.kind)}.`
                : `Make "${p.name}" the active provider for every AI feature?`
            if (!confirm(msg)) { refresh(); return }
            activating.value = true
            try {
                const { ok, data } = await post(`/ai/admin/providers/${p.id}/activate`)
                if (ok) create_message(`"${p.name}" is now the active AI provider`, 'success-subtle')
                else create_message(data.error || 'Failed to activate', 'danger-subtle')
                refresh()
                if (ok) emit('changed')
            } finally {
                activating.value = false
            }
        }

        async function testSaved(p) {
            testingId.value = p.id
            try {
                const { data } = await post(`/ai/admin/providers/${p.id}/test`)
                if (data.success) create_message(`"${p.name}" reachable — ${(data.models || []).length} model(s)`, 'success-subtle')
                else create_message(`"${p.name}": ${data.error || 'test failed'}`, 'danger-subtle')
                refresh()
            } finally {
                testingId.value = null
            }
        }

        async function remove(p) {
            if (!confirm(`Delete the provider "${p.name}"${p.has_api_key ? ' and its stored API key' : ''}?`)) return
            const { ok, data } = await post(`/ai/admin/providers/${p.id}`, null, 'DELETE')
            if (ok) { create_message('Provider deleted', 'success-subtle'); refresh() }
            else create_message(data.error || 'Failed to delete', 'danger-subtle')
        }

        onMounted(load)
        onUnmounted(() => { modal?.dispose(); modal = null })

        return {
            loading, loadError, modalEl, tableRef, fetchUrl, columns, kindFilter, testFilter, testingId, fmtDate,
            testSaved, budgets, budgetLoading, loadBudget, fmtUsd, budgetLevel, budgetTitle, saving, testing, activating, kinds, canEdit, form, testResult,
            kindLabel, kindIcon, formIsExternal, blockedByConsent, externalHost, urlChanged, testedModels,
            suggest, tabFill, startCreate, startEdit, cancel, onKindChange, test, save, activate, remove,
        }
    },
}
