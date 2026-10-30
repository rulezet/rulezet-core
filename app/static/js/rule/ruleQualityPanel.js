/**
 * ruleQualityPanel.js — the Quality section of the rule page: score, what each category checks,
 * how to improve it, and the reviews (approve / request changes) by other users.
 * Scoring: app/features/rule/rule_quality/quality_score_core.py. Reviews: features/rule/rule_review.py.
 *
 * Props:   rule (currentRule: id, quality_score, quality_score_breakdown, quality_score_computed_at),
 *          isAuthenticated, canEdit (owner or admin), canTest (sample tests open to this user),
 *          canUseAi (admin or 'ai.use' — may run the AI analysis), csrfToken
 *          A "How to raise" button only shows when the user may do it (same checks as the server).
 * Emits:   'updated' ({quality_score, quality_score_breakdown, quality_score_computed_at}) after a review
 * Window:  'rz:open-review' opens the review dialog (the Review button of the Actions bar).
 */
import { create_message } from '/static/js/toaster.js';
import { renderMarkdown } from '/static/js/sanitize.js';
import { MarkdownComposer } from '/static/js/components/comments/comment-thread.js';
import { askAndDetect, mergeEntries } from '/static/js/rule/scopeMachine.js';

const { ref, reactive, computed, watch, onMounted, onUnmounted } = Vue;

const CATEGORIES = {
    traceability:    { label: 'Traceability', icon: 'fa-solid fa-route', hint: 'Where it comes from' },
    authorship:      { label: 'Authorship', icon: 'fa-solid fa-signature', hint: 'Who wrote it, under which license' },
    metadata:        { label: 'Metadata', icon: 'fa-solid fa-tags', hint: 'What an analyst needs at alert time' },
    validity:        { label: 'Validity', icon: 'fa-solid fa-circle-check', hint: 'It parses, its source updates cleanly' },
    review:          { label: 'Review', icon: 'fa-solid fa-user-check', hint: 'The owner or an admin approved it' },
    field_reports:   { label: 'Field reports', icon: 'fa-solid fa-globe', hint: 'Scopes users declared: where it works, or not',
                       na: 'Nobody declared a scope yet — "works for me / doesn\'t" on the Scope tab counts here.' },
    usage:           { label: 'Uniqueness & use', icon: 'fa-solid fa-fingerprint', hint: 'Not a copy, used in bundles, linked to a threat, analysed by AI' },
    testing:         { label: 'Testing', icon: 'fa-solid fa-vial', hint: 'Run on sample sets',
                       na: 'Not tested on samples yet — counted once the rule is run on sample sets (Tests).' },
    external_checks: { label: 'External checks', icon: 'fa-solid fa-list-check', hint: 'YARA-X, CCCS standard, yaraQA',
                       na: 'For YARA rules, when the admin enables the external checks.' },
};

// label + how to fix it, per check
const CHECKS = {
    has_original_uuid:         ['Keeps its original id', 'Keep the UUID / sid the rule had in its source.'],
    has_github_path:           ['Linked to its file in the repository', 'Import it from its Git repository so it stays linked.'],
    has_source:                ['Says where it comes from', 'Fill in the Source field.'],
    has_description:           ['Has a description (30+ characters)', 'Explain what it detects and why, in a few sentences.'],
    has_author:                ['Has an author', 'Fill in the Author field.'],
    has_license:               ['Has a license', 'Choose the license it is shared under.'],
    says_how_written:          ['Says how it was written', 'Human, AI, or both — the owner or an admin says it in their review.'],
    has_meaningful_tags:       ['Tagged (beyond tlp / pap)', 'Add tags: malware family, platform, technique…'],
    has_attack_mapping:        ['Mapped to MITRE ATT&CK', 'Link the ATT&CK techniques it detects.'],
    passes_validation:         ["Passes Rulezet's syntax check", 'Fix the syntax errors shown when editing.'],
    no_pending_failed_update:  ['Last update from its source succeeded', 'Look at the failed update in History.'],
    reviewed_since_creation:   ['Looked at since creation', 'Get a review (anyone signed in), or improve it in an edit.'],
    approved_by_reviewer:      ['Approved in a review', 'Someone approves this version in a review.'],
    approved_by_two_reviewers: ['Approved by two people', 'A second approval makes it a trusted rule.'],
    no_changes_requested:      ['No change requested on this version', 'Address the requested changes, then ask for a new review.'],
    not_a_duplicate:           ['Not a copy of an older rule', 'A rule 95%+ similar already exists: see Similar rules, merge or differentiate.'],
    used_in_a_bundle:          ['Used in a bundle', 'Add it to a bundle that groups rules for a threat or a use.'],
    linked_to_a_threat:        ['Linked to a threat (CVE or ATT&CK)', 'Add the CVE or the ATT&CK technique it detects.'],
    has_ai_analysis:           ['Has an AI analysis', 'Ask the AI agent for an analysis report of the rule (AI analysis tab).'],
    works_somewhere:           ['Reported working somewhere', 'Declare a scope where it works (Scope tab).'],
    works_in_several_places:   ['Reported working in two places or more', 'More scopes from people who run it.'],
    no_report_it_fails:        ['No report that it fails', 'Someone reported it does not work: read their scope, fix the rule.'],
    tested_on_samples:         ['Tested on samples', 'Run it on sample sets (Tests).'],
    detects_its_samples:       ['Detects its samples', 'It matched none of the malicious samples: check its conditions.'],
    no_false_positives:        ['No false positive', 'It matched clean samples: make it more specific.'],
    no_test_errors:            ['Ran without errors', 'Some samples failed to run: see the test results.'],
    compiles_with_yara_x:      ['Compiles with YARA-X', 'Open it in the YARA editor: Checks shows what YARA-X refuses.'],
    follows_cccs_standard:     ['Follows the CCCS YARA standard', 'Add the metadata the standard asks for (YARA editor → Checks).'],
    clean_for_yaraqa:          ['No yaraQA issue', 'yaraQA flags slow or weak strings / conditions (YARA editor → Checks).'],
};

// What a "How to raise the score" item offers: a link to the right place, or something done here.
const WRITTEN_WITH = [
    { value: 'human', label: 'Human', icon: 'fa-solid fa-user' },
    { value: 'human_ai', label: 'Human + AI', icon: 'fa-solid fa-user-gear' },
    { value: 'ai', label: 'AI', icon: 'fa-solid fa-robot' },
];
const EDIT_CHECKS = ['has_description', 'has_author', 'has_license', 'has_source', 'has_meaningful_tags',
                     'has_attack_mapping', 'passes_validation'];
const YARA_CHECKS = ['compiles_with_yara_x', 'follows_cccs_standard', 'clean_for_yaraqa'];
const REVIEW_CHECKS = ['reviewed_since_creation', 'approved_by_reviewer', 'approved_by_two_reviewers', 'no_changes_requested'];
const TEST_CHECKS = ['tested_on_samples', 'detects_its_samples', 'no_false_positives', 'no_test_errors'];

export default {
    name: 'RuleQualityPanel',
    delimiters: ['[[', ']]'],
    props: {
        rule: { type: Object, required: true },
        isAuthenticated: { type: Boolean, default: false },
        canEdit: { type: Boolean, default: false },
        canTest: { type: Boolean, default: false },
        canUseAi: { type: Boolean, default: false },
        csrfToken: { type: String, default: '' },
    },
    components: { 'markdown-composer': MarkdownComposer },
    emits: ['updated'],
    setup(props, { emit }) {
        const breakdown = computed(() => props.rule.quality_score_breakdown || null);
        const score = computed(() => props.rule.quality_score);
        const display = computed(() => breakdown.value ? breakdown.value.display_score : score.value);

        const level = computed(() => {
            const s = score.value ?? 0;
            if (s >= 80) return { label: 'Excellent', cls: 'is-excellent' };
            if (s >= 60) return { label: 'Good', cls: 'is-good' };
            if (s >= 40) return { label: 'Fair', cls: 'is-fair' };
            return { label: 'Needs work', cls: 'is-poor' };
        });
        const ring = computed(() => {
            const c = 2 * Math.PI * 42;
            return { c, offset: c * (1 - Math.min(100, Math.max(0, score.value || 0)) / 100) };
        });

        const categories = computed(() => {
            const cats = (breakdown.value && breakdown.value.categories) || {};
            return Object.keys(CATEGORIES).filter(k => cats[k]).map(k => ({
                key: k, ...CATEGORIES[k], ...cats[k],
                pct: cats[k].total ? Math.round(100 * cats[k].earned / cats[k].total) : 0,
                items: Object.entries(cats[k].checks || {}).map(([ck, ok]) => ({ key: ck, ok, label: label(ck) })),
            }));
        });
        const improvements = computed(() => {
            const list = categories.value.flatMap(c =>
                c.not_applicable ? [] : c.items.filter(i => !i.ok).map(i => ({ ...i, icon: c.icon, category: c.label, fix: fix(i.key), action: action(i.key) })));
            const testing = categories.value.find(c => c.key === 'testing');
            if (testing && testing.not_applicable && props.canTest) {
                list.push({ key: 'tested_on_samples', label: 'Test it on samples (bonus category)', icon: testing.icon, category: 'Testing',
                            fix: 'Once tested, detections and false positives count too.', action: action('tested_on_samples') });
            }
            return list;
        });

        // The button of an improvement: { label, icon, href } to go there, or { label, icon, run } done here.
        function action(key) {
            const id = props.rule.id;
            if (!props.isAuthenticated) return { label: 'Sign in', icon: 'fa-solid fa-right-to-bracket', href: '/account/login' };
            const editOrPropose = props.canEdit
                ? { label: 'Edit the rule', icon: 'fa-solid fa-pen', href: `/rule/edit_rule/${id}` }
                : { label: 'Propose an edit', icon: 'fa-solid fa-code-pull-request', href: `/rule/detail_rule/${id}/propose_edit` };
            if (EDIT_CHECKS.includes(key) || key.startsWith('format:')) return editOrPropose;
            if (key === 'says_how_written') return props.canEdit
                ? { label: 'Say it in a review', icon: 'fa-solid fa-robot', run: openReview } : null;
            if (YARA_CHECKS.includes(key)) return props.canEdit
                ? { label: 'Fix in the editor', icon: 'fa-solid fa-code', href: `/rule/edit_rule/${id}` } : editOrPropose;
            if (key === 'not_a_duplicate') return { label: 'See similar rules', icon: 'fa-solid fa-clone', href: `/rule/detail_rule/${id}/similarity` };
            if (key === 'used_in_a_bundle') return { label: 'Add to a bundle', icon: 'fa-solid fa-boxes-stacked', href: `/rule/detail_rule/${id}/bundles` };
            if (key === 'linked_to_a_threat') return editOrPropose;
            if (key === 'has_ai_analysis') return props.canUseAi
                ? { label: 'Run the AI analysis', icon: 'fa-solid fa-wand-magic-sparkles', href: `/rule/detail_rule/${id}/ai_analysis` } : null;
            if (key === 'no_pending_failed_update') return { label: 'See the history', icon: 'fa-solid fa-clock-rotate-left', href: `/rule/detail_rule/${id}/history` };
            if (['works_somewhere', 'works_in_several_places', 'no_report_it_fails'].includes(key))
                return { label: 'Open the scopes', icon: 'fa-solid fa-globe', href: `/rule/detail_rule/${id}/scope` };
            if (TEST_CHECKS.includes(key)) return props.canTest
                ? { label: 'Test on samples', icon: 'fa-solid fa-vial', href: `/rule/detail_rule/${id}/samples` } : null;
            if (REVIEW_CHECKS.includes(key)) return canReview.value
                ? { label: 'Review it', icon: 'fa-solid fa-user-check', run: openReview }
                : null;
            return null;      // set at import (original id, repository link): nothing to do here
        }
        // Why there is no button (the user may not do it here)
        function noteFor(key) {
            if (['has_original_uuid', 'has_github_path'].includes(key)) return 'set at import';
            if (key === 'has_ai_analysis') return 'AI role needed';
            if (TEST_CHECKS.includes(key)) return 'tests not open to you';
            return 'owner or admin';
        }
        function copyLink() {
            const url = `${location.origin}/rule/detail_rule/${props.rule.id}`;
            navigator.clipboard.writeText(url).then(
                () => create_message('Link copied — send it to someone who can review the rule.', 'success-subtle'),
                () => create_message(url, 'info-subtle'));
        }
        // How the rule was written (human / AI / both) — owner or admin
        const writtenBusy = ref(false);
        const writtenWith = computed(() => WRITTEN_WITH.find(w => w.value === props.rule.written_with) || null);
        async function setWrittenWith(value) {
            if (!props.canEdit || writtenBusy.value) return;
            writtenBusy.value = true;
            try {
                const res = await fetch(`/rule/${props.rule.id}/written_with`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ written_with: props.rule.written_with === value ? null : value }),
                });
                const data = await res.json();
                create_message(data.message, data.toast_class);
                if (res.ok) { emit('updated', { written_with: data.written_with }); apply(data); }
            } finally {
                writtenBusy.value = false;
            }
        }
        const reanalysing = ref(false);
        async function reanalyse() {
            reanalysing.value = true;
            try {
                const res = await fetch(`/rule/${props.rule.id}/quality/recompute`, { method: 'POST', headers: { 'X-CSRFToken': props.csrfToken } });
                const data = await res.json();
                create_message(data.message, data.toast_class);
                if (res.ok) apply(data);
            } finally {
                reanalysing.value = false;
            }
        }

        function label(key) {
            if (CHECKS[key]) return CHECKS[key][0];
            return key.replace(/^format:/, '').replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());
        }
        function fix(key) {
            if (CHECKS[key]) return CHECKS[key][1];
            return key.startsWith('format:') ? 'Add it to the rule (format metadata).' : '';
        }

        // ── Reviews ────────────────────────────────────────────────────────
        const reviews = ref([]);
        const myReview = ref(null);
        const canReview = ref(false);
        const isOwner = ref(false);
        const canModerate = ref(false);
        const showAllReviews = ref(false);
        const dialog = reactive({ open: false, verdict: 'approved', comment: '', rating: 0, hover: 0, written_with: '', scope_id: '', saving: false,
                                  editing: null });   // editing: the review being edited (own, or any as admin)
        let improveSaved = false;
        try { improveSaved = localStorage.getItem('rz-quality-improve-closed') === '1'; } catch { /* storage off */ }
        const improveClosed = ref(improveSaved);
        function toggleImprove() {
            improveClosed.value = !improveClosed.value;
            try { localStorage.setItem('rz-quality-improve-closed', improveClosed.value ? '1' : '0'); } catch { /* storage off */ }
        }
        const myScopes = ref([]);
        const commentHtml = reactive({});

        // Scope dialog — same form as the Scope tab (works / criteria / notes), without leaving the page
        const scopeKeys = ref([]);
        let scopeKeysLoaded = false;
        const scopeDialog = reactive({ open: false, works: true, entries: [], comment: '', saving: false });
        async function openScopeDialog() {
            if (!scopeKeysLoaded) {
                try {
                    const d = await fetch('/api/config/settings/rule.scope_keys').then(r => r.json());
                    scopeKeys.value = d.value || [];
                    scopeKeysLoaded = true;
                } catch { /* free text still works */ }
            }
            Object.assign(scopeDialog, { open: true, works: true, entries: [{ key: 'os', value: '' }], comment: '', saving: false });
        }
        const scopeKeyOptions = (key) => (scopeKeys.value.find(k => k.key === key) || {}).options || null;
        async function scopeMyMachine() {
            const found = await askAndDetect();
            if (found.length) scopeDialog.entries = mergeEntries(scopeDialog.entries, found);
        }
        async function saveScope() {
            scopeDialog.saving = true;
            try {
                const entries = scopeDialog.entries.filter(e => (e.value || '').trim());
                const res = await fetch(`/rule/scope/${props.rule.id}`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ works: scopeDialog.works, entries, comment: scopeDialog.comment }),
                });
                const data = await res.json();
                if (!data.success) { create_message(data.message || 'Could not save the scope.', 'danger-subtle'); return; }
                create_message('Scope declared.', 'success-subtle');
                scopeDialog.open = false;
                await loadReviews();
                dialog.scope_id = data.id;          // linked to the review being written
            } finally {
                scopeDialog.saving = false;
            }
        }
        const scopeLabel = (sc) => (sc.works ? 'Works' : "Doesn't work") + (sc.entries && sc.entries.length
            ? ' — ' + sc.entries.slice(0, 3).map(e => `${e.key}: ${e.value}`).join(', ') + (sc.entries.length > 3 ? '…' : '') : '');
        const averageRating = ref(null);
        const writtenOf = (v) => WRITTEN_WITH.find(w => w.value === v) || { label: v, icon: 'fa-solid fa-pen-nib' };

        const approvals = computed(() => reviews.value.filter(r => r.verdict === 'approved' && r.current_version).length);
        const changeRequests = computed(() => reviews.value.filter(r => r.verdict === 'changes_requested' && r.current_version).length);
        const shownReviews = computed(() => showAllReviews.value ? reviews.value : reviews.value.slice(0, 3));

        async function loadReviews() {
            if (!props.rule || !props.rule.id) return;      // the page fills the rule after mounting
            try {
                const res = await fetch(`/rule/${props.rule.id}/reviews`);
                if (!res.ok) return;
                apply(await res.json());
            } catch { /* the panel still shows the score */ }
        }
        function apply(data) {
            reviews.value = data.reviews || [];
            reviews.value.forEach(async r => { if (r.comment) commentHtml[r.uuid] = await renderMarkdown(r.comment); });
            myReview.value = data.my_review;
            canReview.value = !!data.can_review;
            isOwner.value = !!data.is_owner;
            canModerate.value = !!data.can_moderate;
            averageRating.value = data.average_rating ?? null;
            myScopes.value = data.my_scopes || [];
            if (data.quality_score !== undefined) {
                emit('updated', { quality_score: data.quality_score, quality_score_breakdown: data.quality_score_breakdown,
                                  quality_score_computed_at: data.quality_score_computed_at });
            }
        }
        function openReview() {
            if (!props.isAuthenticated) { window.location.href = '/account/login'; return; }

            fillDialog(myReview.value, null);
        }
        function editReview(r) { fillDialog(r, r); }
        function fillDialog(r, editing) {
            Object.assign(dialog, { open: true, saving: false, editing,
                verdict: r ? r.verdict : 'approved',
                comment: r ? (r.comment || '') : '',
                rating: r ? (r.rating || 0) : 0,
                scope_id: r && r.scope ? r.scope.id : '',
                written_with: r ? (r.written_with || '') : (props.rule.written_with || '') });
        }
        async function saveReview() {
            dialog.saving = true;
            try {
                const res = await fetch(`/rule/${props.rule.id}/review`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ verdict: dialog.verdict, comment: dialog.comment, rating: dialog.rating || null,
                                           written_with: dialog.written_with || null, scope_id: dialog.scope_id || null,
                                           review_uuid: dialog.editing ? dialog.editing.uuid : null }),
                });
                const data = await res.json();
                create_message(data.message, data.toast_class || (res.ok ? 'success-subtle' : 'danger-subtle'));
                if (res.ok) {
                    apply(data); dialog.open = false;
                    if (canModerate.value && dialog.written_with) emit('updated', { written_with: dialog.written_with });
                }
            } finally {
                dialog.saving = false;
            }
        }
        async function removeReview(r) {
            if (!window.confirm('Remove this review?')) return;
            const res = await fetch(`/rule/review/${r.uuid}`, { method: 'DELETE', headers: { 'X-CSRFToken': props.csrfToken } });
            const data = await res.json();
            create_message(data.message, data.toast_class);
            if (res.ok) apply(data);
        }

        // Load once the rule is there (the rule page fetches it after this panel is mounted)
        watch(() => props.rule && props.rule.id, id => { if (id) loadReviews(); }, { immediate: true });
        onMounted(() => window.addEventListener('rz:open-review', openReview));
        onUnmounted(() => window.removeEventListener('rz:open-review', openReview));

        return { breakdown, score, display, level, ring, categories, improvements, reviews, myReview, canReview, isOwner, canModerate,
                 showAllReviews, shownReviews, approvals, changeRequests, dialog, openReview, saveReview, removeReview,
                 reanalysing, reanalyse, WRITTEN_WITH, writtenWith, writtenBusy, setWrittenWith, averageRating, writtenOf, myScopes, scopeLabel, editReview, improveClosed, toggleImprove, noteFor,
                 commentHtml, scopeKeys, scopeDialog, openScopeDialog, scopeKeyOptions, scopeMyMachine, saveScope };
    },
    template: `
    <section class="rqp" data-tour="rule-quality">
        <header class="rqp-head">
            <div class="d-flex align-items-center gap-2">
                <div class="rqp-bar"></div>
                <span class="rqp-title"><i class="fa-solid fa-gauge-high me-1"></i>Quality</span>
            </div>
            <button type="button" class="rqp-link" data-bs-toggle="modal" :data-bs-target="'#qualityScoreDocModal' + rule.id">
                <i class="fa-solid fa-circle-info me-1"></i>How is it calculated?
            </button>
        </header>

        <p v-if="score === null || score === undefined" class="text-muted small mb-0">This rule hasn't been analysed yet.</p>
        <template v-else>
            <!-- Score + reviews summary -->
            <div class="rqp-top">
                <div class="rqp-score" :class="level.cls">
                    <svg viewBox="0 0 100 100" aria-hidden="true">
                        <circle cx="50" cy="50" r="42" class="rqp-ring-bg"></circle>
                        <circle cx="50" cy="50" r="42" class="rqp-ring" :stroke-dasharray="ring.c" :stroke-dashoffset="ring.offset"></circle>
                    </svg>
                    <div class="rqp-score__text"><strong>[[ Math.round(score) ]]</strong><small>/ 100</small></div>
                </div>
                <div class="rqp-summary">
                    <div class="rqp-level" :class="level.cls">[[ level.label ]]</div>
                    <div class="rqp-meta">
                        <span v-if="breakdown && breakdown.engagement_boost"><i class="fa-solid fa-star me-1"></i>+[[ breakdown.engagement_boost ]] community boost (shown [[ Math.round(display) ]])</span>
                        <span><i class="fa-regular fa-clock me-1"></i>Analysed [[ rule.quality_score_computed_at || '—' ]]</span>
                    </div>
                    <div class="rqp-review-line">
                        <span class="rqp-chip is-ok" v-if="approvals"><i class="fa-solid fa-user-check"></i>[[ approvals ]] approval[[ approvals > 1 ? 's' : '' ]]</span>
                        <span class="rqp-chip is-warn" v-if="changeRequests"><i class="fa-solid fa-user-pen"></i>[[ changeRequests ]] change request[[ changeRequests > 1 ? 's' : '' ]]</span>
                        <span class="rqp-chip" v-if="!approvals && !changeRequests"><i class="fa-regular fa-user"></i>Not reviewed yet</span>
                        <span class="rqp-chip is-star" v-if="averageRating" :title="averageRating + ' / 5 on this version'">
                            <span class="rqp-stars"><i v-for="n in 5" :key="n" class="fa-solid fa-star" :class="{ 'is-empty': n > Math.round(averageRating) }"></i></span>
                            [[ averageRating ]]</span>
                        <span class="rqp-chip" v-if="writtenWith" :title="'How it was written, said by its owner / an admin'"><i :class="writtenWith.icon"></i>[[ writtenWith.label ]]</span>
                        <button type="button" class="btn btn-sm btn-primary rounded-pill px-3" @click="openReview()" v-if="canReview">
                            <i class="fa-solid fa-user-check me-1"></i>[[ myReview ? 'Update my review' : 'Review this rule' ]]
                        </button>
                        <a v-else-if="!isAuthenticated" href="/account/login" class="text-muted small">Sign in to review it</a>
                    </div>
                </div>
            </div>

            <!-- Categories -->
            <div class="rqp-cats">
                <div v-for="c in categories" :key="c.key" class="rqp-cat" :class="{ 'is-na': c.not_applicable }">
                    <div class="rqp-cat__head">
                        <i :class="c.icon"></i>
                        <span class="rqp-cat__name" :data-rz-pop-title="c.label" :data-rz-pop-text="c.hint">[[ c.label ]]</span>
                        <span class="rqp-cat__pts">[[ c.not_applicable ? 'n/a' : Math.round(c.earned) + '/' + c.total ]]</span>
                    </div>
                    <div class="rqp-cat__bar"><span :style="{ width: (c.not_applicable ? 0 : c.pct) + '%' }" :class="c.pct >= 80 ? 'is-good' : c.pct >= 50 ? 'is-mid' : 'is-low'"></span></div>
                    <p v-if="c.not_applicable" class="rqp-cat__na">[[ c.na ]]</p>
                    <ul v-else class="rqp-checks">
                        <li v-for="i in c.items" :key="i.key" :class="i.ok ? 'is-ok' : 'is-ko'">
                            <i :class="i.ok ? 'fa-solid fa-check' : 'fa-solid fa-xmark'"></i>[[ i.label ]]
                        </li>
                    </ul>
                </div>
            </div>

            <!-- Reviews: everyone who reviewed it, with their review -->
            <div v-if="reviews.length" class="rqp-reviews">
                <div class="rqp-subtitle d-flex align-items-center gap-2">
                    <span><i class="fa-solid fa-comments me-1"></i>Reviews ([[ reviews.length ]])</span>
                    <span v-if="reviews.length > 1" class="rqp-avatars">
                        <img v-for="r in reviews.slice(0, 8)" :key="'a' + r.uuid" :src="r.user && r.user.avatar" :alt="r.user && r.user.name"
                             :title="(r.user ? r.user.name : '') + ' — ' + (r.verdict === 'approved' ? 'approved' : 'changes requested')"
                             :class="r.verdict === 'approved' ? 'is-ok' : 'is-warn'">
                    </span>
                </div>
                <div v-for="r in reviews" :key="r.uuid" class="rqp-review" :class="{ 'is-old': !r.current_version }">
                    <img v-if="r.user && r.user.avatar" :src="r.user.avatar" alt="" class="rqp-review__avatar">
                    <div class="rqp-review__body">
                        <div class="rqp-review__head">
                            <a v-if="r.user" :href="'/account/detail_user/' + r.user.id" class="fw-semibold text-decoration-none">[[ r.user.name ]]</a>
                            <span class="rqp-chip" :class="r.verdict === 'approved' ? 'is-ok' : 'is-warn'">
                                <i :class="r.verdict === 'approved' ? 'fa-solid fa-check' : 'fa-solid fa-pen'"></i>[[ r.verdict === 'approved' ? 'Approved' : 'Changes requested' ]]</span>
                            <span v-if="r.rating" class="rqp-stars" :title="r.rating + ' / 5'">
                                <i v-for="n in 5" :key="n" class="fa-solid fa-star" :class="{ 'is-empty': n > r.rating }"></i></span>
                            <span v-if="r.written_with" class="rqp-chip"><i :class="writtenOf(r.written_with).icon"></i>[[ writtenOf(r.written_with).label ]]</span>
                            <a v-if="r.scope" :href="'/rule/detail_rule/' + rule.id + '/scope'" class="rqp-chip text-decoration-none"
                               :class="r.scope.works ? 'is-ok' : 'is-warn'" :title="'Scope: ' + scopeLabel(r.scope)">
                                <i class="fa-solid fa-globe"></i>[[ scopeLabel(r.scope) ]]</a>
                            <span v-if="!r.current_version" class="rqp-chip" title="The rule changed since this review">older version</span>
                            <span class="text-muted small ms-auto">[[ r.created_at ]]</span>
                        </div>
                        <div v-if="r.comment" class="rqp-review__comment rqp-md" v-html="commentHtml[r.uuid] || ''"></div>
                        <div v-if="r.can_edit" class="rqp-review__actions">
                            <button type="button" @click="editReview(r)"><i class="fa-solid fa-pen"></i>Edit</button>
                            <button type="button" class="is-danger" @click="removeReview(r)"><i class="fa-solid fa-trash"></i>Delete</button>
                            <span v-if="myReview && myReview.uuid !== r.uuid" class="text-muted">as admin</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- How to raise the score: each missing point with what to do -->
            <div v-if="improvements.length" class="rqp-improve">
                <div class="rqp-improve__head" role="button" tabindex="0" @click="toggleImprove()" @keydown.enter.prevent="toggleImprove()">
                    <i class="fa-solid fa-chevron-down rqp-caret" :class="{ 'is-closed': improveClosed }"></i>
                    <span><i class="fa-solid fa-arrow-trend-up me-1"></i>How to raise the score</span>
                    <span class="rqp-improve__count">[[ improvements.length ]] to do</span>
                    <button v-if="canEdit" type="button" class="rqp-link ms-auto" :disabled="reanalysing" @click.stop="reanalyse()">
                        <span v-if="reanalysing" class="spinner-border spinner-border-sm me-1"></span><i v-else class="fa-solid fa-rotate me-1"></i>Re-analyse now</button>
                </div>
                <div class="rqp-todo" v-show="!improveClosed">
                    <div v-for="i in improvements" :key="i.key" class="rqp-todo__item">
                        <span class="rqp-todo__icon"><i :class="i.icon"></i></span>
                        <div class="rqp-todo__text">
                            <strong>[[ i.label ]]</strong>
                            <span>[[ i.fix ]]</span>
                        </div>
                        <a v-if="i.action && i.action.href" :href="i.action.href" class="rqp-todo__btn"><i :class="i.action.icon"></i>[[ i.action.label ]]</a>
                        <button v-else-if="i.action && i.action.run" type="button" class="rqp-todo__btn" @click="i.action.run()"><i :class="i.action.icon"></i>[[ i.action.label ]]</button>
                        <span v-else class="rqp-todo__note">[[ noteFor(i.key) ]]</span>
                    </div>
                </div>
            </div>

        </template>

        <!-- Review dialog -->
        <teleport to="body">
            <div v-if="dialog.open" class="rqp-modal" @click.self="dialog.open = false">
                <div class="rqp-modal__box" role="dialog" aria-modal="true">
                    <h5 class="fw-bold mb-1"><i class="fa-solid fa-user-check me-2 text-primary"></i>[[ dialog.editing ? 'Edit the review' + (dialog.editing.user && (!myReview || myReview.uuid !== dialog.editing.uuid) ? ' of ' + dialog.editing.user.name : '') : 'Review this rule' ]]</h5>
                    <p class="text-muted small mb-3">Read the rule, then say whether it is good to use as is. Your review counts for this version only — an edit asks for a new one — and shows in its history. You can edit or delete it later.</p>
                    <div class="rqp-verdicts">
                        <button type="button" :class="{ 'is-on is-ok': dialog.verdict === 'approved' }" @click="dialog.verdict = 'approved'">
                            <i class="fa-solid fa-circle-check"></i><span><strong>Approve</strong><small>It does what it says, it's usable.</small></span></button>
                        <button type="button" :class="{ 'is-on is-warn': dialog.verdict === 'changes_requested' }" @click="dialog.verdict = 'changes_requested'">
                            <i class="fa-solid fa-pen-to-square"></i><span><strong>Request changes</strong><small>Something should be fixed first.</small></span></button>
                    </div>
                    <div class="rqp-field mt-3">
                        <span class="rqp-field__label">Rating</span>
                        <span class="rqp-stars rqp-stars--input">
                            <button v-for="n in 5" :key="n" type="button" @click="dialog.rating = dialog.rating === n ? 0 : n" :title="n + ' / 5'"
                                    @mouseenter="dialog.hover = n" @mouseleave="dialog.hover = 0">
                                <i class="fa-solid fa-star" :class="{ 'is-empty': n > (dialog.hover || dialog.rating) }"></i></button>
                        </span>
                        <span class="text-muted small">[[ dialog.rating ? dialog.rating + ' / 5' : 'no rating' ]]</span>
                    </div>
                    <div class="rqp-field mt-2">
                        <span class="rqp-field__label">Written</span>
                        <div class="rqp-written__seg">
                            <button v-for="w in WRITTEN_WITH" :key="w.value" type="button" :class="{ 'is-on': dialog.written_with === w.value }"
                                    @click="dialog.written_with = dialog.written_with === w.value ? '' : w.value"><i :class="w.icon"></i>[[ w.label ]]</button>
                        </div>
                    </div>
                    <div class="rqp-field mt-2">
                        <span class="rqp-field__label">Scope</span>
                        <select v-if="myScopes.length && (!dialog.editing || (myReview && myReview.uuid === dialog.editing.uuid))" class="form-select form-select-sm rqp-scope-select" v-model="dialog.scope_id">
                            <option value="">No scope</option>
                            <option v-for="sc in myScopes" :key="sc.id" :value="sc.id">[[ scopeLabel(sc) ]]</option>
                        </select>
                        <span v-else class="text-muted small">You declared no scope on this rule.</span>
                        <button type="button" class="rqp-link small" @click="openScopeDialog()">
                            <i class="fa-solid fa-globe me-1"></i>[[ myScopes.length ? 'Declare another' : 'Declare where it works' ]]</button>
                    </div>
                    <p v-if="canModerate" class="text-muted small mt-1 mb-0">As owner / admin, what you choose here is shown as how the rule was written.</p>
                    <div class="mt-3">
                        <markdown-composer v-model="dialog.comment" :rows="4"
                                           :placeholder="dialog.verdict === 'approved' ? 'Comment (optional, Markdown) — what you checked' : 'What should change? (required, Markdown)'"></markdown-composer>
                    </div>
                    <div class="d-flex justify-content-end gap-2 mt-3">
                        <button type="button" class="btn btn-light rounded-pill" @click="dialog.open = false">Cancel</button>
                        <button type="button" class="btn btn-primary rounded-pill px-4" :disabled="dialog.saving || (dialog.verdict === 'changes_requested' && !dialog.comment.trim())" @click="saveReview()">
                            <span v-if="dialog.saving" class="spinner-border spinner-border-sm me-1"></span>Save the review</button>
                    </div>
                </div>
            </div>
            <div v-if="scopeDialog.open" class="rqp-modal rqp-modal--top" @click.self="scopeDialog.open = false">
                <div class="rqp-modal__box" role="dialog" aria-modal="true">
                    <h5 class="fw-bold mb-1"><i class="fa-solid fa-globe me-2 text-primary"></i>Declare where it works</h5>
                    <p class="text-muted small mb-3">Same as the Scope tab: does the rule work in your environment, and which one.</p>
                    <div class="sc-choice mb-3">
                        <button type="button" @click="scopeDialog.works = true" :class="['sc-choice__btn', { 'is-ok': scopeDialog.works }]"><i class="fa-solid fa-check"></i>Works for me</button>
                        <button type="button" @click="scopeDialog.works = false" :class="['sc-choice__btn', { 'is-ko': !scopeDialog.works }]"><i class="fa-solid fa-xmark"></i>Doesn't work</button>
                    </div>
                    <label class="sc-label">Environment <span class="sc-muted fw-normal">— where you ran it</span></label>
                    <div class="sc-criteria mb-2">
                        <div v-for="(entry, idx) in scopeDialog.entries" :key="idx" class="sc-criteria__row">
                            <select v-model="entry.key" @change="entry.value = ''" class="form-select form-select-sm">
                                <option v-for="k in scopeKeys" :key="k.key" :value="k.key">[[ k.label ]]</option>
                            </select>
                            <select v-if="scopeKeyOptions(entry.key)" v-model="entry.value" class="form-select form-select-sm">
                                <option value="" disabled>Choose…</option>
                                <option v-for="opt in scopeKeyOptions(entry.key)" :key="opt" :value="opt">[[ opt ]]</option>
                            </select>
                            <input v-else v-model="entry.value" class="form-control form-control-sm" maxlength="100" placeholder="e.g. 10.0.19045, 7.1…">
                            <button type="button" @click="scopeDialog.entries.splice(idx, 1)" class="sc-icon-btn" title="Remove"><i class="fa-solid fa-xmark"></i></button>
                        </div>
                        <p v-if="!scopeDialog.entries.length" class="sc-muted mb-0">No criterion yet — OS, protocol, software, version…</p>
                    </div>
                    <div class="d-flex flex-wrap gap-2 mb-3">
                        <button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3" :disabled="scopeDialog.entries.length >= 20"
                                @click="scopeDialog.entries.push({ key: 'os', value: '' })"><i class="fa-solid fa-plus me-1"></i>Add a criterion</button>
                        <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-3" @click="scopeMyMachine()"
                                title="Fill the operating system, architecture and version of this computer (asks first)"><i class="fa-solid fa-laptop me-1"></i>My machine</button>
                    </div>
                    <label class="sc-label">Notes <span class="sc-muted fw-normal">— optional, Markdown supported</span></label>
                    <markdown-composer v-model="scopeDialog.comment" :rows="3" placeholder="e.g. Fires on our legacy AD where NTLMv1 is still enabled…"></markdown-composer>
                    <div class="d-flex justify-content-end gap-2 mt-3">
                        <button type="button" class="btn btn-light rounded-pill" @click="scopeDialog.open = false">Cancel</button>
                        <button type="button" class="btn btn-primary rounded-pill px-4" :disabled="scopeDialog.saving || (scopeDialog.comment || '').length > 10000" @click="saveScope()">
                            <span v-if="scopeDialog.saving" class="spinner-border spinner-border-sm me-1"></span>Save the scope</button>
                    </div>
                </div>
            </div>
        </teleport>
    </section>`,
};
