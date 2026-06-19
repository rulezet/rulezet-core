import ChartViewer from '/static/js/components/chart-viewer.js';

const UserActivityStatsComponent = {
    components: { ChartViewer },
    props: {
        userId:      { type: [String, Number], default: null },
        user_id:     { type: [String, Number], default: null },
        apiEndpoint: { type: String, required: true }
    },
    delimiters: ['[[', ']]'],
    setup(props) {
        const activity_data = Vue.ref(null);
        const loading       = Vue.ref(true);
        const error         = Vue.ref(null);

        const actualUserId = Vue.computed(() => props.userId || props.user_id);

        const fetchData = async () => {
            loading.value = true;
            try {
                const endpoint = props.apiEndpoint.replace('{userId}', actualUserId.value);
                const response = await fetch(endpoint);
                activity_data.value = await response.json();
            } catch {
                error.value = 'Failed to load stats';
            } finally {
                loading.value = false;
            }
        };

        const trustGaugeData = Vue.computed(() => {
            const val = activity_data.value?.activity_stats?.trust_score ?? 0;
            return {
                title:  'Trust Score',
                subtitle: 'Community approval rating',
                series: [{ name: 'Approval', values: [val] }],
                meta:   { unit: '%' }
            };
        });

        const votesBarData = Vue.computed(() => {
            const s = activity_data.value?.activity_stats ?? {};
            return {
                title:      'Community Feedback',
                subtitle:   'Votes received across all content',
                categories: ['Rules Likes', 'Rules Dislikes', 'Bundle Likes', 'Bundle Dislikes'],
                series: [{
                    name:   'Votes',
                    values: [s.rules_likes ?? 0, s.rules_dislikes ?? 0, s.bundles_likes ?? 0, s.bundles_dislikes ?? 0]
                }]
            };
        });

        const formatDonutData = Vue.computed(() => {
            const dist = activity_data.value?.format_distribution ?? {};
            const cats = Object.keys(dist);
            const vals = Object.values(dist);
            return {
                title:      'Rules by Format',
                subtitle:   'Distribution across detection formats',
                categories: cats.length ? cats : ['No data'],
                series: [{ name: 'Rules', values: cats.length ? vals : [1] }]
            };
        });

        const timelineAreaData = Vue.computed(() => {
            const tl = activity_data.value?.timeline ?? {};
            const cats = Object.keys(tl);
            const vals = Object.values(tl);
            return {
                title:      'Contribution Timeline',
                subtitle:   'Rules published per month',
                categories: cats,
                series: [{ name: 'Rules Published', values: vals }]
            };
        });

        const assetsDonutData = Vue.computed(() => {
            const s = activity_data.value?.activity_stats ?? {};
            return {
                title:      'Published Assets',
                subtitle:   'Rules vs Bundles breakdown',
                categories: ['Rules', 'Bundles'],
                series: [{ name: 'Assets', values: [s.total_rules ?? 0, s.total_bundles ?? 0] }]
            };
        });

        Vue.onMounted(() => { if (actualUserId.value) fetchData(); });

        return { activity_data, loading, error, trustGaugeData, votesBarData, formatDonutData, timelineAreaData, assetsDonutData };
    },
    template: `
<div class="ud-charts-root">

    <div v-if="loading" class="ud-charts-loader">
        <div class="spinner-border text-primary" role="status" style="width:2.5rem;height:2.5rem;"></div>
        <span class="ms-3 text-muted fw-medium">Loading activity data…</span>
    </div>

    <div v-else-if="error" class="alert alert-warning rounded-3 border-0 shadow-sm">[[ error ]]</div>

    <div v-else-if="activity_data">

        <!-- KPI row -->
        <div class="row g-3 mb-4">
            <div class="col-sm-4">
                <div class="ud-kpi-card ud-kpi-card--blue">
                    <div class="ud-kpi-icon"><i class="fas fa-shield-halved"></i></div>
                    <div class="ud-kpi-body">
                        <div class="ud-kpi-value">[[ activity_data.activity_stats.total_rules ]]</div>
                        <div class="ud-kpi-label">Rules Published</div>
                    </div>
                </div>
            </div>
            <div class="col-sm-4">
                <div class="ud-kpi-card ud-kpi-card--teal">
                    <div class="ud-kpi-icon"><i class="fas fa-layer-group"></i></div>
                    <div class="ud-kpi-body">
                        <div class="ud-kpi-value">[[ activity_data.activity_stats.total_bundles ]]</div>
                        <div class="ud-kpi-label">Bundles Shared</div>
                    </div>
                </div>
            </div>
            <div class="col-sm-4">
                <div class="ud-kpi-card ud-kpi-card--green">
                    <div class="ud-kpi-icon"><i class="fas fa-circle-check"></i></div>
                    <div class="ud-kpi-body">
                        <div class="ud-kpi-value">[[ activity_data.activity_stats.trust_score ]]%</div>
                        <div class="ud-kpi-label">Trust Score</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Section header -->
        <div class="ud-section-header mb-3">
            <i class="fas fa-chart-pie ud-section-icon"></i>
            <div>
                <div class="ud-section-title">Overview</div>
                <div class="ud-section-sub">Trust rating and asset breakdown at a glance</div>
            </div>
        </div>

        <!-- Row 1: Gauge + Assets donut -->
        <div class="row g-3 mb-4">
            <div class="col-lg-6">
                <div class="ud-chart-card ud-chart-card--accent-blue">
                    <chart-viewer :data="trustGaugeData" views="gauge" height="320px"></chart-viewer>
                </div>
            </div>
            <div class="col-lg-6">
                <div class="ud-chart-card ud-chart-card--accent-teal">
                    <chart-viewer :data="assetsDonutData" views="donut" height="320px"></chart-viewer>
                </div>
            </div>
        </div>

        <!-- Section header -->
        <div class="ud-section-header mb-3">
            <i class="fas fa-thumbs-up ud-section-icon"></i>
            <div>
                <div class="ud-section-title">Votes & Formats</div>
                <div class="ud-section-sub">Community feedback and rule format distribution</div>
            </div>
        </div>

        <!-- Row 2: Votes bar + Format donut -->
        <div class="row g-3 mb-4">
            <div class="col-lg-7">
                <div class="ud-chart-card ud-chart-card--accent-purple">
                    <chart-viewer :data="votesBarData" :views="['bar', 'bar-h']" height="380px"></chart-viewer>
                </div>
            </div>
            <div class="col-lg-5">
                <div class="ud-chart-card ud-chart-card--accent-orange">
                    <chart-viewer :data="formatDonutData" :views="['donut', 'pie']" height="380px"></chart-viewer>
                </div>
            </div>
        </div>

        <!-- Section header -->
        <div class="ud-section-header mb-3">
            <i class="fas fa-chart-line ud-section-icon"></i>
            <div>
                <div class="ud-section-title">Contribution Timeline</div>
                <div class="ud-section-sub">Monthly publication history</div>
            </div>
        </div>

        <!-- Row 3: Timeline -->
        <div class="row g-3">
            <div class="col-12">
                <div class="ud-chart-card ud-chart-card--accent-blue">
                    <chart-viewer :data="timelineAreaData" :views="['area', 'line', 'bar']" height="360px"></chart-viewer>
                </div>
            </div>
        </div>

    </div>
</div>
    `
};

export default UserActivityStatsComponent;
