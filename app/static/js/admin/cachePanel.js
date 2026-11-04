// Admin → Settings → Cache (expert) tab (templates/admin/settings.html): status, settings, actions.
// Data: GET /admin/cache/status, actions: POST /admin/cache/action (app/features/admin/cache/).
// Loads only when the tab is opened (the settings page mounts it with v-if).
import { create_message } from '/static/js/toaster.js';

const { ref, onMounted } = Vue;

export default {
    name: 'CachePanel',
    delimiters: ['[[', ']]'],
    setup() {
        const status = ref(null);
        const busy = ref(false);
        const ruleId = ref('');
        const confirmClear = ref(false);

        const ratio = (s) => (s && s.ratio !== null && s.ratio !== undefined ? `${s.ratio} %` : '—');
        function duration(sec) {
            sec = Number(sec) || 0;
            if (!sec) return 'off';
            if (sec % 3600 === 0) return `${sec / 3600} h`;
            if (sec % 60 === 0) return `${sec / 60} min`;
            return `${sec} s`;
        }
        async function load() {
            try {
                const r = await fetch('/admin/cache/status');
                if (r.ok) status.value = await r.json();
            } catch { /* shown as "loading" */ }
        }
        async function run(action) {
            busy.value = true;
            try {
                const res = await fetch('/admin/cache/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById('csrf_token')?.value || '' },
                    body: JSON.stringify({ action, rule_id: ruleId.value }),
                });
                const data = await res.json().catch(() => ({}));
                create_message(data.message || 'Something went wrong', data.success ? 'success-subtle' : 'danger-subtle');
                if (data.status) status.value = data.status;
            } catch {
                create_message('Something went wrong', 'danger-subtle');
            } finally {
                busy.value = false;
            }
        }
        onMounted(load);
        return { status, busy, ruleId, confirmClear, ratio, duration, run, load, host: window.location.origin };
    },
    template: `
    <div v-if="!status" class="text-center text-muted py-5"><i class="fa-solid fa-spinner fa-spin me-2"></i>Loading the cache status…</div>
    <div v-else>
        <div class="cache-expert mb-4">
            <i class="fa-solid fa-flask-vial me-2"></i><strong>Expert panel.</strong>
            Rule pages, their shared parts and public API answers are kept in the cache; a rule refreshes itself as soon as
            anything about it changes (edit, vote, comment, tag, import), and every deploy starts a fresh cache.
            You should rarely need anything here.
        </div>

        <div class="row g-3 mb-3">
            <div class="col-12 col-md-6 col-xl-3">
                <div class="ud-kpi-card" :class="status.backend.ok ? 'ud-kpi-card--blue' : 'ud-kpi-card--orange'">
                    <div class="ud-kpi-icon"><i class="fa-solid fa-database"></i></div>
                    <div class="ud-kpi-body">
                        <div class="ud-kpi-value">[[ status.backend.type || '—' ]]</div>
                        <div class="ud-kpi-label">Backend <span v-if="!status.backend.shared" class="cache-warn">· not shared</span></div>
                    </div>
                </div>
            </div>
            <div class="col-12 col-md-6 col-xl-3">
                <div class="ud-kpi-card" :class="status.settings['cache.enabled'] ? 'ud-kpi-card--green' : 'ud-kpi-card--orange'">
                    <div class="ud-kpi-icon"><i class="fa-solid fa-power-off"></i></div>
                    <div class="ud-kpi-body">
                        <div class="ud-kpi-value">[[ status.settings['cache.enabled'] ? 'On' : 'Off' ]]</div>
                        <div class="ud-kpi-label">App cache</div>
                    </div>
                </div>
            </div>
            <div class="col-12 col-md-6 col-xl-3">
                <div class="ud-kpi-card ud-kpi-card--purple">
                    <div class="ud-kpi-icon"><i class="fa-solid fa-file-lines"></i></div>
                    <div class="ud-kpi-body">
                        <div class="ud-kpi-value">[[ ratio(status.stats.page) ]]</div>
                        <div class="ud-kpi-label">Anonymous pages from the cache · [[ status.stats.page.hit ]] / [[ status.stats.page.hit + status.stats.page.miss ]]</div>
                    </div>
                </div>
            </div>
            <div class="col-12 col-md-6 col-xl-3">
                <div class="ud-kpi-card ud-kpi-card--teal">
                    <div class="ud-kpi-icon"><i class="fa-solid fa-puzzle-piece"></i></div>
                    <div class="ud-kpi-body">
                        <div class="ud-kpi-value">[[ ratio(status.stats.value) ]]</div>
                        <div class="ud-kpi-label">Shared parts / API from the cache · [[ status.stats.value.hit ]] / [[ status.stats.value.hit + status.stats.value.miss ]]</div>
                    </div>
                </div>
            </div>
        </div>
        <p v-if="status.backend.detail" class="small mb-4" :class="status.backend.ok ? 'text-muted' : 'text-danger'">
            <i class="fa-solid fa-circle-info me-1"></i>[[ status.backend.detail ]] · code version <code>[[ status.code_version ]]</code>
            <button type="button" class="btn btn-sm btn-link p-0 ms-2" @click="load">Refresh</button>
        </p>

        <div class="row g-4">
            <div class="col-12 col-lg-6">
                <div class="card border-0 shadow-sm rounded-3 h-100"><div class="card-body p-4">
                    <div class="ud-section-header mb-3">
                        <div class="ud-section-icon"><i class="fa-solid fa-sliders"></i></div>
                        <div><div class="ud-section-title">Settings</div><div class="ud-section-sub">Changed in the Configuration tab (category Cache)</div></div>
                    </div>
                    <table class="table table-sm cache-table mb-3"><tbody>
                        <tr><td>App cache</td><td class="text-end fw-semibold">[[ status.settings['cache.enabled'] ? 'On' : 'Off' ]]</td></tr>
                        <tr><td>Rule page, anonymous visitors</td><td class="text-end fw-semibold">[[ duration(status.settings['cache.rule_page_seconds']) ]]</td></tr>
                        <tr><td>Rule page, shared parts</td><td class="text-end fw-semibold">[[ duration(status.settings['cache.rule_parts_seconds']) ]]</td></tr>
                        <tr><td>Public API answers</td><td class="text-end fw-semibold">[[ duration(status.settings['cache.api_seconds']) ]]</td></tr>
                        <tr><td>User page, activity data</td><td class="text-end fw-semibold">[[ duration(status.settings['cache.user_activity_seconds']) ]]</td></tr>
                        <tr><td>nginx micro-cache (anonymous)</td><td class="text-end fw-semibold">60 s <span class="text-muted fw-normal">(deploy/nginx)</span></td></tr>
                    </tbody></table>
                    <a href="/admin/configuration?q=cache." class="btn btn-sm btn-outline-primary rounded-pill"><i class="fa-solid fa-sliders me-1"></i>Change the settings</a>
                </div></div>
            </div>
            <div class="col-12 col-lg-6">
                <div class="card border-0 shadow-sm rounded-3 h-100"><div class="card-body p-4">
                    <div class="ud-section-header mb-3">
                        <div class="ud-section-icon"><i class="fa-solid fa-broom"></i></div>
                        <div><div class="ud-section-title">Actions</div><div class="ud-section-sub">Each one is written in the activity log</div></div>
                    </div>
                    <div class="cache-action">
                        <div><div class="fw-semibold">Refresh every rule</div><div class="small text-muted">Rule pages, lists and API answers computed again (after a database restore or a script).</div></div>
                        <button class="btn btn-sm btn-primary rounded-pill" :disabled="busy" @click="run('refresh_rules')"><i class="fa-solid fa-arrows-rotate me-1"></i>Refresh</button>
                    </div>
                    <div class="cache-action">
                        <div><div class="fw-semibold">Refresh one rule</div><div class="small text-muted">Only that rule's page and parts.</div></div>
                        <div class="d-flex gap-2">
                            <input type="number" min="1" class="form-control form-control-sm cache-id" v-model="ruleId" placeholder="Rule id" aria-label="Rule id">
                            <button class="btn btn-sm btn-outline-primary rounded-pill" :disabled="busy || !ruleId" @click="run('refresh_rule')">Refresh</button>
                        </div>
                    </div>
                    <div class="cache-action">
                        <div><div class="fw-semibold">Empty both caches</div><div class="small text-muted">Home figures (formats, platforms, git repositories…), ATT&amp;CK and CVE stats, leaderboard, cached pages and list answers.
                            Use it after a job that changes many rules (e.g. References &amp; metadata) to see the new numbers at once. The next visits are slower.</div></div>
                        <button class="btn btn-sm btn-outline-danger rounded-pill" :disabled="busy" @click="confirmClear = true"><i class="fa-solid fa-trash me-1"></i>Empty</button>
                    </div>
                    <div v-if="confirmClear" class="cache-confirm">
                        Empty every cache now? <button class="btn btn-sm btn-danger rounded-pill ms-2" @click="confirmClear = false; run('clear_all')">Yes, empty</button>
                        <button class="btn btn-sm btn-link" @click="confirmClear = false">Cancel</button>
                    </div>
                    <div class="cache-action">
                        <div><div class="fw-semibold">Reset the counters</div><div class="small text-muted">Start measuring the hit ratio again.</div></div>
                        <button class="btn btn-sm btn-outline-secondary rounded-pill" :disabled="busy" @click="run('reset_stats')">Reset</button>
                    </div>
                </div></div>
            </div>
            <div class="col-12">
                <div class="card border-0 shadow-sm rounded-3"><div class="card-body p-4">
                    <div class="ud-section-header mb-3">
                        <div class="ud-section-icon"><i class="fa-solid fa-diagram-project"></i></div>
                        <div><div class="ud-section-title">Automate it</div><div class="ud-section-sub">Workflows and the front proxy</div></div>
                    </div>
                    <div class="rounded-3 border p-3 mb-3" style="background:var(--light-bg-color);">
                        <i class="fa-solid fa-gauge-high text-primary me-2"></i>
                        Workflow template <strong>Cache maintenance</strong>: every night, refresh the rule caches then warm the 200 most voted rule pages.
                        The tasks <em>Caches — refresh every rule page</em> and <em>Caches — warm the most voted rule pages</em> can end any workflow.
                        <a href="/admin/tasks/" class="ms-1">Open Workflows → Templates</a>
                    </div>
                    <div class="rounded-3 border p-3" style="background:var(--light-bg-color);">
                        <i class="fa-solid fa-server text-primary me-2"></i>
                        nginx keeps anonymous pages and public API answers 60 s (header <code>X-Cache-Status</code>) and serves <code>/static/</code> from disk.
                        Signed-in users, API keys and forms are never cached; the CVE lookup API is never rate-limited.
                        Check: <code>curl -sI [[ host ]]/rule/detail_rule/1 | grep -i x-cache</code> twice → <code>MISS</code> then <code>HIT</code>.
                    </div>
                </div></div>
            </div>
        </div>
    </div>`,
};
