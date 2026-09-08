// Single-select "risk level" picker for the rule-validation quarantine
// review — same dropdown-pill look and feel as MultiTagFilter /
// MultiVulnerabilityFilter, just backed by a fixed, small taxonomy (the
// MISP false-positive:risk="..." tags) instead of a fetched list, and a
// single value instead of an array (a rule has exactly one proposed risk).
const MultiRiskFilter = {
    props: {
        modelValue: { type: String, default: '' },      // '' | <level> | 'mismatch'
        levels: { type: Array, default: () => [] },      // [{ level, label, color }]
        placeholder: { type: String, default: 'Filter by risk…' },
    },
    emits: ['update:modelValue', 'change'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        function textColor(hex) {
            if (!hex) return '#fff'
            const h = hex.replace('#', '')
            const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16)
            return (r * 299 + g * 587 + b * 114) / 1000 > 150 ? '#1a1a1a' : '#fff'
        }
        const MISMATCH_META = { level: 'mismatch', label: "Disagrees with rule's own claim", color: '#dc3545' }
        const selectedMeta = Vue.computed(() => {
            if (!props.modelValue) return null
            if (props.modelValue === 'mismatch') return MISMATCH_META
            return props.levels.find(l => l.level === props.modelValue) || null
        })
        function select(level) {
            const next = props.modelValue === level ? '' : level
            emit('update:modelValue', next)
            emit('change', next)
        }
        return {
            selectedMeta, select, textColor, MISMATCH_META,
            clearAll: () => { emit('update:modelValue', ''); emit('change', '') },
        }
    },
    template: `
    <div class="dropdown multi-risk-filter w-100">
        <div class="form-control d-flex flex-wrap gap-2 align-items-center p-2 shadow-sm border-secondary-subtle"
             data-bs-toggle="dropdown" data-bs-auto-close="outside"
             style="cursor:pointer; min-height:48px; border-radius:12px;">
            <i class="fa-solid fa-triangle-exclamation opacity-75 ms-1 me-1"
               :style="{ color: selectedMeta ? selectedMeta.color : '' }"></i>
            <span v-if="!selectedMeta" class="text-muted small fw-bold">[[ placeholder ]]</span>
            <span v-else class="d-flex align-items-center rounded-2 shadow-sm" style="font-size:0.75rem; overflow:hidden;"
                  :style="{ background: selectedMeta.color }">
                <span class="px-2 py-1 fw-bold" :style="{ color: textColor(selectedMeta.color) }">[[ selectedMeta.label ]]</span>
                <i class="fa-solid fa-circle-xmark opacity-75 me-2" @click.stop="select(selectedMeta.level)"
                   :style="{ color: textColor(selectedMeta.color), cursor: 'pointer' }"></i>
            </span>
            <i class="fa-solid fa-chevron-down ms-auto me-1 text-muted small"></i>
        </div>

        <div class="dropdown-menu shadow-lg border-0 p-2 mt-2" style="border-radius:15px; z-index:1060; min-width:270px;">
            <div v-for="lvl in levels" :key="lvl.level"
                 @click="select(lvl.level)"
                 class="p-2 rounded-3 d-flex align-items-center justify-content-between mb-1"
                 style="cursor:pointer;"
                 :style="{
                     border: '1px solid ' + (modelValue === lvl.level ? lvl.color : 'var(--border-color)'),
                     background: modelValue === lvl.level ? lvl.color + '22' : 'transparent',
                 }">
                <span class="d-flex align-items-center gap-2">
                    <span style="width:.65rem;height:.65rem;border-radius:50%;display:inline-block;" :style="{ background: lvl.color }"></span>
                    <span class="fw-semibold small" style="color:var(--text-color);">[[ lvl.label ]]</span>
                </span>
                <i v-if="modelValue === lvl.level" class="fa-solid fa-check-circle" :style="{ color: lvl.color }"></i>
            </div>

            <div @click="select('mismatch')"
                 class="p-2 rounded-3 d-flex align-items-center justify-content-between"
                 style="cursor:pointer;"
                 :class="modelValue === 'mismatch' ? 'bg-danger-subtle' : ''"
                 :style="{ border: '1px solid ' + (modelValue === 'mismatch' ? MISMATCH_META.color : 'var(--border-color)') }">
                <span class="d-flex align-items-center gap-2 small fw-semibold text-danger">
                    <i class="fa-solid fa-triangle-exclamation"></i> [[ MISMATCH_META.label ]]
                </span>
                <i v-if="modelValue === 'mismatch'" class="fa-solid fa-check-circle text-danger"></i>
            </div>
        </div>
    </div>
    `,
}

export default MultiRiskFilter
