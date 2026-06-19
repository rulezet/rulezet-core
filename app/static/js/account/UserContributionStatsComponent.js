import ChartViewer from '/static/js/components/chart-viewer.js';

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

        const LEVEL_THRESHOLDS = {
            1: 0, 2: 500, 3: 15000, 4: 30000, 5: 50000, 10: 150000, 20: 300000, 100: 1500000
        };
        const BADGE_POINTS = {
            'Bronze Contributor': 1000,
            'Silver Contributor': 10000,
            'Gold Contributor': 50000,
            'Curator Rookie':   { metric: 'suggestions_accepted', min: 5 },
            'Quality Master':   { metric: 'suggestions_accepted', min: 25 }
        };

        const getBadgeClass = (name) => {
            if (name.includes('Master'))      return 'bg-danger text-white border border-light';
            if (name.includes('Gold'))        return 'bg-warning text-dark border border-dark';
            if (name.includes('Silver'))      return 'bg-secondary text-white border border-light';
            if (name.includes('Bronze'))      return 'bg-bronze text-white border border-dark';
            if (name.includes('Curator'))     return 'bg-info text-white';
            if (name.includes('Quality'))     return 'bg-success text-white';
            return 'bg-dark text-white';
        };
        const getBadgeIcon = (name) => {
            if (name.includes('Contributor')) return 'fas fa-star';
            if (name.includes('Master'))      return 'fas fa-brain';
            if (name.includes('Curator'))     return 'fas fa-glasses';
            if (name.includes('Quality'))     return 'fas fa-cogs';
            return 'fas fa-certificate';
        };

        const fetchUserStats = async () => {
            loading.value = true;
            try {
                const res = await fetch(`/account/user_contributions/${props.userId}`);
                if (!res.ok) return;
                const data = await res.json();
                userStats.value = data.user_stats;
            } catch {}
            finally { loading.value = false; }
        };

        const computedBadges = Vue.computed(() => {
            if (userStats.value.total_points === undefined) return [];
            const badges = [];
            const stats = userStats.value;
            for (const [name, threshold] of Object.entries(BADGE_POINTS)) {
                if (typeof threshold === 'number') {
                    if (stats.total_points >= threshold) badges.push({ name, description: `Reached ${threshold.toLocaleString()} pts.` });
                } else if (stats[threshold.metric] >= threshold.min) {
                    badges.push({ name, description: `${threshold.min}+ ${threshold.metric}.` });
                }
            }
            if (stats.current_level >= 5) badges.push({ name: 'Veteran Contributor', description: 'Level 5+.' });
            return badges.sort((a, b) => a.name.localeCompare(b.name));
        });

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

        Vue.onMounted(fetchUserStats);

        return {
            userStats, loading, computedBadges, nextLevelThreshold, progressPercentage,
            getBadgeClass, getBadgeIcon, levelGaugeData, radarData, pointsBarData
        };
    },
    template: `
<div class="ud-charts-root">

    <div v-if="loading" class="ud-charts-loader">
        <div class="spinner-border text-primary" role="status" style="width:2.5rem;height:2.5rem;"></div>
        <span class="ms-3 text-muted fw-medium">Loading contribution data…</span>
    </div>

    <div v-else-if="userStats.total_points !== undefined">

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
        <div class="row g-3 mb-4">
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

        <!-- Section header -->
        <div class="ud-section-header mb-3">
            <i class="fas fa-award ud-section-icon"></i>
            <div>
                <div class="ud-section-title">Earned Badges</div>
                <div class="ud-section-sub">[[ computedBadges.length ]] badge[[ computedBadges.length !== 1 ? 's' : '' ]] unlocked</div>
            </div>
        </div>

        <!-- Badges -->
        <div class="ud-badges-card">
            <template v-if="computedBadges.length">
                <span v-for="badge in computedBadges" :key="badge.name"
                      class="badge rounded-pill p-2 fs-6 me-2 mb-2"
                      :class="getBadgeClass(badge.name)"
                      :title="badge.description">
                    <i :class="getBadgeIcon(badge.name) + ' me-1'"></i>[[ badge.name ]]
                </span>
            </template>
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
