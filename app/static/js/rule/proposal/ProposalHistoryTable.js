import PaginationComponent from '/static/js/rule/paginationComponent.js';
import UserChip from '/static/js/components/UserChip.js';
import ProposalThreadGraph from '/static/js/rule/proposal/ProposalThreadGraph.js';
import { create_message } from '/static/js/toaster.js';
import { renderMarkdown, hardenUserHtml } from '/static/js/sanitize.js';

const { ref, reactive, computed, watch, onMounted } = Vue;

/**
 * ProposalHistoryTable — edit proposals table of the Proposals page
 * (/rule/rule_propose_edit): the review queue and "My submissions".
 *
 * Same chrome as GithubProposalTable / DuplicateTable (.dt-* from
 * components/dataTable.css): toolbar (search, filters, sort, table/card
 * toggle, column picker), selection + floating bulk bar, per-page footer.
 * Unlike them it fetches its own pages — search, filters and sort run
 * server side, across every result.
 */

export const EDIT_TYPES = [
    { value: 'content_update', label: 'Content update',  icon: 'fa-solid fa-code' },
    { value: 'typo',           label: 'Typo / syntax',   icon: 'fa-solid fa-spell-check' },
    { value: 'security',       label: 'Security fix',    icon: 'fa-solid fa-shield-halved' },
    { value: 'documentation',  label: 'Documentation',   icon: 'fa-solid fa-book' },
    { value: 'legal',          label: 'Legal / license', icon: 'fa-solid fa-scale-balanced' },
    { value: 'other',          label: 'Other',           icon: 'fa-solid fa-ellipsis' },
];

const STATUSES = [
    { value: '',           label: 'All' },
    { value: 'pending',    label: 'Pending' },
    { value: 'accepted',   label: 'Accepted' },
    { value: 'rejected',   label: 'Rejected' },
    { value: 'superseded', label: 'Superseded' },
];

const SORTS = [
    { value: 'recent', label: 'Newest first' },
    { value: 'oldest', label: 'Oldest first' },
    { value: 'score',  label: 'Biggest change' },
    { value: 'rule',   label: 'Rule name (A→Z)' },
];

const COLUMNS = [
    { key: 'author',   label: 'Author',    hideable: true },
    { key: 'type',     label: 'Type',      hideable: true },
    { key: 'change',   label: 'Change',    hideable: true },
    { key: 'comments', label: 'Comments',  hideable: true },
    { key: 'status',   label: 'Status',    hideable: false },
    { key: 'date',     label: 'Submitted', hideable: true },
    { key: 'reviewer', label: 'Reviewed by', hideable: true },
];

function readPrefs(key) {
    try { return JSON.parse(localStorage.getItem(key) || '{}') || {}; } catch { return {}; }
}
function writePrefs(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage unavailable */ }
}

const ProposalHistoryTable = {
    name: 'ProposalHistoryTable',
    delimiters: ['[[', ']]'],
    components: { 'pagination-component': PaginationComponent, UserChip, ProposalThreadGraph },
    props: {
        csrfToken:      { type: String, required: true },
        apiEndpoint:    { type: String, required: true },
        submitEndpoint: { type: String, default: '/rule/manage_proposals' },
        // review: proposals on the user's rules (all of them for an admin),
        // with accept / reject; mine: the user's own submissions.
        mode:           { type: String, default: 'review' },
        statusCounts:   { type: Object, default: () => ({}) },
        currentUserId:  { type: Number, default: null },
    },
    emits: ['view-diff', 'decision-made'],
    setup(props, { emit }) {
        const canManage = props.mode === 'review';
        const prefsKey = `rz-proposals-v2-${props.mode}`;
        const prefs = readPrefs(prefsKey);

        const items = ref([]);
        const loading = ref(false);
        const loaded = ref(false);
        const page = ref(1);
        const totalPages = ref(1);
        const totalItems = ref(0);
        const pendingTotal = ref(0);

        const search = ref('');
        const status = ref(canManage ? 'pending' : '');
        const editType = ref('');
        const sort = ref('recent');
        const perPage = ref(prefs.perPage || 20);
        const viewMode = ref(prefs.viewMode || 'thread');   // thread | table | card
        const hiddenColumns = reactive(new Set(prefs.hidden || (props.mode === 'mine' ? ['author'] : ['reviewer'])));
        const showColPicker = ref(false);
        const expanded = reactive(new Set());

        const visibleColumns = computed(() => COLUMNS.filter(c => !hiddenColumns.has(c.key)));
        const colspan = computed(() => visibleColumns.value.length + 3);

        watch([perPage, viewMode, () => [...hiddenColumns]], () => {
            writePrefs(prefsKey, { perPage: perPage.value, viewMode: viewMode.value, hidden: [...hiddenColumns] });
        });

        // ── Fetch ─────────────────────────────────────────────────────────
        let fetchSeq = 0;
        async function fetchPage(p = 1) {
            const seq = ++fetchSeq;
            loading.value = true;
            try {
                const params = new URLSearchParams({
                    page: p, per_page: perPage.value, search: search.value.trim(),
                    group: viewMode.value === 'thread' ? 'thread' : '',
                    status: status.value, edit_type: editType.value, sort: sort.value,
                });
                const res = await fetch(`${props.apiEndpoint}?${params}`);
                if (!res.ok) throw new Error(res.status);
                const data = await res.json();
                if (seq !== fetchSeq) return;
                items.value = data.rules_list || [];
                totalPages.value = data.total_pages_old || 1;
                totalItems.value = data.total_items ?? items.value.length;
                pendingTotal.value = data.total_count ?? 0;
                page.value = p;
                expanded.clear();
                openMessages.clear();
                overflowing.clear();
                items.value.forEach(renderMessage);
            } catch (err) {
                if (seq === fetchSeq) create_message('Could not load the proposals.', 'danger-subtle');
            } finally {
                if (seq === fetchSeq) { loading.value = false; loaded.value = true; }
            }
        }

        let searchTimer = null;
        watch(search, () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => { clearSelection(); fetchPage(1); }, 350);
        });
        watch([status, editType, sort, perPage], () => { clearSelection(); fetchPage(1); });
        // The thread view pages by thread, the others by proposal.
        watch(() => viewMode.value === 'thread', () => { clearSelection(); fetchPage(1); });

        // Thread view: the page's proposals (already in thread order, see
        // get_proposal_list_threads) grouped by thread.
        const threads = computed(() => {
            const map = new Map();
            for (const p of items.value) {
                const key = p.thread_root_id || p.id;
                if (!map.has(key)) map.set(key, { id: key, rule_id: p.rule_id, rule_name: p.rule_name,
                    status: p.thread_status || 'open', versions: [], pending: 0, last: 0 });
                const t = map.get(key);
                t.versions.push({ ...p, version: p.thread_version || 1, discuss_url: discussUrl(p) });
                if (p.status === 'pending') t.pending++;
                t.last = Math.max(t.last, new Date(p.timestamp).getTime());
            }
            return [...map.values()];
        });

        function setStatus(value) { status.value = value; }
        function resetFilters() {
            search.value = ''; editType.value = ''; status.value = ''; sort.value = 'recent';
        }
        const hasFilters = computed(() => !!(search.value.trim() || editType.value || status.value));

        // ── Display helpers ───────────────────────────────────────────────
        function escapeHtml(str) {
            return String(str ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }
        function highlight(text) {
            const str = escapeHtml(text);
            const term = search.value.trim().replace(/^#/, '');
            if (!term) return str;
            const escaped = escapeHtml(term).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            return str.replace(new RegExp(`(${escaped})`, 'gi'), m => `<mark class="prp-highlight">${m}</mark>`);
        }
        function typeOf(value) {
            return EDIT_TYPES.find(t => t.value === (value || 'other')) || { value, label: value, icon: 'fa-solid fa-tag' };
        }
        // Closed because another version of its thread was accepted — older
        // rows were stored as "rejected" with an accepted revision.
        function statusKey(p) {
            if (p.status === 'superseded'
                || (p.status === 'rejected' && (p.revisions || []).some(r => r.status === 'accepted'))) return 'superseded';
            return p.status;
        }
        function formatDate(ts) {
            if (!ts) return '—';
            return new Date(ts).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
        }
        function fullDate(ts) {
            return ts ? new Date(ts).toLocaleString('en-GB') : '';
        }
        function relativeDate(ts) {
            if (!ts) return '—';
            const s = (Date.now() - new Date(ts).getTime()) / 1000;
            if (s < 60) return 'just now';
            if (s < 3600) return `${Math.floor(s / 60)} min ago`;
            if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
            if (s < 86400 * 30) return `${Math.floor(s / 86400)} d ago`;
            return formatDate(ts);
        }
        function scoreValue(p) {
            return p.change_score == null ? null : Math.round(p.change_score);
        }
        function discussUrl(p) { return `/rule/proposal_content_discuss?id=${p.id}`; }
        // Justifications are markdown, rendered in the row and clamped to a
        // few lines with a fade and a "See more" toggle (as bundle
        // descriptions) — the toggle only shows when the text overflows.
        const renderedMessages = reactive({});
        const openMessages = reactive(new Set());
        const overflowing = reactive(new Set());
        async function renderMessage(p) {
            if (!p.message || renderedMessages[p.id] !== undefined) return;
            try {
                renderedMessages[p.id] = hardenUserHtml(await renderMarkdown(p.message));
            } catch {
                renderedMessages[p.id] = null;   // falls back to plain text
            }
        }
        function messageHtml(p) {
            return renderedMessages[p.id] || `<p style="white-space:pre-wrap">${escapeHtml(p.message)}</p>`;
        }
        function measureMessage(id, el) {
            if (!el || openMessages.has(id)) return;
            requestAnimationFrame(() => {
                const over = el.scrollHeight > el.clientHeight + 4;
                if (over !== overflowing.has(id)) over ? overflowing.add(id) : overflowing.delete(id);
            });
        }
        function toggleMessage(id) { openMessages.has(id) ? openMessages.delete(id) : openMessages.add(id); }
        function toggleExpand(p) { expanded.has(p.id) ? expanded.delete(p.id) : expanded.add(p.id); }
        function toggleColumn(key) { hiddenColumns.has(key) ? hiddenColumns.delete(key) : hiddenColumns.add(key); }
        function viewDiff(p) { emit('view-diff', p); }

        // ── Selection (pending proposals only) ────────────────────────────
        const selectedIds = reactive(new Set());
        const excludedIds = reactive(new Set());
        const allMode = ref(false);

        const pendingOnPage = computed(() => items.value.filter(p => p.status === 'pending' && p.in_filter !== false));
        function isSelected(p) { return allMode.value ? p.status === 'pending' && !excludedIds.has(p.id) : selectedIds.has(p.id); }
        function toggleItem(p) {
            if (p.status !== 'pending') return;
            if (allMode.value) excludedIds.has(p.id) ? excludedIds.delete(p.id) : excludedIds.add(p.id);
            else selectedIds.has(p.id) ? selectedIds.delete(p.id) : selectedIds.add(p.id);
        }
        const allOnPageSelected = computed(() => pendingOnPage.value.length > 0 && pendingOnPage.value.every(isSelected));
        const someOnPageSelected = computed(() => !allOnPageSelected.value && pendingOnPage.value.some(isSelected));
        function togglePageSelection() {
            const select = !allOnPageSelected.value;
            pendingOnPage.value.forEach(p => { if (isSelected(p) !== select) toggleItem(p); });
        }
        function selectAllResults() { allMode.value = true; selectedIds.clear(); excludedIds.clear(); }
        function clearSelection() { allMode.value = false; selectedIds.clear(); excludedIds.clear(); }
        const selectedCount = computed(() => allMode.value ? Math.max(pendingTotal.value - excludedIds.size, 0) : selectedIds.size);
        const showSelectAllBanner = computed(() =>
            canManage && !allMode.value && allOnPageSelected.value && pendingTotal.value > pendingOnPage.value.length);

        async function submitBulk(action) {
            if (!selectedCount.value) return;
            const verb = action === 'accept' ? 'Accept' : 'Reject';
            if (!confirm(`${verb} ${selectedCount.value} proposal(s)?` +
                (action === 'accept' ? ' The rules will be updated with the proposed content.' : ''))) return;
            loading.value = true;
            try {
                const res = await fetch(props.submitEndpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({
                        action, mode: allMode.value ? 'all' : 'partial',
                        selected_ids: [...selectedIds], excluded_ids: [...excludedIds],
                        search: search.value.trim(), edit_type: editType.value,
                    }),
                });
                const result = await res.json();
                create_message(result.message, result.toast_class);
                if (res.ok) {
                    clearSelection();
                    emit('decision-made');
                }
            } catch {
                create_message('An error occurred.', 'danger-subtle');
            } finally {
                fetchPage(page.value);
            }
        }

        // ── Single decision (dialog with an optional reason) ──────────────
        const decision = reactive({ open: false, proposal: null, value: '', reason: '', busy: false });
        function openDecision(p, value) {
            Object.assign(decision, { open: true, proposal: p, value, reason: '', busy: false });
        }
        async function confirmDecision() {
            const p = decision.proposal;
            decision.busy = true;
            try {
                const res = await fetch('/rule/validate_proposal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ ruleId: p.rule_id, ruleproposalId: p.id, decision: decision.value, reason: decision.reason }),
                });
                const result = await res.json();
                create_message(res.ok && decision.value === 'accepted'
                    ? `Proposal #${p.id} accepted — "${p.rule_name}" updated to v${result.new_version}.`
                    : result.message, result.toast_class);
                if (res.ok) {
                    decision.open = false;
                    emit('decision-made');
                    fetchPage(page.value);
                }
            } catch {
                create_message('An error occurred.', 'danger-subtle');
            } finally {
                decision.busy = false;
            }
        }

        onMounted(() => fetchPage(1));

        return {
            canManage, items, loading, loaded, page, totalPages, totalItems, pendingTotal,
            search, status, editType, sort, perPage, viewMode, hiddenColumns, showColPicker, expanded, threads,
            columns: COLUMNS, visibleColumns, colspan, editTypes: EDIT_TYPES, statuses: STATUSES, sorts: SORTS,
            fetchPage, setStatus, resetFilters, hasFilters,
            highlight, typeOf, messageHtml, measureMessage, toggleMessage, openMessages, overflowing, statusKey, formatDate, fullDate, relativeDate, scoreValue, discussUrl,
            toggleExpand, toggleColumn, viewDiff,
            isSelected, toggleItem, allOnPageSelected, someOnPageSelected, togglePageSelection, pendingOnPage,
            selectAllResults, clearSelection, selectedCount, showSelectAllBanner, allMode, submitBulk,
            decision, openDecision, confirmDecision,
        };
    },
    template: `
    <div class="dt-wrapper prp-table">

        <!-- Status chips -->
        <div class="prp-status-chips mb-3">
            <button v-for="s in statuses" :key="s.value" type="button"
                class="prp-chip" :class="['prp-chip--' + (s.value || 'all'), { 'is-active': status === s.value }]"
                @click="setStatus(s.value)">
                [[ s.label ]]
                <span v-if="s.value ? statusCounts[s.value] != null : statusCounts.total != null" class="prp-chip-count">
                    [[ s.value ? statusCounts[s.value] : statusCounts.total ]]
                </span>
            </button>
        </div>

        <!-- Toolbar -->
        <div class="dt-toolbar">
            <div class="dt-toolbar-left">
                <div class="dt-search">
                    <i class="fas fa-search dt-search-icon"></i>
                    <input class="dt-search-input prp-search" type="text" v-model="search"
                        placeholder="Search rule, author, message or #id…" aria-label="Search proposals" />
                    <button v-if="search" class="dt-search-clear" @click="search = ''" aria-label="Clear search">
                        <i class="fas fa-xmark"></i>
                    </button>
                </div>
                <select v-model="editType" class="dt-toolbar-btn prp-select" aria-label="Filter by type">
                    <option value="">All types</option>
                    <option v-for="t in editTypes" :key="t.value" :value="t.value">[[ t.label ]]</option>
                </select>
                <select v-model="sort" class="dt-toolbar-btn prp-select" aria-label="Sort">
                    <option v-for="s in sorts" :key="s.value" :value="s.value">[[ s.label ]]</option>
                </select>
                <button v-if="hasFilters" class="dt-toolbar-btn" @click="resetFilters" title="Reset filters">
                    <i class="fas fa-filter-circle-xmark me-1"></i>Reset
                </button>
            </div>

            <div class="dt-toolbar-right">
                <button class="dt-toolbar-btn" @click="fetchPage(page)" title="Refresh" :disabled="loading">
                    <i class="fas fa-rotate" :class="{ 'fa-spin': loading }"></i>
                </button>
                <div class="dt-view-toggle" title="Switch view">
                    <button class="dt-view-btn" :class="{ 'dt-view-btn--active': viewMode === 'thread' }"
                        @click="viewMode = 'thread'" aria-label="Thread view" title="Threads — versions grouped with their branches"><i class="fas fa-code-branch"></i></button>
                    <button class="dt-view-btn" :class="{ 'dt-view-btn--active': viewMode === 'table' }"
                        @click="viewMode = 'table'" aria-label="Table view"><i class="fas fa-table-cells-large"></i></button>
                    <button class="dt-view-btn" :class="{ 'dt-view-btn--active': viewMode === 'card' }"
                        @click="viewMode = 'card'" aria-label="Card view"><i class="fas fa-grip"></i></button>
                </div>
                <div v-if="viewMode === 'table'" class="dt-col-picker-wrap">
                    <button class="dt-toolbar-btn" :class="{ 'dt-toolbar-btn--active': showColPicker }"
                        @click="showColPicker = !showColPicker" title="Show/hide columns"><i class="fas fa-sliders"></i></button>
                    <div v-if="showColPicker" class="dt-col-picker-dropdown">
                        <label v-for="col in columns.filter(c => c.hideable)" :key="col.key" class="dt-col-picker-item">
                            <input type="checkbox" :checked="!hiddenColumns.has(col.key)" @change="toggleColumn(col.key)" />
                            [[ col.label ]]
                        </label>
                    </div>
                </div>
            </div>
        </div>

        <div v-if="showSelectAllBanner" class="dt-select-all-banner">
            All [[ pendingOnPage.length ]] pending proposals on this page are selected.
            <button class="dt-select-all-btn" @click="selectAllResults">Select all [[ pendingTotal ]] pending proposals matching the filters</button>
        </div>
        <div v-else-if="allMode" class="dt-select-all-banner">
            All [[ selectedCount ]] pending proposals matching the filters are selected.
            <button class="dt-select-all-btn" @click="clearSelection">Clear selection</button>
        </div>

        <div class="prp-body" :class="{ 'is-loading': loading && loaded }">
            <div v-if="loading" class="dt-loading-overlay" aria-live="polite"><div class="dt-spinner"></div></div>

            <!-- ══════════ THREAD VIEW ══════════ -->
            <div v-if="viewMode === 'thread'" class="prp-threads">
                <div v-if="canManage && pendingOnPage.length" class="prp-threads-select">
                    <label class="d-inline-flex align-items-center gap-2">
                        <input type="checkbox" class="dt-checkbox" :checked="allOnPageSelected"
                            :indeterminate="someOnPageSelected" @change="togglePageSelection" />
                        Select the [[ pendingOnPage.length ]] pending proposal[[ pendingOnPage.length === 1 ? '' : 's' ]] on this page
                    </label>
                </div>
                <div v-if="!loaded" v-for="i in 3" :key="'tsk' + i" class="prp-thread"><div class="prp-skeleton" style="height:60px"></div></div>
                <div v-if="loaded && !threads.length" class="dt-empty">
                    <div class="dt-empty-icon"><i class="fas fa-code-branch"></i></div>
                    <p class="dt-empty-text">No proposals found</p>
                    <button v-if="hasFilters" class="btn btn-sm btn-outline-primary rounded-pill px-3 mt-3" @click="resetFilters">
                        <i class="fas fa-filter-circle-xmark me-1"></i>Reset filters
                    </button>
                </div>
                <div v-for="t in threads" :key="'t' + t.id" class="prp-thread" :class="'prp-thread--' + t.status">
                    <div class="prp-thread-head">
                        <div class="min-w-0">
                            <a :href="'/rule/detail_rule/' + t.rule_id" class="prp-rule-link" v-html="highlight(t.rule_name)"></a>
                            <div class="prp-thread-sub">
                                <i class="fas fa-code-branch me-1"></i>Thread #[[ t.id ]] · [[ t.versions.length ]] version[[ t.versions.length === 1 ? '' : 's' ]]
                                · last activity [[ relativeDate(t.last) ]]
                            </div>
                        </div>
                        <div class="d-flex align-items-center gap-2 flex-shrink-0">
                            <span v-if="t.pending" class="prp-status prp-status--pending">[[ t.pending ]] pending</span>
                            <span class="prp-thread-state" :class="'prp-thread-state--' + t.status">
                                <i class="fas" :class="t.status === 'accepted' ? 'fa-code-merge' : t.status === 'open' ? 'fa-code-pull-request' : 'fa-circle-xmark'"></i>
                                [[ t.status === 'accepted' ? 'Merged' : t.status === 'open' ? 'Open' : 'Closed' ]]
                            </span>
                        </div>
                    </div>
                    <proposal-thread-graph :versions="t.versions" :current-user-id="currentUserId" compact
                        :rule-url="'/rule/detail_rule/' + t.rule_id + '/history'">
                        <template #row="{ v }">
                            <div class="prp-graph-actions">
                                <input v-if="canManage && v.status === 'pending' && v.in_filter !== false" type="checkbox" class="dt-checkbox"
                                    :checked="isSelected(v)" @change="toggleItem(v)" title="Select" />
                                <span class="prp-type"><i :class="typeOf(v.edit_type).icon"></i>[[ typeOf(v.edit_type).label ]]</span>
                                <span v-if="v.comment_count" class="prp-comments"><i class="fa-regular fa-comment"></i> [[ v.comment_count ]]</span>
                                <span class="ms-auto d-inline-flex gap-1">
                                    <button class="dt-action-btn" title="View diff" @click="viewDiff(v)"><i class="fas fa-code-compare"></i></button>
                                    <a class="dt-action-btn" :href="v.discuss_url" title="Open discussion"><i class="fas fa-comments"></i></a>
                                    <template v-if="canManage && v.status === 'pending'">
                                        <button class="dt-action-btn prp-btn-accept" title="Accept" @click="openDecision(v, 'accepted')"><i class="fas fa-check"></i></button>
                                        <button class="dt-action-btn dt-action-btn--danger" title="Reject" @click="openDecision(v, 'rejected')"><i class="fas fa-xmark"></i></button>
                                    </template>
                                </span>
                            </div>
                        </template>
                    </proposal-thread-graph>
                </div>
            </div>

            <!-- ══════════ CARD VIEW ══════════ -->
            <div v-else-if="viewMode === 'card'" class="dt-card-grid">
                <div v-if="loaded && !items.length" style="grid-column: 1 / -1;">
                    <div class="dt-empty">
                        <div class="dt-empty-icon"><i class="fas fa-inbox"></i></div>
                        <p class="dt-empty-text">No proposals found</p>
                    </div>
                </div>
                <div v-for="p in items" :key="'card-' + p.id" class="dt-card prp-card"
                    :class="['prp-card--' + statusKey(p), { 'dt-card--selected': isSelected(p) }]">
                    <div class="dt-card-header">
                        <input v-if="canManage" type="checkbox" class="dt-checkbox dt-card-checkbox"
                            :checked="isSelected(p)" :disabled="p.status !== 'pending'" @change="toggleItem(p)" />
                        <a :href="discussUrl(p)" class="dt-card-title prp-rule-link" v-html="highlight(p.rule_name)"></a>
                        <span class="prp-status" :class="'prp-status--' + statusKey(p)">[[ statusKey(p) ]]</span>
                    </div>
                    <div class="dt-card-body">
                        <div class="prp-meta mb-2">
                            <span class="prp-id">#[[ p.id ]]</span>
                            <span v-if="p.thread_size > 1" class="prp-version">v[[ p.thread_version ]]</span>
                            <span class="prp-type"><i :class="typeOf(p.edit_type).icon"></i>[[ typeOf(p.edit_type).label ]]</span>
                        </div>
                        <div v-if="p.message" class="prp-msg mb-2" :class="{ 'is-open': openMessages.has(p.id), 'is-clipped': overflowing.has(p.id) && !openMessages.has(p.id) }">
                                        <div class="prp-msg-body prp-md" :ref="el => measureMessage(p.id, el)" v-html="messageHtml(p)"></div>
                                        <button v-if="overflowing.has(p.id)" type="button" class="prp-msg-more" @click="toggleMessage(p.id)">
                                            <i class="fa-solid me-1" :class="openMessages.has(p.id) ? 'fa-chevron-up' : 'fa-chevron-down'"></i>[[ openMessages.has(p.id) ? 'See less' : 'See more' ]]
                                        </button>
                                    </div>
                                    <div v-else class="prp-message"><em>No justification given.</em></div>
                        <div class="d-flex align-items-center justify-content-between gap-2 flex-wrap">
                            <user-chip :user-id="p.user_id" :username="p.user_name" :avatar="p.user_avatar" size="xs"></user-chip>
                            <span class="prp-date" :title="fullDate(p.timestamp)">[[ relativeDate(p.timestamp) ]]</span>
                        </div>
                    </div>
                    <div class="dt-card-footer">
                        <button class="dt-action-btn" title="View diff" @click="viewDiff(p)"><i class="fas fa-code-compare"></i></button>
                        <a class="dt-action-btn" :href="discussUrl(p)" title="Open discussion"><i class="fas fa-comments"></i></a>
                        <template v-if="canManage && p.status === 'pending'">
                            <button class="dt-action-btn prp-btn-accept" title="Accept" @click="openDecision(p, 'accepted')"><i class="fas fa-check"></i></button>
                            <button class="dt-action-btn dt-action-btn--danger" title="Reject" @click="openDecision(p, 'rejected')"><i class="fas fa-xmark"></i></button>
                        </template>
                    </div>
                </div>
            </div>

            <!-- ══════════ TABLE VIEW ══════════ -->
            <div v-else class="dt-table-wrap">
                <table class="dt-table" role="grid">
                    <thead class="dt-thead">
                        <tr>
                            <th class="dt-th dt-th--checkbox">
                                <input v-if="canManage" type="checkbox" class="dt-checkbox"
                                    :checked="allOnPageSelected" :indeterminate="someOnPageSelected"
                                    :disabled="!pendingOnPage.length" @change="togglePageSelection" aria-label="Select page" />
                            </th>
                            <th class="dt-th">Proposal</th>
                            <th v-for="col in visibleColumns" :key="col.key" class="dt-th">[[ col.label ]]</th>
                            <th class="dt-th dt-th--actions">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-if="loaded && !items.length">
                            <td :colspan="colspan">
                                <div class="dt-empty">
                                    <div class="dt-empty-icon"><i class="fas fa-inbox"></i></div>
                                    <p class="dt-empty-text">No proposals found</p>
                                    <button v-if="hasFilters" class="btn btn-sm btn-outline-primary rounded-pill px-3 mt-3" @click="resetFilters">
                                        <i class="fas fa-filter-circle-xmark me-1"></i>Reset filters
                                    </button>
                                </div>
                            </td>
                        </tr>
                        <tr v-if="!loaded" v-for="i in 5" :key="'sk' + i" class="dt-row">
                            <td :colspan="colspan" class="dt-td"><div class="prp-skeleton"></div></td>
                        </tr>

                        <template v-for="p in items" :key="p.id">
                            <tr class="dt-row prp-row" :class="['prp-row--' + statusKey(p), { 'dt-row--selected': isSelected(p), 'dt-row--expanded': expanded.has(p.id) }]">
                                <td class="dt-td dt-td--checkbox">
                                    <input v-if="canManage && p.status === 'pending'" type="checkbox" class="dt-checkbox"
                                        :checked="isSelected(p)" @change="toggleItem(p)" />
                                </td>
                                <td class="dt-td prp-name-cell">
                                    <div class="d-flex align-items-center gap-2 flex-wrap">
                                        <a :href="discussUrl(p)" class="prp-rule-link" v-html="highlight(p.rule_name)"></a>
                                        <span class="prp-id">#[[ p.id ]]</span>
                                        <span v-if="p.thread_size > 1" class="prp-version" title="Level in its thread (v1 = the first proposal, v2 = a revision of it…)">v[[ p.thread_version ]]</span>
                                    </div>
                                    <div v-if="p.message" class="prp-msg mt-1" :class="{ 'is-open': openMessages.has(p.id), 'is-clipped': overflowing.has(p.id) && !openMessages.has(p.id) }">
                                        <div class="prp-msg-body prp-md" :ref="el => measureMessage(p.id, el)" v-html="messageHtml(p)"></div>
                                        <button v-if="overflowing.has(p.id)" type="button" class="prp-msg-more" @click="toggleMessage(p.id)">
                                            <i class="fa-solid me-1" :class="openMessages.has(p.id) ? 'fa-chevron-up' : 'fa-chevron-down'"></i>[[ openMessages.has(p.id) ? 'See less' : 'See more' ]]
                                        </button>
                                    </div>
                                    <div v-else class="prp-message"><em>No justification given.</em></div>
                                </td>
                                <td v-if="!hiddenColumns.has('author')" class="dt-td">
                                    <user-chip :user-id="p.user_id" :username="p.user_name" :avatar="p.user_avatar" size="xs"></user-chip>
                                </td>
                                <td v-if="!hiddenColumns.has('type')" class="dt-td">
                                    <span class="prp-type"><i :class="typeOf(p.edit_type).icon"></i>[[ typeOf(p.edit_type).label ]]</span>
                                </td>
                                <td v-if="!hiddenColumns.has('change')" class="dt-td">
                                    <div v-if="scoreValue(p) != null" class="prp-score" :title="'Similarity with the current rule: ' + scoreValue(p) + '%'">
                                        <div class="prp-score-bar"><div :style="{ width: scoreValue(p) + '%' }"></div></div>
                                        <span>[[ scoreValue(p) ]]%</span>
                                    </div>
                                    <span v-else class="text-muted">—</span>
                                </td>
                                <td v-if="!hiddenColumns.has('comments')" class="dt-td">
                                    <a :href="discussUrl(p)" class="prp-comments" :class="{ 'is-empty': !p.comment_count }">
                                        <i class="fa-regular fa-comment"></i> [[ p.comment_count || 0 ]]
                                    </a>
                                </td>
                                <td v-if="!hiddenColumns.has('status')" class="dt-td">
                                    <span class="prp-status" :class="'prp-status--' + statusKey(p)">[[ statusKey(p) ]]</span>
                                    <button v-if="p.rejection_reason" type="button" class="prp-note-btn" @click="toggleExpand(p)"
                                        :title="'Reviewer’s note: ' + p.rejection_reason"><i class="fa-regular fa-note-sticky"></i></button>
                                </td>
                                <td v-if="!hiddenColumns.has('date')" class="dt-td text-nowrap">
                                    <span class="prp-date" :title="fullDate(p.timestamp)">[[ relativeDate(p.timestamp) ]]</span>
                                </td>
                                <td v-if="!hiddenColumns.has('reviewer')" class="dt-td">
                                    <user-chip v-if="p.reviewed_by_id" :user-id="p.reviewed_by_id" :username="p.reviewed_by_name" :avatar="p.reviewed_by_avatar" size="xs"></user-chip>
                                    <span v-else class="text-muted">—</span>
                                </td>
                                <td class="dt-td dt-td--actions">
                                    <div class="dt-actions">
                                        <button class="dt-action-btn" title="View diff" @click="viewDiff(p)"><i class="fas fa-code-compare"></i></button>
                                        <template v-if="canManage && p.status === 'pending'">
                                            <button class="dt-action-btn prp-btn-accept" title="Accept" @click="openDecision(p, 'accepted')"><i class="fas fa-check"></i></button>
                                            <button class="dt-action-btn dt-action-btn--danger" title="Reject" @click="openDecision(p, 'rejected')"><i class="fas fa-xmark"></i></button>
                                        </template>
                                        <button class="dt-action-btn dt-action-btn--expand" :class="{ 'is-expanded': expanded.has(p.id) }"
                                            title="Details" @click="toggleExpand(p)"><i class="fas fa-chevron-down dt-expand-chevron"></i></button>
                                    </div>
                                </td>
                            </tr>

                            <!-- Expanded details -->
                            <tr v-if="expanded.has(p.id)" class="prp-detail-row">
                                <td :colspan="colspan" class="dt-expand-cell">
                                    <div class="row g-3">
                                        <div class="col-lg-7">
                                            <template v-if="p.rejection_reason">
                                                <div class="prp-detail-label" :class="p.status === 'accepted' ? 'text-success' : 'text-danger'">
                                                    Reviewer's note<template v-if="p.reviewed_by_name"> — [[ p.reviewed_by_name ]]</template>
                                                </div>
                                                <p class="prp-detail-text">[[ p.rejection_reason ]]</p>
                                            </template>
                                            <div class="d-flex flex-wrap gap-2">
                                                <a v-if="p.previous_proposal" :href="p.previous_proposal.discuss_url" class="prp-lineage">
                                                    <i class="fas fa-code-branch"></i>Revision of #[[ p.previous_proposal.id ]]
                                                </a>
                                                <a v-for="r in (p.revisions || [])" :key="r.id" :href="r.discuss_url" class="prp-lineage prp-lineage--next">
                                                    <i class="fas fa-code-branch"></i>Revised in #[[ r.id ]] ([[ r.status ]])
                                                </a>
                                            </div>
                                        </div>
                                        <div class="col-lg-5">
                                            <div class="dt-expand-grid mb-3">
                                                <div class="dt-expand-field"><label>Submitted</label><span>[[ fullDate(p.timestamp) ]]</span></div>
                                                <div class="dt-expand-field"><label>Reviewed</label><span>[[ p.reviewed_at ? fullDate(p.reviewed_at) : 'Not yet' ]]</span></div>
                                                <div class="dt-expand-field"><label>Rule</label><span><a :href="'/rule/detail_rule/' + p.rule_id">#[[ p.rule_id ]]</a></span></div>
                                                <div v-if="p.thread_size > 1" class="dt-expand-field"><label>Thread</label>
                                                    <span><a :href="'/rule/proposal_content_discuss?id=' + p.thread_root_id">#[[ p.thread_root_id ]]</a> · [[ p.thread_size ]] versions</span></div>
                                            </div>
                                            <div class="d-flex gap-2 flex-wrap">
                                                <a :href="discussUrl(p)" class="btn btn-sm btn-primary rounded-pill px-3">
                                                    <i class="fas fa-comments me-1"></i>Open discussion
                                                </a>
                                                <button class="btn btn-sm btn-outline-primary rounded-pill px-3" @click="viewDiff(p)">
                                                    <i class="fas fa-code-compare me-1"></i>View diff
                                                </button>
                                                <a :href="'/rule/detail_rule/' + p.rule_id" class="btn btn-sm btn-outline-secondary rounded-pill px-3">
                                                    <i class="fas fa-arrow-up-right-from-square me-1"></i>Rule
                                                </a>
                                            </div>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </template>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="dt-footer">
            <div class="dt-per-page">
                <span>Per page</span>
                <select v-model.number="perPage" aria-label="Items per page">
                    <option v-for="n in [10, 20, 50, 100]" :key="n" :value="n">[[ n ]]</option>
                </select>
            </div>
            <div class="dt-footer-center">
                <pagination-component v-if="totalPages > 1" :current-page="page" :total-pages="totalPages" @change-page="fetchPage"></pagination-component>
            </div>
            <div class="dt-footer-info">[[ totalItems ]] [[ viewMode === 'thread' ? 'thread' : 'proposal' ]][[ totalItems === 1 ? '' : 's' ]]</div>
        </div>

        <!-- Bulk bar -->
        <transition name="dt-bulk-slide">
            <div v-if="canManage && selectedCount > 0" class="dt-bulk-bar">
                <span class="dt-bulk-count">[[ selectedCount ]] selected</span>
                <div class="dt-bulk-actions">
                    <button class="dt-bulk-btn prp-bulk-accept" :disabled="loading" @click="submitBulk('accept')">
                        <i class="fas fa-check"></i> Accept
                    </button>
                    <button class="dt-bulk-btn dt-bulk-btn--danger" :disabled="loading" @click="submitBulk('reject')">
                        <i class="fas fa-xmark"></i> Reject
                    </button>
                </div>
                <button class="dt-bulk-clear" @click="clearSelection"><i class="fas fa-xmark"></i> Clear</button>
            </div>
        </transition>

        <!-- Decision dialog -->
        <teleport to="body">
            <div v-if="decision.open" class="prp-dialog-backdrop" @click.self="decision.open = false">
                <div class="prp-dialog" role="dialog" aria-modal="true">
                    <div class="d-flex align-items-center gap-3 mb-3">
                        <div class="prp-dialog-icon" :class="decision.value === 'accepted' ? 'is-accept' : 'is-reject'">
                            <i class="fas" :class="decision.value === 'accepted' ? 'fa-check' : 'fa-xmark'"></i>
                        </div>
                        <div>
                            <h5 class="fw-bold mb-0">[[ decision.value === 'accepted' ? 'Accept' : 'Reject' ]] proposal #[[ decision.proposal.id ]]</h5>
                            <div class="small text-muted">[[ decision.proposal.rule_name ]] · by [[ decision.proposal.user_name ]]</div>
                        </div>
                    </div>
                    <p v-if="decision.value === 'accepted'" class="small mb-3">
                        The rule content is replaced by the proposed one and its version is bumped.
                        The other open versions of this thread are closed as <strong>superseded</strong>.
                    </p>
                    <p v-else class="small mb-3">The author is notified. They can still revise the proposal afterwards.</p>
                    <label class="form-label small fw-semibold">Note for the author (optional)</label>
                    <textarea v-model="decision.reason" class="form-control mb-1" rows="3" maxlength="2000"
                        :placeholder="decision.value === 'accepted' ? 'Thanks — merged with…' : 'Why is this change not merged?'"></textarea>
                    <div class="small text-muted mb-3">Shown on the proposal, in its conversation and in the author's notification.</div>
                    <div class="d-flex justify-content-end gap-2">
                        <button class="btn btn-outline-secondary rounded-pill px-3" @click="decision.open = false">Cancel</button>
                        <button class="btn rounded-pill px-4" :class="decision.value === 'accepted' ? 'btn-success' : 'btn-danger'"
                            :disabled="decision.busy" @click="confirmDecision">
                            <span v-if="decision.busy" class="spinner-border spinner-border-sm me-1"></span>
                            [[ decision.value === 'accepted' ? 'Accept & update rule' : 'Reject proposal' ]]
                        </button>
                    </div>
                </div>
            </div>
        </teleport>
    </div>
    `
};

export default ProposalHistoryTable;
