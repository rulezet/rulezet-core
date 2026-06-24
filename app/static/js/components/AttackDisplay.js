/**
 * AttackDisplay.js — Collapsible ATT&CK technique section (rule detail page).
 * Read-only. Exact same style as TagDisplay.
 *
 * Props:
 *   ruleId  (Number) — rule whose techniques to display
 */

const { defineComponent, ref, computed, onMounted } = Vue;

const TACTIC_COLORS = {
    'reconnaissance':       { bg: '#e7f0ff', text: '#1d4ed8', border: '#bfdbfe' },
    'resource-development': { bg: '#ede9fe', text: '#6d28d9', border: '#ddd6fe' },
    'initial-access':       { bg: '#fce7f3', text: '#be185d', border: '#fbcfe8' },
    'execution':            { bg: '#fef3c7', text: '#92400e', border: '#fde68a' },
    'persistence':          { bg: '#d1fae5', text: '#065f46', border: '#a7f3d0' },
    'privilege-escalation': { bg: '#ffedd5', text: '#9a3412', border: '#fed7aa' },
    'defense-evasion':      { bg: '#f3f4f6', text: '#374151', border: '#d1d5db' },
    'credential-access':    { bg: '#fee2e2', text: '#991b1b', border: '#fecaca' },
    'discovery':            { bg: '#e0f2fe', text: '#0c4a6e', border: '#bae6fd' },
    'lateral-movement':     { bg: '#fdf4ff', text: '#86198f', border: '#f0abfc' },
    'collection':           { bg: '#ecfdf5', text: '#064e3b', border: '#6ee7b7' },
    'command-and-control':  { bg: '#fff1f2', text: '#881337', border: '#fda4af' },
    'exfiltration':         { bg: '#fff7ed', text: '#7c2d12', border: '#fdba74' },
    'impact':               { bg: '#fef2f2', text: '#7f1d1d', border: '#fca5a5' },
};

function chipStyle(tacticKeys) {
    const first = (tacticKeys || [])[0] || '';
    const c = TACTIC_COLORS[first] || { bg: '#f3f4f6', text: '#374151', border: '#d1d5db' };
    return { background: c.bg, color: c.text, border: `1px solid ${c.border}` };
}

export default defineComponent({
    name: 'AttackDisplay',
    props: {
        ruleId:     { type: Number, required: true },
        maxVisible: { type: Number, default: 10 },
    },
    setup(props) {
        const techniques  = ref([]);
        const loading     = ref(true);
        const isCollapsed = ref(false);
        const isShowingAll = ref(false);

        const visibleTechniques = computed(() =>
            isShowingAll.value ? techniques.value : techniques.value.slice(0, props.maxVisible)
        );

        async function fetchTechniques() {
            loading.value = true;
            try {
                const res = await fetch(`/attack/rule/${props.ruleId}`);
                techniques.value = await res.json();
            } catch {
                techniques.value = [];
            } finally {
                loading.value = false;
            }
        }

        onMounted(fetchTechniques);

        return { techniques, loading, isCollapsed, isShowingAll, visibleTechniques, chipStyle };
    },
    template: `
<div class="mt-4">

    <!-- ── Section header (same as TagDisplay) ─────────────────────────── -->
    <div @click="isCollapsed = !isCollapsed" style="cursor:pointer" class="user-select-none">
        <div class="d-flex justify-content-between align-items-center">
            <div class="d-flex align-items-center gap-2">
                <div style="width:3px; height:14px; background:#0d6efd; border-radius:2px; flex-shrink:0;"></div>
                <span class="fw-bold d-flex align-items-center" style="font-size:.75rem; text-transform:uppercase; letter-spacing:.07em; color:var(--subtle-text-color);">
                    <i class="fa-solid fa-crosshairs me-1"></i>MITRE ATT&amp;CK
                    <i class="fas fa-chevron-down ms-2 small opacity-50"
                       :style="{ transform: isCollapsed ? 'rotate(0deg)' : 'rotate(180deg)', transition: '0.3s' }"></i>
                </span>
            </div>
            <span v-if="!isCollapsed && techniques.length"
                  class="badge rounded-pill px-3"
                  style="background:var(--light-bg-color); color:var(--subtle-text-color); border:1px solid var(--border-color); font-size:.75rem;">
                {{ techniques.length }} technique{{ techniques.length === 1 ? '' : 's' }}
            </span>
        </div>
        <!-- Collapsed hint -->
        <div v-if="isCollapsed" class="text-muted small mt-1" style="padding-left:1.5rem">
            <i class="fas fa-info-circle me-1"></i>
            <strong>{{ techniques.length }} technique{{ techniques.length === 1 ? '' : 's' }}</strong> hidden — click to expand.
        </div>
    </div>

    <!-- ── Body (same card as TagDisplay) ──────────────────────────────── -->
    <div v-show="!isCollapsed" class="mt-3">
        <div class="d-flex flex-wrap gap-2 p-3 rounded-3 shadow-sm border" style="background: var(--light-bg-color)">

            <!-- Loading -->
            <div v-if="loading" class="d-flex align-items-center gap-2 py-1">
                <div class="spinner-border spinner-border-sm text-primary"></div>
                <small class="text-muted">Loading techniques…</small>
            </div>

            <!-- Empty -->
            <div v-else-if="!techniques.length" class="text-muted small fst-italic py-1">
                <i class="fa-solid fa-crosshairs me-1 opacity-50"></i>
                No ATT&amp;CK techniques detected.
                <span class="d-block mt-1" style="font-size:.72rem;">Run the auto-parse job from Admin → Settings → ATT&amp;CK.</span>
            </div>

            <!-- Technique chips -->
            <template v-else>
                <a v-for="t in visibleTechniques" :key="t.technique_id"
                   :href="'/attack/technique/' + t.technique_id"
                   class="d-inline-flex align-items-center gap-1 text-decoration-none rounded-pill px-2 py-1"
                   :style="chipStyle(t.tactic_keys)"
                   style="font-size:.78rem; transition: filter .12s, transform .1s;"
                   :title="(t.tactic_keys && t.tactic_keys.length ? t.tactic_keys[0].replace(/-/g,' ') : '') + ' — ' + t.name">
                    <span style="font-family:'Courier New',monospace; font-weight:700; font-size:.72rem; white-space:nowrap;">{{ t.technique_id }}</span>
                    <span class="opacity-40">·</span>
                    <span style="font-weight:500; max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ t.name }}</span>
                </a>

                <!-- Show more / less -->
                <button v-if="techniques.length > maxVisible"
                        @click.stop="isShowingAll = !isShowingAll"
                        class="btn btn-sm btn-outline-primary rounded-pill px-3 fw-bold shadow-sm"
                        style="font-size:0.75rem;">
                    {{ isShowingAll ? 'Show less' : '+ ' + (techniques.length - maxVisible) + ' more' }}
                </button>
            </template>

        </div>
    </div>
</div>
`,
});
