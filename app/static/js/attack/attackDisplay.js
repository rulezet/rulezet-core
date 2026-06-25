/**
 * attackDisplay.js — Collapsible ATT&CK section.
 * Same header/wrapper structure as VulnerabilityDisplay and TagDisplay.
 * Delegates chip rendering to AttackDisplayList for visual consistency.
 */
import AttackDisplayList from '/static/js/attack/attackDisplayList.js'

const AttackDisplay = {
    components: { AttackDisplayList },
    props: {
        attacks:      { type: Array,   default: () => [] },
        loading:      { type: Boolean, default: false },
        maxVisible:   { type: Number,  default: 10 },
        sectionTitle: { type: String,  default: 'ATT&CK Techniques' },
    },
    delimiters: ['[[', ']]'],
    data() {
        return { isCollapsed: false };
    },
    template: `
    <div class="mt-4 mb-4">
        <div @click="isCollapsed = !isCollapsed" style="cursor:pointer;" class="user-select-none">
            <div class="d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center gap-2">
                    <div style="width:3px;height:14px;background:#0d6efd;border-radius:2px;flex-shrink:0;"></div>
                    <span class="fw-bold d-flex align-items-center"
                          style="font-size:.75rem;text-transform:uppercase;letter-spacing:.07em;color:var(--subtle-text-color);">
                        <i class="fa-solid fa-crosshairs me-1"></i>[[ sectionTitle ]]
                        <i class="fas fa-chevron-down ms-2 small opacity-50"
                           :style="{ transform: isCollapsed ? 'rotate(0deg)' : 'rotate(180deg)', transition:'0.3s' }"></i>
                    </span>
                </div>
                <span v-if="!isCollapsed" class="badge rounded-pill px-3"
                      style="background:var(--light-bg-color);color:var(--subtle-text-color);border:1px solid var(--border-color);font-size:.75rem;">
                    [[ attacks.length ]] technique[[ attacks.length !== 1 ? 's' : '' ]]
                </span>
            </div>
            <div v-if="isCollapsed" class="text-muted small mt-1" style="padding-left:1.5rem;">
                <i class="fas fa-info-circle me-1"></i>
                <strong>[[ attacks.length ]] technique[[ attacks.length !== 1 ? 's' : '' ]]</strong> hidden — click to expand.
            </div>
        </div>

        <div v-show="!isCollapsed" class="mt-3">
            <div class="p-3 rounded-3 shadow-sm border" style="background:var(--light-bg-color);">
                <div v-if="loading" class="d-flex align-items-center gap-2 py-1">
                    <div class="spinner-border spinner-border-sm text-primary"></div>
                    <small class="text-muted">Loading techniques…</small>
                </div>
                <div v-else-if="attacks.length === 0" class="text-muted small fst-italic py-1">
                    <i class="fa-solid fa-crosshairs me-1 opacity-50"></i> No ATT&amp;CK techniques assigned.
                </div>
                <attack-display-list v-else
                    :initial-attacks="attacks"
                    :max-visible="maxVisible">
                </attack-display-list>
            </div>
        </div>
    </div>
    `,
};

export default AttackDisplay;
