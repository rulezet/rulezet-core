// Multi-select "binary" picker for the rule-validation quarantine review —
// same dropdown-pill look and feel as MultiTagFilter / MultiVulnerabilityFilter,
// just backed by a plain options list already loaded client-side (the full
// run's binary names) instead of a fetched, paginated API.
const MultiBinaryFilter = {
    props: {
        modelValue: { type: Array, default: () => [] },
        options: { type: Array, default: () => [] },
        placeholder: { type: String, default: 'Filter by binary…' },
    },
    emits: ['update:modelValue', 'change'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const searchCtx = Vue.ref('')
        const selectedNames = Vue.ref([...props.modelValue])
        Vue.watch(() => props.modelValue, (val) => { selectedNames.value = [...val] })

        const filteredList = Vue.computed(() => {
            const q = searchCtx.value.trim().toLowerCase()
            return props.options
                .filter(b => !selectedNames.value.includes(b))
                .filter(b => !q || b.toLowerCase().includes(q))
                .slice(0, 50)
        })

        function toggleBinary(name) {
            const i = selectedNames.value.indexOf(name)
            if (i > -1) selectedNames.value.splice(i, 1)
            else selectedNames.value.push(name)
            emit('update:modelValue', [...selectedNames.value])
            emit('change', [...selectedNames.value])
        }

        return {
            searchCtx, selectedNames, filteredList, toggleBinary,
            clearAll: () => { selectedNames.value = []; emit('update:modelValue', []); emit('change', []) },
        }
    },
    template: `
    <div class="dropdown multi-binary-filter w-100">
        <div class="form-control d-flex flex-wrap gap-2 align-items-center p-2 shadow-sm border-secondary-subtle"
             data-bs-toggle="dropdown" data-bs-auto-close="outside"
             style="cursor:pointer; min-height:48px; border-radius:12px;">
            <i class="fa-solid fa-microchip text-danger opacity-75 ms-1 me-1"></i>
            <span v-if="selectedNames.length === 0" class="text-muted small fw-bold">[[ placeholder ]]</span>
            <span v-for="name in selectedNames" :key="name"
                  class="d-flex align-items-center rounded-2 shadow-sm"
                  style="font-size:0.75rem; font-family:monospace; background:rgba(220,53,69,.12); overflow:hidden;">
                <span class="px-2 py-1" style="color:#dc3545;">[[ name ]]</span>
                <i class="fa-solid fa-circle-xmark opacity-75 me-2" @click.stop="toggleBinary(name)"
                   style="color:#dc3545; cursor:pointer;"></i>
            </span>
            <i class="fa-solid fa-chevron-down ms-auto me-1 text-muted small"></i>
        </div>

        <div class="dropdown-menu shadow-lg border-0 w-100 p-3 mt-2" style="max-height:400px; border-radius:15px; z-index:1060; min-width:320px;">
            <div class="input-group input-group-sm mb-2">
                <span class="input-group-text bg-light border-0"><i class="fa-solid fa-magnifying-glass"></i></span>
                <input type="text" v-model="searchCtx" class="form-control bg-light border-0 shadow-none" placeholder="Search binaries…">
            </div>
            <div class="pe-1" style="max-height:280px; overflow-y:auto;">
                <div v-if="filteredList.length === 0" class="text-center py-3 text-muted small">
                    No more matches in this run's results.
                </div>
                <div v-for="name in filteredList" :key="name"
                     @click="toggleBinary(name)"
                     class="p-2 rounded border d-flex align-items-center gap-2 mb-1"
                     style="cursor:pointer; font-size:0.82rem; font-family:monospace; color:#dc3545;">
                    <i class="fa-solid fa-microchip" style="font-size:0.7rem;"></i>[[ name ]]
                </div>
            </div>
        </div>
    </div>
    `,
}

export default MultiBinaryFilter
