import { create_message } from '/static/js/toaster.js';

const { ref, computed, onMounted } = Vue;

/**
 * AIAnalysisRequest — "Request an analysis" box of an AI Analysis section
 * with no report yet, for viewers who can't launch one themselves. A
 * logged-in user picks the analysis type and sends the request to the AI
 * managers; anonymous visitors are invited to log in. Shows the requests
 * already waiting. Renders nothing for someone who can launch the analysis.
 *
 * Used on the rule AI Analysis page and in the bundle AI Analysis panel.
 *
 * Props:
 *   endpoint    GET → { can_launch, can_request, pending }, POST { script, message }
 *   csrf-token
 *   scripts     [{ key, label, icon, desc }] — one entry = no type choice
 *   noun        "rule" | "bundle"
 */
const AIAnalysisRequest = {
    name: 'AIAnalysisRequest',
    delimiters: ['[[', ']]'],
    props: {
        endpoint:  { type: String, required: true },
        csrfToken: { type: String, required: true },
        scripts:   { type: Array, required: true },
        noun:      { type: String, default: 'rule' },
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

        const pendingFor = key => (state.value?.pending || []).filter(p => p.script === key);
        const scriptLabel = key => props.scripts.find(s => s.key === key)?.label || key;
        const alreadyRequested = computed(() => pendingFor(script.value).length > 0);

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

        const fmt = ts => (ts ? new Date(ts).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '');
        const loginUrl = '/account/login?next=' + encodeURIComponent(location.pathname + location.hash);

        onMounted(load);
        return { state, script, message, sending, showForm, pendingFor, scriptLabel, alreadyRequested, send, fmt, loginUrl };
    },
    template: `
    <div v-if="state && !state.can_launch" class="aiq">
        <!-- Already waiting -->
        <div v-if="state.pending.length" class="aiq-pending">
            <i class="fa-solid fa-hourglass-half"></i>
            <div>
                <div v-for="p in state.pending" :key="p.script + p.created_at">
                    <strong>[[ scriptLabel(p.script) ]]</strong> requested
                    <template v-if="p.mine">by you</template><template v-else-if="p.user_name">by [[ p.user_name ]]</template>
                    on [[ fmt(p.created_at) ]] — waiting for an AI manager.
                </div>
            </div>
        </div>

        <!-- Anonymous -->
        <div v-if="!state.can_request" class="aiq-cta">
            <span><i class="fa-solid fa-robot me-1"></i>Want Rulezy to analyse this [[ noun ]]?</span>
            <a :href="loginUrl" class="btn btn-sm btn-outline-primary rounded-pill px-3">
                <i class="fa-solid fa-right-to-bracket me-1"></i>Log in to request an analysis
            </a>
        </div>

        <template v-else>
            <div v-if="!showForm" class="aiq-cta">
                <span><i class="fa-solid fa-robot me-1"></i>This [[ noun ]] needs an analysis? Ask the AI managers.</span>
                <button type="button" class="btn btn-sm btn-primary rounded-pill px-3" @click="showForm = true">
                    <i class="fa-solid fa-paper-plane me-1"></i>Request an analysis
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
                    <span v-if="alreadyRequested" class="small text-muted">Already requested — waiting for an AI manager.</span>
                    <span v-else class="small text-muted">The AI managers are notified and run it when they accept.</span>
                </div>
            </div>
        </template>
    </div>
    `,
};

export default AIAnalysisRequest;
