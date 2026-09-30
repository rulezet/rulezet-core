/**
 * importedTagsExtractor.js — "Imported Tags" tab of the admin Bulk Field Parser.
 *
 * Re-parses existing rules and attaches the author's own tags written in the
 * rule (YARA `rule X : a b` + meta tags, Sigma `tags:`, Kunai `meta.tags`…)
 * as public "Imported" tags — GitHub issue #70. Three parts: pick the
 * formats to scan, try the extraction live on a pasted rule, launch the
 * `import_native_tags` background job (BulkImportRunner shows its progress).
 */
import BulkImportRunner from '/static/js/tags/manage/BulkImportRunner.js'

const { ref, computed, watch, onMounted } = Vue;

const EXAMPLES = {
    yara: `rule ExampleRule : malware ransomware windows
{
    meta:
        author = "Example"
        tags = "apt malware"
    condition:
        true
}`,
    sigma: `title: Example
tags:
    - attack.execution
    - attack.t1059
logsource:
    category: process_creation
detection:
    selection:
        Image|endswith: '\\\\cmd.exe'
    condition: selection`,
    kunai: `name: example
meta:
  tags:
  - os:linux
  - persistence
condition: true`,
};

export default {
    name: 'ImportedTagsExtractor',
    delimiters: ['[[', ']]'],
    components: { BulkImportRunner },
    props: {
        csrfToken: { type: String, required: true },
        // [{ format, where, rules }] — from the page (FORMAT_TAG_SOURCES + counts)
        formats:   { type: Array, required: true },
    },
    emits: ['notify'],
    setup(props, { emit }) {
        // ── Formats to scan ──────────────────────────────────────────────
        const selected = ref(props.formats.filter(f => f.format === 'yara').map(f => f.format));
        const allSelected = computed(() => selected.value.length === props.formats.length);
        function toggleAll() {
            selected.value = allSelected.value ? [] : props.formats.map(f => f.format);
        }
        const selectedRuleCount = computed(() =>
            props.formats.filter(f => selected.value.includes(f.format)).reduce((n, f) => n + f.rules, 0));

        // ── Live preview ─────────────────────────────────────────────────
        const previewFormat  = ref('yara');
        const previewContent = ref(EXAMPLES.yara);
        const previewTags    = ref([]);
        const previewError   = ref('');
        const previewLoading = ref(false);
        let timer = null;

        async function runPreview() {
            previewLoading.value = true;
            previewError.value = '';
            try {
                const res = await fetch('/account/admin/bulk_parse_fields/imported_tags/preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ format: previewFormat.value, content: previewContent.value }),
                });
                const data = await res.json();
                if (data.success) previewTags.value = data.tags;
                else { previewTags.value = []; previewError.value = data.message || 'Preview failed'; }
            } catch (e) {
                previewError.value = 'Network error';
            } finally {
                previewLoading.value = false;
            }
        }
        function schedulePreview() {
            clearTimeout(timer);
            timer = setTimeout(runPreview, 350);
        }
        watch(previewContent, schedulePreview);
        watch(previewFormat, (fmt) => {
            if (EXAMPLES[fmt] && (!previewContent.value.trim() || Object.values(EXAMPLES).includes(previewContent.value))) {
                previewContent.value = EXAMPLES[fmt];
            } else {
                schedulePreview();
            }
        });
        const previewWhere = computed(() => (props.formats.find(f => f.format === previewFormat.value) || {}).where);

        // ── Launch — job uuid kept in ?itjob= so a reload reconnects ─────
        const resumeJobUuid = ref(new URLSearchParams(window.location.search).get('itjob'));
        const jobRunning = ref(false);
        function onJobUuidChanged(uuid) {
            const url = new URL(window.location.href);
            if (uuid) url.searchParams.set('itjob', uuid);
            else url.searchParams.delete('itjob');
            history.replaceState(null, '', url);
        }
        const runnerPayload = computed(() => ({ formats: selected.value, rule_ids: 'ALL' }));
        const runnerDescription = computed(() => {
            if (!selected.value.length) return 'Select at least one format above.';
            return `Scan ${selectedRuleCount.value.toLocaleString()} rule(s) (${selected.value.join(', ')}) and attach ` +
                   `their native tags as public Imported tags owned by you. Tags a rule already has are skipped — safe to re-run.`;
        });

        onMounted(runPreview);

        return {
            selected, allSelected, toggleAll, selectedRuleCount,
            previewFormat, previewContent, previewTags, previewError, previewLoading, previewWhere,
            resumeJobUuid, jobRunning, onJobUuidChanged, runnerPayload, runnerDescription,
            notify: (msg, cls) => emit('notify', msg, cls),
        };
    },
    template: `
<div class="row g-4">

  <!-- ══ Formats ══════════════════════════════════════════════════════════ -->
  <div class="col-xl-6">
    <div class="card border-0 shadow-sm rounded-4 h-100">
      <div class="card-body p-4">
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div class="d-flex align-items-center gap-2">
            <div style="width:3px;height:14px;background:#0d6efd;border-radius:2px;flex-shrink:0;"></div>
            <span class="fw-bold" style="font-size:.75rem;text-transform:uppercase;letter-spacing:.07em;color:var(--subtle-text-color);">
              <i class="fa-solid fa-user-tag me-1"></i>Formats to scan
            </span>
          </div>
          <button @click="toggleAll" :disabled="jobRunning" class="btn btn-xs btn-outline-primary" style="font-size:.72rem;padding:2px 10px;">
            [[ allSelected ? 'Unselect all' : 'Select all' ]]
          </button>
        </div>
        <p class="text-muted small mb-3">
          Tags written by the rule author are kept apart from Rulezet's taxonomy and galaxy tags:
          they are attached as <strong>Imported</strong> tags — public, owned by you, lower-cased and
          deduplicated. New rules get theirs automatically at import; this job catches up existing rules.
        </p>
        <div class="d-flex flex-column gap-2">
          <label v-for="f in formats" :key="f.format"
                 class="rounded-3 border px-3 py-2 d-flex align-items-center gap-3 mb-0"
                 :style="{ cursor: jobRunning ? 'default' : 'pointer',
                           borderColor: selected.includes(f.format) ? '#0d6efd55' : 'var(--border-color)',
                           background: selected.includes(f.format) ? '#0d6efd08' : 'var(--light-bg-color)' }">
            <input type="checkbox" class="form-check-input mt-0" :value="f.format" v-model="selected" :disabled="jobRunning">
            <div class="flex-grow-1" style="min-width:0;">
              <div class="fw-semibold" style="font-size:.85rem;">[[ f.format ]]</div>
              <div class="text-truncate" style="font-size:.74rem;color:var(--subtle-text-color);">[[ f.where ]]</div>
            </div>
            <span class="badge rounded-pill" style="background:var(--card-bg-color);color:var(--subtle-text-color);border:1px solid var(--border-color);font-size:.7rem;">
              [[ f.rules.toLocaleString() ]] rules
            </span>
          </label>
        </div>
      </div>
    </div>
  </div>

  <!-- ══ Live preview ═════════════════════════════════════════════════════ -->
  <div class="col-xl-6">
    <div class="card border-0 shadow-sm rounded-4 h-100">
      <div class="card-body p-4 d-flex flex-column">
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div class="d-flex align-items-center gap-2">
            <div style="width:3px;height:14px;background:#0d6efd;border-radius:2px;flex-shrink:0;"></div>
            <span class="fw-bold" style="font-size:.75rem;text-transform:uppercase;letter-spacing:.07em;color:var(--subtle-text-color);">
              <i class="fa-solid fa-flask me-1"></i>Try the extraction
            </span>
          </div>
          <select v-model="previewFormat" class="form-select form-select-sm" style="width:auto;font-size:.8rem;">
            <option v-for="f in formats" :key="f.format" :value="f.format">[[ f.format ]]</option>
          </select>
        </div>
        <p class="text-muted small mb-2">
          Paste a rule — the exact same parser as the job. Read from: <strong>[[ previewWhere ]]</strong>.
        </p>
        <textarea v-model="previewContent" class="form-control mb-3 flex-grow-1" rows="11" spellcheck="false"
                  style="font-family:var(--font-mono, monospace);font-size:.78rem;background:var(--light-bg-color);color:var(--text-color);border-color:var(--border-color);"></textarea>
        <div class="rounded-3 border p-3" style="background:var(--light-bg-color);min-height:3rem;">
          <div v-if="previewLoading" class="d-flex align-items-center gap-2">
            <div class="spinner-border spinner-border-sm text-primary"></div>
            <small class="text-muted">Extracting…</small>
          </div>
          <div v-else-if="previewError" class="small text-danger"><i class="fa-solid fa-triangle-exclamation me-1"></i>[[ previewError ]]</div>
          <div v-else-if="!previewTags.length" class="small fst-italic" style="color:var(--subtle-text-color);">
            <i class="fa-solid fa-tags me-1 opacity-50"></i>No tags found in this rule.
          </div>
          <div v-else class="d-flex flex-wrap gap-2">
            <span v-for="t in previewTags" :key="t" class="badge rounded-pill px-3 py-2"
                  style="background:#fd7e14;color:#fff;font-size:.75rem;font-weight:600;">
              <i class="fa-solid fa-user-tag me-1" style="opacity:.85;"></i>[[ t ]]
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ══ Launch ═══════════════════════════════════════════════════════════ -->
  <div class="col-12">
    <bulk-import-runner
        :csrf-token="csrfToken"
        endpoint="/account/admin/bulk_parse_fields/trigger_imported_tags"
        title=""
        :show-title="false"
        :description="runnerDescription"
        icon="fa-solid fa-user-tag"
        accent-color="#0d6efd"
        button-label="Launch"
        item-noun="rule"
        :payload="runnerPayload"
        :disabled="!selected.length"
        :show-idle-hint="false"
        :resume-job-uuid="resumeJobUuid"
        @job-uuid-changed="onJobUuidChanged"
        @job-running-changed="jobRunning = $event"
        @notify="notify">
    </bulk-import-runner>
  </div>

</div>
`,
};
