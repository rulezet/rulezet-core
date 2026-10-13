/**
 * WorkflowRunTrace — the execution path of one workflow launch, for the
 * Admin Task Scheduler: what ran, in which order, why (first task, or
 * "after #2 succeeded"), how long each step queued and ran, how far it got,
 * its last log line — and every task that did NOT run, with the reason
 * (branch not taken, never reached, paused). A Gantt strip on top shows
 * sequencing and parallel branches at a glance.
 *
 * Props:
 *   trace        — GET /admin/tasks/workflows/<uuid>/runs/<run_uuid>/trace .trace
 *   taskTypes    — the TASK_TYPES registry (icon/label per task_type)
 *   focusedUuid  — task whose logs are open below (its step is highlighted)
 * Emits:
 *   'select' (task_uuid) — show that step's logs
 */
const STATUS_META = {
    done:      { icon: 'fa-solid fa-check',          label: 'Succeeded' },
    failed:    { icon: 'fa-solid fa-xmark',          label: 'Failed' },
    cancelled: { icon: 'fa-solid fa-ban',            label: 'Cancelled' },
    running:   { icon: 'fa-solid fa-spinner fa-spin', label: 'Running' },
    pending:   { icon: 'fa-regular fa-clock',        label: 'Queued' },
    paused:    { icon: 'fa-solid fa-pause',          label: 'Paused' },
};

const SKIP_META = {
    branch_not_taken: { icon: 'fa-solid fa-code-branch', label: 'Branch not taken' },
    not_reached:      { icon: 'fa-solid fa-link-slash',  label: 'Never reached' },
    waiting:          { icon: 'fa-regular fa-hourglass-half', label: 'Waiting' },
    not_launched:     { icon: 'fa-solid fa-power-off',   label: 'Not launched' },
};

const CONDITION_LABEL = { success: 'on success', failure: 'on failure', always: 'always' };

function parseIso(s) { return s ? new Date(s).getTime() : null; }

export function formatDuration(seconds) {
    if (seconds === null || seconds === undefined) return '—';
    if (seconds < 1) return '<1s';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const sec = Math.floor(seconds % 60);
    if (h) return `${h}h ${m}m`;
    if (m) return `${m}m ${sec}s`;
    return `${sec}s`;
}

const WorkflowRunTrace = {
    props: {
        trace: { type: Object, required: true },
        taskTypes: { type: Object, default: () => ({}) },
        focusedUuid: { type: String, default: null },
    },
    emits: ['select'],
    delimiters: ['[[', ']]'],
    data() {
        return { now: Date.now(), timer: null, showSkipped: true };
    },
    computed: {
        isRunning() { return this.trace.status === 'running'; },
        stepNumberByTask() {
            const map = {};
            for (const s of this.trace.steps) map[s.task_uuid] = s.step;
            return map;
        },
        // Gantt span: launch start → last finish (or now while running).
        span() {
            const start = parseIso(this.trace.started_at);
            let end = parseIso(this.trace.finished_at);
            if (!end || this.isRunning) end = this.now;
            for (const s of this.trace.steps) {
                const f = parseIso(s.finished_at);
                if (f && f > end) end = f;
            }
            return { start, end, total: Math.max(1, end - start) };
        },
        ganttRows() {
            const { start, total } = this.span;
            return this.trace.steps.map(s => {
                const queued = parseIso(s.queued_at) ?? start;
                const began = parseIso(s.started_at);
                const ended = parseIso(s.finished_at) ?? (began ? this.now : null);
                const pct = t => Math.min(100, Math.max(0, ((t - start) / total) * 100));
                const waitLeft = pct(queued);
                const runLeft = began ? pct(began) : null;
                const runWidth = began ? Math.max(1.2, pct(ended) - runLeft) : 0;
                return {
                    ...s,
                    labelStyle: began ? this.labelPlacement(runLeft, runWidth) : null,
                    waitLeft,
                    waitWidth: began ? Math.max(0, runLeft - waitLeft) : Math.max(0.8, pct(this.now) - waitLeft),
                    runLeft,
                    runWidth,
                };
            });
        },
        ticks() {
            const total = this.span.total / 1000;
            return [0, 0.25, 0.5, 0.75, 1].map(f => ({ left: f * 100, label: f === 0 ? '0' : formatDuration(total * f) }));
        },
        totalDuration() {
            if (this.trace.duration_seconds !== null && this.trace.duration_seconds !== undefined) return this.trace.duration_seconds;
            return this.span.start ? Math.floor((this.now - this.span.start) / 1000) : null;
        },
    },
    watch: {
        'trace.status': { immediate: true, handler() { this.syncTimer(); } },
    },
    beforeUnmount() { if (this.timer) clearInterval(this.timer); },
    methods: {
        syncTimer() {
            if (this.isRunning && !this.timer) this.timer = setInterval(() => { this.now = Date.now(); }, 1000);
            if (!this.isRunning && this.timer) { clearInterval(this.timer); this.timer = null; }
        },
        // The duration label sits next to its bar, never clipped: after the
        // bar while there is room on the right, inside it when the bar is
        // wide enough, otherwise before it (a short bar ending at 100%).
        labelPlacement(left, width) {
            const end = left + width;
            if (end <= 82) return { cls: 'wrt-gantt-time--after', style: { left: end + '%' } };
            if (width >= 14) return { cls: 'wrt-gantt-time--inside', style: { right: (100 - end) + '%' } };
            return { cls: 'wrt-gantt-time--before', style: { right: (100 - left) + '%' } };
        },
        statusMeta(status) { return STATUS_META[status] || STATUS_META.pending; },
        skipMeta(kind) { return SKIP_META[kind] || SKIP_META.not_reached; },
        typeIcon(t) { return (this.taskTypes[t] || {}).icon || 'fa-solid fa-gear'; },
        typeLabel(t) { return (this.taskTypes[t] || {}).label || t; },
        conditionLabel(c) { return CONDITION_LABEL[c] || c; },
        fmt: formatDuration,
        localTime(iso) {
            if (!iso) return '—';
            return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        },
        localDateTime(iso) {
            if (!iso) return '—';
            return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
        },
        stepDuration(s) {
            if (s.duration_seconds !== null && s.duration_seconds !== undefined) return s.duration_seconds;
            if (s.started_at && ['running', 'paused'].includes(s.status)) return Math.floor((this.now - parseIso(s.started_at)) / 1000);
            return null;
        },
        progressPct(s) {
            if (!s.total) return s.status === 'done' ? 100 : 0;
            return Math.min(100, Math.round((s.done / s.total) * 100));
        },
        parentOutcome(trigger) {
            return trigger.parent_status === 'done' ? 'succeeded' : trigger.parent_status === 'failed' ? 'failed' : trigger.parent_status;
        },
    },
    template: `
    <div class="wrt">
        <!-- ── Summary ── -->
        <div class="wrt-summary">
            <div class="wrt-summary-main">
                <span class="wrt-status-pill" :class="'wrt-status-pill--' + trace.status">
                    <i :class="statusMeta(trace.status).icon"></i>[[ statusMeta(trace.status).label ]]
                </span>
                <span class="wrt-summary-meta"><i class="fa-regular fa-calendar me-1"></i>[[ localDateTime(trace.started_at) ]]</span>
                <span class="wrt-summary-meta"><i class="fa-regular fa-clock me-1"></i>[[ isRunning ? 'Running for' : 'Took' ]] <strong>[[ fmt(totalDuration) ]]</strong></span>
                <span class="wrt-summary-meta">
                    <i class="fa-solid fa-user me-1"></i>[[ trace.triggered_by ? trace.triggered_by.name : 'Scheduler' ]]
                </span>
            </div>
            <div class="wrt-counts">
                <span class="wrt-count wrt-count--done" title="Succeeded"><i class="fa-solid fa-check"></i>[[ trace.counts.done ]]</span>
                <span class="wrt-count wrt-count--failed" title="Failed"><i class="fa-solid fa-xmark"></i>[[ trace.counts.failed ]]</span>
                <span v-if="trace.counts.cancelled" class="wrt-count wrt-count--cancelled" title="Cancelled"><i class="fa-solid fa-ban"></i>[[ trace.counts.cancelled ]]</span>
                <span v-if="trace.counts.running" class="wrt-count wrt-count--running" title="Running / queued"><i class="fa-solid fa-spinner fa-spin"></i>[[ trace.counts.running ]]</span>
                <span class="wrt-count wrt-count--skipped" title="Did not run"><i class="fa-solid fa-forward"></i>[[ trace.counts.skipped ]]</span>
                <span class="wrt-count-total">/ [[ trace.counts.total ]] tasks</span>
            </div>
        </div>

        <!-- ── Gantt: when each step queued and ran, relative to the launch ── -->
        <div v-if="trace.steps.length" class="wrt-section">
            <div class="wrt-section-title"><i class="fa-solid fa-bars-staggered me-1"></i>Timeline</div>
            <div class="wrt-gantt">
                <div class="wrt-gantt-axis">
                    <div class="wrt-gantt-label"></div>
                    <div class="wrt-gantt-track wrt-gantt-track--axis">
                        <span v-for="t in ticks" :key="t.left" class="wrt-gantt-tick" :style="{ left: t.left + '%' }">[[ t.label ]]</span>
                    </div>
                </div>
                <div v-for="r in ganttRows" :key="r.task_uuid" class="wrt-gantt-row"
                     :class="{ 'wrt-gantt-row--focused': focusedUuid === r.task_uuid }" @click="$emit('select', r.task_uuid)">
                    <div class="wrt-gantt-label" :title="r.task_title">
                        <span class="wrt-step-num wrt-step-num--sm" :class="'wrt-step-num--' + r.status">[[ r.step ]]</span>
                        <span class="wrt-gantt-title">[[ r.task_title ]]</span>
                    </div>
                    <div class="wrt-gantt-track">
                        <div class="wrt-gantt-wait" :style="{ left: r.waitLeft + '%', width: r.waitWidth + '%' }"
                             :title="'Queued ' + fmt(r.wait_seconds)"></div>
                        <div v-if="r.runLeft !== null" class="wrt-gantt-bar" :class="'wrt-gantt-bar--' + r.status"
                             :style="{ left: r.runLeft + '%', width: r.runWidth + '%' }"
                             :title="statusMeta(r.status).label + ' — ' + fmt(stepDuration(r))"></div>
                        <span v-if="r.labelStyle" class="wrt-gantt-time" :class="[r.labelStyle.cls, 'wrt-gantt-time--' + r.status]"
                              :style="r.labelStyle.style">[[ fmt(stepDuration(r)) ]]</span>
                    </div>
                </div>
            </div>
            <div class="wrt-gantt-legend">
                <span><span class="wrt-legend-swatch wrt-legend-swatch--wait"></span>queued</span>
                <span><span class="wrt-legend-swatch wrt-legend-swatch--done"></span>succeeded</span>
                <span><span class="wrt-legend-swatch wrt-legend-swatch--failed"></span>failed</span>
                <span><span class="wrt-legend-swatch wrt-legend-swatch--running"></span>running</span>
            </div>
        </div>

        <!-- ── Steps, in execution order ── -->
        <div class="wrt-section">
            <div class="wrt-section-title"><i class="fa-solid fa-list-ol me-1"></i>Execution path</div>
            <p v-if="!trace.steps.length" class="text-muted small mb-0">No task has fired yet in this launch.</p>
            <ol class="wrt-steps">
                <li v-for="s in trace.steps" :key="s.task_uuid" class="wrt-step" :class="['wrt-step--' + s.status, { 'wrt-step--focused': focusedUuid === s.task_uuid }]">
                    <div class="wrt-step-rail">
                        <span class="wrt-step-num" :class="'wrt-step-num--' + s.status">
                            <i :class="statusMeta(s.status).icon"></i>
                        </span>
                    </div>
                    <div class="wrt-step-card" @click="$emit('select', s.task_uuid)">
                        <div class="wrt-step-trigger">
                            <template v-if="s.trigger.kind === 'root'">
                                <i class="fa-solid fa-rocket me-1"></i>Step [[ s.step ]] · started by the launch
                            </template>
                            <template v-else>
                                <i class="fa-solid fa-link me-1"></i>Step [[ s.step ]] · after
                                <span class="wrt-step-ref">#[[ stepNumberByTask[s.trigger.parent_task_uuid] ]] [[ s.trigger.parent_title ]]</span>
                                [[ parentOutcome(s.trigger) ]]
                                <span class="wrt-cond" :class="'wrt-cond--' + s.trigger.condition">[[ conditionLabel(s.trigger.condition) ]]</span>
                            </template>
                        </div>
                        <div class="wrt-step-head">
                            <div class="wrt-step-icon"><i :class="typeIcon(s.task_type)"></i></div>
                            <div class="wrt-step-titles">
                                <div class="wrt-step-title">[[ s.task_title ]]</div>
                                <div class="wrt-step-type">[[ typeLabel(s.task_type) ]]</div>
                            </div>
                            <span class="wrt-status-pill wrt-status-pill--sm" :class="'wrt-status-pill--' + s.status">
                                <i :class="statusMeta(s.status).icon"></i>[[ statusMeta(s.status).label ]]
                            </span>
                        </div>
                        <div class="wrt-step-times">
                            <span title="Fired at"><i class="fa-solid fa-bolt me-1"></i>[[ localTime(s.queued_at) ]]</span>
                            <span v-if="s.wait_seconds" title="Time spent waiting in the job queue"><i class="fa-regular fa-hourglass-half me-1"></i>queued [[ fmt(s.wait_seconds) ]]</span>
                            <span title="Run time"><i class="fa-solid fa-stopwatch me-1"></i>[[ s.started_at ? fmt(stepDuration(s)) : 'not started' ]]</span>
                            <span v-if="s.finished_at" title="Finished at"><i class="fa-solid fa-flag-checkered me-1"></i>[[ localTime(s.finished_at) ]]</span>
                            <span v-if="s.total"><i class="fa-solid fa-layer-group me-1"></i>[[ s.done ]] / [[ s.total ]]</span>
                        </div>
                        <div v-if="s.total || s.status === 'running'" class="wrt-step-progress">
                            <div class="wrt-step-progress-bar" :class="'wrt-step-progress-bar--' + s.status" :style="{ width: progressPct(s) + '%' }"></div>
                        </div>
                        <div v-if="s.error" class="wrt-step-error"><i class="fa-solid fa-triangle-exclamation me-1"></i>[[ s.error ]]</div>
                        <div v-else-if="s.last_log" class="wrt-step-log" :class="'wrt-step-log--' + s.last_log.level">
                            <i class="fa-solid fa-terminal me-1"></i>[[ s.last_log.message ]]
                        </div>
                        <div class="wrt-step-actions" @click.stop>
                            <button v-if="s.job_uuid" type="button" class="wrt-step-btn" @click="$emit('select', s.task_uuid)">
                                <i class="fa-solid fa-terminal me-1"></i>Logs
                            </button>
                            <a v-if="s.job_uuid" class="wrt-step-btn" :href="'/jobs/detail/' + s.job_uuid" target="_blank" rel="noopener">
                                <i class="fa-solid fa-up-right-from-square me-1"></i>Job
                            </a>
                        </div>
                    </div>
                </li>
            </ol>
        </div>

        <!-- ── Tasks that did not run, and why ── -->
        <div v-if="trace.skipped.length" class="wrt-section">
            <button type="button" class="wrt-section-title wrt-section-toggle" @click="showSkipped = !showSkipped">
                <i class="fa-solid me-1" :class="showSkipped ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
                Did not run in this launch ([[ trace.skipped.length ]])
            </button>
            <div v-if="showSkipped" class="wrt-skipped">
                <div v-for="k in trace.skipped" :key="k.task_uuid" class="wrt-skip" :class="'wrt-skip--' + k.kind">
                    <div class="wrt-step-icon wrt-step-icon--muted"><i :class="typeIcon(k.task_type)"></i></div>
                    <div class="wrt-skip-body">
                        <div class="wrt-skip-title">[[ k.task_title ]]
                            <span class="wrt-skip-kind"><i :class="skipMeta(k.kind).icon" class="me-1"></i>[[ skipMeta(k.kind).label ]]</span>
                        </div>
                        <div class="wrt-skip-reason">[[ k.reason ]]</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `,
};

export default WorkflowRunTrace;
