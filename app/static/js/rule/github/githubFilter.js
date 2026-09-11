import MultiPersonFilter from '/static/js/rule/multiPersonFilter.js'

const GithubFilter = {
    props: {
        apiEndpoint: { type: String, required: true },
        placeholder: { type: String, default: 'Search by repository URL...' },
        autoFetch: { type: Boolean, default: true },
        sortKey: { type: String, default: '' },
        sortDir: { type: String, default: 'asc' }
    },
    emits: ['update:results', 'loading'],
    delimiters: ['[[', ']]'],
    components: {
        'multi-person-filter': MultiPersonFilter
    },
    setup(props, { emit }) {
        // ── Initial state from the URL — filters (and sort, read by the
        // parent) survive a reload/share instead of silently resetting. ──
        const _url = new URLSearchParams(window.location.search)
        const _p   = (key, fallback = '') => _url.get(key) ?? fallback

        const searchQuery     = Vue.ref(_p('search'))
        const searchField     = Vue.ref(_p('search_field', 'url'))
        const selectedFormat  = Vue.ref(_p('format'))
        const selectedLicense = Vue.ref(_p('license'))
        const conflictsOnly   = Vue.ref(_p('conflicts_only') === 'true')
        const personFilter    = Vue.ref({
            mode:   _p('person_mode', 'author'),
            values: (_p('editors') || _p('authors') || '').split(',').filter(Boolean),
        })
        // person_mode defaults to 'author' — if only `editors` was present in
        // the URL (no explicit person_mode), the values above came from the
        // editors param, so the mode must say so too.
        if (!_url.get('person_mode') && _url.get('editors')) personFilter.value.mode = 'editor'

        const currentPage      = Vue.ref(parseInt(_p('page', '1'), 10) || 1);
        const searchIsLoading  = Vue.ref(false);
        const totalUrls        = Vue.ref(0);
        const availableFormats = Vue.ref([]);
        const availableLicenses = Vue.ref([]);
        const filtersOpen      = Vue.ref(false);
        const activeFilterCount = Vue.computed(() =>
            (selectedFormat.value ? 1 : 0) +
            (selectedLicense.value ? 1 : 0) +
            (conflictsOnly.value ? 1 : 0) +
            (personFilter.value.values.length ? 1 : 0)
        );

        const fetchMetadata = async () => {
            try {
                const res = await fetch('/rule/get_rules_formats');
                const data = await res.json();
                availableFormats.value = data.formats || [];
            } catch (e) {
                availableFormats.value = [];
            }
            try {
                const res = await fetch('/rule/get_github_licenses_usage');
                availableLicenses.value = res.ok ? await res.json() : [];
            } catch (e) {
                availableLicenses.value = [];
            }
        };

        function syncToUrl() {
            const p = new URLSearchParams(window.location.search)
            const _upd = (key, val) => val ? p.set(key, val) : p.delete(key)

            _upd('search',         searchQuery.value || null)
            _upd('search_field',   searchField.value !== 'url' ? searchField.value : null)
            _upd('format',         selectedFormat.value || null)
            _upd('license',        selectedLicense.value || null)
            _upd('conflicts_only', conflictsOnly.value ? 'true' : null)
            _upd('page',           currentPage.value > 1 ? currentPage.value : null)
            if (props.sortKey) { p.set('sort', props.sortKey); p.set('dir', props.sortDir) }
            else               { p.delete('sort'); p.delete('dir') }

            if (personFilter.value.values.length) {
                const pKey = personFilter.value.mode === 'editor' ? 'editors' : 'authors'
                p.set(pKey, personFilter.value.values.join(','))
                _upd('person_mode', personFilter.value.mode !== 'author' ? personFilter.value.mode : null)
                p.delete(pKey === 'editors' ? 'authors' : 'editors')
            } else {
                p.delete('authors'); p.delete('editors'); p.delete('person_mode')
            }

            const qs = p.toString()
            history.replaceState(null, '', qs ? `?${qs}` : window.location.pathname)
        }

        const fetchUrls = async (page = 1) => {
            currentPage.value = page;
            searchIsLoading.value = true;
            emit('loading', true);

            const params = new URLSearchParams({
                page: page.toString(),
                search: searchQuery.value || '',
                search_field: searchField.value,
                format: selectedFormat.value,
                license: selectedLicense.value || '',
                conflicts_only: conflictsOnly.value ? 'true' : 'false',
            });
            if (props.sortKey) {
                params.set('sort', props.sortKey);
                params.set('dir', props.sortDir);
            }
            if (personFilter.value.values.length) {
                const pKey = personFilter.value.mode === 'editor' ? 'editors' : 'authors'
                params.set(pKey, personFilter.value.values.join(','))
            }

            try {
                const res = await fetch(`${props.apiEndpoint}?${params.toString()}`);
                const data = await res.json();

                if (res.status === 200) {
                    totalUrls.value = data.total_url || 0;
                    emit('update:results', {
                        github_url: data.github_url || [],
                        total_url: data.total_url || 0,
                        total_pages: data.total_pages || 1,
                        current_page: page
                    });
                }
            } catch (err) {
                console.error('Error fetching GitHub URLs:', err);
            } finally {
                searchIsLoading.value = false;
                emit('loading', false);
                syncToUrl();
            }
        };

        const clearSearch = () => {
            searchQuery.value = '';
            fetchUrls(1);
        };

        const resetFilters = () => {
            selectedFormat.value = '';
            selectedLicense.value = '';
            conflictsOnly.value = false;
            personFilter.value = { mode: 'author', values: [] };
            fetchUrls(1);
        };

        Vue.watch(searchQuery, (newSearch, oldSearch) => {
            if (oldSearch !== '' && newSearch === '') fetchUrls(1);
        });

        Vue.onMounted(() => {
            fetchMetadata();
            if (props.autoFetch) fetchUrls(currentPage.value);
        });

        return {
            searchQuery,
            searchField,
            selectedFormat,
            selectedLicense,
            conflictsOnly,
            personFilter,
            searchIsLoading,
            totalUrls,
            availableFormats,
            availableLicenses,
            filtersOpen,
            activeFilterCount,
            fetchUrls,
            clearSearch,
            resetFilters,
        };
    },
    template: `
    <div>
        <div class="rl-toolbar">
            <div class="rl-toolbar-left">
                <div class="dt-search">
                    <i v-if="!searchIsLoading" class="fas fa-search dt-search-icon"></i>
                    <span v-else class="spinner-border spinner-border-sm text-primary dt-search-icon" style="width:.85rem;height:.85rem;"></span>
                    <input class="dt-search-input" type="text" :placeholder="placeholder"
                           v-model="searchQuery" @keyup.enter="fetchUrls(1)" aria-label="Search repositories" />
                    <button v-if="searchQuery" class="dt-search-clear" @click="clearSearch"
                            aria-label="Clear search">
                        <i class="fas fa-xmark"></i>
                    </button>
                </div>
                <select v-model="searchField" class="rl-fp-select" @change="fetchUrls(1)" aria-label="Search in" style="width:auto;">
                    <option value="url">URL only</option>
                    <option value="all">URL, format &amp; title</option>
                </select>
                <span v-if="!searchIsLoading" class="text-muted small text-nowrap">
                    <strong>[[ totalUrls ]]</strong> repositor[[ totalUrls === 1 ? 'y' : 'ies' ]]
                </span>
            </div>

            <div class="rl-toolbar-right">
                <slot name="toolbar-extra"></slot>

                <button class="dt-toolbar-btn"
                        :class="{ 'dt-toolbar-btn--active': filtersOpen }"
                        @click="filtersOpen = !filtersOpen"
                        :aria-expanded="filtersOpen">
                    <i class="fa-solid fa-filter"></i>
                    <span>Filters</span>
                    <span v-if="activeFilterCount > 0" class="rl-filter-badge ms-1">[[ activeFilterCount ]]</span>
                </button>
            </div>
        </div>

        <div v-show="filtersOpen" class="rl-filter-panel">
            <div class="rl-fp-row rl-fp-row--multi">
                <div class="rl-fp-multi-item" style="min-width:240px;">
                    <multi-person-filter v-model="personFilter"
                        author-endpoint="/rule/get_github_authors_usage"
                        editor-endpoint="/rule/get_github_editors_usage"
                        @change="fetchUrls(1)">
                    </multi-person-filter>
                </div>

                <div class="rl-fp-item">
                    <select v-model="selectedFormat" @change="fetchUrls(1)" class="rl-fp-select" aria-label="Format">
                        <option value="">All formats</option>
                        <option v-for="fmt in availableFormats"
                                :key="typeof fmt === 'object' ? fmt.name : fmt"
                                :value="typeof fmt === 'object' ? fmt.name : fmt">
                            [[ typeof fmt === 'object' ? fmt.name : fmt ]]
                        </option>
                    </select>
                </div>

                <div class="rl-fp-item">
                    <select v-model="selectedLicense" @change="fetchUrls(1)" class="rl-fp-select" aria-label="License">
                        <option value="">All licenses</option>
                        <option v-for="lic in availableLicenses" :key="lic.name" :value="lic.name">
                            [[ lic.name ]] ([[ lic.count ]])
                        </option>
                    </select>
                </div>

                <label class="rl-fp-switch" title="Only repositories with a high-similarity conflict">
                    <input type="checkbox" v-model="conflictsOnly" @change="fetchUrls(1)" />
                    <span>Conflicts only</span>
                </label>

                <button v-if="activeFilterCount > 0" class="rl-fp-reset" @click="resetFilters">
                    <i class="fas fa-rotate-left me-1"></i>Reset
                </button>
            </div>
        </div>
    </div>
    `
};

export default GithubFilter;
