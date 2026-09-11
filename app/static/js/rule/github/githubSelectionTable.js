import PaginationComponent from '/static/js/rule/paginationComponent.js';
import GithubFilter from '/static/js/rule/github/githubFilter.js';
import GithubActionModal from '/static/js/rule/github/githubActionModal.js';
import JobTracker from '/static/js/jobs/JobTracker.js';
import { message_list, create_message } from '/static/js/toaster.js'

// Columns hidden behind the column-picker (same pattern as ruleList.js) —
// URL/Rules/Actions stay always visible, everything else is optional.
const TOGGLEABLE_COLS = [
    { key: 'author',    label: 'Author' },
    { key: 'formats',   label: 'Formats' },
    { key: 'license',   label: 'License' },
    { key: 'cves',      label: 'CVEs' },
    { key: 'conflicts', label: 'Conflicts' },
    { key: 'imported',  label: 'Imported' },
    { key: 'updated',   label: 'Updated' },
]

const GitHubSelectionTable = {
    props: {
        apiEndpoint: { type: String, required: true },
        submitEndpoint: { type: String, required: true },
        csrfToken: { type: String, required: true },
        currentUserIsAdmin: {
            type: [Boolean, String], set: v => v === 'true' || v === true
        }
    },
    delimiters: ['[[', ']]'],
    components: {
        'pagination-component': PaginationComponent,
        'github-filter': GithubFilter,
        'github-action-modal': GithubActionModal,
        'job-tracker': JobTracker,
    },
    data() {
        return {
            githubUrls: [],
            totalUrls: 0,
            currentPage: 1,
            totalPages: 1,
            loading: false,
            selectedIds: new Set(),
            excludedIds: new Set(),
            isAllSelectedMode: false,
            expandedRows: new Set(),
            isActionLoading: false,

            sortKey: 'url',
            sortDir: 'asc',
            colVisible: Object.fromEntries(TOGGLEABLE_COLS.map(c => [c.key, true])),
            showColPicker: false,
            colPickerStyle: {},

            // ── Job tracking per repo URL ─────────────────────────────────────
            // { [url]: jobUuid }  — tracks active delete jobs per repo
            activeDeleteJobs: {},

            // Bulk delete was removed from the UI — bulk actions are
            // export-only now (a single repo can still be deleted from its
            // own row). Kept as an object (not a hardcoded template) in case
            // another bulk action joins export later.
            activeAction: {
                type: 'export',
                title: 'Export Repositories',
                icon: 'fa-file-export',
                variant: 'primary',
                confirmText: 'Start Export'
            }
        };
    },
    computed: {
        TOGGLEABLE_COLS() {
            return TOGGLEABLE_COLS;
        },
        tableColspan() {
            let n = 4; // checkbox + URL + Rules + Actions (chevron lives inside Actions now)
            for (const col of TOGGLEABLE_COLS) if (this.colVisible[col.key]) n++;
            return n;
        },
        isAdmin() {
            return this.currentUserIsAdmin === 'true' || this.currentUserIsAdmin === true;
        },
        selectedCount() {
            if (this.isAllSelectedMode) {
                return this.totalUrls - this.excludedIds.size;
            }
            return this.selectedIds.size;
        },
        isPageFullySelected() {
            if (this.githubUrls.length === 0) return false;
            return this.githubUrls.every(item => this.isItemChecked(item.url));
        },
        showSelectBanner() {
            if (this.githubUrls.length === 0) return false;
            if (this.isAllSelectedMode) return true;
            return this.isPageFullySelected && this.totalUrls > this.githubUrls.length;
        },
        actionPayload() {
            const filter = this.$refs.filter || {};
            return {
                mode: this.isAllSelectedMode ? 'all' : 'partial',
                search_query: filter.searchQuery || '',
                search_field: filter.searchField || 'url',
                format_filter: filter.selectedFormat || '',
                author_filter: filter.authorQuery || '',
                selected_ids: Array.from(this.selectedIds),
                excluded_ids: Array.from(this.excludedIds)
            };
        }
    },
    mounted() {
        document.addEventListener('click', this.handleColPickerOutsideClick);
    },
    beforeUnmount() {
        document.removeEventListener('click', this.handleColPickerOutsideClick);
    },
    methods: {
        setSort(key) {
            if (this.sortKey === key) {
                this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                this.sortKey = key;
                this.sortDir = 'asc';
            }
            this.$refs.filter.fetchUrls(1);
        },

        sortIcon(key) {
            if (this.sortKey !== key) return 'fa-sort';
            return this.sortDir === 'asc' ? 'fa-sort-up' : 'fa-sort-down';
        },

        toggleColumn(key) {
            this.colVisible[key] = !this.colVisible[key];
        },

        positionColPicker() {
            const btn = this.$refs.colPickerBtn;
            if (!btn) return;
            const rect = btn.getBoundingClientRect();
            this.colPickerStyle = {
                position: 'fixed',
                top: (rect.bottom + 4) + 'px',
                right: (window.innerWidth - rect.right) + 'px',
                zIndex: 1071,
                minWidth: '165px',
                borderRadius: '12px',
            };
        },

        toggleColPicker() {
            if (!this.showColPicker) this.positionColPicker();
            this.showColPicker = !this.showColPicker;
        },

        handleColPickerOutsideClick(e) {
            if (!this.showColPicker) return;
            if (this.$refs.colPickerBtn && this.$refs.colPickerBtn.contains(e.target)) return;
            this.showColPicker = false;
        },

        handleSearchResults(data) {
            this.githubUrls = data.github_url.map(item => ({ ...item, isUpdating: false }));
            this.totalUrls = data.total_url;
            this.totalPages = data.total_pages;
            this.currentPage = data.current_page;
        },

        changePage(page) {
            this.$refs.filter.fetchUrls(page);
        },

        toggleRow(url) {
            if (this.expandedRows.has(url)) this.expandedRows.delete(url);
            else this.expandedRows.add(url);
        },

        updateSelection(itemUrl, isChecked) {
            if (this.isAllSelectedMode) {
                if (!isChecked) this.excludedIds.add(itemUrl);
                else this.excludedIds.delete(itemUrl);
            } else {
                if (isChecked) this.selectedIds.add(itemUrl);
                else this.selectedIds.delete(itemUrl);
            }
        },

        isItemChecked(itemUrl) {
            if (this.isAllSelectedMode) return !this.excludedIds.has(itemUrl);
            return this.selectedIds.has(itemUrl);
        },

        toggleAllOnPage(event) {
            const checked = event.target.checked;
            this.githubUrls.forEach(item => this.updateSelection(item.url, checked));
        },

        toggleGlobalSelectAll() {
            this.isAllSelectedMode = true;
            this.selectedIds.clear();
            this.excludedIds.clear();
        },

        clearSelection() {
            this.isAllSelectedMode = false;
            this.selectedIds.clear();
            this.excludedIds.clear();
        },

        handleActionSuccess(result) {
            this.clearSelection();
            setTimeout(() => this.changePage(this.currentPage), 1500);
        },

        openExportModal() {
            const modal = new bootstrap.Modal(document.getElementById('githubActionModal'));
            modal.show();
        },

        // ── Single repo delete — smart: sync if small, job if large ──────────
        async deleteSingleRepo(url) {
            this.isActionLoading = true;
            try {
                const res = await fetch(`/rule/delete_all_rule_github?url=${encodeURIComponent(url)}`);
                const data = await res.json();

                if (data.status === 'job_queued') {
                    // large delete → background job
                    create_message(
                        `${data.message} — tracking in background.`,
                        'info-subtle'
                    );
                    // store job uuid so the row can show a tracker
                    this.activeDeleteJobs = {
                        ...this.activeDeleteJobs,
                        [url]: data.job_uuid
                    };
                    // mark rule_count as "deleting" in the row
                    const repo = this.githubUrls.find(u => u.url === url);
                    if (repo) repo.rule_count = 'Deleting…';

                } else if (res.status === 202 || data.status === 'done') {
                    // small delete → already done
                    create_message(data.message, 'success-subtle');
                    const repo = this.githubUrls.find(u => u.url === url);
                    if (repo) repo.rule_count = 0;
                    setTimeout(() => this.changePage(1), 2000);

                } else {
                    create_message(data.message || 'Error during deletion.', 'danger-subtle');
                }

            } catch (err) {
                console.error('Deletion request failed', err);
                create_message('Network error. Could not reach the server.', 'danger-subtle');
            } finally {
                this.isActionLoading = false;
            }
        },

        // called by job-tracker @done event for a delete job
        onDeleteJobDone(url, job) {
            create_message(
                `Deletion complete — ${job.done.toLocaleString()} rule(s) removed.`,
                'success-subtle'
            );
            // remove from tracking and refresh after a short delay
            const jobs = { ...this.activeDeleteJobs };
            delete jobs[url];
            this.activeDeleteJobs = jobs;
            setTimeout(() => this.changePage(1), 1500);
        },

        onDeleteJobFailed(url, job) {
            create_message(`Deletion job failed: ${job.error}`, 'danger-subtle');
            const jobs = { ...this.activeDeleteJobs };
            delete jobs[url];
            this.activeDeleteJobs = jobs;
        },

        async updateSingleRepo(item) {
            if (!confirm(`Check for updates for: ${item.url}?`)) return;
            item.isUpdating = true;
            try {
                const response = await fetch('/rule/check_updates_by_url', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({ url: [{ url: item.url }] }),
                });
                if (response.status === 201) {
                    const data = await response.json();
                    window.location.href = '/rule/update_loading/' + data.session_uuid;
                } else {
                    const errorData = await response.json();
                    alert(errorData.message || 'Error starting update check');
                    item.isUpdating = false;
                }
            } catch (err) {
                console.error('Update check failed', err);
                item.isUpdating = false;
            }
        },
    },

    template: `
    <div class="dt-wrapper">
        <github-filter
            ref="filter"
            :api-endpoint="apiEndpoint"
            :sort-key="sortKey"
            :sort-dir="sortDir"
            @update:results="handleSearchResults"
            @loading="val => loading = val">
            <template #toolbar-extra>
                <div class="dt-col-picker-wrap">
                    <button class="dt-toolbar-btn" ref="colPickerBtn"
                            :class="{ 'dt-toolbar-btn--active': showColPicker }"
                            @click.stop="toggleColPicker" aria-label="Toggle columns">
                        <i class="fas fa-table-columns"></i>
                        <span>Columns</span>
                    </button>
                    <teleport to="body">
                        <ul v-if="showColPicker"
                            class="dropdown-menu show shadow border-0 py-2"
                            :style="colPickerStyle" @click.stop>
                            <li v-for="col in TOGGLEABLE_COLS" :key="col.key">
                                <label class="dropdown-item rounded-2 d-flex align-items-center gap-2"
                                       style="cursor:pointer;font-size:.84rem;user-select:none;">
                                    <input type="checkbox"
                                           :checked="colVisible[col.key]"
                                           @change="toggleColumn(col.key)" />
                                    [[ col.label ]]
                                </label>
                            </li>
                        </ul>
                    </teleport>
                </div>
            </template>
        </github-filter>

        <!-- ── Select-all-pages banner (RuleList pattern): checking the page
             header checkbox only ever selects what's on this page; this
             banner is the one place that offers to extend that to every
             matching repository. ── -->
        <div v-if="showSelectBanner" class="rl-select-banner">
            <span v-if="!isAllSelectedMode">
                All [[ githubUrls.length ]] repositories on this page are selected.
            </span>
            <span v-else>All [[ totalUrls ]] repositories are selected.</span>
            <button v-if="!isAllSelectedMode" class="rl-select-banner-btn" @click="toggleGlobalSelectAll">
                Select all [[ totalUrls ]] repositories
            </button>
            <button class="rl-select-banner-btn" @click="clearSelection">Clear selection</button>
        </div>

        <div class="dt-table-wrap position-relative">
            <div v-if="loading" class="dt-loading-overlay">
                <div class="dt-spinner"></div>
            </div>
            <table class="dt-table" role="grid">
                <thead class="dt-thead">
                    <tr>
                        <th class="dt-th dt-th--checkbox">
                            <input type="checkbox" class="dt-checkbox"
                                   :checked="isPageFullySelected"
                                   @change="toggleAllOnPage">
                        </th>
                        <th class="dt-th dt-th--sortable"
                            :class="{ 'dt-th--sorted': sortKey === 'url' }"
                            @click="setSort('url')">
                            <div class="dt-th-inner">
                                Repository <i class="fas dt-sort-icon" :class="sortIcon('url')"></i>
                            </div>
                        </th>
                        <th v-show="colVisible.author" class="dt-th dt-th--sortable"
                            :class="{ 'dt-th--sorted': sortKey === 'author' }"
                            @click="setSort('author')">
                            <div class="dt-th-inner">
                                Author <i class="fas dt-sort-icon" :class="sortIcon('author')"></i>
                            </div>
                        </th>
                        <th class="dt-th text-center dt-th--sortable"
                            :class="{ 'dt-th--sorted': sortKey === 'rule_count' }"
                            @click="setSort('rule_count')">
                            <div class="dt-th-inner" style="justify-content:center;">
                                Rules <i class="fas dt-sort-icon" :class="sortIcon('rule_count')"></i>
                            </div>
                        </th>
                        <th v-show="colVisible.formats" class="dt-th">Formats</th>
                        <th v-show="colVisible.license" class="dt-th">License</th>
                        <th v-show="colVisible.cves" class="dt-th text-center dt-th--sortable"
                            :class="{ 'dt-th--sorted': sortKey === 'cve_count' }"
                            @click="setSort('cve_count')">
                            <div class="dt-th-inner" style="justify-content:center;">
                                CVEs <i class="fas dt-sort-icon" :class="sortIcon('cve_count')"></i>
                            </div>
                        </th>
                        <th v-show="colVisible.conflicts" class="dt-th text-center">Conflicts</th>
                        <th v-show="colVisible.imported" class="dt-th">Imported</th>
                        <th v-show="colVisible.updated" class="dt-th">Updated</th>
                        <th class="dt-th text-end">Actions</th>
                    </tr>
                </thead>
                <tbody v-if="!loading">
                    <template v-for="(item, index) in githubUrls" :key="item.url">
                        <tr class="dt-row"
                            :class="{ 'dt-row--selected': isItemChecked(item.url), 'dt-row--expanded': expandedRows.has(item.url) }"
                            style="cursor:pointer"
                            @click="toggleRow(item.url)">
                            <td class="dt-td dt-td--checkbox" @click.stop>
                                <input type="checkbox" class="dt-checkbox"
                                       :checked="isItemChecked(item.url)"
                                       @change="updateSelection(item.url, $event.target.checked)">
                            </td>
                            <td class="dt-td">
                                <div class="d-flex align-items-center">
                                    <div class="bg-light rounded p-2 me-3 flex-shrink-0">
                                        <i class="fab fa-github fa-lg"></i>
                                    </div>
                                    <div class="fw-bold text-dark" style="word-break:break-all;">[[ item.url ]]</div>
                                </div>
                            </td>
                            <td v-show="colVisible.author" class="dt-td">[[ item.author || '—' ]]</td>
                            <td class="dt-td text-center">
                                <span class="badge bg-primary-soft text-primary rounded-pill px-3">
                                    [[ item.rule_count ]]
                                </span>
                            </td>
                            <td v-show="colVisible.formats" class="dt-td">
                                <span v-for="fmt in item.formats" :key="fmt" class="badge border text-dark fw-normal me-1">[[ fmt ]]</span>
                                <span v-if="!item.formats.length" class="text-muted small">—</span>
                            </td>
                            <td v-show="colVisible.license" class="dt-td">
                                <span v-for="lic in item.licenses" :key="lic" class="badge border text-dark fw-normal me-1">[[ lic ]]</span>
                                <span v-if="!item.licenses || !item.licenses.length" class="text-muted small">—</span>
                            </td>
                            <td v-show="colVisible.cves" class="dt-td text-center">[[ item.cve_count ]]</td>
                            <td v-show="colVisible.conflicts" class="dt-td text-center">
                                <span v-if="item.has_conflicts" class="badge bg-danger" title="High similarity (&gt;90%) with another rule">
                                    <i class="fas fa-triangle-exclamation"></i>
                                </span>
                                <span v-else class="text-muted small">—</span>
                            </td>
                            <td v-show="colVisible.imported" class="dt-td">[[ item.last_import ? item.last_import.date : '—' ]]</td>
                            <td v-show="colVisible.updated" class="dt-td">[[ item.last_update ? item.last_update.date : 'Never' ]]</td>
                            <td class="dt-td dt-td--actions" @click.stop>
                                <div class="dt-actions justify-content-end">
                                    <template v-if="isAdmin">
                                        <button class="dt-action-btn dt-action-btn--danger"
                                                data-bs-toggle="modal"
                                                :data-bs-target="'#delete_repo_modal_' + index"
                                                title="Delete Repository">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </template>

                                    <!-- Delete confirmation modal (single repo — bulk delete was removed) -->
                                    <div class="modal fade" :id="'delete_repo_modal_' + index"
                                         tabindex="-1" aria-hidden="true">
                                        <div class="modal-dialog modal-dialog-centered">
                                            <div class="modal-content border-0 shadow-lg"
                                                 style="border-radius:15px">
                                                <div class="modal-header border-0 pb-0">
                                                    <h5 class="modal-title fw-bold">Confirm Deletion</h5>
                                                    <button type="button" class="btn-close"
                                                            data-bs-dismiss="modal"></button>
                                                </div>
                                                <div class="modal-body py-4 text-center">
                                                    <div class="text-danger mb-3">
                                                        <i class="fas fa-exclamation-triangle fa-3x"></i>
                                                    </div>
                                                    <p class="mb-0 text-dark">
                                                        Delete all rules for:<br>
                                                        <strong class="text-break">[[ item.url ]]</strong>?
                                                    </p>
                                                    <!-- warn if large -->
                                                    <div v-if="item.rule_count > 200"
                                                         class="alert alert-info border-0 small rounded-3 mt-3 mb-0 text-start">
                                                        <i class="fas fa-info-circle me-1"></i>
                                                        <strong>[[ item.rule_count ]] rules</strong> — this will run
                                                        as a background job. You can track progress on the
                                                        <a href="/jobs/list" target="_blank">Jobs page</a>.
                                                    </div>
                                                </div>
                                                <div class="modal-footer border-0 pt-0">
                                                    <button type="button" class="btn btn-light rounded-pill px-4"
                                                            data-bs-dismiss="modal">Cancel</button>
                                                    <button class="btn btn-danger rounded-pill px-4"
                                                            @click="deleteSingleRepo(item.url)"
                                                            data-bs-dismiss="modal">
                                                        Confirm Delete
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <a :href="'/rule/github_detail?url=' + encodeURIComponent(item.url)"
                                       class="dt-action-btn" title="View Details">
                                        <i class="fas fa-external-link-alt"></i>
                                    </a>
                                    <template v-if="isAdmin">
                                        <button class="dt-action-btn"
                                                @click="updateSingleRepo(item)"
                                                :disabled="item.isUpdating"
                                                title="Check for updates">
                                            <i class="fas fa-sync-alt"
                                               :class="{'fa-spin': item.isUpdating}"></i>
                                        </button>
                                    </template>

                                    <!-- Expand: always last -->
                                    <button class="dt-action-btn dt-action-btn--expand"
                                            :class="{ 'is-expanded': expandedRows.has(item.url) }"
                                            title="Expand" @click="toggleRow(item.url)">
                                        <i class="fas fa-chevron-down dt-expand-chevron" style="font-size:.65rem;"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>

                        <!-- ── Expanded detail row ── -->
                        <tr v-if="expandedRows.has(item.url)" class="dt-row-expand">
                            <td :colspan="tableColspan" class="dt-expand-cell">
                                    <div class="animate__animated animate__fadeIn">

                                        <!-- ── Job tracker (shown when a delete job is active) ── -->
                                        <div v-if="activeDeleteJobs[item.url]"
                                             class="card border-0 shadow-sm rounded-4 mb-3 border-danger">
                                            <div class="card-body p-3">
                                                <h6 class="fw-bold mb-3 text-danger">
                                                    <i class="fas fa-trash me-2"></i>Deletion in progress
                                                </h6>
                                                <job-tracker
                                                    :job-uuid="activeDeleteJobs[item.url]"
                                                    @done="onDeleteJobDone(item.url, $event)"
                                                    @failed="onDeleteJobFailed(item.url, $event)"
                                                    @deleted="() => { const j = {...activeDeleteJobs}; delete j[item.url]; activeDeleteJobs = j; }">
                                                </job-tracker>
                                            </div>
                                        </div>

                                        <div class="d-flex justify-content-between align-items-center mb-3">
                                            <h6 class="fw-bold mb-0">
                                                <i class="fas fa-info-circle me-2"></i>Repository Analysis
                                            </h6>
                                            <span v-if="item.has_conflicts"
                                                  class="badge bg-danger animate__animated animate__pulse animate__infinite">
                                                <i class="fas fa-exclamation-triangle me-1"></i>
                                                High Similarity Detected (&gt;90%)
                                            </span>
                                            <span v-else class="badge bg-success">
                                                <i class="fas fa-check-circle me-1"></i> No Duplicate Conflicts
                                            </span>
                                        </div>

                                        <div class="row g-3">
                                            <div class="col-md-4">
                                                <div class="p-3 border rounded h-100">
                                                    <small class="text-muted d-block mb-2 text-uppercase fw-bold"
                                                           style="font-size:0.7rem">Detected Formats</small>
                                                    <div class="d-flex flex-wrap gap-1">
                                                        <span v-for="fmt in item.formats" :key="fmt"
                                                              class="badge border text-dark fw-normal">
                                                            [[ fmt ]]
                                                        </span>
                                                        <span v-if="!item.formats.length"
                                                              class="text-muted small">None</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="col-md-4">
                                                <div class="p-3 border rounded h-100 d-flex flex-column justify-content-center">
                                                    <small class="text-muted d-block mb-1 text-uppercase fw-bold"
                                                           style="font-size:0.7rem">CVE Identifiers</small>
                                                    <div class="d-flex align-items-center">
                                                        <h4 class="mb-0 fw-bold text-primary">[[ item.cve_count ]]</h4>
                                                        <i class="fas fa-bug ms-2 text-muted"></i>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="col-md-4">
                                                <div class="p-3 border rounded h-100">
                                                    <small class="text-muted d-block mb-2 text-uppercase fw-bold"
                                                           style="font-size:0.7rem">Repository Link</small>
                                                    <a :href="item.url" target="_blank"
                                                       class="btn btn-sm btn-outline-dark w-100 text-truncate">
                                                        <i class="fab fa-github me-2"></i>Open on GitHub
                                                    </a>
                                                </div>
                                            </div>
                                        </div>

                                        <div class="row g-4 mt-1">
                                            <div class="col-md-6" v-if="item.last_import">
                                                <div class="p-3 border-0 rounded-4 shadow-sm h-100">
                                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                                        <div class="d-flex align-items-center mb-3">
                                                            <div class="bg-success-soft rounded-circle p-2 me-2">
                                                                <i class="fas fa-file-import text-success"></i>
                                                            </div>
                                                            <small class="text-muted text-uppercase fw-bold"
                                                                   style="font-size:0.75rem">Latest Import</small>
                                                        </div>
                                                        <a v-if="item.last_import.url_imported"
                                                           :href="item.last_import.url_imported"
                                                           class="btn btn-sm btn-link text-success p-1"
                                                           title="View Import Details">
                                                            <i class="fas fa-external-link-alt"></i>
                                                        </a>
                                                    </div>
                                                    <div class="vstack gap-2">
                                                        <div class="d-flex justify-content-between">
                                                            <span class="small text-muted">
                                                                <i class="far fa-calendar-alt me-1"></i>Date
                                                            </span>
                                                            <span class="small fw-bold">[[ item.last_import.date ]]</span>
                                                        </div>
                                                        <hr class="my-1 opacity-5">
                                                        <div class="d-flex justify-content-between">
                                                            <span class="small text-muted">Imported Rules</span>
                                                            <span class="badge rounded-pill bg-success-subtle text-success border border-success-subtle px-3">
                                                                [[ item.last_import.imported ]]
                                                            </span>
                                                        </div>
                                                        <div class="d-flex justify-content-between">
                                                            <span class="small text-muted">Bad Rules</span>
                                                            <span class="badge rounded-pill"
                                                                  :class="item.last_import.bad_rules > 0
                                                                      ? 'bg-danger text-white'
                                                                      : 'bg-light text-muted px-3'">
                                                                [[ item.last_import.bad_rules ]]
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="col-md-6" v-if="item.last_update">
                                                <div class="p-3 border-0 rounded-4 shadow-sm h-100">
                                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                                        <div class="d-flex align-items-center mb-3">
                                                            <div class="bg-primary-soft rounded-circle p-2 me-2">
                                                                <i class="fas fa-sync-alt text-primary"></i>
                                                            </div>
                                                            <small class="text-muted text-uppercase fw-bold"
                                                                   style="font-size:0.75rem">Latest Update</small>
                                                        </div>
                                                        <div class="d-flex align-items-center">
                                                            <button class="btn btn-sm btn-outline-success border-0 rounded-circle me-1"
                                                                    @click="updateSingleRepo(item)"
                                                                    :disabled="item.isUpdating"
                                                                    title="Check for updates">
                                                                <i class="fas fa-sync-alt"
                                                                   :class="{'fa-spin': item.isUpdating}"></i>
                                                            </button>
                                                            <a v-if="item.last_update.url_updated"
                                                               :href="item.last_update.url_updated"
                                                               class="btn btn-sm btn-link text-primary p-1"
                                                               title="View Update Details">
                                                                <i class="fas fa-external-link-alt"></i>
                                                            </a>
                                                        </div>
                                                    </div>
                                                    <div class="vstack gap-2">
                                                        <div class="d-flex justify-content-between">
                                                            <span class="small text-muted">
                                                                <i class="far fa-calendar-alt me-1"></i>Date
                                                            </span>
                                                            <span class="small fw-bold">[[ item.last_update.date ]]</span>
                                                        </div>
                                                        <hr class="my-1 opacity-5">
                                                        <div class="d-flex justify-content-between">
                                                            <span class="small text-muted">Updated</span>
                                                            <span v-if="item.last_update.updated > 0"
                                                                  class="badge rounded-pill bg-primary px-3">
                                                                [[ item.last_update.updated ]]
                                                            </span>
                                                            <span v-else class="text-muted smaller italic">No changes</span>
                                                        </div>
                                                        <div class="d-flex justify-content-between">
                                                            <span class="small text-muted">New Rules Found</span>
                                                            <span class="badge rounded-pill bg-info-subtle text-info border border-info-subtle px-3">
                                                                [[ item.last_update.new_rules_count ]]
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        </template>
                </tbody>
            </table>

            <div v-if="githubUrls.length === 0 && !loading" class="dt-empty">
                <i class="fas fa-search dt-empty-icon"></i>
                <p class="dt-empty-text">No GitHub URLs found matching your search.</p>
            </div>
        </div>

        <div class="mt-4">
            <pagination-component
                :current-page="currentPage"
                :total-pages="totalPages"
                @change-page="changePage">
            </pagination-component>
        </div>

        <!-- ── Bulk bar (sticky bottom, export-only — bulk delete removed) ── -->
        <transition name="rl-bulk-slide">
            <div v-if="selectedCount > 0" class="rl-bulk-bar">
                <span class="rl-bulk-count">[[ selectedCount ]] selected</span>
                <div class="rl-bulk-actions">
                    <button class="rl-bulk-btn" @click="openExportModal" :disabled="isActionLoading">
                        <i class="fas fa-file-export"></i> Export Selected
                    </button>
                </div>
                <button class="rl-bulk-clear" @click="clearSelection">
                    <i class="fas fa-xmark"></i> Clear
                </button>
            </div>
        </transition>

        <github-action-modal
            modal-id="githubActionModal"
            :title="activeAction.title"
            :icon="activeAction.icon"
            :variant="activeAction.variant"
            :confirm-text="activeAction.confirmText"
            :selected-count="selectedCount"
            :action-type="activeAction.type"
            :endpoint="submitEndpoint"
            :csrf-token="csrfToken"
            :payload="actionPayload"
            @success="handleActionSuccess">
            <template #description>
                <div class="text-muted small">
                    This will prepare a bundle of all selected repositories for export.
                </div>
            </template>
        </github-action-modal>
    </div>
    `
};

export default GitHubSelectionTable;