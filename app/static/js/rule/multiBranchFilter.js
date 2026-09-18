const MultiBranchFilter = {
    props: {
        modelValue: { type: Array, default: () => [] },
        placeholder: { type: String, default: 'Filter by branch...' },
        apiEndpoint: { type: String, default: '/rule/get_rules_branches_usage' },
        userId: { type: Number, default: null },
        sourceRules: { type: String, default: '' },
        // Query string of every OTHER currently active RuleList filter — keeps
        // these counts scoped to what's actually visible.
        filterContext: { type: String, default: '' },
    },
    emits: ['update:modelValue', 'change'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const list_branches = Vue.ref([]);
        const searchCtx = Vue.ref('');
        const selectedNames = Vue.ref([...props.modelValue]);
        const isLoading = Vue.ref(false);

        Vue.watch(() => props.modelValue, (newVal) => {
            selectedNames.value = [...newVal];
        }, { deep: true });

        const fetchBranches = async () => {
            isLoading.value = true;
            try {
                let url = props.apiEndpoint;
                const params = new URLSearchParams(props.filterContext);

                if (props.userId !== null && !isNaN(props.userId)) {
                    params.append('user_id', props.userId.toString());
                }

                if (props.sourceRules && !params.has('sources')) {
                    params.append('sources', props.sourceRules);
                }

                if (params.toString()) {
                    url += (url.includes('?') ? '&' : '?') + params.toString();
                }

                const response = await fetch(url);
                if (response.ok) {
                    const data = await response.json();
                    list_branches.value = Array.isArray(data) ? data : (data.branches || []);
                }
            } catch (e) {
                console.error("Error loading filter branches", e);
            } finally {
                isLoading.value = false;
            }
        };

        Vue.watch(() => props.sourceRules, fetchBranches);
        Vue.watch(() => props.filterContext, fetchBranches);

        const filteredList = Vue.computed(() => {
            if (!searchCtx.value) return list_branches.value;
            const q = searchCtx.value.toLowerCase();
            return list_branches.value.filter(b => b.name.toLowerCase().includes(q));
        });

        const toggleBranch = (name) => {
            const index = selectedNames.value.indexOf(name);
            if (index > -1) {
                selectedNames.value.splice(index, 1);
            } else {
                selectedNames.value.push(name);
            }
            emit('update:modelValue', [...selectedNames.value]);
            emit('change', [...selectedNames.value]);
        };

        Vue.onMounted(fetchBranches);

        return {
            searchCtx, selectedNames, list_branches, filteredList,
            toggleBranch, isLoading,
            clearAll: () => {
                selectedNames.value = [];
                emit('update:modelValue', []);
                emit('change', []);
            }
        };
    },
    template: `
    <div class="dropdown multi-branch-filter w-100">
        <div class="form-control d-flex flex-wrap gap-2 align-items-center p-2 shadow-sm border-secondary-subtle"
             data-bs-toggle="dropdown" data-bs-auto-close="outside"
             style="cursor: pointer; min-height: 48px; border-radius: 12px;">

            <i class="fa-solid fa-code-branch text-info opacity-75 ms-1 me-1"></i>
            <span v-if="selectedNames.length === 0" class="text-muted small fw-bold">[[ placeholder ]]</span>

            <span v-for="name in selectedNames" :key="name"
                  class="d-flex align-items-center rounded-2 shadow-sm bg-secondary text-white animate__animated animate__fadeInSmall"
                  style="font-size: 0.75rem; overflow: hidden;">
                <div class="px-2 py-1 bg-black bg-opacity-10 border-end border-white border-opacity-10">
                    <i class="fa-solid fa-code-branch"></i>
                </div>
                <div class="px-2 py-1 d-flex align-items-center">
                    <span class="fw-bold me-2" style="font-family:'JetBrains Mono',monospace;">[[ name ]]</span>
                    <i class="fa-solid fa-circle-xmark opacity-75 ms-1 hover-scale" @click.stop="toggleBranch(name)" style="cursor: pointer;"></i>
                </div>
            </span>
            <i class="fa-solid fa-chevron-down ms-auto me-1 text-muted small"></i>
        </div>

        <div class="dropdown-menu shadow-lg border-0 w-100 p-3 mt-2 animate__animated animate__fadeIn"
             style="max-height: 450px; border-radius: 15px; z-index: 1060; min-width: 320px;">

            <div class="input-group input-group-sm mb-3">
                <span class="input-group-text bg-light border-0"><i class="fa-solid fa-magnifying-glass"></i></span>
                <input type="text" v-model="searchCtx" class="form-control bg-light border-0 shadow-none" placeholder="Search branch...">
            </div>

            <div class="custom-tag-scroll pe-2" style="max-height: 350px; overflow-y: auto;">

                <div v-if="!isLoading && filteredList.length === 0"
                     class="text-center py-4 animate__animated animate__fadeIn" style="color: var(--text-color)">
                    <div class="mb-2">
                        <i class="fa-solid fa-code-branch fa-3x text-muted opacity-25"></i>
                    </div>
                    <h6 class="text-muted fw-bold">No branches found</h6>
                    <p class="small text-muted opacity-75">Try a different search term, or no imported rule tracks a branch yet.</p>
                </div>

                <div v-else class="d-flex flex-column gap-1">
                    <div v-for="b in filteredList" :key="b.name"
                         @click="toggleBranch(b.name)"
                         class="p-2 rounded border d-flex align-items-center justify-content-between tag-item-hover"
                         :class="{'border-primary bg-primary-subtle shadow-sm': selectedNames.includes(b.name)}"
                         style="cursor:pointer;">
                         <div class="d-flex align-items-center">
                            <i class="fa-solid fa-code-branch me-2" style="color: var(--text-color)"></i>
                            <span class="small fw-bold" style="color: var(--text-color); font-family:'JetBrains Mono',monospace;">[[ b.name ]]</span>
                         </div>
                         <div class="d-flex align-items-center gap-2">
                            <span class="badge rounded-pill bg-light border" style="font-size: 0.65rem; color: var(--text-color);">[[ b.count ]]</span>
                            <i v-if="selectedNames.includes(b.name)" class="fa-solid fa-check-circle text-primary"></i>
                         </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `
};

export default MultiBranchFilter;
