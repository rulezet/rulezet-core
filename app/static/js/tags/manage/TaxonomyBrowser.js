/**
 * TaxonomyBrowser
 * Tab for adding MISP taxonomies with search, stats, and per-taxonomy import.
 */
const TaxonomyBrowser = {
    props: {
        csrfToken: { type: String, required: true },
    },
    emits: ['notify', 'refresh-main'],
    setup(props, { emit }) {
        const { ref, onMounted } = Vue;

        const tags = ref([]);
        const total = ref(0);
        const totalPages = ref(1);
        const page = ref(1);
        const searchQ = ref('');
        const loadingMap = ref({});
        const pageLoading = ref(false);

        async function load(p = 1) {
            pageLoading.value = true;
            try {
                const res = await fetch('/tags/get_tags_misp?' + new URLSearchParams({ page: p, search: searchQ.value }));
                const data = await res.json();
                if (res.ok) {
                    tags.value = data.tags;
                    total.value = data.total_tags;
                    totalPages.value = data.total_pages;
                    page.value = p;
                }
            } finally {
                pageLoading.value = false;
            }
        }

        async function addTaxonomy(uuid) {
            loadingMap.value[uuid] = true;
            try {
                const res = await fetch('/tags/add_tags_misp?' + new URLSearchParams({ uuid }));
                const data = await res.json();
                emit('notify', data.message, res.ok ? 'success-subtle' : 'danger-subtle');
                if (res.ok) {
                    await load(page.value);
                    emit('refresh-main');
                }
            } finally {
                loadingMap.value[uuid] = false;
            }
        }

        function onSearchInput() {
            if (!searchQ.value.trim()) load(1);
        }

        onMounted(() => load(1));

        return { tags, total, totalPages, page, searchQ, loadingMap, pageLoading, load, addTaxonomy, onSearchInput };
    },
    template: `
        <div>
            <!-- Search -->
            <div class="d-flex gap-2 align-items-center mb-3">
                <div class="input-group input-group-sm flex-grow-1">
                    <span class="input-group-text bg-transparent border-end-0">
                        <i class="fas fa-search text-muted"></i>
                    </span>
                    <input
                        type="text" v-model="searchQ"
                        class="form-control border-start-0"
                        placeholder="Search taxonomies…"
                        @keyup.enter="load(1)"
                        @input="onSearchInput"
                    >
                    <button class="btn btn-sm btn-primary" @click="load(1)">Search</button>
                </div>
                <span class="badge rounded-pill bg-light text-dark border px-3 py-2 text-nowrap">
                    <i class="fas fa-list me-1 text-primary"></i><strong>{{ total }}</strong> available
                </span>
            </div>

            <!-- Table -->
            <div class="table-responsive">
                <table class="table table-sm align-middle browser-table">
                    <thead>
                        <tr>
                            <th>Namespace</th>
                            <th>Description</th>
                            <th>Version</th>
                            <th class="text-end">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-if="pageLoading">
                            <td colspan="4" class="text-center py-4">
                                <div class="spinner-border spinner-border-sm text-primary"></div>
                            </td>
                        </tr>
                        <template v-else>
                            <tr v-for="t in tags" :key="t.uuid">
                                <td>
                                    <span class="tag-split shadow-sm">
                                        <span class="tag-left"><i class="fas fa-tag"></i></span>
                                        <span class="tag-right" style="background:#0d6efd; color:#fff">{{ t.namespace }}</span>
                                    </span>
                                </td>
                                <td class="text-muted small" style="max-width:300px">
                                    {{ t.description || t.expanded || '—' }}
                                </td>
                                <td><span class="badge bg-light text-dark border">v{{ t.version || '?' }}</span></td>
                                <td class="text-end">
                                    <button
                                        class="btn btn-sm btn-success rounded-pill"
                                        :disabled="loadingMap[t.uuid]"
                                        @click="addTaxonomy(t.uuid)"
                                    >
                                        <span v-if="loadingMap[t.uuid]" class="spinner-border spinner-border-sm me-1"></span>
                                        <i v-else class="fas fa-plus me-1"></i>Import
                                    </button>
                                </td>
                            </tr>
                            <tr v-if="!tags.length && !pageLoading">
                                <td colspan="4" class="text-center text-muted py-4">
                                    <i class="fas fa-list fa-2x d-block mb-2 opacity-25"></i>
                                    No taxonomies available (all already imported, or no match)
                                </td>
                            </tr>
                        </template>
                    </tbody>
                </table>
            </div>

            <!-- Pagination -->
            <browser-pagination :current="page" :total="totalPages" @change="load"></browser-pagination>
        </div>
    `
};

export default TaxonomyBrowser;