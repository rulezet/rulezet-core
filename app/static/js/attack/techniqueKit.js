// ATT&CK technique page (templates/attack/technique_detail.html, backend
// features/attack/attack_kit_core.py) — the same kit as a CVE page:
// coverage per format and gaps, charts (loaded only when their card is
// opened), every rule, zip, bundle, alert.
import RuleList from '/static/js/rule/ruleList.js';
import TagsDisplaysList from '/static/js/tags/tagsDisplaysList.js';
import VulnerabilityDisplaysList from '/static/js/vulnerability/vulnerabilityDisplayList.js';
import ChartViewer from '/static/js/components/chart-viewer.js';
import { useCollapsedCards } from '/static/js/components/collapsible-cards.js';
import { create_message } from '/static/js/toaster.js';

const { createApp, ref, computed, onMounted } = Vue;

const csrf = () => document.getElementById('csrf_token')?.value || '';

// Links to this page carry ?attacks=T…; RuleList would read it from the URL
// and drop the sub-techniques the kit includes — the page sets its own filter.
(() => {
    const url = new URL(window.location.href);
    if (url.searchParams.has('attacks')) {
        url.searchParams.delete('attacks');
        history.replaceState(history.state, '', url);
    }
})();

createApp({
    delimiters: ['[[', ']]'],
    components: { RuleList, TagsDisplaysList, VulnerabilityDisplaysList, ChartViewer },
    setup() {
        const technique = window.KIT_TECHNIQUE;
        const base = '/attack/technique/' + encodeURIComponent(technique.id);
        const loading = ref(true);
        const kit = ref(null);
        const stats = ref(null);
        const descOpen = ref(false);
        const bundleBusy = ref(false);
        const csrfToken = csrf();

        async function loadStats() {
            if (stats.value) return;
            const res = await fetch(base + '/kit_stats');
            stats.value = res.ok ? await res.json() : null;
        }
        // The Coverage charts are closed by default and computed only when opened.
        const { collapsed, toggle } = useCollapsedCards('attack-kit', { charts: true },
            (card) => { if (card === 'charts') loadStats(); });

        const info = computed(() => (kit.value ? kit.value.info : { tactics: [], subtechniques: [], siblings: [] }));
        const coverageChart = computed(() => ({
            categories: ['Coverage'],
            series: [{ name: 'Coverage', values: [stats.value ? stats.value.coverage_pct : 0] }],
            meta: { unit: '%' },
        }));

        const alertUrl = computed(() => {
            const p = new URLSearchParams({ attacks: technique.id, target: 'both', name: `New rules for ${technique.id}` });
            return '/alert/new?' + p.toString();
        });
        const aiDraftUrl = computed(() => {
            if (!kit.value) return '#';
            const p = new URLSearchParams({ tab: 'ai_generate', attack: technique.id, attack_name: technique.name, prompt: kit.value.ai_draft.prompt });
            return '/rule/create_rule?' + p.toString();
        });
        const writeUrl = (format) => {
            const p = new URLSearchParams({ tab: 'manual', attack: technique.id, attack_name: technique.name });
            if (format) p.set('format', format);
            return '/rule/create_rule?' + p.toString();
        };

        async function load() {
            loading.value = true;
            try {
                const res = await fetch(base + '/kit_data');
                kit.value = res.ok ? await res.json() : null;
                if (kit.value && kit.value.total_rules && !collapsed.charts) loadStats();
            } finally {
                loading.value = false;
            }
        }

        async function createBundle() {
            bundleBusy.value = true;
            try {
                const res = await fetch(base + '/bundle', {
                    method: 'POST', headers: { 'X-CSRFToken': csrf(), Accept: 'application/json' },
                });
                let data;
                try { data = await res.json(); }
                catch { return create_message(`Could not create the bundle (HTTP ${res.status}) — reload the page and try again.`, 'danger-subtle'); }
                if (!data.success) return create_message(data.message, 'danger-subtle');
                create_message(data.message, 'success-subtle');
                window.location.href = data.url;
            } finally {
                bundleBusy.value = false;
            }
        }

        onMounted(load);

        return {
            base, loading, kit, info, stats, coverageChart, descOpen, bundleBusy, csrfToken,
            collapsed, toggle, alertUrl, aiDraftUrl, writeUrl, createBundle,
        };
    },
}).mount('#main-container');
