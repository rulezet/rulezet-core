import UserChip from '/static/js/components/UserChip.js';
import PaginationComponent from '/static/js/rule/paginationComponent.js';
import { create_message } from '/static/js/toaster.js';

const { ref, reactive, computed, watch, onMounted } = Vue;

/**
 * AIRequestsTable — users' requests for an AI analysis, on the Rule /
 * Bundle Analysis admin pages (/ai/admin/rule-analysis, bundle-analysis).
 *
 * Same chrome as the other admin tables (.dt-* from components/dataTable.css):
 * status chips, search, selection + floating bulk bar, "select all pending
 * matching". Accepting asks for the model / visibility once, then queues the
 * analyses (one job per script for rules, one per bundle) — see
 * app/features/ai/ai_request_core.py.
 */

const SCRIPT_LABELS = {
    standard: { label: 'Standard analysis', icon: 'fa-list-check' },
    deep:     { label: 'In-depth report',   icon: 'fa-book-open' },
    full:     { label: 'Full bundle review', icon: 'fa-layer-group' },
};

const AIRequestsTable = {
    name: 'AIRequestsTable',
    delimiters: ['[[', ']]'],
    components: { UserChip, 'pagination-component': PaginationComponent },
    props: {
        targetType: { type: String, required: true },          // rule | bundle
        csrfToken:  { type: String, required: true },
    },
    emits: ['decided'],
    setup(props, { emit }) {
        const items = ref([]);
        const counts = ref({ pending: 0, accepted: 0, rejected: 0 });
        const loading = ref(false);
        const loaded = ref(false);
        const page = ref(1);
        const pages = ref(1);
        const total = ref(0);
        const status = ref('pending');
        const search = ref('');
        const perPage = ref(20);

        const base = `/ai/admin/requests/${props.targetType}`;
        const modelsUrl = props.targetType === 'rule' ? '/rule/ai_analysis/models' : '/bundle/ai_analysis/models';

        async function fetchPage(p = 1) {
            loading.value = true;
            try {
                const params = new URLSearchParams({ page: p, per_page: perPage.value, status: status.value, q: search.value.trim() });
                const res = await fetch(`${base}/data?${params}`);
                if (!res.ok) throw new Error(res.status);
                const data = await res.json();
                items.value = data.items || [];
                counts.value = data.counts || counts.value;
                total.value = data.total || 0;
                pages.value = data.pages || 1;
                page.value = p;
            } catch {
                create_message('Could not load the requests.', 'danger-subtle');
            } finally {
                loading.value = false;
                loaded.value = true;
            }
        }

        let timer = null;
        watch(search, () => { clearTimeout(timer); timer = setTimeout(() => { clearSelection(); fetchPage(1); }, 350); });
        watch([status, perPage], () => { clearSelection(); fetchPage(1); });

        // ── Selection (pending only) ──
        const selected = reactive(new Set());
        const allMode = ref(false);
        const pendingOnPage = computed(() => items.value.filter(r => r.status === 'pending'));
        const isSelected = r => (allMode.value ? r.status === 'pending' : selected.has(r.id));
        function toggle(r) {
            if (r.status !== 'pending' || allMode.value) return;
            selected.has(r.id) ? selected.delete(r.id) : selected.add(r.id);
        }
        const allOnPage = computed(() => pendingOnPage.value.length > 0 && pendingOnPage.value.every(isSelected));
        const someOnPage = computed(() => !allOnPage.value && pendingOnPage.value.some(isSelected));
        function togglePage() {
            if (allMode.value) return clearSelection();
            const on = !allOnPage.value;
            pendingOnPage.value.forEach(r => (on ? selected.add(r.id) : selected.delete(r.id)));
        }
        function clearSelection() { allMode.value = false; selected.clear(); }
        const pendingMatching = computed(() => (status.value === 'pending' ? total.value : counts.value.pending));
        const selectedCount = computed(() => (allMode.value ? pendingMatching.value : selected.size));
        const showSelectAll = computed(() => !allMode.value && allOnPage.value && pendingMatching.value > pendingOnPage.value.length);

        // ── Decision dialog (accept: model + visibility; both: note) ──
        const dialog = reactive({ open: false, action: '', ids: null, all: false, count: 0,
                                  note: '', model: '', models: [], defaultPublic: true, busy: false, modelsLoaded: false });
        async function loadModels() {
            if (dialog.modelsLoaded) return;
            try {
                const res = await fetch(modelsUrl);
                if (res.ok) {
                    const data = await res.json();
                    dialog.models = data.models || [];
                    dialog.model = data.default_model && dialog.models.includes(data.default_model)
                        ? data.default_model : (dialog.models[0] || '');
                }
            } catch { /* the job falls back to the agent's default model */ }
            dialog.modelsLoaded = true;
        }
        function openDialog(action, request = null) {
            Object.assign(dialog, {
                open: true, action, note: '', busy: false,
                ids: request ? [request.id] : (allMode.value ? null : [...selected]),
                all: !request && allMode.value,
                count: request ? 1 : selectedCount.value,
            });
            if (action === 'accept') loadModels();
        }
        async function confirm() {
            dialog.busy = true;
            try {
                const res = await fetch(`${base}/decide`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({
                        action: dialog.action, ids: dialog.ids, all: dialog.all, q: search.value.trim(),
                        model: dialog.model || null, default_public: dialog.defaultPublic, note: dialog.note,
                    }),
                });
                const data = await res.json();
                create_message(data.message, data.toast_class || (res.ok ? 'success' : 'danger'));
                if (res.ok) {
                    dialog.open = false;
                    clearSelection();
                    emit('decided', data);
                    fetchPage(page.value);
                }
            } catch {
                create_message('An error occurred.', 'danger-subtle');
            } finally {
                dialog.busy = false;
            }
        }

        const scriptOf = s => SCRIPT_LABELS[s] || { label: s, icon: 'fa-robot' };
        const fmt = ts => (ts ? new Date(ts).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—');

        onMounted(() => fetchPage(1));

        return {
            items, counts, loading, loaded, page, pages, total, status, search, perPage,
            fetchPage, isSelected, toggle, allOnPage, someOnPage, togglePage, clearSelection, allMode,
            selectedCount, showSelectAll, pendingOnPage, pendingMatching,
            dialog, openDialog, confirm, scriptOf, fmt,
            selectAll: () => { allMode.value = true; selected.clear(); },
        };
    },
    template: `
    <div class="dt-wrapper air-table">
        <div class="air-chips mb-3">
            <button v-for="s in ['pending', 'accepted', 'rejected', '']" :key="s || 'all'" type="button"
                class="air-chip" :class="{ 'is-active': status === s }" @click="status = s">
                [[ s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All' ]]
                <span class="air-chip-count">[[ s ? counts[s] : counts.pending + counts.accepted + counts.rejected ]]</span>
            </button>
        </div>

        <div class="dt-toolbar">
            <div class="dt-toolbar-left">
                <div class="dt-search">
                    <i class="fas fa-search dt-search-icon"></i>
                    <input class="dt-search-input" type="text" v-model="search"
                        :placeholder="'Search ' + targetType + ', requester or message…'" aria-label="Search requests" />
                    <button v-if="search" class="dt-search-clear" @click="search = ''" aria-label="Clear search"><i class="fas fa-xmark"></i></button>
                </div>
            </div>
            <div class="dt-toolbar-right">
                <button class="dt-toolbar-btn" @click="fetchPage(page)" :disabled="loading" title="Refresh">
                    <i class="fas fa-rotate" :class="{ 'fa-spin': loading }"></i>
                </button>
                <button v-if="pendingMatching" class="dt-toolbar-btn dt-toolbar-btn--primary" @click="selectAll(); openDialog('accept')"
                    :title="'Accept the ' + pendingMatching + ' pending requests matching the search'">
                    <i class="fas fa-check-double me-1"></i>Accept all pending ([[ pendingMatching ]])
                </button>
            </div>
        </div>

        <div v-if="showSelectAll" class="dt-select-all-banner">
            All [[ pendingOnPage.length ]] pending requests on this page are selected.
            <button class="dt-select-all-btn" @click="selectAll">Select all [[ pendingMatching ]] pending requests</button>
        </div>
        <div v-else-if="allMode" class="dt-select-all-banner">
            All [[ selectedCount ]] pending requests are selected.
            <button class="dt-select-all-btn" @click="clearSelection">Clear selection</button>
        </div>

        <div class="dt-table-wrap position-relative">
            <div v-if="loading && loaded" class="dt-loading-overlay"><div class="dt-spinner"></div></div>
            <table class="dt-table">
                <thead class="dt-thead">
                    <tr>
                        <th class="dt-th dt-th--checkbox">
                            <input type="checkbox" class="dt-checkbox" :checked="allOnPage || allMode" :indeterminate="someOnPage"
                                :disabled="!pendingOnPage.length" @change="togglePage" aria-label="Select page" />
                        </th>
                        <th class="dt-th">[[ targetType === 'rule' ? 'Rule' : 'Bundle' ]]</th>
                        <th class="dt-th">Analysis</th>
                        <th class="dt-th">Requested by</th>
                        <th class="dt-th">Message</th>
                        <th class="dt-th">Requested</th>
                        <th class="dt-th">Status</th>
                        <th class="dt-th dt-th--actions">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-if="loaded && !items.length">
                        <td colspan="8"><div class="dt-empty">
                            <div class="dt-empty-icon"><i class="fas fa-inbox"></i></div>
                            <p class="dt-empty-text">[[ status === 'pending' ? 'No request waiting — all caught up.' : 'No requests.' ]]</p>
                        </div></td>
                    </tr>
                    <tr v-for="r in items" :key="r.id" class="dt-row" :class="{ 'dt-row--selected': isSelected(r), 'air-row--pending': r.status === 'pending' }">
                        <td class="dt-td dt-td--checkbox">
                            <input v-if="r.status === 'pending'" type="checkbox" class="dt-checkbox" :checked="isSelected(r)"
                                :disabled="allMode" @change="toggle(r)" />
                        </td>
                        <td class="dt-td air-target">
                            <a v-if="r.target_title" :href="r.target_url" class="air-target-link">[[ r.target_title ]]</a>
                            <span v-else class="text-muted fst-italic">deleted</span>
                            <span v-if="r.target_format" class="air-format">[[ r.target_format ]]</span>
                        </td>
                        <td class="dt-td"><span class="air-script"><i class="fa-solid" :class="scriptOf(r.script).icon"></i>[[ scriptOf(r.script).label ]]</span></td>
                        <td class="dt-td">
                            <user-chip v-if="r.user_id" :user-id="r.user_id" :username="r.user_name" :avatar="r.user_avatar" size="xs"></user-chip>
                            <span v-else class="text-muted">—</span>
                        </td>
                        <td class="dt-td air-message" :title="r.message || ''">[[ r.message || '—' ]]</td>
                        <td class="dt-td text-nowrap small">[[ fmt(r.created_at) ]]</td>
                        <td class="dt-td">
                            <span class="air-status" :class="'air-status--' + r.status">[[ r.status ]]</span>
                            <div v-if="r.decided_by_name" class="air-decided">by [[ r.decided_by_name ]]</div>
                            <div v-if="r.decision_note" class="air-decided fst-italic" :title="r.decision_note">“[[ r.decision_note ]]”</div>
                        </td>
                        <td class="dt-td dt-td--actions">
                            <div class="dt-actions">
                                <template v-if="r.status === 'pending'">
                                    <button class="dt-action-btn air-btn-accept" title="Accept — queue the analysis" @click="openDialog('accept', r)"><i class="fas fa-check"></i></button>
                                    <button class="dt-action-btn dt-action-btn--danger" title="Reject" @click="openDialog('reject', r)"><i class="fas fa-xmark"></i></button>
                                </template>
                                <a v-if="r.job_uuid" class="dt-action-btn" :href="'/jobs/detail/' + r.job_uuid" title="Open the analysis job"><i class="fas fa-gears"></i></a>
                                <a v-if="r.target_title" class="dt-action-btn" :href="r.target_url" title="Open the AI Analysis section"><i class="fas fa-arrow-up-right-from-square"></i></a>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="dt-footer">
            <div class="dt-per-page">
                <span>Per page</span>
                <select v-model.number="perPage"><option v-for="n in [10, 20, 50, 100]" :key="n" :value="n">[[ n ]]</option></select>
            </div>
            <div class="dt-footer-center">
                <pagination-component v-if="pages > 1" :current-page="page" :total-pages="pages" @change-page="fetchPage"></pagination-component>
            </div>
            <div class="dt-footer-info">[[ total ]] request[[ total === 1 ? '' : 's' ]]</div>
        </div>

        <transition name="dt-bulk-slide">
            <div v-if="selectedCount > 0 && !dialog.open" class="dt-bulk-bar">
                <span class="dt-bulk-count">[[ selectedCount ]] selected</span>
                <div class="dt-bulk-actions">
                    <button class="dt-bulk-btn air-bulk-accept" @click="openDialog('accept')"><i class="fas fa-check"></i> Accept &amp; analyse</button>
                    <button class="dt-bulk-btn dt-bulk-btn--danger" @click="openDialog('reject')"><i class="fas fa-xmark"></i> Reject</button>
                </div>
                <button class="dt-bulk-clear" @click="clearSelection"><i class="fas fa-xmark"></i> Clear</button>
            </div>
        </transition>

        <teleport to="body">
            <div v-if="dialog.open" class="air-dialog-backdrop" @click.self="dialog.open = false">
                <div class="air-dialog" role="dialog" aria-modal="true">
                    <h5 class="fw-bold mb-1">
                        <i class="fa-solid me-1" :class="dialog.action === 'accept' ? 'fa-wand-magic-sparkles text-primary' : 'fa-xmark text-danger'"></i>
                        [[ dialog.action === 'accept' ? 'Accept and analyse' : 'Reject' ]] [[ dialog.count ]] request[[ dialog.count === 1 ? '' : 's' ]]
                    </h5>
                    <p class="small text-muted mb-3" v-if="dialog.action === 'accept'">
                        <template v-if="targetType === 'rule'">The requested rules are analysed in the background — one job per analysis type (standard / in-depth).</template>
                        <template v-else>One review job is queued per bundle.</template>
                        The requesters are notified.
                    </p>
                    <p class="small text-muted mb-3" v-else>The requesters are notified, with your note if you write one.</p>
                    <template v-if="dialog.action === 'accept'">
                        <div class="row g-2 mb-3">
                            <div class="col-sm-7">
                                <label class="form-label small mb-1">Model</label>
                                <select class="form-select form-select-sm" v-model="dialog.model" :disabled="!dialog.models.length">
                                    <option v-if="!dialog.models.length" value="">Agent default</option>
                                    <option v-for="m in dialog.models" :key="m" :value="m">[[ m ]]</option>
                                </select>
                            </div>
                            <div class="col-sm-5 d-flex align-items-end">
                                <div class="form-check form-switch mb-1">
                                    <input class="form-check-input" type="checkbox" id="air-public" v-model="dialog.defaultPublic">
                                    <label class="form-check-label small" for="air-public">Public immediately</label>
                                </div>
                            </div>
                        </div>
                    </template>
                    <label class="form-label small fw-semibold">Note for the requesters (optional)</label>
                    <textarea v-model="dialog.note" class="form-control mb-3" rows="2" maxlength="2000"
                        :placeholder="dialog.action === 'accept' ? 'Queued — thanks for the suggestion!' : 'Why this analysis is not run'"></textarea>
                    <div class="d-flex justify-content-end gap-2">
                        <button class="btn btn-outline-secondary rounded-pill px-3" @click="dialog.open = false; if (dialog.all) clearSelection()">Cancel</button>
                        <button class="btn rounded-pill px-4" :class="dialog.action === 'accept' ? 'btn-primary' : 'btn-danger'"
                            :disabled="dialog.busy" @click="confirm">
                            <span v-if="dialog.busy" class="spinner-border spinner-border-sm me-1"></span>
                            [[ dialog.action === 'accept' ? 'Accept & queue analysis' : 'Reject' ]]
                        </button>
                    </div>
                </div>
            </div>
        </teleport>
    </div>
    `,
};

export default AIRequestsTable;
