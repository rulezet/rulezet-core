/**
 * BundleJsonImport.js — admin "Import from JSON" section of the create-bundle page.
 *
 * Paste a bundle export (Download → Bundle JSON on another instance), click
 * "Review import": a modal summarises what will be created — bundle fields,
 * every rule (new / already here / invalid), structure, notes, AI analyses,
 * releases — before anything is written. When the bundle already exists here
 * (imported before, or the same instance) the modal offers to update it in
 * place instead of creating a copy. Server side: bundle_portable.py.
 */
import SmartEditor from '/static/js/components/smart-editor.js';
import RuleImportPreview from '/static/js/components/RuleImportPreview.js';
import { create_message } from '/static/js/toaster.js';

const ACTIONS = {
    create:   { label: 'New — will be created', icon: 'fa-circle-plus', cls: 'bji-badge--create' },
    update:   { label: 'Already here — will be updated', icon: 'fa-rotate', cls: 'bji-badge--update' },
    existing: { label: 'Already here — reused', icon: 'fa-triangle-exclamation', cls: 'bji-badge--existing' },
    invalid:  { label: 'Invalid — skipped', icon: 'fa-circle-xmark', cls: 'bji-badge--invalid' },
    trash:    { label: 'In the trash — skipped', icon: 'fa-trash', cls: 'bji-badge--invalid' },
};

export default {
    name: 'BundleJsonImport',
    components: { 'smart-editor': SmartEditor, 'rule-import-preview': RuleImportPreview },
    delimiters: ['[[', ']]'],
    data() {
        return { open: false, raw: '', loading: false, importing: false, error: '', preview: null,
                 name: '', mode: 'create', releaseBefore: true, expanded: null, ACTIONS };
    },
    computed: {
        canImport() {
            return this.preview && this.name.trim() && !this.importing;
        },
        nameTaken() {
            if (!this.preview) return false;
            const eb = this.preview.existing_bundle;
            if (this.mode === 'update') return !!(eb && eb.name_taken && this.name.trim() === this.preview.bundle.name);
            return this.preview.bundle.name_taken && this.name.trim() === this.preview.bundle.name;
        },
    },
    methods: {
        csrf() { return document.getElementById('csrf_token')?.value || ''; },
        onFile(e) {
            const f = e.target.files[0];
            if (!f) return;
            f.text().then(t => { this.raw = t; });
        },
        async review() {
            this.error = '';
            this.loading = true;
            try {
                const res = await fetch('/bundle/import_json/preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrf() },
                    body: JSON.stringify({ bundle_json: this.raw }),
                });
                const data = await res.json().catch(() => ({}));
                if (!data.success) { this.error = data.message || 'Preview failed.'; return; }
                this.preview = data.preview;
                this.name = data.preview.bundle.name;
                const eb = data.preview.existing_bundle;
                this.mode = eb && eb.can_update ? 'update' : 'create';
                this.expanded = null;
                bootstrap.Modal.getOrCreateInstance(this.$refs.modal).show();
            } catch {
                this.error = 'Preview failed.';
            } finally {
                this.loading = false;
            }
        },
        async doImport() {
            this.importing = true;
            try {
                const res = await fetch('/bundle/import_json', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrf() },
                    body: JSON.stringify({ bundle_json: this.raw, name: this.name.trim(), mode: this.mode, release_before: this.releaseBefore }),
                });
                const data = await res.json().catch(() => ({}));
                if (!data.success) { create_message(data.message || 'Import failed.', 'danger-subtle'); return; }
                const r = data.report;
                if (r.release_before) create_message(`Release ${r.release_before} saved the bundle as it was before the update.`, 'info-subtle');
                create_message(`Bundle ${r.mode === 'update' ? 'updated' : 'imported'} — ${r.created.length} rule(s) created, ${r.updated.length} updated, ${r.reused.length} unchanged, ${r.skipped.length} skipped.`, 'success-subtle');
                window.location.href = data.url;
            } catch {
                create_message('Import failed.', 'danger-subtle');
            } finally {
                this.importing = false;
            }
        },
    },
    template: `
    <div class="card border-0 shadow-sm rounded-3 mb-4 bji">
        <button type="button" class="bji-toggle" @click="open = !open" :aria-expanded="open">
            <span><i class="fa-solid fa-file-import me-2"></i>Import from JSON
                <span class="badge bg-primary-subtle text-primary-emphasis rounded-pill ms-1">admin</span></span>
            <i class="fa-solid" :class="open ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
        </button>
        <div v-show="open" class="card-body p-4 pt-2">
            <p class="bc-hint mb-3">Paste a bundle exported with <strong>Download → Bundle JSON</strong> (from this or another instance).
                Rules missing here are created under your account after being checked; rules that already exist are reused. You'll see a full summary before anything is created.</p>
            <div class="d-flex justify-content-end mb-2">
                <label class="bd-btn bd-btn--ghost bji-file"><i class="fa-solid fa-upload"></i><span>Load a .json file</span>
                    <input type="file" accept=".json,application/json" @change="onFile" hidden></label>
            </div>
            <smart-editor v-model="raw" mode="code" language="json"
                placeholder='{"format": "rulezet-bundle", "bundle": {...}, "rules": [...]}'
                min-height="220px" max-height="50vh"></smart-editor>
            <div v-if="error" class="alert alert-danger py-2 px-3 mt-2 mb-0" style="font-size:.82rem;">
                <i class="fas fa-circle-exclamation me-1"></i>[[ error ]]</div>
            <div class="d-flex justify-content-end mt-3">
                <button type="button" class="bd-btn bd-btn--primary" :disabled="!raw.trim() || loading" @click="review">
                    <i class="fa-solid" :class="loading ? 'fa-spinner fa-spin' : 'fa-magnifying-glass'"></i><span>Review import</span>
                </button>
            </div>
        </div>

        <div class="modal fade" ref="modal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-xl modal-dialog-scrollable">
                <div class="modal-content" v-if="preview">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fa-solid fa-box-archive me-2 text-primary"></i>Import summary</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="bji-kpis">
                            <div class="bji-kpi"><strong>[[ preview.counts.create ]]</strong><span>rules to create</span></div>
                            <div class="bji-kpi bji-kpi--upd"><strong>[[ preview.counts.update ]]</strong><span>rules to update</span></div>
                            <div class="bji-kpi bji-kpi--warn"><strong>[[ preview.counts.existing ]]</strong><span>already here, unchanged</span></div>
                            <div class="bji-kpi bji-kpi--err"><strong>[[ preview.counts.invalid + preview.counts.trash ]]</strong><span>skipped</span></div>
                            <div class="bji-kpi"><strong>[[ preview.structure.folders ]] / [[ preview.structure.files ]]</strong><span>folders / files</span></div>
                            <div class="bji-kpi"><strong>[[ preview.notes ]]</strong><span>notes</span></div>
                            <div class="bji-kpi"><strong>[[ preview.ai_analyses ]]</strong><span>AI analyses</span></div>
                            <div class="bji-kpi"><strong>[[ preview.releases.length ]]</strong><span>releases</span></div>
                        </div>

                        <div v-if="preview.existing_bundle" class="bji-existing">
                            <div class="fw-semibold mb-1"><i class="fa-solid fa-triangle-exclamation me-1"></i>This bundle already exists here:
                                <a :href="'/bundle/detail/' + preview.existing_bundle.id" target="_blank" rel="noopener">[[ preview.existing_bundle.name ]]</a>
                                <span class="text-muted fw-normal">— owner [[ preview.existing_bundle.owner ]], [[ preview.existing_bundle.rules ]] rule(s),
                                [[ preview.existing_bundle.notes ]] note(s)<template v-if="preview.existing_bundle.releases.length">, releases [[ preview.existing_bundle.releases.join(', ') ]]</template></span></div>
                            <label class="bji-mode" v-if="preview.existing_bundle.can_update">
                                <input type="radio" value="update" v-model="mode">
                                <div><strong>Update the existing bundle</strong><small>New rules are created and added; name, description, visibility, tags, rule list and tree replaced by the JSON's; changed rules updated (with history); notes, AI analyses and releases it doesn't have yet are added. Rules no longer in it are only unlinked.</small></div>
                            </label>
                            <label class="form-check ms-4 mt-2 mb-0" v-if="mode === 'update'">
                                <input class="form-check-input" type="checkbox" v-model="releaseBefore">
                                <span class="form-check-label"><strong>Release the bundle first</strong> — a release of its current state is published before the update, so it can be compared or downloaded as it was (skipped when nothing changed since the last release).</span>
                            </label>
                            <label class="bji-mode">
                                <input type="radio" value="create" v-model="mode">
                                <div><strong>Create a new copy</strong><small>A separate bundle under your account, the existing one is left untouched.</small></div>
                            </label>
                        </div>

                        <h6 class="bji-h">Bundle</h6>
                        <div class="rounded-3 border p-3 mb-3" style="background:var(--light-bg-color);">
                            <label class="bc-label">Name</label>
                            <input class="form-control mb-1" :class="{ 'is-invalid': nameTaken }" v-model="name" maxlength="255">
                            <div v-if="nameTaken" class="invalid-feedback d-block">[[ mode === 'update' ? 'The owner already has another bundle with this name' : 'You already have a bundle with this name' ]] — change it to import.</div>
                            <div class="bji-meta mt-2">
                                <span><i class="fa-solid" :class="preview.bundle.access ? 'fa-globe' : 'fa-lock'"></i>[[ preview.bundle.access ? 'Public' : 'Private' ]]</span>
                                <span v-if="preview.bundle.instance"><i class="fa-solid fa-server"></i>From [[ preview.bundle.instance ]]</span>
                                <span v-if="preview.bundle.exported_at"><i class="fa-regular fa-clock"></i>Exported [[ preview.bundle.exported_at.slice(0, 16).replace('T', ' ') ]]</span>
                                <span v-if="preview.bundle.vulnerabilities.length"><i class="fa-solid fa-bug"></i>[[ preview.bundle.vulnerabilities.join(', ') ]]</span>
                                <span v-if="preview.releases.length"><i class="fa-solid fa-code-tag"></i>[[ preview.releases.join(', ') ]]</span>
                            </div>
                            <div v-if="preview.bundle.tags.length" class="mt-2">
                                <span v-for="t in preview.bundle.tags" :key="t.name" class="rip-chip" :class="{ 'rip-chip--missing': !t.found }"
                                      :title="t.found ? 'Will be attached' : 'Unknown here — skipped'"><i class="fas fa-tag"></i>[[ t.name ]]</span>
                            </div>
                            <details class="mt-2" v-if="preview.bundle.description">
                                <summary class="small text-muted">Description</summary>
                                <pre class="bji-desc">[[ preview.bundle.description ]]</pre>
                            </details>
                        </div>

                        <h6 class="bji-h">Rules ([[ preview.rules.length ]])</h6>
                        <div v-if="preview.counts.existing" class="alert alert-warning py-2 px-3" style="font-size:.82rem;">
                            <i class="fa-solid fa-triangle-exclamation me-1"></i>[[ preview.counts.existing + preview.counts.update ]] rule(s) already exist on this instance — they are linked, not duplicated[[ preview.counts.update ? '; ' + preview.counts.update + ' of them changed and will be updated' : '' ]].
                        </div>
                        <div class="bji-rules">
                            <div v-for="(r, i) in preview.rules" :key="r.ref + i" class="bji-rule">
                                <button type="button" class="bji-rule-head" @click="expanded = expanded === i ? null : i" :disabled="!r.preview">
                                    <span class="bji-badge" :class="ACTIONS[r.action].cls"><i class="fa-solid" :class="ACTIONS[r.action].icon"></i>[[ ACTIONS[r.action].label ]]</span>
                                    <span class="bji-rule-title">[[ r.title || '(untitled)' ]]</span>
                                    <span v-if="r.action === 'invalid'" class="bji-rule-err">[[ r.error ]]</span>
                                    <span v-if="r.action === 'update'" class="bji-rule-changes">changes: [[ r.changes.join(', ') ]]</span>
                                    <i v-if="r.preview" class="fa-solid ms-auto" :class="expanded === i ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
                                </button>
                                <div v-if="expanded === i && r.preview" class="p-3">
                                    <rule-import-preview :preview="r.preview"></rule-import-preview>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="bd-btn bd-btn--ghost" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="bd-btn bd-btn--primary" :disabled="!canImport || nameTaken" @click="doImport">
                            <i class="fa-solid" :class="importing ? 'fa-spinner fa-spin' : 'fa-plus'"></i><span>[[ mode === 'update' ? 'Update the bundle' : 'Create the bundle' ]]</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>`,
};
