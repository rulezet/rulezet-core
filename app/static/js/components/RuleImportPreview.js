/**
 * RuleImportPreview.js — what a JSON import will create for one rule.
 *
 * Props:
 *   preview   Object (required) — preview_rule() from rule_portable.py:
 *             { fields: [{key, label, value}], valid, error,
 *               existing: {kind, id, title} | null,
 *               tags: [{name, found}], attacks: [{id, found}] }
 *   compact   Boolean — hide the content viewer and the empty fields (bundle modal)
 *
 * Used by the "From JSON" tab of the create-rule page and the bundle JSON import modal.
 */
import CodeViewer from '/static/js/components/code-viewer.js';

const EXISTING_LABELS = {
    uuid: 'A rule with this UUID already exists',
    content: 'A rule with this exact content already exists',
    trash: 'A rule with this content is in the trash',
};

export default {
    name: 'RuleImportPreview',
    components: { 'code-viewer': CodeViewer },
    props: {
        preview: { type: Object, required: true },
        compact: { type: Boolean, default: false },
    },
    computed: {
        content() {
            return (this.preview.fields.find(f => f.key === 'to_string') || {}).value || '';
        },
        format() {
            return (this.preview.fields.find(f => f.key === 'format') || {}).value || 'text';
        },
        rows() {
            return this.preview.fields.filter(f => f.key !== 'to_string'
                && (!this.compact || (Array.isArray(f.value) ? f.value.length : f.value)));
        },
        existingLabel() {
            const e = this.preview.existing;
            return e ? EXISTING_LABELS[e.kind] || 'This rule already exists' : '';
        },
    },
    methods: {
        display(value) {
            if (Array.isArray(value)) return value.length ? value.join(', ') : '';
            return value || '';
        },
    },
    template: `
    <div class="rip">
        <div v-if="!preview.valid" class="rip-status rip-status--error">
            <i class="fas fa-circle-xmark"></i><span>Invalid rule: [[ preview.error ]]</span>
        </div>
        <div v-else-if="preview.existing" class="rip-status rip-status--warn">
            <i class="fas fa-triangle-exclamation"></i>
            <span>[[ existingLabel ]]:
                <a :href="'/rule/detail_rule/' + preview.existing.id" target="_blank" rel="noopener">[[ preview.existing.title ]]</a>
            </span>
        </div>
        <div v-else class="rip-status rip-status--ok">
            <i class="fas fa-circle-check"></i><span>Valid — a new rule will be created under your account.</span>
        </div>

        <div class="rip-grid">
            <div v-for="f in rows" :key="f.key" class="rip-cell">
                <div class="rip-label">[[ f.label ]]</div>
                <div class="rip-value" :class="{ 'rip-value--empty': !display(f.value) }">
                    [[ display(f.value) || 'empty — default value' ]]
                </div>
            </div>
            <div class="rip-cell rip-cell--wide">
                <div class="rip-label">Tags</div>
                <div class="rip-value">
                    <span v-if="!preview.tags.length" class="rip-value--empty">none</span>
                    <span v-for="t in preview.tags" :key="t.name" class="rip-chip" :class="{ 'rip-chip--missing': !t.found }"
                          :title="t.found ? 'Will be attached' : 'Unknown on this instance — skipped'">
                        <i class="fas" :class="t.found ? 'fa-tag' : 'fa-ban'"></i>[[ t.name ]]
                    </span>
                </div>
            </div>
            <div class="rip-cell rip-cell--wide">
                <div class="rip-label">ATT&amp;CK techniques</div>
                <div class="rip-value">
                    <span v-if="!preview.attacks.length" class="rip-value--empty">none</span>
                    <span v-for="a in preview.attacks" :key="a.id" class="rip-chip" :class="{ 'rip-chip--missing': !a.found }"
                          :title="a.found ? 'Will be attached' : 'Unknown on this instance — skipped'">
                        <i class="fas" :class="a.found ? 'fa-crosshairs' : 'fa-ban'"></i>[[ a.id ]]
                    </span>
                </div>
            </div>
        </div>

        <code-viewer v-if="!compact" :code="content" :language="format" title="Content" max-height="320px"></code-viewer>
    </div>`,
    delimiters: ['[[', ']]'],
};
