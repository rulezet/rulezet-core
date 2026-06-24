const { defineComponent, ref, computed } = Vue;

const MITRE_BASE = 'https://attack.mitre.org/techniques/';

export default defineComponent({
    name: 'AttackMatrix',
    props: {
        coverage: { type: Object, default: null },
        loading:  { type: Boolean, default: false },
    },
    setup(props) {
        const selected = ref(null); // { tactic, technique }

        function selectTechnique(tactic, technique) {
            if (
                selected.value &&
                selected.value.technique.id === technique.id &&
                selected.value.tactic.key   === tactic.key
            ) {
                selected.value = null;
            } else {
                selected.value = { tactic, technique };
            }
        }

        function closePicker() { selected.value = null; }

        // Colour logic — one blue gradient per coverage level
        function techBg(count) {
            if (!count) return null;
            const stops = [
                'rgba(13,110,253,.15)',
                'rgba(13,110,253,.30)',
                'rgba(13,110,253,.50)',
                'rgba(13,110,253,.70)',
                '#0d6efd',
            ];
            const idx = count === 1 ? 0 : count <= 3 ? 1 : count <= 7 ? 2 : count <= 15 ? 3 : 4;
            return stops[idx];
        }

        function techColor(count) {
            return count > 7 ? '#fff' : 'var(--text-color)';
        }

        function tacticHeaderStyle(tactic) {
            if (!tactic.covered) return {};
            const max = 20;
            const pct = Math.min(tactic.rule_count / max, 1);
            const alpha = 0.18 + pct * 0.72; // 0.18 → 0.90
            return { background: `rgba(13,110,253,${alpha.toFixed(2)})`, color: alpha > 0.5 ? '#fff' : 'var(--text-color)' };
        }

        function mitreUrl(techId) {
            return MITRE_BASE + techId.replace('.', '/');
        }

        const showAllTactics = ref(false);

        const stats   = computed(() => props.coverage?.stats ?? {});
        const tactics = computed(() => props.coverage?.tactics ?? []);

        const visibleTactics = computed(() =>
            showAllTactics.value
                ? tactics.value
                : tactics.value.filter(t => t.covered)
        );

        const hiddenCount = computed(() =>
            tactics.value.filter(t => !t.covered).length
        );

        const coveragePct = computed(() => {
            const s = stats.value;
            if (!s.total_tactics) return 0;
            return Math.round((s.covered_tactics / s.total_tactics) * 100);
        });

        const overallRulePct = computed(() => {
            const s = stats.value;
            if (!s.total_rules) return 0;
            return Math.round((s.rules_with_attack / s.total_rules) * 100);
        });

        return {
            selected, selectTechnique, closePicker,
            techBg, techColor, tacticHeaderStyle, mitreUrl,
            stats, tactics, visibleTactics, hiddenCount,
            showAllTactics, coveragePct, overallRulePct,
        };
    },
    template: `
<div class="am-root">

    <!-- ── Loading ─────────────────────────────────────────────── -->
    <div v-if="loading" class="am-loading">
        <div class="spinner-border text-primary" role="status" style="width:2rem;height:2rem;"></div>
        <span class="ms-3 small" style="color:var(--subtle-text-color);">Analysing ATT&amp;CK coverage…</span>
    </div>

    <!-- ── No data ─────────────────────────────────────────────── -->
    <div v-else-if="!coverage || !stats.total_rules" class="am-empty">
        <i class="fa-solid fa-grid-2 fa-2x mb-3 opacity-25"></i>
        <div class="fw-semibold mb-1">No ATT&amp;CK data available</div>
        <div class="small">Add Sigma rules with <code>attack.*</code> tags or YARA rules with technique IDs in metadata.</div>
    </div>

    <!-- ── Main content ────────────────────────────────────────── -->
    <template v-else>

        <!-- Stats bar -->
        <div class="am-stats-bar">
            <div class="am-stat am-stat--blue">
                <div class="am-stat-value">{{ stats.covered_tactics }}<span class="am-stat-total">/{{ stats.total_tactics }}</span></div>
                <div class="am-stat-label">Tactics covered</div>
            </div>
            <div class="am-stat am-stat--teal">
                <div class="am-stat-value">{{ stats.unique_techniques }}</div>
                <div class="am-stat-label">Unique techniques</div>
            </div>
            <div class="am-stat am-stat--green">
                <div class="am-stat-value">{{ stats.rules_with_attack }}</div>
                <div class="am-stat-label">Rules with ATT&amp;CK</div>
            </div>
            <div class="am-stat am-stat--purple am-stat--wide">
                <div class="am-stat-label mb-2" style="font-size:.72rem;">
                    Tactic coverage
                    <span class="ms-1 fw-bold" style="color:var(--text-color);">{{ coveragePct }}%</span>
                </div>
                <div class="am-progress">
                    <div class="am-progress-fill" :style="{ width: coveragePct + '%' }"></div>
                </div>
                <div class="am-stat-label mt-2" style="font-size:.72rem;">
                    Rules annotated
                    <span class="ms-1 fw-bold" style="color:var(--text-color);">{{ overallRulePct }}%</span>
                </div>
                <div class="am-progress">
                    <div class="am-progress-fill am-progress-fill--teal" :style="{ width: overallRulePct + '%' }"></div>
                </div>
            </div>
        </div>

        <!-- Legend -->
        <div class="am-legend">
            <span class="am-legend-label">Coverage density:</span>
            <span class="am-legend-chip" style="background:var(--light-bg-color);color:var(--subtle-text-color);border:1px solid var(--border-color);">Not covered</span>
            <span class="am-legend-chip" style="background:rgba(13,110,253,.15);color:var(--text-color);">1 rule</span>
            <span class="am-legend-chip" style="background:rgba(13,110,253,.35);color:var(--text-color);">2–3 rules</span>
            <span class="am-legend-chip" style="background:rgba(13,110,253,.55);color:var(--text-color);">4–7 rules</span>
            <span class="am-legend-chip" style="background:rgba(13,110,253,.75);color:#fff;">8–15 rules</span>
            <span class="am-legend-chip" style="background:#0d6efd;color:#fff;">16+ rules</span>
        </div>

        <!-- Toggle bar -->
        <div class="d-flex align-items-center justify-content-between mb-2">
            <span class="small" style="color:var(--subtle-text-color);">
                <template v-if="!showAllTactics && hiddenCount > 0">
                    Showing {{ visibleTactics.length }} covered tactic{{ visibleTactics.length === 1 ? '' : 's' }}
                </template>
                <template v-else>
                    Showing all {{ tactics.length }} tactics
                </template>
            </span>
            <button v-if="hiddenCount > 0"
                    class="btn btn-sm btn-outline-secondary"
                    style="font-size:.72rem;padding:.2rem .65rem;border-radius:99px;"
                    @click="showAllTactics = !showAllTactics">
                <i :class="showAllTactics ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'" class="me-1"></i>
                <template v-if="showAllTactics">Hide uncovered</template>
                <template v-else>Show all {{ hiddenCount }} uncovered</template>
            </button>
        </div>

        <!-- Matrix grid -->
        <div class="am-matrix-scroll">
            <div class="am-matrix">
                <div
                    v-for="tactic in visibleTactics"
                    :key="tactic.key"
                    class="am-col"
                    :class="{ 'am-col--empty': !tactic.covered, 'am-col--active': selected && selected.tactic.key === tactic.key }">

                    <!-- Tactic header -->
                    <div class="am-col-head" :style="tacticHeaderStyle(tactic)">
                        <div class="am-col-head-name" :title="tactic.label">{{ tactic.label }}</div>
                        <div class="am-col-head-meta">
                            <span v-if="tactic.covered" class="am-col-badge">
                                {{ tactic.technique_count }} tech · {{ tactic.rule_count }} rule{{ tactic.rule_count === 1 ? '' : 's' }}
                            </span>
                            <span v-else class="am-col-badge am-col-badge--empty">–</span>
                        </div>
                    </div>

                    <!-- Technique chips -->
                    <div class="am-tech-list">
                        <button
                            v-for="tech in tactic.techniques"
                            :key="tech.id"
                            class="am-tech"
                            :class="{ 'am-tech--selected': selected && selected.technique.id === tech.id && selected.tactic.key === tactic.key }"
                            :style="{ background: techBg(tech.count), color: techColor(tech.count) }"
                            :title="tech.id + ' — ' + tech.count + ' rule' + (tech.count === 1 ? '' : 's')"
                            @click="selectTechnique(tactic, tech)">
                            {{ tech.id }}
                            <span class="am-tech-badge">{{ tech.count }}</span>
                        </button>
                        <div v-if="!tactic.techniques.length" class="am-tech-empty">—</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Detail panel -->
        <transition name="am-panel-slide">
            <div v-if="selected" class="am-detail-panel">
                <div class="am-detail-header">
                    <div class="am-detail-ids">
                        <span class="am-detail-tactic">{{ selected.tactic.label }}</span>
                        <i class="fa-solid fa-chevron-right mx-2 small opacity-50"></i>
                        <span class="am-detail-tech-id">{{ selected.technique.id }}</span>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <a :href="mitreUrl(selected.technique.id)" target="_blank" rel="noopener"
                           class="btn btn-sm btn-outline-primary" style="font-size:.72rem;padding:.2rem .6rem;">
                            <i class="fa-solid fa-arrow-up-right-from-square me-1"></i>MITRE ATT&amp;CK
                        </a>
                        <button class="btn btn-sm btn-outline-secondary" style="font-size:.72rem;padding:.2rem .55rem;" @click="closePicker">
                            <i class="fa-solid fa-xmark"></i>
                        </button>
                    </div>
                </div>
                <div class="am-detail-body">
                    <div class="am-detail-rules-label">
                        <i class="fa-solid fa-shield-halved me-1 text-primary"></i>
                        {{ selected.technique.count }} rule{{ selected.technique.count === 1 ? '' : 's' }} covering this technique
                    </div>
                    <div class="am-detail-rules">
                        <a
                            v-for="rule in selected.technique.rules"
                            :key="rule.id"
                            :href="'/rule/detail_rule/' + rule.id"
                            target="_blank"
                            class="am-rule-chip">
                            <i class="fa-solid fa-file-shield me-1 opacity-60" style="font-size:.7rem;"></i>
                            {{ rule.name || 'Rule #' + rule.id }}
                        </a>
                    </div>
                </div>
            </div>
        </transition>

    </template>
</div>
`,
});
