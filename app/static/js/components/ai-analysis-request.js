import { create_message } from '/static/js/toaster.js';

const { ref, computed, onMounted } = Vue;

/**
 * AIAnalysisRequest — the "Request an analysis" box of an AI Analysis section, for viewers who can't
 * launch one themselves (issues #88 / #89). Shown with or without an existing report ("Request a new
 * analysis"). Lists the requests with their approval (pending / approved / declined) and, separately,
 * their execution (queued / running / completed / failed) — approved is not done. Explains why the
 * viewer can't launch it directly, and why they can't request it when the instance limits requests to
 * owners. Anonymous visitors are invited to log in. Renders nothing for someone who can launch it.
 *
 * Used on the rule AI Analysis page and in the bundle AI Analysis panel.
 *
 * Props:
 *   endpoint    GET → { can_launch, can_request, why_not, launch_needs, pending, recent }, POST { script, message }
 *   csrf-token
 *   scripts     [{ key, label, icon, desc }] — one entry = no type choice
 *   noun        "rule" | "bundle"
 *   has-report  a report already exists → "Request a new analysis"
 */
const APPROVAL = { pending: ['Waiting for approval', 'fa-hourglass-half', 'wait'], approved: ['Approved', 'fa-check', 'ok'],
                   declined: ['Declined', 'fa-xmark', 'bad'] };
const EXECUTION = { not_started: ['Not started', 'fa-circle', 'muted'], queued: ['Queued', 'fa-clock', 'wait'],
                    running: ['Running', 'fa-spinner fa-spin', 'run'], completed: ['Report ready', 'fa-file-circle-check', 'ok'],
                    failed: ['Failed — can be requested again', 'fa-triangle-exclamation', 'bad'] };

const AIAnalysisRequest = {
    name: 'AIAnalysisRequest',
    delimiters: ['[[', ']]'],
    props: {
        endpoint:  { type: String, required: true },
        csrfToken: { type: String, required: true },
        scripts:   { type: Array, required: true },
        noun:      { type: String, default: 'rule' },
        hasReport: { type: Boolean, default: false },
    },
    emits: ['requested'],
    setup(props, { emit }) {
        const state = ref(null);           // GET response
        const script = ref(props.scripts[0]?.key);
        const message = ref('');
        const sending = ref(false);
        const showForm = ref(false);

        async function load() {
            try {
                const res = await fetch(props.endpoint);
                if (res.ok) state.value = await res.json();
            } catch { /* box stays hidden */ }
        }

        const scriptLabel = key => props.scripts.find(s => s.key === key)?.label || key;
        // the same analysis of the current version is still to come → no second request
        const alreadyRequested = computed(() => (state.value?.pending || []).some(
            p => p.script === script.value && p.current_revision !== false));
        const shown = computed(() => {
            const recent = state.value?.recent || [];
            const pending = state.value?.pending || [];
            return [...pending, ...recent.filter(r => !pending.some(p => p.uuid === r.uuid))].slice(0, 6);
        });

        async function send() {
            sending.value = true;
            try {
                const res = await fetch(props.endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ script: script.value, message: message.value }),
                });
                const data = await res.json();
                create_message(data.message, data.toast_class || (res.ok ? 'success' : 'danger'));
                if (res.ok) {
                    message.value = '';
                    showForm.value = false;
                    emit('requested', data.request);
                    load();
                }
            } catch {
                create_message('Network error — please try again.', 'danger');
            } finally {
                sending.value = false;
            }
        }

        // dates with the viewer's time zone, never an ambiguous bare timestamp
        const fmt = ts => (ts ? new Date(ts.endsWith('Z') || /[+-]\d\d:\d\d$/.test(ts) ? ts : ts + 'Z').toLocaleString(undefined,
            { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' }) : '');
        const loginUrl = '/account/login?next=' + encodeURIComponent(location.pathname + location.hash);

        onMounted(load);
        return { state, script, message, sending, showForm, scriptLabel, alreadyRequested, shown, send, fmt, loginUrl,
                 APPROVAL, EXECUTION };
    },
    template: `
    <div v-if="state && !state.can_launch" class="aiq">
        <!-- The requests: approval and execution are two different things -->
        <div v-if="shown.length" class="aiq-list">
            <div class="aiq-list-title"><i class="fa-solid fa-list-check me-1"></i>Analysis requests</div>
            <div v-for="p in shown" :key="p.uuid" class="aiq-req">
                <div class="aiq-req-main">
                    <strong>[[ scriptLabel(p.script) ]]</strong>
                    <span class="text-muted"> — requested <template v-if="p.mine">by you</template><template v-else-if="p.user_name">by [[ p.user_name ]]</template>, [[ fmt(p.created_at) ]]</span>
                    <span v-if="p.revision" class="aiq-rev" :title="'Revision analysed: ' + p.revision">
                        rev. [[ p.revision ]]<template v-if="p.current_revision === false"> (older version)</template></span>
                </div>
                <div class="aiq-req-status">
                    <span class="aiq-chip" :class="'is-' + APPROVAL[p.approval][2]"><i class="fa-solid" :class="APPROVAL[p.approval][1]"></i>[[ APPROVAL[p.approval][0] ]]<template v-if="p.decided_by_name"> by [[ p.decided_by_name ]]</template></span>
                    <span v-if="p.approval === 'approved'" class="aiq-chip" :class="'is-' + EXECUTION[p.execution][2]"><i class="fa-solid" :class="EXECUTION[p.execution][1]"></i>[[ EXECUTION[p.execution][0] ]]</span>
                    <a v-if="p.job_uuid" :href="'/jobs/detail/' + p.job_uuid" class="aiq-link" title="The background job running it">job</a>
                </div>
            </div>
        </div>

        <!-- Why not launch it directly -->
        <p v-if="state.can_request || state.why_not" class="aiq-note">
            <i class="fa-solid fa-circle-info me-1"></i>Generating an analysis directly needs [[ state.launch_needs ]].
            <template v-if="state.can_request">You can ask the AI managers instead — the exact current version of this [[ noun ]] is what will be analysed.</template>
        </p>

        <!-- Anonymous -->
        <div v-if="!state.can_request && !state.why_not" class="aiq-cta">
            <span><i class="fa-solid fa-robot me-1"></i>Want Rulezy to analyse this [[ noun ]]?</span>
            <a :href="loginUrl" class="btn btn-sm btn-outline-primary rounded-pill px-3">
                <i class="fa-solid fa-right-to-bracket me-1"></i>Log in to request an analysis
            </a>
        </div>
        <!-- Signed in, but requests are limited to owners on this instance -->
        <div v-else-if="!state.can_request" class="aiq-cta aiq-cta--off">
            <span><i class="fa-solid fa-lock me-1"></i>[[ state.why_not ]]</span>
        </div>

        <template v-else>
            <div v-if="!showForm" class="aiq-cta">
                <span><i class="fa-solid fa-robot me-1"></i>[[ hasReport ? 'This ' + noun + ' changed, or you want another type of analysis?' : 'This ' + noun + ' needs an analysis? Ask the AI managers.' ]]</span>
                <button type="button" class="btn btn-sm btn-primary rounded-pill px-3" @click="showForm = true">
                    <i class="fa-solid fa-paper-plane me-1"></i>[[ hasReport ? 'Request a new analysis' : 'Request an analysis' ]]
                </button>
            </div>

            <div v-else class="aiq-form">
                <div class="aiq-form-title">Request an AI analysis of this [[ noun ]]</div>
                <div v-if="scripts.length > 1" class="aiq-scripts">
                    <label v-for="s in scripts" :key="s.key" class="aiq-script" :class="{ 'is-active': script === s.key }">
                        <input type="radio" class="form-check-input mt-1" :value="s.key" v-model="script">
                        <span class="aiq-script-icon"><i class="fa-solid" :class="s.icon"></i></span>
                        <span>
                            <span class="aiq-script-title">[[ s.label ]]</span>
                            <span class="aiq-script-desc">[[ s.desc ]]</span>
                        </span>
                    </label>
                </div>
                <textarea v-model="message" class="form-control form-control-sm mb-2" rows="2" maxlength="1000"
                    placeholder="Why this analysis would help (optional) — e.g. the rule has no description, unclear condition…"></textarea>
                <div class="d-flex align-items-center gap-2 flex-wrap">
                    <button type="button" class="btn btn-sm btn-primary rounded-pill px-3" :disabled="sending || alreadyRequested" @click="send">
                        <i class="fa-solid me-1" :class="sending ? 'fa-spinner fa-spin' : 'fa-paper-plane'"></i>
                        Request [[ scripts.length > 1 ? scriptLabel(script).toLowerCase() : 'an analysis' ]]
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3" @click="showForm = false">Cancel</button>
                    <span v-if="alreadyRequested" class="small text-muted">Already requested for this version — waiting or running.</span>
                    <span v-else class="small text-muted">The AI managers are notified and run it when they accept.</span>
                </div>
            </div>
        </template>
    </div>
    `,
};

export default AIAnalysisRequest;
