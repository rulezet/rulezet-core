/**
 * ruleDataTable.js — DataTable preconfigured for Rule objects.
 *
 * Drop it on any page that lists rules:
 *
 *   <rule-data-table source="https://github.com/x/y" :exportable="true"
 *                    :csrf-token="'{{ csrf_token() }}'"
 *                    :current-user-is-authenticated="'{{ current_user.is_authenticated }}'">
 *   </rule-data-table>
 *
 * Features on top of the generic DataTable (table/card views, search, sort,
 * column picker, pagination, expand):
 *   - Tags and CVE columns
 *   - Integrated advanced filter panel (format, search field, exact match,
 *     tags, licenses, vulnerabilities, sources) — same backend filters as
 *     the rule filter bar (filter_rules)
 *   - Selection + export: bulk bar with an Export action; "select all"
 *     covers every matching rule (filter-driven export), a manual selection
 *     exports exactly those ids
 *
 * Data comes from GET /rule/data_table. Requires
 * /static/css/components/dataTable.css on the page.
 *
 * Events re-emitted: create, edit, delete, view, bulk-action, send.
 * Exposed method: fetchData() — re-fetch current page.
 */

import DataTable from '/static/js/components/dataTable/dataTable.js'
import VulnerabilityDisplaysList from '/static/js/vulnerability/vulnerabilityDisplayList.js'
import TagsDisplaysList from '/static/js/tags/tagsDisplaysList.js'
import MultiVulnerabilityFilter from '/static/js/vulnerability/multiVulnerabilityFilter.js'
import MultiSourceFilter from '/static/js/rule/multiSourceFilter.js'
import MultiLicenseFilter from '/static/js/rule/multiLicenseFilter.js'
import MultiTagFilter from '/static/js/tags/multiTagFIlter.js'
import RuleExportAction from '/static/js/rule/ruleExportAction.js'

const { ref, computed, onMounted, nextTick } = Vue

export default {
    name: 'RuleDataTable',
    components: {
        'data-table': DataTable,
        'vulnerability-displays-list': VulnerabilityDisplaysList,
        'tags-displays-list': TagsDisplaysList,
        'multi-vulnerability-filter': MultiVulnerabilityFilter,
        'multi-source-filter': MultiSourceFilter,
        'multi-license-filter': MultiLicenseFilter,
        'multi-tag-filter': MultiTagFilter,
        'rule-export-action': RuleExportAction,
    },

    props: {
        fetchUrl:       { type: String,  default: '/rule/data_table' },
        source:         { type: String,  default: null },
        userId:         { type: [Number, String], default: null },
        mode:           { type: String,  default: 'read' },
        canCreate:      { type: Boolean, default: false },
        canEdit:        { type: Boolean, default: false },
        canDelete:      { type: Boolean, default: false },
        canView:        { type: Boolean, default: true },
        bulkActions:    { type: Array,   default: () => [] },
        defaultView:    { type: String,  default: 'table' },
        initialPerPage: { type: Number,  default: 10 },
        showFilters:    { type: Boolean, default: true },
        exportable:     { type: Boolean, default: false },
        csrfToken:      { type: String,  default: '' },
        currentUserIsAuthenticated: { type: [String, Boolean], default: false },
    },

    emits: ['create', 'edit', 'delete', 'view', 'bulk-action', 'send'],

    expose: ['fetchData'],

    template: `
    <div>
        <!-- ── Advanced filter panel ── -->
        <div v-if="showFilters" class="mb-3">
            <button class="btn btn-sm d-inline-flex align-items-center gap-2 px-3 mb-2"
                    style="background:var(--light-bg-color); border:1px solid var(--border-color); border-radius:20px; font-size:.75rem; color:var(--subtle-text-color);"
                    @click="filtersOpen = !filtersOpen">
                <i class="fas fa-sliders" style="font-size:.7rem;"></i> Advanced filters
                <span v-if="activeFilterCount > 0" class="badge bg-primary rounded-pill">{{ activeFilterCount }}</span>
                <i class="fa-solid ms-1" :class="filtersOpen ? 'fa-chevron-up' : 'fa-chevron-down'" style="font-size:.7rem;"></i>
            </button>

            <div v-show="filtersOpen" class="card shadow-sm border-0"
                 style="border-radius: 15px; background-color: var(--card-bg-color);">
                <div class="card-body p-3">
                    <div class="row g-3">
                        <div class="col-md-3">
                            <label class="small fw-bold text-muted mb-1 ms-1 text-uppercase">Format</label>
                            <select v-model="ruleType" class="form-select form-select-sm border-0 bg-light px-3"
                                    style="border-radius: 10px; height: 38px;">
                                <option value="">All Formats</option>
                                <option v-for="f in rulesFormats" :key="f.id" :value="f.name">{{ f.name.toUpperCase() }}</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="small fw-bold text-muted mb-1 ms-1 text-uppercase">Search in</label>
                            <select v-model="searchField" class="form-select form-select-sm border-0 bg-light px-3"
                                    style="border-radius: 10px; height: 38px;">
                                <option value="all">All fields</option>
                                <option value="title">Title</option>
                                <option value="content">Content</option>
                            </select>
                        </div>
                        <div class="col-md-3 d-flex align-items-end">
                            <div class="form-check form-switch mb-2 ms-1">
                                <input class="form-check-input" type="checkbox" v-model="exactMatch">
                                <label class="form-check-label small text-muted">Exact match</label>
                            </div>
                        </div>
                        <div class="col-md-3 d-flex align-items-end justify-content-end">
                            <button v-if="activeFilterCount > 0" class="btn btn-sm btn-outline-secondary rounded-pill mb-1"
                                    @click="resetFilters">
                                <i class="fas fa-rotate-left me-1"></i>Reset filters
                            </button>
                        </div>
                    </div>

                    <div class="row g-3 mt-1">
                        <div class="col-md-6" v-if="!source">
                            <label class="small fw-bold text-muted mb-1 ms-1 text-uppercase">
                                <i class="fa-solid fa-code-branch me-1 text-primary"></i> Sources
                            </label>
                            <multi-source-filter v-model="selectedSourceNames"
                                api-endpoint="/rule/get_rules_sources_usage" placeholder="Filter sources..." :userId="numericUserId">
                            </multi-source-filter>
                        </div>
                        <div class="col-md-6">
                            <label class="small fw-bold text-muted mb-1 ms-1 text-uppercase">
                                <i class="fa-solid fa-shield-virus me-1 text-danger"></i> Vulnerabilities
                            </label>
                            <multi-vulnerability-filter v-model="selectedVulnerabilityNames"
                                api-endpoint="/rule/get_all_rules_vulnerabilities_usage" placeholder="CVE, GHSA..."
                                :user-id="numericUserId" :source-rules="source || ''">
                            </multi-vulnerability-filter>
                        </div>
                        <div class="col-md-6">
                            <label class="small fw-bold text-muted mb-1 ms-1 text-uppercase">
                                <i class="fa-solid fa-scale-balanced me-1 text-info"></i> Licenses
                            </label>
                            <multi-license-filter v-model="selectedLicenseNames"
                                api-endpoint="/rule/get_rules_licenses_usage" placeholder="Filter licenses..."
                                :user-id="numericUserId" :source-rules="source || ''">
                            </multi-license-filter>
                        </div>
                        <div class="col-md-6">
                            <label class="small fw-bold text-muted mb-1 ms-1 text-uppercase">
                                <i class="fa-solid fa-tags me-1 text-primary"></i> Tags
                            </label>
                            <multi-tag-filter v-model="selectedTagNames"
                                api-endpoint="/rule/get_all_tags_usage" placeholder="Filter tags..."
                                :user-id="numericUserId" target-type="rule">
                            </multi-tag-filter>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ── Table / cards ── -->
        <data-table
            ref="table"
            :fetch-url="computedUrl"
            :mode="effectiveMode"
            :columns="columns"
            :can-create="canCreate"
            :can-edit="canEdit"
            :can-delete="canDelete"
            :can-view="canView"
            :bulk-actions="effectiveBulkActions"
            :default-view="defaultView"
            :initial-per-page="initialPerPage"
            @create="$emit('create')"
            @edit="item => $emit('edit', item)"
            @delete="item => $emit('delete', item)"
            @view="onView"
            @bulk-action="onBulkAction"
            @send="ids => $emit('send', ids)">

            <!-- Title: link to the rule detail page -->
            <template #cell-title="{ item }">
                <a :href="'/rule/detail_rule/' + item.id" class="dt-rule-title"
                   :title="item.title">{{ item.title }}</a>
            </template>

            <!-- Format badge — same style as the rule detail page -->
            <template #cell-format="{ value }">
                <span v-if="value" class="badge rounded-pill bg-dark pt-1 shadow-sm">{{ value.toUpperCase() }}</span>
                <span v-else class="text-muted small">—</span>
            </template>

            <!-- Tags -->
            <template #cell-tags="{ item }">
                <span v-if="!item.tags || !item.tags.length" class="text-muted small">—</span>
                <tags-displays-list v-else
                    object-type="rule" :object-id="item.id" :max-visible="3">
                </tags-displays-list>
            </template>

            <!-- CVEs -->
            <template #cell-cves="{ item }">
                <span v-if="!item.cves || !item.cves.length" class="text-muted small">—</span>
                <vulnerability-displays-list v-else
                    object-type="rule" :object-id="item.id" :max-visible="2">
                </vulnerability-displays-list>
            </template>

            <!-- Votes -->
            <template #cell-vote_up="{ item }">
                <span class="text-success me-2" style="font-size:.82rem;">
                    <i class="fas fa-thumbs-up me-1"></i>{{ item.vote_up }}
                </span>
                <span class="text-danger" style="font-size:.82rem;">
                    <i class="fas fa-thumbs-down me-1"></i>{{ item.vote_down }}
                </span>
            </template>

            <!-- Expanded row: full rule detail -->
            <template #expand="{ item }">
                <div class="dt-expand-grid mb-2">
                    <div class="dt-expand-field">
                        <label>Author</label>
                        <span>{{ item.author || '—' }}</span>
                    </div>
                    <div class="dt-expand-field">
                        <label>License</label>
                        <span>{{ item.license || '—' }}</span>
                    </div>
                    <div class="dt-expand-field">
                        <label>Created</label>
                        <span>{{ item.creation_date || '—' }}</span>
                    </div>
                    <div class="dt-expand-field">
                        <label>Last modified</label>
                        <span>{{ item.last_modif || '—' }}</span>
                    </div>
                    <div class="dt-expand-field" v-if="item.source">
                        <label>Source</label>
                        <span><a :href="item.source" target="_blank" rel="noreferrer">{{ item.source }}</a></span>
                    </div>
                </div>

                <div class="dt-expand-field mb-2" v-if="item.description">
                    <label>Description</label>
                    <span>{{ item.description }}</span>
                </div>

                <div class="dt-expand-field mb-2" v-if="item.tags && item.tags.length">
                    <label>Tags</label>
                    <tags-displays-list
                        object-type="rule"
                        :object-id="item.id"
                        :max-visible="10">
                    </tags-displays-list>
                </div>

                <div class="mb-2" v-if="item.cves && item.cves.length">
                    <vulnerability-displays-list
                        object-type="rule"
                        :object-id="item.id"
                        :max-visible="4">
                    </vulnerability-displays-list>
                </div>

                <pre class="dt-rule-content" v-if="item.to_string">{{ item.to_string }}</pre>
            </template>

            <!-- Card body -->
            <template #card-body="{ item }">
                <div class="d-flex align-items-center gap-2 flex-wrap">
                    <span v-if="item.format" class="badge rounded-pill bg-dark pt-1 shadow-sm">{{ item.format.toUpperCase() }}</span>
                    <span style="font-size:.78rem; color: var(--subtle-text-color)">
                        <i class="fas fa-user me-1"></i>{{ item.author || '—' }}
                    </span>
                </div>
                <div v-if="item.tags && item.tags.length">
                    <tags-displays-list object-type="rule" :object-id="item.id" :max-visible="3">
                    </tags-displays-list>
                </div>
                <div v-if="item.cves && item.cves.length">
                    <vulnerability-displays-list object-type="rule" :object-id="item.id" :max-visible="2">
                    </vulnerability-displays-list>
                </div>
                <div style="font-size:.8rem; color: var(--subtle-text-color);
                            display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical;
                            overflow:hidden;">
                    {{ item.description || 'No description.' }}
                </div>
                <div class="d-flex align-items-center gap-3 mt-auto"
                     style="font-size:.75rem; color: var(--subtle-text-color)">
                    <span><i class="fas fa-calendar me-1 opacity-50"></i>{{ item.creation_date }}</span>
                    <span class="text-success"><i class="fas fa-thumbs-up me-1"></i>{{ item.vote_up }}</span>
                    <span class="text-danger"><i class="fas fa-thumbs-down me-1"></i>{{ item.vote_down }}</span>
                </div>
            </template>
        </data-table>

        <!-- ── Export modal (opened from the bulk bar) ── -->
        <rule-export-action
            v-if="exportable"
            :show-button="false"
            modal-id="ruleDtExportModal"
            :rule-ids="exportIds"
            :total-rules="exportCount"
            :search-query="exportSearch"
            :search-field="searchField"
            :rule-type="ruleType"
            :selected-sources="exportSources"
            :selected-vulnerabilities="selectedVulnerabilityNames"
            :selected-licenses="selectedLicenseNames"
            :selected-tags="selectedTagNames"
            :user-id="numericUserId"
            :csrf-token="csrfToken"
            :current-user-is-authenticated="currentUserIsAuthenticated">
        </rule-export-action>
    </div>
    `,

    setup(props, { emit }) {
        const table = ref(null)

        const columns = [
            { key: 'title',         label: 'Title',       sortable: true, truncate: true },
            { key: 'format',        label: 'Format',      sortable: true, width: '100px' },
            { key: 'author',        label: 'Author',      sortable: true, truncate: true, width: '140px' },
            { key: 'description',   label: 'Description', truncate: true },
            { key: 'tags',          label: 'Tags',        width: '180px' },
            { key: 'cves',          label: 'CVE',         width: '150px' },
            { key: 'creation_date', label: 'Created',     sortable: true, width: '140px' },
            { key: 'vote_up',       label: 'Votes',       sortable: true, width: '110px' },
        ]

        // ── Advanced filters state ───────────────────────────────────────
        const filtersOpen  = ref(false)
        const ruleType     = ref('')
        const searchField  = ref('all')
        const exactMatch   = ref(false)
        const selectedSourceNames        = ref([])
        const selectedVulnerabilityNames = ref([])
        const selectedLicenseNames       = ref([])
        const selectedTagNames           = ref([])
        const rulesFormats = ref([])

        const numericUserId = computed(() =>
            props.userId !== null && props.userId !== '' ? Number(props.userId) : null
        )

        const activeFilterCount = computed(() =>
            (ruleType.value ? 1 : 0) +
            (exactMatch.value ? 1 : 0) +
            (searchField.value !== 'all' ? 1 : 0) +
            selectedSourceNames.value.length +
            selectedVulnerabilityNames.value.length +
            selectedLicenseNames.value.length +
            selectedTagNames.value.length
        )

        function resetFilters() {
            ruleType.value = ''
            searchField.value = 'all'
            exactMatch.value = false
            selectedSourceNames.value = []
            selectedVulnerabilityNames.value = []
            selectedLicenseNames.value = []
            selectedTagNames.value = []
        }

        async function fetchFormats() {
            try {
                const res = await fetch('/rule/get_rules_formats')
                const data = await res.json()
                rulesFormats.value = data.formats || []
            } catch { /* format list stays empty */ }
        }
        onMounted(fetchFormats)

        // The DataTable refetches automatically whenever this URL changes
        const computedUrl = computed(() => {
            const params = new URLSearchParams()
            if (props.source) params.set('source', props.source)
            if (numericUserId.value) params.set('user_id', numericUserId.value)
            if (ruleType.value) params.set('rule_type', ruleType.value)
            if (searchField.value !== 'all') params.set('search_field', searchField.value)
            if (exactMatch.value) params.set('exact_match', 'true')
            if (selectedSourceNames.value.length) params.set('sources', selectedSourceNames.value.join(','))
            if (selectedVulnerabilityNames.value.length) params.set('vulnerabilities', selectedVulnerabilityNames.value.join(','))
            if (selectedLicenseNames.value.length) params.set('licenses', selectedLicenseNames.value.join(','))
            if (selectedTagNames.value.length) params.set('tags', selectedTagNames.value.join(','))
            const qs = params.toString()
            return qs ? `${props.fetchUrl}?${qs}` : props.fetchUrl
        })

        // ── Selection / export ───────────────────────────────────────────
        const effectiveMode = computed(() =>
            props.exportable && props.mode === 'read' ? 'manage' : props.mode
        )
        const effectiveBulkActions = computed(() =>
            props.exportable
                ? [...props.bulkActions, { key: 'export', label: 'Export', icon: 'fa-file-export' }]
                : props.bulkActions
        )

        const exportIds    = ref(null)   // null = filter-driven (select all pages)
        const exportCount  = ref(0)
        const exportSearch = ref('')
        const exportSources = computed(() =>
            props.source ? [props.source] : selectedSourceNames.value
        )

        async function onBulkAction(payload) {
            if (payload.action === 'export' && props.exportable) {
                exportIds.value    = payload.ids === 'ALL' ? null : payload.ids
                exportCount.value  = payload.count
                exportSearch.value = payload.search || ''
                await nextTick()
                const el = document.getElementById('ruleDtExportModal')
                if (el) bootstrap.Modal.getOrCreateInstance(el).show()
                return
            }
            emit('bulk-action', payload)
        }

        // ── Misc ─────────────────────────────────────────────────────────
        function onView(item) {
            emit('view', item)
            window.location.href = '/rule/detail_rule/' + item.id
        }

        function fetchData() {
            table.value?.fetchData()
        }

        return {
            table, columns, computedUrl,
            filtersOpen, ruleType, searchField, exactMatch,
            selectedSourceNames, selectedVulnerabilityNames,
            selectedLicenseNames, selectedTagNames,
            rulesFormats, activeFilterCount, resetFilters, numericUserId,
            effectiveMode, effectiveBulkActions,
            exportIds, exportCount, exportSearch, exportSources,
            onBulkAction, onView, fetchData,
        }
    }
}
