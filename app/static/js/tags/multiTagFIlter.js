import { getTextColor, mapIcon } from './utils/galaxie.js';

const MultiTagFilter = {
    props: {
        modelValue: { type: Array, default: () => [] },
        placeholder: { type: String, default: 'Filter by tags…' },
        apiEndpoint: { type: String, default: '/bundle/get_all_tags_usage' },
        showNamespace: { type: Boolean, default: true },
        // Query string of every OTHER currently active RuleList filter — keeps
        // these counts scoped to what's actually visible.
        filterContext: { type: String, default: '' },
    },
    emits: ['update:modelValue', 'change'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        // Everything is loaded lazily — the folder list when the panel opens,
        // one folder (or one search) page at a time, and just the selected
        // chips on mount — never every used tag (thousands of them after the
        // MISP and imported-tags imports). See tags_core.usage_view().
        const namespaces = Vue.ref(null);          // [{namespace, label, tag_count, usage}] for activeSource
        const folderTags = Vue.ref([]);
        const folderPage = Vue.ref(0);
        const folderTotal = Vue.ref(0);
        const folderHasMore = Vue.ref(false);
        const searchResults = Vue.ref([]);
        const isSearching = Vue.ref(false);
        const knownTags = Vue.reactive({});        // lower-cased name -> tag, for the selected chips
        const PAGE_SIZE = 50;
        let requestId = 0;
        let searchTimer = null;
        const tagSearchQuery = Vue.ref('');
        const selectedTagNames = Vue.ref([...props.modelValue]);
        const activeNamespace = Vue.ref(null);
        const activeSource = Vue.ref('all');   // 'all' | 'Taxonomy' | 'Galaxy' | 'Manual' | 'Imported'
        const isLoading = Vue.ref(false);

        const sourceOptions = [
            { value: 'all', label: 'All', icon: 'fa-layer-group', color: '#6c757d' },
            { value: 'Taxonomy', label: 'Taxonomy', icon: 'fa-list', color: '#0d6efd' },
            { value: 'Galaxy', label: 'Galaxy', icon: 'fa-atom', color: '#9b7ede' },
            { value: 'Manual', label: 'Manual', icon: 'fa-tag', color: '#198754' },
            // The rule author's own tags extracted from the rule (GitHub #70)
            { value: 'Imported', label: 'Imported', icon: 'fa-user-tag', color: '#fd7e14' },
        ];

        function valueOf(name) {
            if (!name) return '';
            const m = name.match(/="(.+)"$/);
            if (m) return m[1];
            if (name.includes(':')) return name.split(':').slice(1).join(':');
            return name;
        }
        // Full detail: parses the RAW name directly rather than via the
        // browse folder (tag.namespace, which collapses "misp-galaxy:tool=..."
        // down to just "tool").
        function tagLabel(name) {
            if (!props.showNamespace) return valueOf(name);
            if (!name) return '';
            const colonIdx = name.indexOf(':');
            if (colonIdx === -1) return name;
            const rawNs = name.slice(0, colonIdx);
            const rest  = name.slice(colonIdx + 1);
            // Only a genuine MISP-galaxy predicate="value" pair ends the
            // string in a closing quote right after "=" — a plain value
            // that merely contains a literal "=" (e.g. a version
            // constraint like '"<=0.6"') must be left untouched instead of
            // being torn apart at the first "=" found anywhere in it.
            const predMatch = rest.match(/^(.*?)="(.*)"$/);
            if (!predMatch) return `${rawNs}:${rest}`;
            const pred = predMatch[1];
            return `${rawNs}:${pred}=${valueOf(name)}`;
        }

        const isNameSelected = (name) =>
            selectedTagNames.value.some(n => n.toLowerCase() === name.toLowerCase());

        // Vue.watch(() => props.modelValue, (val) => { selectedTagNames.value = [...val]; });
        Vue.watch(() => props.modelValue, (val) => {
            if (val && val.length > 0) selectedTagNames.value = [...val];
        });

        function url(params) {
            const qs = new URLSearchParams(params);
            const ctx = props.filterContext ? props.filterContext + '&' : '';
            return `${props.apiEndpoint}?${ctx}${qs}`;
        }

        function remember(tags) {
            for (const t of tags || []) knownTags[t.name.toLowerCase()] = t;
        }

        async function getJson(params) {
            const res = await fetch(url(params));
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        }

        async function fetchNamespaces() {
            const myId = ++requestId;
            isLoading.value = true;
            try {
                const data = await getJson({ view: 'namespaces', tag_source: activeSource.value });
                if (myId === requestId) namespaces.value = data.namespaces || [];
            } catch (e) {
                console.error('MultiTagFilter fetch error:', e);
            } finally {
                if (myId === requestId) isLoading.value = false;
            }
        }

        async function loadFolderPage() {
            if (activeNamespace.value === null) return;
            const myId = ++requestId;
            isLoading.value = true;
            try {
                const data = await getJson({
                    view: 'tags', tag_source: activeSource.value, tag_ns: activeNamespace.value.namespace,
                    tag_page: String(folderPage.value + 1), tag_per_page: String(PAGE_SIZE),
                });
                if (myId !== requestId) return;
                remember(data.tags);
                folderTags.value = [...folderTags.value, ...(data.tags || [])];
                folderPage.value = data.page;
                folderTotal.value = data.total;
                folderHasMore.value = !!data.has_more;
            } catch (e) {
                console.error('MultiTagFilter folder error:', e);
            } finally {
                if (myId === requestId) isLoading.value = false;
            }
        }

        async function runSearch(q) {
            const myId = ++requestId;
            isSearching.value = true;
            try {
                const data = await getJson({ view: 'tags', tag_source: activeSource.value, tag_q: q,
                                             tag_per_page: String(PAGE_SIZE) });
                if (myId !== requestId) return;
                remember(data.tags);
                searchResults.value = data.tags || [];
            } catch (e) {
                console.error('MultiTagFilter search error:', e);
            } finally {
                if (myId === requestId) isSearching.value = false;
            }
        }

        // Chips of the current selection — resolved by name, only for the
        // names not already seen in a loaded page.
        async function resolveSelected() {
            const missing = selectedTagNames.value.filter(n => !knownTags[n.toLowerCase()]);
            if (!missing.length) return;
            try {
                const data = await getJson({ view: 'selected', names: missing.join(',') });
                remember(data.tags);
            } catch (e) {
                console.error('MultiTagFilter selected error:', e);
            }
        }

        // Called when the panel opens: the folder list, once per filter state.
        function ensureLoaded() {
            if (namespaces.value === null && !isLoading.value) fetchNamespaces();
        }

        function openFolder(folder) {
            activeNamespace.value = folder;
            folderTags.value = [];
            folderPage.value = 0;
            folderHasMore.value = false;
            loadFolderPage();
        }

        function closeFolder() {
            requestId++;
            activeNamespace.value = null;
            folderTags.value = [];
            isLoading.value = false;
        }

        // Counts depend on every other active filter: drop what was loaded,
        // reload lazily (now if the panel shows a folder list).
        function resetLoaded() {
            requestId++;
            namespaces.value = null;
            folderTags.value = [];
            searchResults.value = [];
            isLoading.value = false;
            isSearching.value = false;
            activeNamespace.value = null;
        }

        Vue.watch(tagSearchQuery, (val) => {
            clearTimeout(searchTimer);
            const q = val.trim();
            if (!q) { requestId++; searchResults.value = []; isSearching.value = false; return; }
            isSearching.value = true;
            searchTimer = setTimeout(() => runSearch(q), 300);
        });

        const selectedTagsObjects = Vue.computed(() =>
            selectedTagNames.value.map(n => knownTags[n.toLowerCase()] || { name: n, icon: null, color: null })
        );

        function setSource(src) {
            activeSource.value = src;
            tagSearchQuery.value = '';
            resetLoaded();
            fetchNamespaces();
        }

        function toggleTag(tagName) {
            const i = selectedTagNames.value.findIndex(n => n.toLowerCase() === tagName.toLowerCase());
            if (i > -1) selectedTagNames.value.splice(i, 1);
            else selectedTagNames.value.push(tagName);
            emit('update:modelValue', [...selectedTagNames.value]);
            emit('change', [...selectedTagNames.value]);
        }

        Vue.onMounted(resolveSelected);
        Vue.watch(() => props.filterContext, resetLoaded);
        Vue.watch(selectedTagNames, resolveSelected, { deep: true });

        return {
            tagSearchQuery, selectedTagNames, activeNamespace, activeSource, isLoading, isSearching,
            sourceOptions, namespaces, folderTags, folderTotal, folderHasMore, searchResults, selectedTagsObjects,
            isNameSelected, toggleTag, tagLabel, setSource,
            ensureLoaded, openFolder, closeFolder, loadFolderPage,
            getTextColor, mapIcon,
            clearAll: () => {
                selectedTagNames.value = [];
                emit('update:modelValue', []);
                emit('change', []);
            }
        };
    },
    template: `
        <div class="dropdown multi-tag-filter w-100">

            <!-- Trigger pill -->
            <div class="form-control d-flex flex-wrap gap-2 align-items-center p-2 shadow-sm border-secondary-subtle"
                 data-bs-toggle="dropdown" data-bs-auto-close="outside" @click="ensureLoaded"
                 style="cursor:pointer; min-height:48px; border-radius:12px;">
                <i class="fa-solid fa-tags text-primary opacity-75 ms-1 me-1"></i>
                <span v-if="selectedTagsObjects.length === 0" class="text-muted small fw-bold">[[ placeholder ]]</span>
                <span v-for="tag in selectedTagsObjects" :key="tag.name" class="tag-split shadow-sm m-0">
                    <span v-if="tag.icon" class="tag-left" v-html="mapIcon(tag.icon)"></span>
                    <span class="tag-right" :style="{ backgroundColor: tag.color || '#6c757d' }">
                        <span :style="{ color: getTextColor(tag.color || '#6c757d') }" class="me-2" style="font-size:0.75rem">
                            [[ tagLabel(tag.name) ]]
                        </span>
                        <i class="fa-solid fa-circle-xmark opacity-75 ms-1" @click.stop="toggleTag(tag.name)"
                           :style="{ color: getTextColor(tag.color || '#6c757d'), cursor: 'pointer' }"></i>
                    </span>
                </span>
                <i class="fa-solid fa-chevron-down ms-auto me-1 text-muted small"></i>
            </div>

            <!-- Dropdown panel -->
            <div class="dropdown-menu shadow-lg border-0 w-100 p-3 mt-2"
                 style="max-height:600px; border-radius:15px; z-index:1060; min-width:350px;">

                <!-- Search -->
                <div class="d-flex align-items-center mb-2">
                    <button v-if="activeNamespace && !tagSearchQuery"
                            @click="closeFolder"
                            class="btn btn-sm btn-outline-primary border-0 me-2 rounded-circle d-flex align-items-center justify-content-center"
                            style="width:30px; height:30px;">
                        <i class="fa-solid fa-arrow-left"></i>
                    </button>
                    <div class="input-group input-group-sm">
                        <span class="input-group-text bg-light border-0"><i class="fa-solid fa-magnifying-glass"></i></span>
                        <input type="text" v-model="tagSearchQuery"
                               class="form-control bg-light border-0 shadow-none"
                               placeholder="Search tags…">
                    </div>
                </div>

                <!-- Source filter chips -->
                <div v-if="!activeNamespace" class="d-flex gap-1 flex-wrap mb-2">
                    <button
                        v-for="opt in sourceOptions" :key="opt.value"
                        class="btn btn-xs rounded-pill px-2 py-1"
                        :style="activeSource === opt.value
                            ? { background: opt.color, borderColor: opt.color, color: '#fff', fontSize: '0.72rem' }
                            : { fontSize: '0.72rem' }"
                        :class="activeSource === opt.value ? '' : 'btn-outline-secondary'"
                        @click.stop="setSource(opt.value)"
                    >
                        <i :class="'fa-solid ' + opt.icon + ' me-1'"></i>[[ opt.label ]]
                    </button>
                </div>

                <div class="pe-1" style="max-height:380px; overflow-y:auto; overflow-x:hidden;">

                    <!-- Search results (server-side, 50 best) -->
                    <div v-if="tagSearchQuery" class="d-flex flex-column gap-1">
                        <div v-if="isSearching && !searchResults.length" class="text-center py-4">
                            <div class="spinner-border spinner-border-sm text-primary"></div>
                        </div>
                        <div v-else-if="!searchResults.length" class="text-center py-4">
                            <i class="fa-solid fa-tags fa-3x text-muted opacity-25 mb-2 d-block"></i>
                            <h6 class="text-muted fw-bold">No tags found</h6>
                        </div>
                        <div v-for="tag in searchResults" :key="tag.name"
                             @click="toggleTag(tag.name)"
                             class="p-2 rounded border d-flex align-items-center justify-content-between"
                             :class="{ 'border-primary bg-primary-subtle': isNameSelected(tag.name) }"
                             style="cursor:pointer">
                            <span class="tag-split shadow-sm">
                                <span class="tag-left" v-html="mapIcon(tag.icon)"></span>
                                <span class="tag-right" :style="{ backgroundColor: tag.color || '#6c757d' }">
                                    <span :style="{ color: getTextColor(tag.color || '#6c757d') }" class="small fw-bold">
                                        [[ tagLabel(tag.name) ]]
                                    </span>
                                </span>
                            </span>
                            <span class="badge rounded-pill border" style="background:var(--light-bg-color); color:var(--text-color)">
                                [[ tag.usage_count ]]
                            </span>
                        </div>
                    </div>

                    <!-- Namespace list -->
                    <div v-else-if="!activeNamespace" class="d-flex flex-column gap-2">
                        <div v-if="isLoading || namespaces === null" class="text-center py-4">
                            <div class="spinner-border spinner-border-sm text-primary"></div>
                        </div>
                        <div v-else-if="!namespaces.length" class="text-center py-4">
                            <i class="fa-solid fa-tags fa-3x text-muted opacity-25 mb-2 d-block"></i>
                            <h6 class="text-muted fw-bold">No tags found</h6>
                        </div>
                        <div v-for="folder in (isLoading ? [] : namespaces || [])" :key="folder.namespace"
                             @click="openFolder(folder)"
                             class="p-2 px-3 rounded-3 border d-flex align-items-center justify-content-between"
                             style="cursor:pointer; min-height:50px;">
                            <div class="d-flex align-items-center">
                                <i class="fa-solid fa-folder text-primary me-3 opacity-75"></i>
                                <span class="fw-bold text-truncate" style="max-width:180px; color:var(--text-color)">[[ folder.label ]]</span>
                            </div>
                            <div class="d-flex align-items-center gap-3">
                                <span class="small fw-bold text-nowrap" style="color:var(--subtle-text-color)">[[ folder.tag_count ]] tags</span>
                                <i class="fa-solid fa-chevron-right opacity-50 small"></i>
                            </div>
                        </div>
                    </div>

                    <!-- Tags in namespace, one page at a time -->
                    <div v-else>
                        <div class="px-2 mb-2 d-flex justify-content-between align-items-center">
                            <small class="fw-bold text-primary text-uppercase">[[ activeNamespace.label ]]</small>
                            <small style="color:var(--subtle-text-color)">[[ activeNamespace.tag_count ]] items</small>
                        </div>
                        <div class="d-flex flex-column gap-2">
                            <div v-for="tag in folderTags" :key="tag.name"
                                 @click="toggleTag(tag.name)"
                                 class="p-2 rounded-3 border d-flex align-items-center justify-content-between"
                                 :class="{ 'border-primary bg-primary-subtle': isNameSelected(tag.name) }"
                                 style="cursor:pointer">
                                <span class="tag-split shadow-sm">
                                    <span class="tag-left" v-html="mapIcon(tag.icon)"></span>
                                    <span class="tag-right" :style="{ backgroundColor: tag.color || '#6c757d' }">
                                        <span :style="{ color: getTextColor(tag.color || '#6c757d') }">
                                            [[ tagLabel(tag.name) ]]
                                        </span>
                                    </span>
                                </span>
                                <div class="d-flex align-items-center gap-2">
                                    <span class="badge rounded-pill border" style="font-size:0.65rem; background:var(--light-bg-color); color:var(--text-color)">
                                        [[ tag.usage_count ]]
                                    </span>
                                    <i v-if="isNameSelected(tag.name)" class="fa-solid fa-check-circle text-primary"></i>
                                </div>
                            </div>
                            <div v-if="isLoading" class="text-center py-3">
                                <div class="spinner-border spinner-border-sm text-primary"></div>
                            </div>
                            <button v-else-if="folderHasMore" type="button" @click.stop="loadFolderPage"
                                    class="btn btn-sm btn-outline-primary rounded-pill fw-bold" style="font-size:.75rem;">
                                Load more ([[ folderTotal - folderTags.length ]] left)
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `
};

export default MultiTagFilter;