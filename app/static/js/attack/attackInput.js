/**
 * attackInput.js — ATT&CK technique picker for the rule edit page.
 * Same UX pattern as TagInput: search + tactic drill-down + selected chips.
 *
 * Props:
 *   modelValue  Array<{technique_id, name, tactic_keys}>   selected techniques
 *   label       String
 *   ruleId      Number   — used to save to DB on add/remove (optional; if absent works in form-only mode)
 *   csrfToken   String
 *
 * Emits: update:modelValue
 */

const TACTIC_COLORS = {
    'reconnaissance':       '#1d4ed8',
    'resource-development': '#6d28d9',
    'initial-access':       '#be185d',
    'execution':            '#92400e',
    'persistence':          '#065f46',
    'privilege-escalation': '#9a3412',
    'defense-evasion':      '#374151',
    'credential-access':    '#991b1b',
    'discovery':            '#0c4a6e',
    'lateral-movement':     '#86198f',
    'collection':           '#064e3b',
    'command-and-control':  '#881337',
    'exfiltration':         '#7c2d12',
    'impact':               '#7f1d1d',
};
const TACTIC_BG = {
    'reconnaissance':       '#e7f0ff',
    'resource-development': '#ede9fe',
    'initial-access':       '#fce7f3',
    'execution':            '#fef3c7',
    'persistence':          '#d1fae5',
    'privilege-escalation': '#ffedd5',
    'defense-evasion':      '#f3f4f6',
    'credential-access':    '#fee2e2',
    'discovery':            '#e0f2fe',
    'lateral-movement':     '#fdf4ff',
    'collection':           '#ecfdf5',
    'command-and-control':  '#fff1f2',
    'exfiltration':         '#fff7ed',
    'impact':               '#fef2f2',
};
const TACTIC_BORDER = {
    'reconnaissance':       '#bfdbfe', 'resource-development': '#ddd6fe',
    'initial-access':       '#fbcfe8', 'execution':            '#fde68a',
    'persistence':          '#a7f3d0', 'privilege-escalation': '#fed7aa',
    'defense-evasion':      '#d1d5db', 'credential-access':    '#fecaca',
    'discovery':            '#bae6fd', 'lateral-movement':     '#f0abfc',
    'collection':           '#6ee7b7', 'command-and-control':  '#fda4af',
    'exfiltration':         '#fdba74', 'impact':               '#fca5a5',
};
const TACTIC_ORDER = [
    'reconnaissance','resource-development','initial-access','execution','persistence',
    'privilege-escalation','defense-evasion','credential-access','discovery',
    'lateral-movement','collection','command-and-control','exfiltration','impact',
];

function tacticLabel(key) {
    return (key || '').replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}
function chipStyle(tacticKeys) {
    const first = (tacticKeys || [])[0] || '';
    return {
        background:  TACTIC_BG[first]     || '#f3f4f6',
        color:       TACTIC_COLORS[first]  || '#374151',
        border:      `1px solid ${TACTIC_BORDER[first] || '#d1d5db'}`,
    };
}

const AttackInput = {
    name: 'AttackInput',
    props: {
        modelValue: { type: Array,  default: () => [] },
        label:      { type: String, default: 'ATT&CK Techniques' },
        ruleId:     { type: Number, default: null },
        csrfToken:  { type: String, default: '' },
    },
    emits: ['update:modelValue'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const { ref, computed, watch, onMounted } = Vue;

        const searchQuery      = ref('');
        const allTechniques    = ref([]);
        const isLoading        = ref(false);
        const isDropdownOpen   = ref(false);
        const activeTactic     = ref(null);
        const saving           = ref(null);  // technique_id being saved

        // ── Fetch all techniques from DB ─────────────────────────────────────
        async function fetchTechniques() {
            isLoading.value = true;
            try {
                const res  = await fetch('/attack/techniques/usage');
                const data = await res.json();
                allTechniques.value = data.techniques || [];
            } catch { allTechniques.value = []; }
            finally  { isLoading.value = false; }
        }

        // ── Grouped by tactic ────────────────────────────────────────────────
        const tacticMap = computed(() => {
            const map = {};
            allTechniques.value.forEach(t => {
                const keys = t.tactic_keys && t.tactic_keys.length ? t.tactic_keys : ['unknown'];
                keys.forEach(k => {
                    if (!map[k]) map[k] = [];
                    map[k].push(t);
                });
            });
            return map;
        });

        const tacticList = computed(() => {
            const out = [];
            TACTIC_ORDER.forEach(k => {
                if (tacticMap.value[k]) out.push({ key: k, label: tacticLabel(k), techniques: tacticMap.value[k] });
            });
            if (tacticMap.value['unknown']) out.push({ key: 'unknown', label: 'Unknown', techniques: tacticMap.value['unknown'] });
            return out;
        });

        const searchResults = computed(() => {
            const q = searchQuery.value.toLowerCase().trim();
            if (!q) return [];
            return allTechniques.value.filter(t =>
                t.id.toLowerCase().includes(q) || t.name.toLowerCase().includes(q)
            );
        });

        // ── Selection helpers ────────────────────────────────────────────────
        function isSelected(id) {
            return props.modelValue.some(t => t.technique_id === id || t.id === id);
        }

        async function toggleTechnique(tech) {
            const id   = tech.id || tech.technique_id;
            const name = tech.name;
            const keys = tech.tactic_keys || [];

            if (isSelected(id)) {
                // Remove
                if (props.ruleId) {
                    saving.value = id;
                    try {
                        await fetch(`/attack/rule/${props.ruleId}/remove/${id}`, {
                            method: 'DELETE',
                            headers: { 'X-CSRFToken': props.csrfToken },
                        });
                    } finally { saving.value = null; }
                }
                emit('update:modelValue', props.modelValue.filter(t => (t.technique_id || t.id) !== id));
            } else {
                // Add
                if (props.ruleId) {
                    saving.value = id;
                    try {
                        await fetch(`/attack/rule/${props.ruleId}/add`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                            body: JSON.stringify({ technique_id: id }),
                        });
                    } finally { saving.value = null; }
                }
                emit('update:modelValue', [...props.modelValue, { technique_id: id, name, tactic_keys: keys }]);
            }
        }

        function toggleDropdown() {
            if (!isDropdownOpen.value && allTechniques.value.length === 0) fetchTechniques();
            isDropdownOpen.value = !isDropdownOpen.value;
        }

        watch(searchQuery, v => { if (v) activeTactic.value = null; });

        onMounted(() => {
            window.addEventListener('click', e => {
                if (!e.target.closest('.attack-input-container')) {
                    isDropdownOpen.value = false;
                    activeTactic.value = null;
                    searchQuery.value = '';
                }
            });
        });

        return {
            searchQuery, allTechniques, isLoading, isDropdownOpen, activeTactic, saving,
            tacticMap, tacticList, searchResults,
            isSelected, toggleTechnique, toggleDropdown,
            chipStyle, tacticLabel,
            TACTIC_COLORS, TACTIC_BG, TACTIC_BORDER,
        };
    },
    template: `
<div class="attack-input-container text-start position-relative">
    <label class="form-label fw-bold text-muted small text-uppercase">[[ label ]]</label>

    <!-- ── Input bar ────────────────────────────────────────────────────── -->
    <div class="input-group shadow-sm rounded-3 border" style="border-width:2px; background:var(--card-bg-color);">
        <span class="input-group-text border-0" style="background:var(--card-bg-color); cursor:pointer;" @click="toggleDropdown">
            <i class="fa-solid fa-crosshairs small" style="color:#e67e22;"></i>
        </span>
        <input type="text" v-model="searchQuery"
               class="form-control border-0 shadow-none"
               style="background:var(--card-bg-color);"
               placeholder="Search by ID or name… or click to browse"
               @focus="toggleDropdown" @input="isDropdownOpen = true" />
        <span class="input-group-text border-0" style="background:var(--card-bg-color);">
            <i class="fas fa-chevron-down small" style="color:var(--subtle-text-color);"
               :style="{ transform: isDropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: '.2s' }"></i>
        </span>
    </div>

    <!-- ── Dropdown ──────────────────────────────────────────────────────── -->
    <div v-if="isDropdownOpen"
         class="position-absolute w-100 shadow-lg border-0 rounded-3 p-3 mt-2"
         style="background:var(--card-bg-color); z-index:1060; max-height:460px; overflow:hidden; display:flex; flex-direction:column; border:1px solid var(--border-color) !important;">

        <!-- Loading -->
        <div v-if="isLoading" class="text-center py-3 text-muted small">
            <div class="spinner-border spinner-border-sm me-2"></div>Loading techniques…
        </div>

        <!-- No DB data -->
        <div v-else-if="!allTechniques.length" class="text-center py-4">
            <i class="fa-solid fa-crosshairs fa-2x text-muted opacity-25 mb-2 d-block"></i>
            <small class="text-muted">No ATT&amp;CK data — run the update job in Admin → Settings → ATT&amp;CK.</small>
        </div>

        <template v-else>
            <!-- Back button (tactic drill) -->
            <div v-if="activeTactic && !searchQuery" class="d-flex align-items-center gap-2 mb-2">
                <button @click.stop="activeTactic = null"
                        class="btn btn-sm btn-outline-primary border-0 rounded-circle d-flex align-items-center justify-content-center"
                        style="width:30px; height:30px; flex-shrink:0;">
                    <i class="fa-solid fa-arrow-left"></i>
                </button>
                <span class="fw-bold small text-uppercase" :style="{ color: TACTIC_COLORS[activeTactic] || '#374151' }">
                    [[ tacticLabel(activeTactic) ]]
                </span>
            </div>

            <div style="overflow-y:auto; flex:1;">

                <!-- ① Search results -->
                <div v-if="searchQuery" class="d-flex flex-column gap-1">
                    <div v-if="!searchResults.length" class="text-center py-3 text-muted small">
                        No match for "[[ searchQuery ]]"
                    </div>
                    <div v-for="t in searchResults" :key="t.id"
                         @click.stop="toggleTechnique(t)"
                         class="p-2 rounded border d-flex align-items-center justify-content-between"
                         :class="{ 'border-primary bg-primary-subtle': isSelected(t.id) }"
                         style="cursor:pointer;">
                        <div class="d-flex align-items-center gap-2">
                            <i class="fa-solid" :class="isSelected(t.id) ? 'fa-square-check text-primary' : 'fa-square'" style="font-size:.75rem; flex-shrink:0;"></i>
                            <span class="badge rounded-pill"
                                  :style="{ background: TACTIC_BG[(t.tactic_keys||[])[0]], color: TACTIC_COLORS[(t.tactic_keys||[])[0]] || '#374151', fontFamily:'monospace', fontSize:'.72rem', border: '1px solid ' + (TACTIC_BORDER[(t.tactic_keys||[])[0]] || '#d1d5db') }">
                                [[ t.id ]]
                            </span>
                            <span class="small fw-bold text-truncate" style="max-width:200px; color:var(--text-color);">[[ t.name ]]</span>
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <div v-if="saving === t.id" class="spinner-border spinner-border-sm text-primary" style="width:14px; height:14px;"></div>
                            <i v-else-if="isSelected(t.id)" class="fa-solid fa-check-circle text-primary"></i>
                        </div>
                    </div>
                </div>

                <!-- ② Tactic folder list -->
                <div v-else-if="!activeTactic" class="d-flex flex-column gap-2">
                    <div v-for="tac in tacticList" :key="tac.key"
                         @click.stop="activeTactic = tac.key"
                         class="p-2 px-3 rounded-3 border d-flex align-items-center justify-content-between"
                         style="cursor:pointer; min-height:46px;">
                        <div class="d-flex align-items-center gap-2">
                            <span class="d-inline-flex align-items-center justify-content-center rounded-circle"
                                  :style="{ background: TACTIC_BG[tac.key] || '#f3f4f6', width:'28px', height:'28px', flexShrink:0 }">
                                <i class="fa-solid fa-crosshairs" :style="{ color: TACTIC_COLORS[tac.key] || '#374151', fontSize:'.65rem' }"></i>
                            </span>
                            <span class="fw-bold" style="color:var(--text-color); font-size:.85rem;">[[ tac.label ]]</span>
                        </div>
                        <div class="d-flex align-items-center gap-3">
                            <span class="small fw-bold text-nowrap" style="color:var(--subtle-text-color);">[[ tac.techniques.length ]] techniques</span>
                            <i class="fa-solid fa-chevron-right opacity-50 small"></i>
                        </div>
                    </div>
                </div>

                <!-- ③ Techniques inside tactic -->
                <div v-else class="d-flex flex-column gap-1">
                    <div v-for="t in (tacticMap[activeTactic] || [])" :key="t.id"
                         @click.stop="toggleTechnique(t)"
                         class="p-2 rounded-3 border d-flex align-items-center justify-content-between"
                         :class="{ 'border-primary bg-primary-subtle': isSelected(t.id) }"
                         style="cursor:pointer;">
                        <div class="d-flex align-items-center gap-2">
                            <i class="fa-solid" :class="isSelected(t.id) ? 'fa-square-check text-primary' : 'fa-square'" style="font-size:.75rem; flex-shrink:0;"></i>
                            <span class="badge rounded-pill"
                                  :style="{ background: TACTIC_BG[activeTactic], color: TACTIC_COLORS[activeTactic] || '#374151', fontFamily:'monospace', fontSize:'.72rem', border: '1px solid ' + (TACTIC_BORDER[activeTactic] || '#d1d5db'), flexShrink:0 }">
                                [[ t.id ]]
                            </span>
                            <span class="small fw-bold text-truncate" style="max-width:190px; color:var(--text-color);">[[ t.name ]]</span>
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge rounded-pill border" style="font-size:.65rem; background:var(--light-bg-color); color:var(--subtle-text-color);">[[ t.count ]]</span>
                            <div v-if="saving === t.id" class="spinner-border spinner-border-sm text-primary" style="width:14px; height:14px;"></div>
                            <i v-else-if="isSelected(t.id)" class="fa-solid fa-check-circle text-primary"></i>
                        </div>
                    </div>
                </div>

            </div>
        </template>
    </div>

    <!-- ── Selected chips ───────────────────────────────────────────────── -->
    <div v-if="modelValue.length" class="d-flex flex-wrap gap-2 mt-3 p-3 rounded-3 border shadow-sm" style="background:var(--light-bg-color);">
        <span v-for="t in modelValue" :key="t.technique_id || t.id"
              class="d-inline-flex align-items-center gap-1 rounded-pill px-2 py-1"
              :style="chipStyle(t.tactic_keys)"
              style="font-size:.78rem;">
            <span style="font-family:'Courier New',monospace; font-weight:700; font-size:.72rem;">[[ t.technique_id || t.id ]]</span>
            <span class="opacity-40">·</span>
            <span style="font-weight:500; max-width:130px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">[[ t.name ]]</span>
            <button @click.stop="toggleTechnique({ id: t.technique_id || t.id, name: t.name, tactic_keys: t.tactic_keys })"
                    class="btn p-0 border-0 ms-1 d-flex align-items-center"
                    style="background:transparent; color:inherit; opacity:.7; cursor:pointer;"
                    :disabled="saving === (t.technique_id || t.id)">
                <div v-if="saving === (t.technique_id || t.id)" class="spinner-border spinner-border-sm" style="width:12px; height:12px;"></div>
                <i v-else class="fa-solid fa-circle-xmark" style="font-size:.8rem;"></i>
            </button>
        </span>
    </div>

</div>
`,
};

export default AttackInput;
