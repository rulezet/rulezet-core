/**
 * ruleMetadataExtractor.js — "References & metadata" tab of the admin Bulk Field Parser.
 *
 * Every rule keeps the references and other metadata written in its own text (rule_references /
 * extra_metadata, app/features/rule/rule_metadata_core.py) — new and edited rules automatically.
 * This tab catches up existing rules: pick the formats, try the extraction live on a pasted
 * rule, launch the `reparse_rule_metadata` background job (BulkImportRunner shows its progress).
 */
import BulkImportRunner from '/static/js/tags/manage/BulkImportRunner.js'

const { ref, computed, watch, onMounted } = Vue;

const EXAMPLES = {
    yara: `rule Example_Downloader
{
    meta:
        author = "Example"
        description = "Small downloader"
        reference = "https://example.org/report-1"
        reference = "https://example.org/report-2"
        date = "2024-05-02"
        hash = "44d88612fea8a8f36de82e1278abb02f"
        tlp = "clear"
        score = 80
    strings:
        $a = "URLDownloadToFileA"
    condition:
        $a
}`,
    sigma: `title: Example
status: test
references:
    - https://example.org/blog/technique
date: 2024/01/10
modified: 2024/03/01
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        Image|endswith: '\\\\cmd.exe'
    condition: selection
falsepositives:
    - Administrators
level: medium`,
    suricata: `alert http any any -> any any (msg:"Example"; content:"evil"; reference:url,www.example.org/advisory; reference:cve,2021-44228; classtype:trojan-activity; sid:1000001; rev:3; metadata: created_at 2024_01_01, signature_severity Major;)`,
};

export default {
    name: 'RuleMetadataExtractor',
    delimiters: ['[[', ']]'],
    components: { BulkImportRunner },
    props: {
        csrfToken: { type: String, required: true },
        // [{ format, where, rules }] — every format with rules (rule_metadata_core)
        formats:   { type: Array, required: true },
    },
    emits: ['notify'],
    setup(props, { emit }) {
        // ── Formats to scan (all by default) ─────────────────────────────
        const selected = ref(props.formats.map(f => f.format));
        const allSelected = computed(() => selected.value.length === props.formats.length);
        function toggleAll() {
            selected.value = allSelected.value ? [] : props.formats.map(f => f.format);
        }
        const selectedRuleCount = computed(() =>
            props.formats.filter(f => selected.value.includes(f.format)).reduce((n, f) => n + f.rules, 0));

        // ── Live preview ─────────────────────────────────────────────────
        const previewFormats = computed(() => {
            const names = props.formats.map(f => f.format);
            return [...new Set(['yara', 'sigma', 'suricata', ...names])];
        });
        const previewFormat  = ref('yara');
        const previewContent = ref(EXAMPLES.yara);
        const preview        = ref({ references: [], extra: [] });
        const previewError   = ref('');
        const previewLoading = ref(false);
        let timer = null;

        async function runPreview() {
            previewLoading.value = true;
            previewError.value = '';
            try {
                const res = await fetch('/account/admin/bulk_parse_fields/rule_metadata/preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ format: previewFormat.value, content: previewContent.value }),
                });
                const data = await res.json();
                if (data.success) preview.value = { references: data.references, extra: data.extra };
                else { preview.value = { references: [], extra: [] }; previewError.value = data.message || 'Preview failed'; }
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
        const previewWhere = computed(() => (props.formats.find(f => f.format === previewFormat.value) || {}).where
            || 'well-known "# key: value" header comments');
        const isUrl = v => /^https?:\/\//i.test(v);

        // ── Launch — job uuid kept in ?rmjob= so a reload reconnects ─────
        const resumeJobUuid = ref(new URLSearchParams(window.location.search).get('rmjob'));
        const jobRunning = ref(false);
        function onJobUuidChanged(uuid) {
            const url = new URL(window.location.href);
            if (uuid) url.searchParams.set('rmjob', uuid);
            else url.searchParams.delete('rmjob');
            history.replaceState(null, '', url);
        }
        const runnerPayload = computed(() => ({ formats: allSelected.value ? 'ALL' : selected.value, rule_ids: 'ALL' }));
        const runnerDescription = computed(() => {
            if (!selected.value.length) return 'Select at least one format above.';
            return `Read the references and other metadata of ${selectedRuleCount.value.toLocaleString()} rule(s) ` +
                   `again from their text. Only those two fields are written — never the rule itself — so it is safe to re-run.`;
        });

        onMounted(runPreview);

        return {
            selected, allSelected, toggleAll, selectedRuleCount,
            previewFormats, previewFormat, previewContent, preview, previewError, previewLoading, previewWhere, isUrl,
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
          <span class="rmx-title"><i class="fa-solid fa-book-bookmark me-1"></i>Formats to scan</span>
          <button @click="toggleAll" :disabled="jobRunning" class="btn btn-sm btn-outline-primary rmx-small-btn">
            [[ allSelected ? 'Unselect all' : 'Select all' ]]
          </button>
        </div>
        <p class="text-muted small mb-3">
          The references of a rule and every other metadata it carries (dates, hashes, status, level, TLP…)
          are read from its own text and shown on the rule page. New and edited rules get them automatically;
          this job catches up existing rules.
        </p>
        <div class="d-flex flex-column gap-2 rmx-formats">
          <label v-for="f in formats" :key="f.format" class="rmx-format" :class="{ 'is-on': selected.includes(f.format), 'is-locked': jobRunning }">
            <input type="checkbox" class="form-check-input mt-0" :value="f.format" v-model="selected" :disabled="jobRunning">
            <div class="flex-grow-1 rmx-format__main">
              <div class="fw-semibold rmx-format__name">[[ f.format ]]</div>
              <div class="text-truncate rmx-format__where">[[ f.where ]]</div>
            </div>
            <span class="badge rounded-pill rmx-count">[[ f.rules.toLocaleString() ]] rules</span>
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
          <span class="rmx-title"><i class="fa-solid fa-flask me-1"></i>Try the extraction</span>
          <select v-model="previewFormat" class="form-select form-select-sm rmx-select">
            <option v-for="f in previewFormats" :key="f" :value="f">[[ f ]]</option>
          </select>
        </div>
        <p class="text-muted small mb-2">
          Paste a rule — the exact same parser as every rule gets. Read from: <strong>[[ previewWhere ]]</strong>.
        </p>
        <textarea v-model="previewContent" class="form-control mb-3 flex-grow-1 rmx-textarea" rows="12" spellcheck="false"></textarea>
        <div class="rounded-3 border p-3 rmx-result">
          <div v-if="previewLoading" class="d-flex align-items-center gap-2">
            <div class="spinner-border spinner-border-sm text-primary"></div>
            <small class="text-muted">Extracting…</small>
          </div>
          <div v-else-if="previewError" class="small text-danger"><i class="fa-solid fa-triangle-exclamation me-1"></i>[[ previewError ]]</div>
          <div v-else-if="!preview.references.length && !preview.extra.length" class="small fst-italic text-muted">
            Nothing found in this rule.
          </div>
          <template v-else>
            <div v-if="preview.references.length" class="rule-meta-block">
              <div class="rule-meta-head"><i class="fa-solid fa-book-bookmark"></i>References <span>[[ preview.references.length ]]</span></div>
              <ul class="rule-refs">
                <li v-for="r in preview.references" :key="r">
                  <i class="fa-solid" :class="isUrl(r) ? 'fa-arrow-up-right-from-square' : 'fa-quote-left'"></i>
                  <a v-if="isUrl(r)" :href="r" target="_blank" rel="noopener noreferrer">[[ r ]]</a>
                  <span v-else>[[ r ]]</span>
                </li>
              </ul>
            </div>
            <div v-if="preview.extra.length" class="rule-meta-block">
              <div class="rule-meta-head"><i class="fa-solid fa-circle-info"></i>Other metadata <span>[[ preview.extra.length ]]</span></div>
              <div class="rule-meta-grid">
                <div v-for="f in preview.extra" :key="f.key" class="rule-meta-cell">
                  <div class="rule-meta-cell__label"><i class="fa-solid" :class="f.icon"></i>[[ f.label ]]</div>
                  <div v-for="v in f.values" :key="v" class="rule-meta-cell__value" :class="{ 'is-hash': f.is_hash }">[[ v ]]</div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>

  <!-- ══ Launch ═══════════════════════════════════════════════════════════ -->
  <div class="col-12">
    <bulk-import-runner
        :csrf-token="csrfToken"
        endpoint="/account/admin/bulk_parse_fields/trigger_rule_metadata"
        title=""
        :show-title="false"
        :description="runnerDescription"
        icon="fa-solid fa-book-bookmark"
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
