/**
 * ValidationRunner.js
 * Tag Manager / Admin component — runs rulezet-validation's false-positive
 * gate: pulls this instance's rules, scans them against a known-clean
 * binary baseline, and quarantines anything that fires.
 *
 * Launches 'rule_validation_run' (job_handlers.py), streams its log like a
 * terminal while it runs, then renders the quarantined-rule result.
 *
 * Since rulezet-validation 6eac375, every quarantine entry also carries a
 * `proposed_tag` — a false-positive risk level (low/medium/high/cannot-be-
 * judged) derived purely from how many known-clean binaries the rule fired
 * on, in the exact vocabulary of the MISP "false-positive" taxonomy already
 * imported here as real tags — plus an `upstream_tag` when the rule already
 * claimed a risk level of its own, so a reviewer can see at a glance where
 * a rule's own claim disagrees with what was actually observed.
 *
 * The quarantined-rule result is browsed with the same RuleList used
 * everywhere else in the app (card/table toggle, search, sort, its own
 * bulk-selection toolbar) rather than a bespoke table — pointed at a
 * dedicated fetch-url (tags.py's /admin/validation/rules_data_table) that
 * embeds each rule's risk assessment under `validation_risk`, an opt-in
 * RuleList extension (see ruleList.js's showValidationRisk prop, mirroring
 * the Rule Tester's showTestResults). "Accept proposed risk tag" and
 * "Apply a different tag…" are both bulk actions on that same toolbar —
 * nothing is ever applied automatically.
 */

import JobTracker  from '/static/js/jobs/JobTracker.js';
import AnsiTerminal from '/static/js/components/ansi-terminal.js';
import RuleList     from '/static/js/rule/ruleList.js';
import TagsDisplaysList          from '/static/js/tags/tagsDisplaysList.js';
import VulnerabilityDisplaysList from '/static/js/vulnerability/vulnerabilityDisplayList.js';
import TagInput     from '/static/js/tags/tagInput.js';

const { ref, computed, watch, onMounted, onUnmounted } = Vue;

// false-positive:risk=<level>  ->  <level>
const RISK_TAG_RE = /^false-positive:risk=(.+)$/;

// Fallback only — real color/description come from the taxonomy tag itself
// once loaded (loadRiskTags below); used for the brief window before that
// fetch resolves, and if the taxonomy somehow isn't imported on this instance.
const RISK_META = {
    high:               { color: '#FF2B2B', label: 'High' },
    medium:             { color: '#FFFF00', label: 'Medium' },
    low:                { color: '#33FF00', label: 'Low' },
    'cannot-be-judged': { color: '#FFC000', label: 'Cannot be judged' },
};
const RISK_ORDER = ['high', 'medium', 'low', 'cannot-be-judged'];

function riskLevel(tagString) {
    if (!tagString) return null;
    const m = RISK_TAG_RE.exec(tagString);
    return m ? m[1] : null;
}

// Readable text color against a taxonomy swatch — several of these (yellow,
// green) are far too light for white text.
function contrastColor(hex) {
    if (!hex) return '#000';
    const h = hex.replace('#', '');
    const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
    return (r * 299 + g * 587 + b * 114) / 1000 > 150 ? '#1a1a1a' : '#fff';
}

export default {
    name: 'ValidationRunner',
    delimiters: ['[[', ']]'],
    components: {
        JobTracker, AnsiTerminal,
        'rule-list':                   RuleList,
        'tags-displays-list':          TagsDisplaysList,
        'vulnerability-displays-list': VulnerabilityDisplaysList,
        'tag-input':                   TagInput,
    },
    props: {
        csrfToken:                  { type: String,             required: true },
        currentUserId:              { type: [Number, String],   default: null },
        currentUserIsAdmin:         { type: Boolean,            default: false },
        currentUserIsAuthenticated: { type: Boolean,            default: false },
        // Which of the page's two dr-nav panels is open — 'validation'
        // (launch + live result) or 'history' (past runs list). Owned by
        // the page (see validation.html), not here, so the tab bar itself
        // stays plain page markup like every other dr-nav on the site.
        activeTab:                  { type: String,             default: 'validation' },
    },
    emits: ['notify', 'update:active-tab'],
    setup(props, { emit }) {
        // ── Launch options ──────────────────────────────────────────────────
        const fullSync = ref(false);
        const limit    = ref(null);

        // ── Validation job state ────────────────────────────────────────────
        const running     = ref(false);
        const jobUuid      = ref(null);
        const jobStatus    = ref('idle');   // idle | pending | running | done | failed | cancelled
        const allLogs      = ref([]);
        const lastLogId    = ref(0);
        const quarantined  = ref([]);
        let   pollTimer    = null;

        const isDone = computed(() => ['done', 'failed', 'cancelled'].includes(jobStatus.value));

        // Which run's detail is open rides along in the URL (?job=<uuid>) —
        // reloading the page (or sharing the link) reopens the same run
        // instead of dropping back to the launch/history overview. RuleList's
        // own risk_level/binary/view/etc. sync onto the same query string
        // independently (see ruleList.js's syncToUrl) — nothing extra needed
        // here for those, only for which run is currently open.
        watch(jobUuid, (uuid) => {
            const p = new URLSearchParams(window.location.search);
            if (uuid) p.set('job', uuid); else p.delete('job');
            const qs = p.toString();
            window.history.replaceState(null, '', qs ? `?${qs}` : window.location.pathname);
        });

        // ansi-terminal wants {ts, level, msg} — the job log API returns
        // {id, level, event, message, created_at}.
        const terminalEntries = computed(() =>
            allLogs.value.map(l => ({ ts: l.created_at, level: l.level, msg: l.message }))
        );
        function clearLogs() { allLogs.value = []; }

        // Auto-collapse the live log once a run finishes — still one click
        // away, but a completed run shouldn't leave a wall of scrollback
        // sitting above its own result.
        const logsCollapsed = ref(false);
        watch(isDone, (done) => { if (done) logsCollapsed.value = true; });

        // ── Known-clean baseline — the actual corpus a run's verdicts are
        //    measured against. Collapsed by default (it's routinely 300+
        //    files) and fetched lazily, the first time it's opened.
        const baselineOpen     = ref(false);
        const baselineLoading  = ref(false);
        const baselineLoaded   = ref(false);
        const baselineFiles    = ref([]);
        const baselineExcluded = ref([]);
        const baselineDirs     = ref([]);

        async function toggleBaseline() {
            baselineOpen.value = !baselineOpen.value;
            if (!baselineOpen.value || baselineLoaded.value) return;
            baselineLoading.value = true;
            try {
                const res  = await fetch('/tags/admin/validation/baseline_files');
                const data = await res.json();
                if (res.ok) {
                    baselineFiles.value    = data.files || [];
                    baselineExcluded.value = data.excluded_files || [];
                    baselineDirs.value     = data.dirs || [];
                    baselineLoaded.value   = true;
                }
            } catch (e) {
                emit('notify', { message: 'Failed to load the baseline: ' + e, level: 'error' });
            } finally {
                baselineLoading.value = false;
            }
        }

        // ── Risk taxonomy tags (false-positive:risk="...") ─────────────────
        // Loaded by search rather than the full tag catalog (which runs into
        // the thousands after MISP taxonomy/galaxy imports) — only these 4
        // rows are needed to color/apply a proposal.
        const riskTags = ref([]);   // [{id, name, color, ...}]
        async function loadRiskTags() {
            if (riskTags.value.length) return;
            try {
                const res  = await fetch('/tags/get_all_tags?search=' + encodeURIComponent('false-positive:risk'));
                const data = await res.json();
                if (res.ok) riskTags.value = data.tags || [];
            } catch (e) { console.error('[ValidationRunner] loadRiskTags error:', e); }
        }
        function riskTagRow(level) {
            return riskTags.value.find(t => t.name === `false-positive:risk="${level}"`) || null;
        }
        function riskMeta(level) {
            const row = riskTagRow(level);
            const fallback = RISK_META[level] || { color: '#adb5bd', label: level || 'Unknown' };
            return {
                id:    row ? row.id : null,
                color: row ? row.color : fallback.color,
                label: row ? row.name.replace(/^false-positive:risk="(.+)"$/, '$1') : fallback.label,
            };
        }

        // ── History — past runs, so the page isn't empty before the first
        //    click, and a previous run's result can be revisited without
        //    re-running it. ───────────────────────────────────────────────
        const history        = ref([]);
        const historyLoading = ref(false);

        const STATUS_COLOR = { pending: 'secondary', running: 'primary', done: 'success', failed: 'danger', cancelled: 'warning', paused: 'info' };
        const STATUS_ICON  = { pending: 'fa-clock', running: 'fa-spinner fa-spin', done: 'fa-check-circle', failed: 'fa-times-circle', cancelled: 'fa-ban', paused: 'fa-pause-circle' };

        async function loadHistory() {
            historyLoading.value = true;
            try {
                const res  = await fetch('/jobs/get_jobs?job_type=rule_validation_run&per_page=8&page=1');
                const data = await res.json();
                if (res.ok) history.value = data.jobs || [];
            } catch (e) {
                console.error('[ValidationRunner] loadHistory error:', e);
            } finally {
                historyLoading.value = false;
            }
        }

        // Load a past run's result into the same view a fresh run ends up
        // in — reuses every bit of quarantine-table/accept-tag logic below,
        // rather than a second, separate "history detail" view.
        async function viewHistoryRun(h) {
            if (running.value) return;
            emit('update:active-tab', 'validation');
            jobUuid.value          = h.uuid;
            jobStatus.value        = h.status;
            quarantined.value      = [];
            pendingCustomTagIds.value = [];
            allLogs.value          = [];
            lastLogId.value        = 0;
            if (h.status === 'done' || h.status === 'failed' || h.status === 'cancelled') {
                await loadResult();
            }
        }

        // Leave a run's detail (fresh or from history) back to the
        // launch/history overview, without forgetting the run itself —
        // it's still sitting in history, refreshed in case anything changed.
        function goBackToOverview() {
            jobUuid.value       = null;
            jobStatus.value     = 'idle';
            quarantined.value   = [];
            pendingCustomTagIds.value = [];
            allLogs.value       = [];
            lastLogId.value     = 0;
            loadHistory();
        }

        onMounted(() => { loadHistory(); restoreFromUrl(); });

        async function deleteHistoryRun(h) {
            if (h.status === 'pending' || h.status === 'running') return;
            if (!confirm(`Delete this validation run (${h.created_at})? This cannot be undone.`)) return;
            try {
                const res  = await fetch(`/jobs/delete/${h.uuid}`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': props.csrfToken },
                });
                const data = await res.json();
                if (res.ok) {
                    history.value = history.value.filter(x => x.uuid !== h.uuid);
                    if (jobUuid.value === h.uuid) {
                        jobUuid.value = null;
                        jobStatus.value = 'idle';
                        quarantined.value = [];
                    }
                    emit('notify', { message: 'Run deleted.', level: 'success' });
                } else {
                    emit('notify', { message: data.message || 'Failed to delete run', level: 'error' });
                }
            } catch (e) {
                emit('notify', { message: 'Network error: ' + e, level: 'error' });
            }
        }

        // ── Fetch the parsed result once the job is done ───────────────────
        async function loadResult() {
            const res = await fetch(`/jobs/api/${jobUuid.value}`);
            const data = await res.json();
            if (res.ok) {
                quarantined.value = (data.meta && data.meta.result && data.meta.result.quarantined) || [];
                if (quarantined.value.length) loadRiskTags();
            }
        }

        async function pollLogs() {
            if (!jobUuid.value) return;
            try {
                const sRes  = await fetch(`/jobs/status/${jobUuid.value}`);
                const sData = await sRes.json();
                jobStatus.value = sData.status || 'running';

                const lRes  = await fetch(`/jobs/logs/${jobUuid.value}?since_id=${lastLogId.value}`);
                const lines = await lRes.json();
                if (lines.length) {
                    allLogs.value.push(...lines);
                    lastLogId.value = lines[lines.length - 1].id;
                }

                if (isDone.value) {
                    clearInterval(pollTimer);
                    pollTimer = null;
                    running.value = false;
                    await loadResult();
                    loadHistory();
                    if (jobStatus.value === 'done') {
                        emit('notify', { message: `Validation done — ${quarantined.value.length} rule(s) quarantined.`, level: 'success' });
                    } else {
                        emit('notify', { message: 'Validation run did not complete.', level: 'error' });
                    }
                }
            } catch (e) {
                console.error('[ValidationRunner] poll error:', e);
            }
        }

        // Reopen whatever run ?job=<uuid> in the URL points to — a fresh
        // run's own reload, a shared link, or a history entry that was
        // opened before the page got reloaded. A dead/foreign uuid (job
        // deleted, or belongs to someone else) just drops the param and
        // falls back to the launch/history overview instead of erroring.
        async function restoreFromUrl() {
            const jobParam = new URLSearchParams(window.location.search).get('job');
            if (!jobParam) return;
            try {
                const res = await fetch(`/jobs/api/${jobParam}`);
                if (!res.ok) { jobUuid.value = null; return; }
                emit('update:active-tab', 'validation');
                const data = await res.json();
                jobUuid.value   = data.uuid;
                jobStatus.value = data.status;
                if (isDone.value) {
                    await loadResult();
                } else {
                    running.value = true;
                    pollTimer = setInterval(pollLogs, 2000);
                    pollLogs();
                }
            } catch (e) {
                console.error('[ValidationRunner] restoreFromUrl error:', e);
            }
        }

        async function startRun() {
            if (running.value) return;

            running.value     = true;
            allLogs.value      = [];
            lastLogId.value    = 0;
            jobUuid.value      = null;
            jobStatus.value    = 'pending';
            quarantined.value  = [];
            logsCollapsed.value = false;
            pendingCustomTagIds.value = [];

            try {
                const res = await fetch('/tags/admin/validation/launch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ full: fullSync.value, limit: limit.value || null }),
                });
                const data = await res.json();
                if (!data.success) {
                    emit('notify', { message: data.message || 'Failed to start validation run', level: 'error' });
                    running.value = false;
                    return;
                }
                jobUuid.value   = data.job.uuid;
                jobStatus.value = 'running';
                pollTimer = setInterval(pollLogs, 2000);
                pollLogs();
            } catch (e) {
                emit('notify', { message: 'Network error: ' + e, level: 'error' });
                running.value = false;
            }
        }

        onUnmounted(() => {
            if (pollTimer) clearInterval(pollTimer);
        });

        // ── Quarantined-rule browser — RuleList pointed at a dedicated
        //    fetch-url (see tags.py) that embeds each rule's risk
        //    assessment. Re-keyed on jobUuid whenever a fresh run finishes
        //    or a history entry is opened. The Risk-level/Binary filter UI
        //    itself now lives inside RuleList (showValidationFilters) —
        //    this page only supplies the taxonomy + the full-run binary
        //    list, both of which RuleList has no way to know on its own.
        const quarantineListRef = ref(null);
        const quarantineFetchUrl = computed(() =>
            jobUuid.value ? `/tags/admin/validation/rules_data_table?job_uuid=${jobUuid.value}` : ''
        );

        // Every distinct binary name mentioned across this run's results —
        // a picklist grounded in what's actually there, not blind free
        // text, and spanning the WHOLE run rather than RuleList's current
        // page (quarantined.value carries matched_files for every rule).
        const allBinaryOptions = computed(() => {
            const names = new Set();
            for (const q of quarantined.value) {
                for (const m of q.matched_files || []) if (m.file) names.add(m.file);
            }
            return [...names].sort();
        });

        // MISP false-positive taxonomy, in the shape RuleList's filter panel
        // expects — this page owns the taxonomy (labels/colors via
        // riskMeta()), RuleList just renders whatever it's handed.
        const validationRiskLevels = computed(() => RISK_ORDER.map(level => ({ level, ...riskMeta(level) })));

        const riskBulkActions = [
            { key: 'accept_proposed', label: 'Accept proposed risk tag', icon: 'fa-tag' },
            { key: 'custom_tag',      label: 'Apply a different tag…',   icon: 'fa-tags' },
        ];

        const tagJobUuid = ref(null);
        const tagging    = ref(false);

        async function launchTagJob(ruleIds, tagIds, labelTags) {
            const res = await fetch('/jobs/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                body: JSON.stringify({
                    job_type: 'bulk_add_tag_to_rules',
                    payload:  { tag_ids: tagIds, filters: { rule_ids: ruleIds } },
                    label:    `Tag ${ruleIds.length} quarantined rule(s) with ${labelTags}`,
                }),
            });
            const data = await res.json();
            if (res.ok) {
                tagJobUuid.value = data.job.uuid;
                return true;
            }
            emit('notify', { message: data.error || 'Failed to launch bulk tag job', level: 'error' });
            return false;
        }

        // "Accept proposed risk tag" — resolves each selected rule's own
        // proposed_tag (from the flat quarantine result already loaded, see
        // loadResult()/viewHistoryRun()) and groups by distinct tag, since a
        // mixed selection can span several risk levels at once.
        async function acceptProposedForRules(ruleIds) {
            await loadRiskTags();
            const byLevel = {};
            for (const rid of ruleIds) {
                const q = quarantined.value.find(x => x.rule_id === rid);
                const level = riskLevel(q && q.proposed_tag);
                if (!level) continue;
                (byLevel[level] = byLevel[level] || []).push(rid);
            }
            const levels = Object.keys(byLevel);
            if (!levels.length) {
                emit('notify', { message: 'None of the selected rules have a proposed risk tag.', level: 'error' });
                return;
            }
            for (const level of levels) {
                const tag = riskTagRow(level);
                if (!tag) continue;
                await launchTagJob(byLevel[level], [tag.id], tag.name);
            }
            emit('notify', {
                message: `Queued tagging for ${ruleIds.length} rule(s) across ${levels.length} risk level(s).`,
                level: 'success',
            });
        }

        // Every quarantined rule that both exists locally and has a proposed
        // tag — the full set "Accept all" targets, independent of whatever
        // page of the rule browser is currently showing or selected.
        const acceptableRuleIds = computed(() =>
            quarantined.value.filter(q => q.rule_id && riskLevel(q.proposed_tag)).map(q => q.rule_id)
        );

        function acceptAllProposed() {
            const ids = acceptableRuleIds.value;
            if (!ids.length) return;
            if (!confirm(`Accept the proposed risk tag for all ${ids.length} quarantined rule(s)?`)) return;
            acceptProposedForRules(ids);
        }

        // ── "Apply a different tag…" — a small modal (see .bt-modal-* in
        //    validation.html) instead of a panel sitting at the bottom of the
        //    page. Tag search reuses TagInput (server-side search + debounce,
        //    already fixed for the "thousands of tags after MISP imports"
        //    slowdown — see its own comments) instead of hand-rolling another
        //    picker, and a "quick pick" row shortcuts straight to the same 4
        //    risk tags the filter/proposals use, so applying one doesn't
        //    require typing+searching at all. ──────────────────────────────
        const pendingCustomTagIds = ref([]);
        const selectedTags        = ref([]);   // full tag objects — TagInput's own v-model shape
        const showAllSelectedTags = ref(false); // false = capped preview (first 5), true = everything

        function isQuickTagSelected(level) {
            const tag = riskTagRow(level);
            return !!tag && selectedTags.value.some(t => t.id === tag.id);
        }
        function toggleQuickTag(level) {
            const tag = riskTagRow(level);
            if (!tag) return;
            selectedTags.value = isQuickTagSelected(level)
                ? selectedTags.value.filter(t => t.id !== tag.id)
                : [...selectedTags.value, tag];
        }
        function removeSelectedTag(id) {
            selectedTags.value = selectedTags.value.filter(t => t.id !== id);
        }
        function closeCustomTagModal() {
            pendingCustomTagIds.value = [];
            selectedTags.value        = [];
            showAllSelectedTags.value = false;
        }

        async function applyCustomTags() {
            if (tagging.value || pendingCustomTagIds.value.length === 0 || selectedTags.value.length === 0) return;
            tagging.value = true;
            try {
                const ok = await launchTagJob(
                    pendingCustomTagIds.value,
                    selectedTags.value.map(t => t.id),
                    selectedTags.value.map(t => t.name).join(', ')
                );
                if (ok) closeCustomTagModal();
            } finally {
                tagging.value = false;
            }
        }

        // RuleList's bulk toolbar sends the literal string 'ALL' (not an id
        // array) once "select all N pages" is used — it never had every id
        // loaded client-side to send. Resolve it here by re-hitting the data
        // endpoint directly. Built from the CURRENT URL (not the static
        // job_uuid-only quarantineFetchUrl computed) because RuleList owns
        // its risk_level/binary/search/sort filter state internally and
        // syncs all of it onto the address bar — that's the only place this
        // component can see "what's actually filtered right now", and it's
        // exactly what "select all pages" is supposed to mean (every row
        // matching the current filters, not the whole run).
        //
        // get_rules_data_table() caps per_page at 100 server-side no matter
        // what's requested (rule_core.py: `max(1, min(100, per_page))`) — a
        // single oversized request silently comes back truncated to page 1
        // of 100, not everything. So this pages through every result instead
        // of trusting one big per_page to do it in one shot.
        const resolvingBulkIds = ref(false);
        async function resolveBulkIds(ids) {
            if (ids !== 'ALL') return ids;
            if (!jobUuid.value) return [];
            const p = new URLSearchParams(window.location.search);
            p.set('job_uuid', jobUuid.value);
            p.set('per_page', '100');
            resolvingBulkIds.value = true;
            try {
                const collected = [];
                let page = 1;
                let totalPages = 1;
                do {
                    p.set('page', String(page));
                    const res = await fetch(`/tags/admin/validation/rules_data_table?${p.toString()}`);
                    if (!res.ok) break;
                    const data = await res.json();
                    collected.push(...(data.items || []).map(r => r.id));
                    totalPages = data.total_pages || 1;
                    page++;
                } while (page <= totalPages);
                return collected;
            } catch (e) {
                console.error('[ValidationRunner] resolveBulkIds error:', e);
                return [];
            } finally {
                resolvingBulkIds.value = false;
            }
        }

        async function onRiskBulkAction({ action, ids }) {
            if (ids !== 'ALL' && (!Array.isArray(ids) || ids.length === 0)) return;
            const resolvedIds = await resolveBulkIds(ids);
            if (!resolvedIds.length) {
                emit('notify', { message: 'No matching rules to act on.', level: 'error' });
                return;
            }
            if (action === 'accept_proposed') {
                acceptProposedForRules(resolvedIds);
            } else if (action === 'custom_tag') {
                // Quick-pick buttons need riskTagRow() to resolve — guarantee
                // it's loaded before the modal (with those buttons) opens,
                // rather than relying on loadResult()'s earlier fire-and-forget
                // call having already won the race.
                await loadRiskTags();
                pendingCustomTagIds.value = resolvedIds;
            }
        }

        return {
            fullSync, limit, running, jobUuid, jobStatus, isDone,
            terminalEntries, clearLogs, startRun, quarantined, logsCollapsed,
            baselineOpen, baselineLoading, baselineLoaded, baselineFiles, baselineExcluded, baselineDirs, toggleBaseline,
            quarantineListRef, quarantineFetchUrl, allBinaryOptions, validationRiskLevels,
            riskBulkActions, onRiskBulkAction, resolvingBulkIds,
            acceptableRuleIds, acceptAllProposed,
            pendingCustomTagIds, selectedTags, showAllSelectedTags,
            isQuickTagSelected, toggleQuickTag, removeSelectedTag, closeCustomTagModal,
            RISK_ORDER, riskMeta, contrastColor,
            tagJobUuid, tagging, applyCustomTags,
            history, historyLoading, viewHistoryRun, deleteHistoryRun, goBackToOverview, STATUS_COLOR, STATUS_ICON,
        };
    },

    template: `
<div>
  <!-- Launch card -->
  <div v-if="activeTab === 'validation'" class="vr-card">
    <div class="vr-card__header">
      <div class="vr-card__header-left">
        <div class="vr-card__accent"></div>
        <span class="vr-card__title"><i class="fa-solid fa-shield-virus me-1"></i>Run Validation</span>
      </div>
      <button @click="startRun" :disabled="running" class="btn btn-primary btn-sm fw-semibold px-3">
        <i class="fa-solid me-2" :class="running ? 'fa-spinner fa-spin' : 'fa-play'"></i>
        [[ running ? 'Running…' : 'Start Validation' ]]
      </button>
    </div>
    <div class="vr-card__body">
      <small class="text-muted d-block mb-3">
        Pulls this instance's rules, scans them against a known-clean binary
        baseline, and quarantines anything that fires — a false-positive gate
        powered by <code>rulezet-validation</code>.
      </small>

      <div class="d-flex flex-wrap gap-4 align-items-center mb-1" v-if="!running && jobStatus === 'idle'">
        <div class="form-check form-switch">
          <input class="form-check-input" type="checkbox" id="full-sync-switch" v-model="fullSync">
          <label class="form-check-label small" for="full-sync-switch">
            Full re-sync <span class="text-muted">(ignore last-sync date)</span>
          </label>
        </div>
        <div class="d-flex align-items-center gap-2">
          <label class="small text-muted mb-0" for="limit-input">Limit</label>
          <input id="limit-input" type="number" min="1" class="form-control form-control-sm" style="width:110px"
                 v-model.number="limit" placeholder="trial run">
        </div>
      </div>

      <!-- Live log — real terminal component, same one used on the job detail
           page. Auto-collapses once the run finishes (still stays a click
           away) so a completed run doesn't leave a wall of scrollback
           sitting above its own result. -->
      <div v-if="terminalEntries.length > 0" class="mt-3">
        <button class="btn btn-sm btn-link text-decoration-none text-muted ps-0 mb-1" @click="logsCollapsed = !logsCollapsed">
          <i class="fa-solid" :class="logsCollapsed ? 'fa-chevron-right' : 'fa-chevron-down'"></i>
          [[ logsCollapsed ? 'Show log' : 'Hide log' ]]
        </button>
        <div v-show="!logsCollapsed">
          <ansi-terminal
              :entries="terminalEntries"
              :live="!isDone"
              title="Rule validation"
              @clear="clearLogs">
          </ansi-terminal>
        </div>
      </div>
    </div>
  </div>

  <!-- History — past runs, so there's always something to look at even
       before the first click, and any of them can be revisited. -->
  <div v-if="activeTab === 'history'" class="vr-card">
    <div class="vr-card__header">
      <div class="vr-card__header-left">
        <div class="vr-card__accent" style="background:#6f42c1;"></div>
        <span class="vr-card__title"><i class="fa-solid fa-clock-rotate-left me-1"></i>Recent runs</span>
      </div>
    </div>
    <div class="vr-card__body">
      <div v-if="historyLoading" class="text-center text-muted py-3">
        <span class="spinner-border spinner-border-sm me-2"></span>Loading…
      </div>

      <div v-else-if="history.length === 0" class="text-center py-4 text-muted">
        <i class="fa-solid fa-shield-virus fa-2x mb-2 d-block opacity-25"></i>
        <small>No validation run yet. Switch to the <strong>Validation</strong> tab to run the first one.</small>
      </div>

      <div v-else class="list-group list-group-flush">
        <div v-for="h in history" :key="h.uuid"
             class="list-group-item d-flex align-items-center gap-3 px-2">
          <div class="d-flex align-items-center gap-3 flex-grow-1" role="button" style="cursor:pointer;"
               @click="viewHistoryRun(h)">
            <i class="fa-solid" :class="[STATUS_ICON[h.status] || 'fa-clock', 'text-' + (STATUS_COLOR[h.status] || 'secondary')]"></i>
            <div class="flex-grow-1 text-start">
              <div class="small fw-semibold" style="color:var(--text-color);">
                [[ h.label || 'Rule validation run' ]]
              </div>
              <div class="text-muted" style="font-size:.75rem;">
                [[ h.created_at ]]<span v-if="h.finished_at"> — finished [[ h.finished_at ]]</span>
              </div>
            </div>
            <span class="badge rounded-pill" :class="'bg-' + (STATUS_COLOR[h.status] || 'secondary') + '-subtle text-' + (STATUS_COLOR[h.status] || 'secondary')">
              [[ h.status ]]
            </span>
            <i class="fa-solid fa-chevron-right text-muted opacity-50"></i>
          </div>
          <button type="button" class="btn btn-sm btn-outline-danger border-0"
                  :disabled="h.status === 'pending' || h.status === 'running'"
                  title="Delete this run" @click="deleteHistoryRun(h)">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Results card -->
  <div v-if="activeTab === 'validation' && isDone && quarantined.length > 0" class="vr-card">
    <div class="vr-card__header">
      <div class="vr-card__header-left">
        <div class="vr-card__accent" style="background:#ffc107;"></div>
        <span class="vr-card__title"><i class="fa-solid fa-triangle-exclamation me-1"></i>[[ quarantined.length ]] rule(s) quarantined</span>
      </div>
      <div class="d-flex align-items-center gap-2">
        <button v-if="acceptableRuleIds.length > 0" class="btn btn-sm btn-primary rounded-pill" @click="acceptAllProposed">
          <i class="fa-solid fa-check-double me-1"></i>Accept all ([[ acceptableRuleIds.length ]])
        </button>
        <a v-if="jobUuid" :href="'/jobs/detail/' + jobUuid" target="_blank" rel="noopener"
           class="btn btn-sm btn-outline-secondary rounded-pill" title="Full run log">
          <i class="fa-solid fa-up-right-from-square me-1"></i>Full log
        </a>
        <button class="btn btn-sm btn-outline-secondary rounded-pill" @click="goBackToOverview">
          <i class="fa-solid fa-arrow-left me-1"></i>Back
        </button>
      </div>
    </div>
    <div class="vr-card__body">
      <div class="rounded-3 p-3 mb-3" style="background:var(--light-bg-color);font-size:.83rem;">
        <i class="fa-solid fa-lightbulb me-2 text-primary"></i>
        Each rule's <strong>proposed</strong> risk level is derived only from how many known-clean
        binaries it fired on during this run — never from what the rule itself claims. Where a rule
        already carries its own risk tag and it disagrees with what was actually observed, both are
        shown, disagreements first. Accepting a proposal tags the rule — nothing happens on its own.
      </div>

      <!-- Known-clean baseline — collapsed by default, loaded on first open. -->
      <div class="mb-3">
        <button class="btn btn-sm btn-link text-decoration-none ps-0" @click="toggleBaseline">
          <i class="fa-solid" :class="baselineOpen ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
          <span v-if="baselineLoaded">[[ baselineFiles.length ]] known-clean binaries scanned</span>
          <span v-else>Show known-clean binaries</span>
        </button>
        <div v-show="baselineOpen" class="mt-2">
          <div v-if="baselineLoading" class="text-center text-muted py-3">
            <span class="spinner-border spinner-border-sm me-2"></span>Loading…
          </div>
          <div v-else-if="baselineLoaded" class="rounded-3 border p-3" style="background:var(--light-bg-color);">
            <div class="text-muted small mb-2">
              Sourced from <code v-for="d in baselineDirs" :key="d">[[ d ]]</code> —
              deterministic, so re-running the gate measures the same corpus.
            </div>
            <div style="max-height:260px;overflow-y:auto;font-size:.78rem;font-family:monospace;">
              <div v-for="f in baselineFiles" :key="f.path"
                   style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-color);"
                   :title="f.path">[[ f.path ]]<span style="color:var(--subtle-text-color);"> — [[ (f.size / 1024).toFixed(1) ]] KB</span></div>
            </div>
            <div v-if="baselineExcluded.length" class="text-muted small mt-2 pt-2 border-top" style="border-color:var(--border-color)!important;">
              [[ baselineExcluded.length ]] excluded: [[ baselineExcluded.join(', ') ]]
            </div>
          </div>
        </div>
      </div>

      <!-- Same rule browser used everywhere else in the app — card/table
           toggle, search, sort, and its own bulk-selection toolbar. Keyed
           on jobUuid so switching to a different run (fresh or from
           history) remounts it against the new fetch-url instead of
           reusing stale pagination/selection state. -->
      <rule-list
          ref="quarantineListRef"
          :key="jobUuid"
          mode="manage"
          default-view="card"
          :fetch-url="quarantineFetchUrl"
          :show-validation-risk="true"
          :show-validation-filters="true"
          :validation-risk-levels="validationRiskLevels"
          :validation-binary-options="allBinaryOptions"
          :current-user-id="currentUserId"
          :current-user-is-admin="currentUserIsAdmin"
          :current-user-is-authenticated="currentUserIsAuthenticated"
          :csrf-token="csrfToken"
          :show-create="false"
          :hidden-filters="['format', 'search_field', 'exact_match', 'quality', 'sources', 'vulnerabilities', 'attacks', 'licenses', 'tags', 'person']"
          :hidden-columns="['id', 'editor', 'cves', 'attacks', 'votes']"
          :bulk-actions="riskBulkActions"
          @bulk-action="onRiskBulkAction">
      </rule-list>

      <div v-if="tagJobUuid" class="mt-3 border rounded-3 p-3">
        <job-tracker :job-uuid="tagJobUuid" @done="quarantineListRef?.fetchData()"></job-tracker>
      </div>
    </div>
  </div>

  <!-- Apply-a-tag modal — opened by the "Apply a different tag…" bulk
       action above, targeting whatever selection (single page or "all N
       pages") triggered it. -->
  <transition name="bt-modal-fade">
    <div v-if="pendingCustomTagIds.length > 0" class="bt-modal-backdrop" @click.self="closeCustomTagModal">
      <div class="bt-modal-dialog" role="dialog" aria-modal="true" aria-label="Apply a tag">
        <div class="bt-modal-header">
          <div class="bt-modal-header__icon"><i class="fa-solid fa-tags"></i></div>
          <div class="bt-modal-header__body">
            <div class="bt-modal-header__title">Apply a tag</div>
            <div class="bt-modal-header__sub">[[ pendingCustomTagIds.length ]] rule(s) will be tagged</div>
          </div>
          <button type="button" class="bt-modal-close" @click="closeCustomTagModal" aria-label="Close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="bt-modal-body">
          <div class="mb-3">
            <div class="small fw-semibold text-muted mb-2">Quick pick</div>
            <div class="d-flex flex-wrap gap-2">
              <button v-for="level in RISK_ORDER" :key="level" type="button"
                      class="btn btn-sm rounded-pill fw-semibold"
                      :style="isQuickTagSelected(level)
                          ? { background: riskMeta(level).color, color: contrastColor(riskMeta(level).color), border: '2px solid ' + riskMeta(level).color }
                          : { background: 'transparent', color: riskMeta(level).color, border: '2px solid ' + riskMeta(level).color }"
                      @click="toggleQuickTag(level)">
                <i v-if="isQuickTagSelected(level)" class="fa-solid fa-check me-1"></i>[[ riskMeta(level).label ]]
              </button>
            </div>
          </div>

          <tag-input v-model="selectedTags" label="Or search for a tag" placeholder="Search tags to apply…"></tag-input>

          <div v-if="selectedTags.length > 0" class="mt-3 pt-3 border-top">
            <div class="small fw-semibold text-muted mb-1">Selected ([[ selectedTags.length ]])</div>
            <div class="d-flex flex-wrap gap-1">
              <span v-for="tag in (showAllSelectedTags ? selectedTags : selectedTags.slice(0, 5))" :key="tag.id"
                    class="badge d-flex align-items-center gap-1 px-2" :style="{ backgroundColor: tag.color || '#6c757d' }">
                [[ tag.name ]]
                <i class="fas fa-times ms-1" style="cursor:pointer;font-size:.65rem" @click="removeSelectedTag(tag.id)"></i>
              </span>
              <button v-if="!showAllSelectedTags && selectedTags.length > 5" type="button"
                      class="badge border-0 bg-secondary-subtle text-secondary-emphasis" style="cursor:pointer;"
                      @click="showAllSelectedTags = true">
                +[[ selectedTags.length - 5 ]] more
              </button>
              <button v-if="showAllSelectedTags && selectedTags.length > 5" type="button"
                      class="badge border-0 bg-secondary-subtle text-secondary-emphasis" style="cursor:pointer;"
                      @click="showAllSelectedTags = false">
                Show less
              </button>
            </div>
          </div>
        </div>

        <div class="bt-modal-footer">
          <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill" @click="closeCustomTagModal">Cancel</button>
          <button type="button" class="btn btn-sm btn-primary fw-bold rounded-pill px-4"
                  :disabled="tagging || selectedTags.length === 0"
                  @click="applyCustomTags">
            <span v-if="tagging" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="fas fa-tag me-2"></i>
            Apply to [[ pendingCustomTagIds.length ]] rule(s)
          </button>
        </div>
      </div>
    </div>
  </transition>

  <!-- A finished run (fresh or revisited from history) that quarantined nothing -->
  <div v-if="activeTab === 'validation' && isDone && quarantined.length === 0" class="vr-card">
    <div class="vr-card__header">
      <div class="vr-card__header-left">
        <div class="vr-card__accent" style="background:#198754;"></div>
        <span class="vr-card__title"><i class="fa-solid fa-circle-check me-1"></i>Nothing quarantined</span>
      </div>
      <button class="btn btn-sm btn-outline-secondary rounded-pill" @click="goBackToOverview">
        <i class="fa-solid fa-arrow-left me-1"></i>Back
      </button>
    </div>
    <div class="vr-card__body text-center py-5 text-muted">
      <i class="fa-solid fa-circle-check fa-2x mb-2 d-block text-success opacity-75"></i>
      <small>This run quarantined nothing — every scanned rule stayed clean against the baseline.</small>
    </div>
  </div>
</div>
    `,
};
