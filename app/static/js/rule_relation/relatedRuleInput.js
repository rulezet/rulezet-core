/**
 * relatedRuleInput.js — "link this rule to other rules" picker for the
 * rule create/edit pages. Same dual-mode pattern as AttackInput
 * (/static/js/attack/attackInput.js): if `ruleId` is set (edit page),
 * add/remove persist immediately against /rule_relation/...; if absent
 * (create page), selections only live in modelValue and are submitted as
 * a hidden JSON field, parsed server-side once the rule itself is
 * inserted (so a source_rule_id actually exists).
 *
 * Picking a rule is a single path: click the field to open a modal with
 * the full <rule-list mode="select"> faceted-filter browser (same picker
 * used by the Task Scheduler's rule target and the Workspace "Add Rules"
 * modal) — tags/sources/licenses/CVEs/ATT&CK/author filters, pagination,
 * search all included there already, so a separate lightweight search
 * box here would just be a second, weaker way to do the same thing.
 *
 * No Confirm step: every checkbox toggle inside the modal commits (or
 * un-links) immediately via RuleList's 'toggle-select' emit — there is no
 * "pick several, then confirm" batch step for this consumer specifically
 * (:show-confirm-button="false"). This avoids a desync where a user picks
 * rules, closes the modal without confirming, then reopens it and the
 * checkboxes don't match what's actually linked. The modal is also force-
 * unmounted (v-if) on every close — X, backdrop, Escape, or the picker's
 * own dismiss — via the 'hidden.bs.modal' listener below, not just the
 * one path that used to call closeBrowseModal() itself; otherwise RuleList
 * would keep stale internal selection state across a reopen even though
 * :pre-selected looked right from the outside.
 *
 * Client-side capped at MAX_MANUAL_RELATIONS_PER_RULE (keep in sync with
 * app/features/rule_relation/rule_relation_core.py) — the server enforces
 * the same cap regardless (status 'limit_reached'), this is just so the
 * picker stops offering to add more before hitting that wall. Only
 * applies to hand-linking from this component; auto-detected links
 * created during import (Wazuh if_sid, Kunai rule() composition, ...)
 * are not capped.
 *
 * Props:
 *   modelValue  Array<{id, title, format, relation_type, relation_uuid}>
 *   label       String
 *   ruleId      Number   — optional; presence toggles immediate-persist mode
 *   csrfToken   String
 *
 * Emits: update:modelValue
 */
import RuleList from '/static/js/rule/ruleList.js';
import RuleHoverPreview from '/static/js/rule_relation/ruleHoverPreview.js';
import { create_message } from '/static/js/toaster.js';

// Keep in sync with RULE_RELATION_TYPES in app/core/db_class/db.py — this
// is the manual-link vocabulary; auto-detected links (Wazuh if_sid, Kunai
// rule() composition, ...) use their own format-specific kind instead and
// never go through this picker.
const RELATION_TYPES = [
    { value: 'references',   label: 'References' },
    { value: 'depends_on',   label: 'Depends on' },
    { value: 'related',      label: 'Related to' },
    { value: 'variant_of',   label: 'Variant of' },
    { value: 'duplicate_of', label: 'Duplicate of' },
];

// Keep in sync with MAX_MANUAL_RELATIONS_PER_RULE in
// app/features/rule_relation/rule_relation_core.py.
const MAX_MANUAL_RELATIONS = 20;

const BROWSE_MODAL_ID = 'relatedRuleBrowseModal';

const RelatedRuleInput = {
    name: 'RelatedRuleInput',
    components: { 'rule-list': RuleList, 'rule-hover-preview': RuleHoverPreview },
    props: {
        modelValue: { type: Array,  default: () => [] },
        label:      { type: String, default: 'Linked Rules' },
        ruleId:     { type: Number, default: null },
        csrfToken:  { type: String, default: '' },
    },
    emits: ['update:modelValue'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const { ref, nextTick } = Vue;

        const saving          = ref(null);   // rule id currently being added/removed
        const showBrowseModal = ref(false);
        const ruleListRef     = ref(null);
        let browseModalInstance = null;

        const atLimit = () => props.modelValue.length >= MAX_MANUAL_RELATIONS;

        /** Persists (edit mode) and builds the modelValue entry for one
         * rule. Returns null when the rule can't be linked (self, already
         * linked, or the cap is reached) so callers can skip it. */
        async function commitRule(id, title, format) {
            if (id === props.ruleId || props.modelValue.some(r => r.id === id)) return null;
            if (atLimit()) return null;

            const entry = { id, title, format, relation_type: 'references', relation_uuid: null };
            if (props.ruleId) {
                saving.value = id;
                try {
                    const res = await fetch(`/rule_relation/rule/${props.ruleId}/add`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                        body: JSON.stringify({ target_rule_id: id, relation_type: entry.relation_type }),
                    });
                    const data = await res.json();
                    if (!res.ok) {
                        create_message(data.error || 'Could not link that rule.', 'danger-subtle');
                        return null;
                    }
                    if (data.relation) entry.relation_uuid = data.relation.uuid;
                } finally { saving.value = null; }
            }
            return entry;
        }

        async function removeRule(entry) {
            if (props.ruleId && entry.relation_uuid) {
                saving.value = entry.id;
                try {
                    await fetch(`/rule_relation/rule/${props.ruleId}/remove/${entry.relation_uuid}`, {
                        method: 'DELETE',
                        headers: { 'X-CSRFToken': props.csrfToken },
                    });
                } finally { saving.value = null; }
            }
            emit('update:modelValue', props.modelValue.filter(r => r.id !== entry.id));
        }

        async function changeRelationType(entry, newType) {
            if (entry.relation_type === newType) return;

            if (props.ruleId) {
                saving.value = entry.id;
                try {
                    if (entry.relation_uuid) {
                        await fetch(`/rule_relation/rule/${props.ruleId}/remove/${entry.relation_uuid}`, {
                            method: 'DELETE',
                            headers: { 'X-CSRFToken': props.csrfToken },
                        });
                    }
                    const res = await fetch(`/rule_relation/rule/${props.ruleId}/add`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                        body: JSON.stringify({ target_rule_id: entry.id, relation_type: newType }),
                    });
                    const data = await res.json();
                    entry.relation_uuid = data.relation ? data.relation.uuid : null;
                } finally { saving.value = null; }
            }
            entry.relation_type = newType;
            emit('update:modelValue', [...props.modelValue]);
        }

        // ── Browse-all-rules modal (rule-list mode="select") ────────────
        function openBrowseModal() {
            if (atLimit()) {
                create_message(`You've already linked the maximum of ${MAX_MANUAL_RELATIONS} rules.`, 'warning-subtle');
                return;
            }
            showBrowseModal.value = true;
            nextTick(() => {
                const el = document.getElementById(BROWSE_MODAL_ID);
                browseModalInstance = bootstrap.Modal.getOrCreateInstance(el);
                browseModalInstance.show();
                ruleListRef.value?.fetchData();

                // Single source of truth for "the modal is closed": fires no
                // matter how it closed (X button, backdrop click, Escape, or
                // a future programmatic .hide()). Without this, dismissing
                // any way other than our own close path left showBrowseModal
                // stuck at true, so the next openBrowseModal() skipped the
                // v-if remount and RuleList reused stale selection state
                // instead of picking up fresh :pre-selected — that was the
                // root cause of the reported checkbox desync.
                el.addEventListener('hidden.bs.modal', () => {
                    showBrowseModal.value = false;
                }, { once: true });
            });
        }

        // 'ALL' ("select every rule matching the current filters") makes
        // sense for a bulk admin job, not for hand-linking a handful of
        // related rules — RuleList's Confirm button is hidden here
        // (:show-confirm-button="false") so 'send'/'ALL' can't actually
        // reach this component anymore, but the guard is cheap to keep in
        // case that ever changes.
        function onRulesPicked(ids) {
            if (ids === 'ALL') {
                create_message('Pick individual rules to link — "select all matching filters" isn\'t supported here.', 'warning-subtle');
            }
        }

        // Fired on every single checkbox toggle inside the modal — commits
        // or un-links immediately, live, instead of waiting for a Confirm
        // click that no longer exists for this picker.
        async function onSingleToggle(rule, isSelected) {
            if (isSelected) {
                if (atLimit()) {
                    create_message(`You've already linked the maximum of ${MAX_MANUAL_RELATIONS} rules.`, 'warning-subtle');
                    return;
                }
                const entry = await commitRule(rule.id, rule.title, rule.format);
                if (entry) emit('update:modelValue', [...props.modelValue, entry]);
            } else {
                const entry = props.modelValue.find(r => r.id === rule.id);
                if (entry) await removeRule(entry);
            }
        }

        return {
            saving, showBrowseModal, ruleListRef, BROWSE_MODAL_ID,
            RELATION_TYPES, MAX_MANUAL_RELATIONS,
            removeRule, changeRelationType, openBrowseModal, onRulesPicked, onSingleToggle,
        };
    },
    template: `
<div class="related-rule-input-container text-start position-relative">
    <div class="d-flex align-items-center justify-content-between">
        <label class="form-label fw-bold text-muted small text-uppercase mb-1">[[ label ]]</label>
        <small v-if="modelValue.length" class="text-muted" style="font-size:.7rem;">[[ modelValue.length ]] / [[ MAX_MANUAL_RELATIONS ]]</small>
    </div>

    <button type="button"
            class="d-flex align-items-center gap-2 w-100 rounded-3 border shadow-sm px-3 py-2"
            style="border-width:2px; background:var(--card-bg-color); color:var(--subtle-text-color); text-align:left;"
            @click="openBrowseModal">
        <i class="fa-solid fa-diagram-project" style="color:#0d6efd;"></i>
        <span class="small">Click to browse and pick rules to link…</span>
    </button>

    <!-- ── Selected chips ───────────────────────────────────────────────── -->
    <div v-if="modelValue.length" class="d-flex flex-column gap-2 mt-3 p-3 rounded-3 border shadow-sm" style="background:var(--light-bg-color);">
        <div v-for="entry in modelValue" :key="entry.id"
             class="d-flex align-items-center justify-content-between gap-2 rounded-3 px-2 py-1"
             style="background:var(--card-bg-color); border:1px solid var(--border-color);">
            <rule-hover-preview :rule-id="entry.id">
                <div class="d-flex align-items-center gap-2" style="min-width:0;">
                    <span class="badge rounded-pill bg-secondary-subtle text-secondary-emphasis" style="font-size:.65rem; flex-shrink:0;">[[ entry.format ]]</span>
                    <span class="small fw-bold text-truncate" style="max-width:200px; color:var(--text-color);">[[ entry.title ]]</span>
                </div>
            </rule-hover-preview>
            <div class="d-flex align-items-center gap-2 flex-shrink-0">
                <select class="form-select form-select-sm py-0"
                        style="font-size:.72rem; width:auto; background-color:var(--card-bg-color); color:var(--text-color); border-color:var(--border-color);"
                        :value="entry.relation_type" @change="changeRelationType(entry, $event.target.value)"
                        :disabled="saving === entry.id">
                    <option v-for="rt in RELATION_TYPES" :key="rt.value" :value="rt.value" style="background-color:var(--card-bg-color); color:var(--text-color);">[[ rt.label ]]</option>
                </select>
                <button @click.stop="removeRule(entry)"
                        class="btn p-0 border-0 d-flex align-items-center"
                        style="background:transparent; color:var(--subtle-text-color); opacity:.7;"
                        :disabled="saving === entry.id">
                    <div v-if="saving === entry.id" class="spinner-border spinner-border-sm" style="width:12px; height:12px;"></div>
                    <i v-else class="fa-solid fa-circle-xmark"></i>
                </button>
            </div>
        </div>
    </div>

    <!-- ── Browse-all-rules modal ───────────────────────────────────────── -->
    <teleport to="body">
        <div class="modal fade" :id="BROWSE_MODAL_ID" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-fullscreen">
                <div class="modal-content border-0 shadow-lg">
                    <div class="modal-header border-0 pb-0">
                        <h6 class="modal-title fw-bold">
                            <i class="fa-solid fa-diagram-project me-2 text-primary"></i>Browse rules to link
                        </h6>
                        <button type="button" class="btn-close shadow-none" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <rule-list
                            v-if="showBrowseModal"
                            ref="ruleListRef"
                            mode="select"
                            default-view="table"
                            fetch-url="/rule/data_table"
                            :sync-url="false"
                            :show-filters="true"
                            :show-export="false"
                            :show-create="false"
                            :current-user-is-authenticated="true"
                            :csrf-token="csrfToken"
                            :initial-per-page="20"
                            :pre-selected="modelValue"
                            :show-confirm-button="false"
                            @toggle-select="onSingleToggle"
                            @send="onRulesPicked">
                        </rule-list>
                    </div>
                </div>
            </div>
        </div>
    </teleport>
</div>
`,
};

export default RelatedRuleInput;
