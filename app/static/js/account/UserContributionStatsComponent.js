import ChartViewer from '/static/js/components/chart-viewer.js';
import { MASCOT_ENABLED } from '/static/js/components/mascot.js';

// Short, first-person, dry-humor lines matching Rulezy's established voice
// elsewhere (chatbot greetings, 404 page, rule fixer) — picked at random so
// a repeat badge-unlock visit doesn't say the exact same thing twice.
const CONGRATS_LINES = [
    "Nice, a new badge. I'd clap but I don't have hands.",
    "Look at you go. I'm mildly impressed, which for me is a lot.",
    "Achievement unlocked. Somewhere, a rule feels safer already.",
    "Another one. At this rate you'll out-rank me and that's a personal problem.",
    "I logged that. I log everything. It's kind of my thing.",
];
const ALL_BADGES_LINES = [
    "Every badge. All of them. I have nothing left to give you except this sentence.",
    "You cleared the whole shelf. I'm equal parts proud and slightly concerned.",
    "That's the full set. I'm not crying, there's just dust in my circuits.",
];

const UserContributionStatsComponent = {
    components: { ChartViewer },
    props: {
        userId: { type: [String, Number], required: true }
    },
    delimiters: ['[[', ']]'],
    setup(props) {
        const userStats = Vue.ref({
            total_points: undefined,
            current_level: 1,
            suggestions_accepted: 0,
            rules_owned: 0,
            rules_popular_score: 0,
            rules_liked: 0,
            consecutive_days_active: 0,
            global_rank: null
        });
        const loading = Vue.ref(true);
        const badgeCatalog = Vue.ref([]);   // full catalog — {key, name, description, icon, rulezy_pose}
        const unlockedKeys = Vue.ref(new Set());
        const congratsMessage = Vue.ref(null);
        const congratsPose = Vue.ref('armcross');
        const fxRoot = Vue.ref(null);
        const mascotEnabled = MASCOT_ENABLED;

        const LEVEL_THRESHOLDS = {
            1: 0, 2: 500, 3: 15000, 4: 30000, 5: 50000, 10: 150000, 20: 300000, 100: 1500000
        };

        const fetchBadgeCatalog = async () => {
            try {
                const res = await fetch('/account/badges_catalog');
                if (!res.ok) return;
                const data = await res.json();
                badgeCatalog.value = data.badges || [];
            } catch {}
        };

        const FX_COLORS = ['#0d6efd', '#ffd447', '#ff6b8f', '#4be08a', '#a06bff', '#ff8f6b'];
        const launchConfetti = () => {
            const fx = fxRoot.value;
            if (!fx) return;
            fx.innerHTML = '';
            for (let i = 0; i < 70; i++) {
                const piece = document.createElement('div');
                piece.className = 'ud-confetti';
                piece.style.left = Math.random() * 100 + '%';
                piece.style.background = FX_COLORS[i % FX_COLORS.length];
                piece.style.animationDelay = (Math.random() * 1.2) + 's';
                piece.style.animationDuration = (2.4 + Math.random() * 1.8) + 's';
                fx.appendChild(piece);
            }
            setTimeout(() => { if (fx) fx.innerHTML = ''; }, 4500);
        };

        const fetchUserStats = async () => {
            loading.value = true;
            try {
                const res = await fetch(`/account/user_contributions/${props.userId}`);
                if (!res.ok) return;
                const data = await res.json();
                userStats.value = data.user_stats;

                const badges = data.badges || [];
                unlockedKeys.value = new Set(badges.map(b => b.badge_key));
                const newBadges = data.new_badges || [];

                if (mascotEnabled && newBadges.length && badgeCatalog.value.length) {
                    const firstNew = badgeCatalog.value.find(b => b.key === newBadges[0]);
                    congratsPose.value = firstNew?.rulezy_pose || 'armcross';
                    const names = newBadges
                        .map(k => badgeCatalog.value.find(b => b.key === k)?.name)
                        .filter(Boolean).join(', ');
                    const line = CONGRATS_LINES[Math.floor(Math.random() * CONGRATS_LINES.length)];
                    congratsMessage.value = `${line} <strong>${names}</strong>`;
                }

                if (mascotEnabled && badgeCatalog.value.length && unlockedKeys.value.size >= badgeCatalog.value.length) {
                    congratsPose.value = 'armcross';
                    congratsMessage.value = ALL_BADGES_LINES[Math.floor(Math.random() * ALL_BADGES_LINES.length)];
                    Vue.nextTick(launchConfetti);
                }
            } catch {}
            finally { loading.value = false; }
        };

        const catalogWithState = Vue.computed(() =>
            badgeCatalog.value.map(b => ({ ...b, unlocked: unlockedKeys.value.has(b.key) }))
        );
        const unlockedCount = Vue.computed(() => unlockedKeys.value.size);

        const nextLevelThreshold = Vue.computed(() => {
            const lvl = userStats.value.current_level;
            const sorted = Object.keys(LEVEL_THRESHOLDS).map(Number).sort((a, b) => a - b);
            const idx = sorted.findIndex(l => l > lvl);
            if (idx !== -1) return { level: sorted[idx], points: LEVEL_THRESHOLDS[sorted[idx]] };
            return { level: lvl, points: userStats.value.total_points || 0 };
        });

        const progressPercentage = Vue.computed(() => {
            const pts = userStats.value.total_points;
            const lvl = userStats.value.current_level;
            if (pts === undefined) return 0;
            const prevPts = LEVEL_THRESHOLDS[lvl] || 0;
            const nextPts = nextLevelThreshold.value.points;
            if (nextPts === pts && nextLevelThreshold.value.level === lvl) return 100;
            const span = nextPts - prevPts;
            if (span <= 0) return 0;
            return Math.min(100, ((pts - prevPts) / span) * 100);
        });

        /* ── Chart data ──────────────────────────────────────────────── */

        const levelGaugeData = Vue.computed(() => ({
            title:    `Level ${userStats.value.current_level}`,
            subtitle: `Progress to level ${nextLevelThreshold.value.level}`,
            series: [{ name: 'Level Progress', values: [Math.round(progressPercentage.value)] }],
            meta:   { unit: '%' }
        }));

        const radarData = Vue.computed(() => {
            const s = userStats.value;
            const normalize = (v, max) => max > 0 ? Math.min(100, Math.round((v / max) * 100)) : 0;
            return {
                title:      'Contribution Profile',
                subtitle:   'Normalised multi-axis score',
                categories: ['Rules', 'Suggestions', 'Popularity', 'Streak', 'Liked'],
                series: [{
                    name:   'Score',
                    values: [
                        normalize(s.rules_owned, 100),
                        normalize(s.suggestions_accepted, 50),
                        normalize(s.rules_popular_score, 5000),
                        normalize(s.consecutive_days_active, 30),
                        normalize(s.rules_liked, 50)
                    ]
                }]
            };
        });

        const pointsBarData = Vue.computed(() => ({
            title:      'Contribution Metrics',
            subtitle:   'Raw counts per activity type',
            categories: ['Rules Owned', 'Accepted Suggestions', 'Rules Liked', 'Streak (days)'],
            series: [{
                name:   'Count',
                values: [
                    userStats.value.rules_owned,
                    userStats.value.suggestions_accepted,
                    userStats.value.rules_liked,
                    userStats.value.consecutive_days_active
                ]
            }]
        }));

        const hasContributionData = Vue.computed(() => {
            const s = userStats.value;
            return !!(s && (
                (s.rules_owned ?? 0) > 0 || (s.suggestions_accepted ?? 0) > 0 ||
                (s.rules_liked ?? 0) > 0 || (s.consecutive_days_active ?? 0) > 0 ||
                (s.rules_popular_score ?? 0) > 0
            ));
        });

        Vue.onMounted(async () => {
            await fetchBadgeCatalog();
            await fetchUserStats();
        });

        return {
            userStats, loading, nextLevelThreshold, progressPercentage,
            levelGaugeData, radarData, pointsBarData, hasContributionData,
            catalogWithState, unlockedCount, congratsMessage, congratsPose, fxRoot, mascotEnabled,
        };
    },
    template: `
<div class="ud-charts-root">
    <div ref="fxRoot" class="ud-fx"></div>

    <div v-if="loading" class="ud-charts-loader">
        <div class="spinner-border text-primary" role="status" style="width:2.5rem;height:2.5rem;"></div>
        <span class="ms-3 text-muted fw-medium">Loading contribution data…</span>
    </div>

    <div v-else-if="userStats.total_points !== undefined">

        <!-- Rulezy congrats — shown once when a badge was just unlocked, or all badges are complete -->
        <div v-if="mascotEnabled && congratsMessage" class="ud-rulezy-congrats">
            <img :src="'/static/images/rulezy/' + congratsPose + '.png'" alt="Rulezy">
            <div class="ud-rulezy-congrats__text" v-html="congratsMessage"></div>
        </div>

        <!-- KPI row -->
        <div class="row g-3 mb-4">
            <div class="col-sm-3">
                <div class="ud-kpi-card ud-kpi-card--gold">
                    <div class="ud-kpi-icon"><i class="fas fa-trophy"></i></div>
                    <div class="ud-kpi-body">
                        <div class="ud-kpi-value">[[ userStats.total_points.toLocaleString() ]]</div>
                        <div class="ud-kpi-label">Reputation Points</div>
                    </div>
                </div>
            </div>
            <div class="col-sm-3">
                <div class="ud-kpi-card ud-kpi-card--blue">
                    <div class="ud-kpi-icon"><i class="fas fa-ranking-star"></i></div>
                    <div class="ud-kpi-body">
                        <div class="ud-kpi-value">#[[ userStats.global_rank || '—' ]]</div>
                        <div class="ud-kpi-label">Global Rank</div>
                    </div>
                </div>
            </div>
            <div class="col-sm-3">
                <div class="ud-kpi-card ud-kpi-card--purple">
                    <div class="ud-kpi-icon"><i class="fas fa-fire-flame-curved"></i></div>
                    <div class="ud-kpi-body">
                        <div class="ud-kpi-value">[[ userStats.consecutive_days_active ]]d</div>
                        <div class="ud-kpi-label">Active Streak</div>
                    </div>
                </div>
            </div>
            <div class="col-sm-3">
                <div class="ud-kpi-card ud-kpi-card--green">
                    <div class="ud-kpi-icon"><i class="fas fa-check-double"></i></div>
                    <div class="ud-kpi-body">
                        <div class="ud-kpi-value">[[ userStats.suggestions_accepted ]]</div>
                        <div class="ud-kpi-label">Accepted Edits</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Section header -->
        <div class="ud-section-header mb-3">
            <i class="fas fa-bolt ud-section-icon"></i>
            <div>
                <div class="ud-section-title">Level & Profile</div>
                <div class="ud-section-sub">XP progress and multi-dimensional contribution score</div>
            </div>
        </div>

        <!-- Row 1: Stats list + Level gauge -->
        <div class="row g-3 mb-4">
            <div class="col-lg-5">
                <div class="ud-stat-card h-100">
                    <div class="ud-stat-card-header">
                        <i class="fas fa-list-check me-2"></i>
                        Core Stats — Level [[ userStats.current_level ]]
                    </div>
                    <div class="ud-stat-card-body">
                        <div class="ud-rep-score">
                            <span class="ud-rep-label">Reputation Score</span>
                            <span class="ud-rep-value">[[ userStats.total_points.toLocaleString() ]]</span>
                        </div>
                        <ul class="ud-stat-list">
                            <li class="ud-stat-item ud-stat-item--blue">
                                <span><i class="fas fa-globe-americas me-2"></i>Global Rank</span>
                                <span class="ud-stat-badge ud-stat-badge--blue">#[[ userStats.global_rank || 'N/A' ]]</span>
                            </li>
                            <li class="ud-stat-item ud-stat-item--green">
                                <span><i class="fas fa-check-circle me-2"></i>Accepted Suggestions</span>
                                <span class="ud-stat-badge ud-stat-badge--green">[[ userStats.suggestions_accepted ]]</span>
                            </li>
                            <li class="ud-stat-item ud-stat-item--teal">
                                <span><i class="fas fa-cloud-upload-alt me-2"></i>Rules Owned</span>
                                <span class="ud-stat-badge ud-stat-badge--teal">[[ userStats.rules_owned ]]</span>
                            </li>
                            <li class="ud-stat-item ud-stat-item--orange">
                                <span><i class="fas fa-fire-alt me-2"></i>Activity Streak</span>
                                <span class="ud-stat-badge ud-stat-badge--orange">[[ userStats.consecutive_days_active ]]d</span>
                            </li>
                            <li class="ud-stat-item ud-stat-item--red">
                                <span><i class="fas fa-heart me-2"></i>Rules Liked</span>
                                <span class="ud-stat-badge ud-stat-badge--red">[[ userStats.rules_liked ]]</span>
                            </li>
                            <li class="ud-stat-item ud-stat-item--purple">
                                <span><i class="fas fa-star me-2"></i>Popularity Score</span>
                                <span class="ud-stat-badge ud-stat-badge--purple">[[ userStats.rules_popular_score.toLocaleString() ]]</span>
                            </li>
                        </ul>
                        <div class="ud-next-level">
                            Next: Level [[ nextLevelThreshold.level ]] — [[ nextLevelThreshold.points.toLocaleString() ]] pts needed
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-lg-7">
                <div class="row g-3 h-100">
                    <div class="col-12">
                        <div class="ud-chart-card ud-chart-card--accent-gold h-100">
                            <chart-viewer :data="levelGaugeData" views="gauge" height="320px"></chart-viewer>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Section header -->
        <div class="ud-section-header mb-3">
            <i class="fas fa-spider ud-section-icon"></i>
            <div>
                <div class="ud-section-title">Analysis</div>
                <div class="ud-section-sub">Contribution profile and metric breakdown</div>
            </div>
        </div>

        <!-- Row 2: Radar + Bar -->
        <div v-if="hasContributionData" class="row g-3 mb-4">
            <div class="col-lg-5">
                <div class="ud-chart-card ud-chart-card--accent-purple">
                    <chart-viewer :data="radarData" views="radar" height="380px"></chart-viewer>
                </div>
            </div>
            <div class="col-lg-7">
                <div class="ud-chart-card ud-chart-card--accent-blue">
                    <chart-viewer :data="pointsBarData" :views="['bar', 'bar-h']" height="380px"></chart-viewer>
                </div>
            </div>
        </div>
        <p v-else class="text-muted mb-4 text-center py-4">
            <i class="fas fa-chart-simple me-2 opacity-25"></i>No contributions yet — this will fill in once there's activity to show.
        </p>

        <!-- Section header -->
        <div class="ud-section-header mb-3">
            <i class="fas fa-award ud-section-icon"></i>
            <div>
                <div class="ud-section-title">Earned Badges</div>
                <div class="ud-section-sub">[[ unlockedCount ]] of [[ catalogWithState.length ]] badge[[ catalogWithState.length !== 1 ? 's' : '' ]] unlocked</div>
            </div>
        </div>

        <!-- Badges -->
        <div class="ud-badges-card">
            <div v-if="catalogWithState.length" class="ud-badge-grid">
                <div v-for="badge in catalogWithState" :key="badge.key"
                     class="ud-badge-tile" :class="['ud-badge-tile--' + badge.color, { 'ud-badge-tile--locked': !badge.unlocked }]"
                     :title="badge.description">
                    <div class="ud-badge-tile__icon-wrap">
                        <img v-if="mascotEnabled" :src="'/static/images/rulezy/' + badge.rulezy_pose + '.png'" alt="" class="ud-badge-tile__icon">
                        <i v-else :class="'fas ' + badge.icon" :style="{ color: badge.unlocked ? '' : 'var(--subtle-text-color)', fontSize: '1.2rem' }"></i>
                    </div>
                    <div>
                        <div class="ud-badge-tile__name">[[ badge.name ]]</div>
                        <div class="ud-badge-tile__desc">[[ badge.description ]]</div>
                    </div>
                </div>
            </div>
            <p v-else class="text-muted mb-0 text-center py-3">
                <i class="fas fa-medal me-2 opacity-25"></i>No badges yet — keep contributing!
            </p>
        </div>

    </div>

    <div v-else class="ud-charts-loader">
        <i class="fas fa-spinner fa-spin fa-2x text-muted"></i>
    </div>
</div>
    `
};

export default UserContributionStatsComponent;
