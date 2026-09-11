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
    setup(props, { emit }) {
        const searchQuery = Vue.ref('');
        const searchField = Vue.ref('url');
        const selectedFormat = Vue.ref('');
        const authorQuery = Vue.ref('');
        const searchIsLoading = Vue.ref(false);
        const totalUrls = Vue.ref(0);
        const availableFormats = Vue.ref([]);
        const filtersOpen = Vue.ref(false);
        const activeFilterCount = Vue.computed(() =>
            (selectedFormat.value ? 1 : 0) + (authorQuery.value ? 1 : 0)
        );

        const fetchMetadata = async () => {
            try {
                const res = await fetch('/rule/get_rules_formats');
                const data = await res.json();
                availableFormats.value = data.formats || [];
            } catch (e) { 
                availableFormats.value = [];
            }
        };

        const fetchUrls = async (page = 1) => {
            searchIsLoading.value = true;
            emit('loading', true);

            const params = new URLSearchParams({
                page: page.toString(),
                search: searchQuery.value || '',
                search_field: searchField.value,
                format: selectedFormat.value,
                author: authorQuery.value
            });
            if (props.sortKey) {
                params.set('sort', props.sortKey);
                params.set('dir', props.sortDir);
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
            }
        };

        const clearSearch = () => {
            searchQuery.value = '';
            fetchUrls(1);
        };

        const clearAuthor = () => {
            authorQuery.value = '';
            fetchUrls(1);
        };
        
        Vue.watch([searchQuery, authorQuery], ([newSearch, newAuthor], [oldSearch, oldAuthor]) => {
            if ((oldSearch !== '' && newSearch === '') || (oldAuthor !== '' && newAuthor === '')) {
                fetchUrls(1);
            }
        });

        Vue.onMounted(() => {
            fetchMetadata();
            if (props.autoFetch) fetchUrls(1);
        });

        return {
            searchQuery,
            searchField,
            selectedFormat,
            searchIsLoading,
            totalUrls,
            availableFormats,
            filtersOpen,
            activeFilterCount,
            fetchUrls,
            clearSearch,
            clearAuthor,
            authorQuery
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
            <div class="rl-fp-row">
                <div class="rl-fp-item" style="min-width:220px;">
                    <input type="text"
                           v-model="authorQuery"
                           @keyup.enter="fetchUrls(1)"
                           class="rl-fp-select"
                           placeholder="Author, e.g. Neo23x0"
                           style="width:100%;">
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
                <button v-if="activeFilterCount > 0" class="rl-fp-reset" @click="selectedFormat = ''; clearAuthor()">
                    <i class="fas fa-rotate-left me-1"></i>Reset
                </button>
            </div>
        </div>
    </div>
    `
};

export default GithubFilter;