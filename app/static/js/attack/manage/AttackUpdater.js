/**
 * AttackUpdater.js
 * Admin component — two independent operations with live polling:
 *   1) Update ATT&CK catalogue from MITRE GitHub
 *   2) Auto-parse all rules for technique associations
 *
 * Polls /jobs/status/<uuid> and /jobs/logs/<uuid>?since_id=N every 2 s.
 */

const { ref, computed, onUnmounted } = Vue;

function levelColor(l) {
    if (l === 'success') return '#3fb950';   // green
    if (l === 'warning') return '#d29922';   // amber
    if (l === 'error')   return '#f85149';   // red
    return '#8b949e';                         // gray
}
function levelPrefix(l) {
    if (l === 'success') return '[OK]  ';
    if (l === 'warning') return '[WARN]';
    if (l === 'error')   return '[ERR] ';
    return '[INFO]';
}
// keep for non-terminal status icons
function levelClass(l) {
    if (l === 'success') return 'text-success';
    if (l === 'warning') return 'text-warning';
    if (l === 'error')   return 'text-danger';
    return 'text-muted';
}
function levelIcon(l) {
    if (l === 'success') return 'fa-solid fa-check';
    if (l === 'warning') return 'fa-solid fa-triangle-exclamation';
    if (l === 'error')   return 'fa-solid fa-xmark';
    return 'fa-solid fa-circle-dot';
}
function statusIcon(s) {
    if (s === 'running') return 'fa-solid fa-spinner fa-spin text-primary';
    if (s === 'done')    return 'fa-solid fa-circle-check text-success';
    if (s === 'failed' || s === 'error') return 'fa-solid fa-circle-xmark text-danger';
    return 'fa-regular fa-circle text-muted';
}
function statusBorderClass(s) {
    if (s === 'running') return 'border-primary';
    if (s === 'done')    return 'border-success';
    if (s === 'failed' || s === 'error') return 'border-danger';
    return '';
}

function makeOperation() {
    return {
        running:  ref(false),
        uuid:     ref(null),
        status:   ref('idle'),
        logs:     ref([]),
        lastId:   ref(0),
        timer:    null,
    };
}

export default {
    name: 'AttackUpdater',
    delimiters: ['[[', ']]'],
    props: { csrfToken: { type: String, required: true } },
    emits: ['notify', 'refresh-main'],

    setup(props, { emit }) {
        const upd  = makeOperation();
        const prs  = makeOperation();

        // ── parse-specific state ─────────────────────────────────────────────
        const parseTotal  = ref(0);
        const parseDone   = ref(0);
        const parseFormat = ref(null);  // null | 'sigma' | ...
        const parsePct    = computed(() =>
            parseTotal.value > 0 ? Math.round(parseDone.value / parseTotal.value * 100) : 0
        );

        // ── update-specific state ────────────────────────────────────────────
        const updateSummary = ref('');

        // ── shared: make a polling function for an operation ─────────────────
        function buildPoll(op, onLogEntry) {
            return async function poll() {
                if (!op.uuid.value) return;
                try {
                    const [sRes, lRes] = await Promise.all([
                        fetch(`/jobs/status/${op.uuid.value}`),
                        fetch(`/jobs/logs/${op.uuid.value}?since_id=${op.lastId.value}`),
                    ]);
                    const sData = await sRes.json();
                    const lines = await lRes.json();

                    op.status.value = sData.status || 'running';

                    for (const log of lines) {
                        op.logs.value.push(log);
                        op.lastId.value = Math.max(op.lastId.value, log.id);
                        if (onLogEntry) onLogEntry(log);
                    }

                    const done = ['done', 'failed', 'cancelled'].includes(op.status.value);
                    if (done) {
                        clearInterval(op.timer);
                        op.timer   = null;
                        op.running.value = false;
                        if (op.status.value === 'done') {
                            emit('refresh-main');
                            emit('notify', 'Operation complete!');
                        }
                    }
                } catch (e) {
                    console.error('[AttackUpdater] poll error:', e);
                }
            };
        }

        const pollUpdate = buildPoll(upd, (log) => {
            if (log.event === 'done') updateSummary.value = log.message;
        });

        const pollParse = buildPoll(prs, (log) => {
            if (log.event === 'start') {
                const m = log.message.match(/(\d+) rules/);
                if (m) parseTotal.value = parseInt(m[1]);
            }
            if (log.event === 'progress') {
                const m = log.message.match(/^(\d+)\/(\d+)/);
                if (m) { parseDone.value = parseInt(m[1]); parseTotal.value = parseInt(m[2]); }
            }
            if (log.event === 'done') {
                const m = log.message.match(/^(\d+) rules/);
                if (m) parseDone.value = parseTotal.value;
            }
        });

        // ── start update ─────────────────────────────────────────────────────
        async function startUpdate() {
            if (upd.running.value) return;
            upd.running.value = true;
            upd.logs.value    = [];
            upd.lastId.value  = 0;
            upd.uuid.value    = null;
            upd.status.value  = 'pending';
            updateSummary.value = '';

            try {
                const res  = await fetch('/attack/admin/trigger_update', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': props.csrfToken },
                });
                const data = await res.json();
                if (!data.success) {
                    emit('notify', data.error || 'Failed to start update');
                    upd.running.value = false;
                    return;
                }
                upd.uuid.value   = data.job_uuid;
                upd.status.value = 'running';
                upd.timer = setInterval(pollUpdate, 2000);
                pollUpdate();
            } catch (e) {
                emit('notify', 'Network error: ' + e);
                upd.running.value = false;
            }
        }

        // ── start parse ───────────────────────────────────────────────────────
        async function startParse(fmt) {
            if (prs.running.value) return;
            prs.running.value = true;
            prs.logs.value    = [];
            prs.lastId.value  = 0;
            prs.uuid.value    = null;
            prs.status.value  = 'pending';
            parseTotal.value  = 0;
            parseDone.value   = 0;
            parseFormat.value = fmt || null;

            try {
                const res  = await fetch('/attack/admin/trigger_parse', {
                    method:  'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body:    JSON.stringify({ format: fmt || null }),
                });
                const data = await res.json();
                if (!data.success) {
                    emit('notify', data.error || 'Failed to start parse job');
                    prs.running.value = false;
                    return;
                }
                prs.uuid.value   = data.job_uuid;
                prs.status.value = 'running';
                prs.timer = setInterval(pollParse, 2000);
                pollParse();
            } catch (e) {
                emit('notify', 'Network error: ' + e);
                prs.running.value = false;
            }
        }

        onUnmounted(() => {
            if (upd.timer) clearInterval(upd.timer);
            if (prs.timer) clearInterval(prs.timer);
        });

        return {
            upd, prs,
            parseTotal, parseDone, parsePct, parseFormat,
            updateSummary,
            startUpdate, startParse,
            levelClass, levelIcon, levelColor, levelPrefix,
            statusIcon, statusBorderClass,
        };
    },

    template: `
<div class="row g-4">

  <!-- ── Card 1: Update from MITRE ──────────────────────────────────────── -->
  <div class="col-12">
    <div class="card border-0 shadow-sm rounded-4">
      <div class="card-body p-4">

        <div class="d-flex align-items-start justify-content-between flex-wrap gap-3 mb-4">
          <div>
            <h6 class="fw-bold mb-1">
              <i class="fa-solid fa-rotate me-2 text-primary"></i>Update ATT&amp;CK Catalogue
            </h6>
            <small class="text-muted">
              Downloads the latest Enterprise ATT&amp;CK data from
              <code>github.com/mitre/cti</code> and upserts all technique records locally.
            </small>
          </div>
          <button @click="startUpdate" :disabled="upd.running.value"
                  class="btn btn-primary fw-semibold px-4">
            <i class="fa-solid me-2" :class="upd.running.value ? 'fa-spinner fa-spin' : 'fa-rotate'"></i>
            [[ upd.running.value ? 'Running…' : 'Update from MITRE' ]]
          </button>
        </div>

        <!-- Status card -->
        <div class="border rounded-3 p-3 mb-3" :class="statusBorderClass(upd.status.value)">
          <div class="d-flex align-items-center gap-2 mb-2">
            <i :class="statusIcon(upd.status.value)" class="fs-5"></i>
            <span class="fw-semibold small">Fetch &amp; Import</span>
          </div>
          <template v-if="updateSummary">
            <span class="badge bg-success-subtle text-success small">[[ updateSummary ]]</span>
          </template>
          <div v-else-if="upd.status.value === 'running'" class="text-primary small">
            <i class="fa-solid fa-spinner fa-spin me-1"></i>Fetching data from MITRE GitHub…
          </div>
          <p v-else class="text-muted small mb-0 fst-italic">Not started yet.</p>
        </div>

        <!-- Terminal live log -->
        <template v-if="upd.logs.value.length">
          <div class="d-flex align-items-center justify-content-between mb-1">
            <span class="fw-semibold small" style="color:#8b949e;"><i class="fa-solid fa-terminal me-1"></i>Live log</span>
            <span v-if="upd.uuid.value" style="font-size:.65rem;color:#8b949e;">job&nbsp;<span style="color:#58a6ff;font-family:monospace;">[[ upd.uuid.value ]]</span></span>
          </div>
          <div class="rounded-3 p-3" style="max-height:240px;overflow-y:auto;background:#0d1117;border:1px solid #30363d;font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace;font-size:.72rem;line-height:1.6;">
            <div v-for="log in upd.logs.value" :key="log.id" style="display:flex;gap:.5rem;margin-bottom:.15rem;">
              <span style="color:#484f58;flex-shrink:0;min-width:145px;">[[ log.created_at ]]</span>
              <span :style="{ color: levelColor(log.level), flexShrink: 0, minWidth: '3.5rem' }">[[ levelPrefix(log.level) ]]</span>
              <span :style="{ color: levelColor(log.level) }" style="white-space:pre-wrap;word-break:break-all;">[[ log.message ]]</span>
            </div>
          </div>
        </template>
        <div v-else class="text-center py-3 text-muted">
          <i class="fa-solid fa-rotate fa-2x mb-2 d-block opacity-25"></i>
          <small>Click <strong>Update from MITRE</strong> to fetch the latest ATT&amp;CK data.</small>
        </div>

      </div>
    </div>
  </div>

  <!-- ── Card 2: Auto-parse rules ───────────────────────────────────────── -->
  <div class="col-12">
    <div class="card border-0 shadow-sm rounded-4">
      <div class="card-body p-4">

        <div class="d-flex align-items-start justify-content-between flex-wrap gap-3 mb-4">
          <div>
            <h6 class="fw-bold mb-1">
              <i class="fa-solid fa-wand-magic-sparkles me-2" style="color:#e67e22;"></i>Auto-parse Rules
            </h6>
            <small class="text-muted">
              Scans all rule content and creates ATT&amp;CK associations automatically
              (Sigma tags, YARA meta, Suricata metadata, Wazuh XML, etc.)
            </small>
          </div>
          <div class="d-flex gap-2 flex-wrap">
            <button @click="startParse(null)" :disabled="prs.running.value"
                    class="btn btn-warning fw-semibold px-4">
              <i class="fa-solid me-2" :class="(prs.running.value && !parseFormat) ? 'fa-spinner fa-spin' : 'fa-layer-group'"></i>
              All formats
            </button>
            <button @click="startParse('sigma')" :disabled="prs.running.value"
                    class="btn btn-outline-secondary px-3">
              <i class="fa-solid me-2" :class="(prs.running.value && parseFormat === 'sigma') ? 'fa-spinner fa-spin' : 'fa-sigma'"></i>
              Sigma only
            </button>
          </div>
        </div>

        <!-- Progress card -->
        <div class="border rounded-3 p-3 mb-3" :class="statusBorderClass(prs.status.value)">
          <div class="d-flex align-items-center gap-2 mb-2">
            <i :class="statusIcon(prs.status.value)" class="fs-5"></i>
            <span class="fw-semibold small">Scanning rules</span>
            <span v-if="parseFormat" class="badge bg-secondary rounded-pill" style="font-size:.7rem;">[[ parseFormat ]]</span>
          </div>

          <template v-if="prs.status.value === 'running' && parseTotal > 0">
            <div class="progress mb-2" style="height:6px;">
              <div class="progress-bar bg-warning" :style="{ width: parsePct + '%' }"></div>
            </div>
            <small class="text-muted">[[ parseDone ]] / [[ parseTotal ]] rules ([[ parsePct ]]%)</small>
          </template>
          <div v-else-if="prs.status.value === 'running'" class="text-warning small">
            <i class="fa-solid fa-spinner fa-spin me-1"></i>Starting…
          </div>
          <template v-else-if="prs.status.value === 'done'">
            <span class="badge bg-success-subtle text-success small">
              [[ prs.logs.value.slice().reverse().find(l => l.event === 'done')?.message || 'Complete' ]]
            </span>
          </template>
          <p v-else class="text-muted small mb-0 fst-italic">Not started yet.</p>
        </div>

        <!-- Terminal live log -->
        <template v-if="prs.logs.value.length">
          <div class="d-flex align-items-center justify-content-between mb-1">
            <span class="fw-semibold small" style="color:#8b949e;"><i class="fa-solid fa-terminal me-1"></i>Live log</span>
            <span v-if="prs.uuid.value" style="font-size:.65rem;color:#8b949e;">job&nbsp;<span style="color:#58a6ff;font-family:monospace;">[[ prs.uuid.value ]]</span></span>
          </div>
          <div class="rounded-3 p-3" style="max-height:240px;overflow-y:auto;background:#0d1117;border:1px solid #30363d;font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace;font-size:.72rem;line-height:1.6;">
            <div v-for="log in prs.logs.value" :key="log.id" style="display:flex;gap:.5rem;margin-bottom:.15rem;">
              <span style="color:#484f58;flex-shrink:0;min-width:145px;">[[ log.created_at ]]</span>
              <span :style="{ color: levelColor(log.level), flexShrink: 0, minWidth: '3.5rem' }">[[ levelPrefix(log.level) ]]</span>
              <span :style="{ color: levelColor(log.level) }" style="white-space:pre-wrap;word-break:break-all;">[[ log.message ]]</span>
            </div>
          </div>
        </template>
        <div v-else class="text-center py-3 text-muted">
          <i class="fa-solid fa-wand-magic-sparkles fa-2x mb-2 d-block opacity-25"></i>
          <small>Click <strong>All formats</strong> or <strong>Sigma only</strong> to start scanning rules.</small>
        </div>

      </div>
    </div>
  </div>

</div>
`,
};
