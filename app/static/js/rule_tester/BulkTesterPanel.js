import InputEditorByFormat from './InputEditorByFormat.js';
import { create_message }  from '/static/js/toaster.js';

const BulkTesterPanel = {
    name: 'BulkTesterPanel',
    delimiters: ['[[', ']]'],
    components: { InputEditorByFormat },
    props: {
        isAuthenticated: { type: Boolean, default: false },
        csrfToken:       { type: String, default: '' },
    },
    data() {
        return {
            format:     '',
            tags:       '',
            search:     '',
            inputData:  { type: 'string', value: '' },
            inputLabel: '',
            label:      '',
            isPublic:   false,

            submitting:   false,
            jobUuid:      null,
            testUuid:     null,
            jobStatus:    null,
            jobDone:      0,
            jobTotal:     0,
            jobPct:       0,
            pollTimer:    null,
            logSinceId:   0,
            logs:         [],
            result:       null,
        };
    },
    computed: {
        formats() {
            return ['yara'];
        },
        isRunning() {
            return this.jobStatus === 'pending' || this.jobStatus === 'running';
        },
        progressBarStyle() {
            const pct = this.jobPct;
            let color = '#0d6efd';
            if (pct === 100) color = '#198754';
            return `width:${pct}%;background:${color};transition:width .4s ease;`;
        },
    },
    async mounted() {
        // Restore job from URL ?job=<uuid>
        const params   = new URLSearchParams(window.location.search);
        const jobParam = params.get('job');
        if (jobParam) {
            this.jobUuid  = jobParam;
            this.jobStatus = 'running';
            // fetch payload to recover testUuid
            try {
                const r = await fetch(`/jobs/api/${jobParam}`);
                if (r.ok) {
                    const d = await r.json();
                    if (d.meta && d.meta.test_uuid) {
                        this.testUuid = d.meta.test_uuid;
                    }
                }
            } catch (_) {}
            this._startPoll();
        }
    },
    beforeUnmount() { this._stopPoll(); },
    methods: {
        async submit() {
            if (!this.format) { create_message('Select a format to test.', 'danger'); return; }
            if (!this.inputData.value && !['host_json','http_request'].includes(this.inputData.type)) {
                create_message('Enter test input before launching.', 'danger');
                return;
            }
            this.submitting  = true;
            this.jobUuid     = null;
            this.testUuid    = null;
            this.jobStatus   = null;
            this.jobDone     = 0;
            this.jobTotal    = 0;
            this.jobPct      = 0;
            this.logs        = [];
            this.logSinceId  = 0;
            this.result      = null;

            try {
                const resp = await fetch('/api/rule_tester/private/test', {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken },
                    body: JSON.stringify({
                        test_type:    'bulk',
                        format:       this.format,
                        bulk_filters: { format: this.format, tags: this.tags, search: this.search },
                        input_type:   this.inputData.type,
                        input_data:   this.inputData.value,
                        input_label:  this.inputLabel || null,
                        label:        this.label || null,
                        is_public:    this.isPublic,
                    }),
                });
                const data = await resp.json();
                if (!resp.ok) { create_message(data.message || 'Failed to launch.', 'danger'); return; }

                // redirect immediately to the test detail page
                window.location = '/rule_tester/test/' + data.test_uuid;
            } catch (e) {
                create_message('Network error: ' + e.message, 'danger');
            } finally {
                this.submitting = false;
            }
        },

        _startPoll() {
            this._stopPoll();
            this._poll();
            this.pollTimer = setInterval(this._poll, 2500);
        },
        _stopPoll() {
            if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
        },

        async _poll() {
            if (!this.jobUuid) return;
            try {
                // job status
                const sResp = await fetch(`/jobs/status/${this.jobUuid}`);
                if (sResp.ok) {
                    const sData = await sResp.json();
                    this.jobStatus = sData.status;
                    this.jobDone   = sData.done   || 0;
                    this.jobTotal  = sData.total  || 0;
                    this.jobPct    = sData.progress_pct || 0;
                }

                // incremental logs
                const lResp = await fetch(`/jobs/logs/${this.jobUuid}?since_id=${this.logSinceId}`);
                if (lResp.ok) {
                    const newLogs = await lResp.json();
                    if (newLogs.length) {
                        this.logs.push(...newLogs);
                        this.logSinceId = newLogs[newLogs.length - 1].id;
                        this.$nextTick(() => {
                            const el = this.$el.querySelector('.rtr-log');
                            if (el) el.scrollTop = el.scrollHeight;
                        });
                    }
                }

                if (this.jobStatus === 'done' || this.jobStatus === 'failed') {
                    this._stopPoll();
                    this.jobPct = this.jobStatus === 'done' ? 100 : this.jobPct;
                    if (this.jobStatus === 'done') {
                        create_message(`Done — ${this.jobDone} rule(s) processed.`, 'success');
                    } else {
                        create_message('Job failed. See logs below.', 'danger');
                    }
                }
            } catch (e) { /* retry next tick */ }
        },

        statusBadgeClass(s) {
            const m = { pending: 'bg-secondary', running: 'bg-primary', done: 'bg-success', failed: 'bg-danger' };
            return 'badge ' + (m[s] || 'bg-secondary');
        },
        defaultType() {
            const map = {
                yara: 'string', sigma: 'json', suricata: 'text_payload',
                zeek: 'zeek_log_json', wazuh: 'syslog_line', nse: 'host_json',
                crs: 'http_request', atr: 'text', nova: 'text',
            };
            return map[this.format] || 'string';
        },
    },

    template: `
<div class="rtr-panel">
  <div class="rtr-panel__header">
    <i class="fa-solid fa-flask-vial text-primary"></i>
    <span class="rtr-panel__title">Bulk Rule Tester</span>
    <span v-if="jobStatus" class="ms-auto" :class="statusBadgeClass(jobStatus)">
      [[ jobStatus.toUpperCase() ]]
    </span>
  </div>

  <div class="rtr-panel__body">

    <!-- ── Job tracker (visible as soon as a job is running) ── -->
    <div v-if="jobUuid" class="mb-4">

      <!-- Progress bar -->
      <div class="d-flex align-items-center justify-content-between mb-1">
        <span style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--subtle-text-color);">
          Progress
        </span>
        <span style="font-size:.72rem;color:var(--subtle-text-color);">
          [[ jobDone ]] / [[ jobTotal ]] rules · [[ jobPct ]]%
        </span>
      </div>
      <div style="height:10px;border-radius:6px;background:var(--border-color);overflow:hidden;">
        <div :style="progressBarStyle" style="height:100%;border-radius:6px;"></div>
      </div>

      <!-- 25 / 50 / 75 / 100 markers -->
      <div class="d-flex justify-content-between mt-1" style="font-size:.6rem;color:var(--subtle-text-color);">
        <span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span>
      </div>

      <!-- Quick links -->
      <div class="d-flex gap-2 mt-2 flex-wrap">
        <a :href="'/jobs/detail/' + jobUuid" target="_blank"
           class="btn btn-outline-secondary btn-sm" style="font-size:.72rem;">
          <i class="fa-solid fa-chart-line me-1"></i>Job detail
        </a>
        <a v-if="testUuid" :href="'/rule_tester/test/' + testUuid" target="_blank"
           class="btn btn-outline-primary btn-sm" style="font-size:.72rem;">
          <i class="fa-solid fa-list me-1"></i>View results
        </a>
      </div>

      <!-- Live logs -->
      <div v-if="logs.length" class="rtr-log mt-3" style="max-height:220px;overflow-y:auto;">
        <div v-for="l in logs" :key="l.id"
             class="rtr-log-line" :class="'rtr-log-line--' + l.level">
          <span style="opacity:.5;font-size:.65rem;margin-right:.5em;">[[ l.created_at ? l.created_at.slice(11,19) : '' ]]</span>
          [[ l.message ]]
        </div>
      </div>

      <!-- Done summary -->
      <div v-if="jobStatus === 'done'" class="alert alert-success mt-3 mb-0" style="font-size:.85rem;">
        <i class="fa-solid fa-circle-check me-2"></i>
        Completed — [[ jobDone ]] rules processed.
        <a v-if="testUuid" :href="'/rule_tester/test/' + testUuid" class="alert-link ms-2">
          View full results →
        </a>
      </div>
      <div v-if="jobStatus === 'failed'" class="alert alert-danger mt-3 mb-0" style="font-size:.85rem;">
        <i class="fa-solid fa-circle-xmark me-2"></i>Job failed — check the logs above.
      </div>

      <hr class="my-4">
    </div>

    <!-- ── Launch form ── -->
    <p style="font-size:.82rem;color:var(--subtle-text-color);">
      Run a test payload against every rule matching the filters. YARA rules are compiled in 4 batches for speed.
    </p>

    <!-- Filters -->
    <div class="rounded-3 border p-3 mb-4" style="background:var(--light-bg-color);">
      <div class="row g-2">
        <div class="col-md-4">
          <label class="form-label" style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--subtle-text-color);">Format *</label>
          <select v-model="format" class="form-select form-select-sm"
                  @change="inputData = { type: defaultType(), value: '' }"
                  :disabled="isRunning">
            <option value="">— select —</option>
            <option v-for="f in formats" :key="f" :value="f">[[ f.toUpperCase() ]]</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label" style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--subtle-text-color);">Tags filter</label>
          <input type="text" v-model="tags" class="form-control form-control-sm"
                 placeholder="e.g. malware,apt" :disabled="isRunning">
        </div>
        <div class="col-md-4">
          <label class="form-label" style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--subtle-text-color);">Keyword search</label>
          <input type="text" v-model="search" class="form-control form-control-sm"
                 placeholder="title or description" :disabled="isRunning">
        </div>
      </div>
    </div>

    <!-- Input editor -->
    <div class="mb-3" v-if="format">
      <label class="form-label" style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--subtle-text-color);">Test Input</label>
      <InputEditorByFormat :format="format" v-model="inputData" />
    </div>
    <div v-else class="alert alert-secondary mb-3" style="font-size:.82rem;">
      <i class="fa-solid fa-arrow-up me-2"></i>Select a format above to configure the test input.
    </div>

    <!-- Metadata -->
    <div class="rtr-meta-row mb-3" v-if="format">
      <div class="rtr-field">
        <label>Input label</label>
        <input type="text" v-model="inputLabel" placeholder="e.g. EICAR string" :disabled="isRunning">
      </div>
      <div class="rtr-field">
        <label>Job label</label>
        <input type="text" v-model="label" placeholder="e.g. YARA bulk test v1" :disabled="isRunning">
      </div>
    </div>

    <!-- Privacy -->
    <div class="rtr-privacy-row mb-3" v-if="format">
      <input type="checkbox" id="bulk-public" v-model="isPublic" class="form-check-input me-2"
             :disabled="isRunning">
      <label for="bulk-public" style="cursor:pointer;">
        <i class="fa-solid" :class="isPublic ? 'fa-globe text-success' : 'fa-lock'"></i>
        [[ isPublic ? 'Results public' : 'Results private' ]]
      </label>
    </div>

    <!-- Launch button -->
    <button class="rtr-run-btn" :class="{ 'rtr-run-btn--loading': submitting }"
            @click="submit" :disabled="submitting || isRunning || !format">
      <i class="fa-solid fa-rocket rtr-run-icon"></i>
      <i class="fa-solid fa-circle-notch rtr-spin"></i>
      [[ submitting ? 'Queuing…' : (isRunning ? 'Job running…' : 'Launch Bulk Test') ]]
    </button>

  </div>
</div>
`,
};

export default BulkTesterPanel;
