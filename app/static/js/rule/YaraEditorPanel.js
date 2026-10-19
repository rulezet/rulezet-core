/**
 * YaraEditorPanel.js — "YARA editor" tab of the create-rule page: the rule editor from
 * app/modules/rulezet-editor (completion, lint checked against libyara, quick fixes, rule
 * tools, several rules per document), backed by this Rulezet through /editor-api.
 *
 * Saving posts the whole document to /rule/parse_rule (format yara), exactly like the
 * Parse tab: every rule of the document is created, with its metadata read from meta:.
 *
 * Props:
 *   active     Boolean — the tab is shown; the editor is loaded the first time it is
 *   csrfToken  String
 *   author     String — offered by the "Set author" rule tool
 *   parseUrl   String — url_for('rule.parse_rule')
 */
const { ref, watch, onMounted, onBeforeUnmount, nextTick } = Vue

const EDITOR_JS = '/editor-api/assets/rulezet-editor.js'
const EDITOR_CSS = '/editor-api/assets/rulezet-editor.css'

function loadCss() {
    if (document.querySelector(`link[href^="${EDITOR_CSS}"]`)) return
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = EDITOR_CSS
    document.head.appendChild(link)
}

export default {
    name: 'YaraEditorPanel',
    delimiters: ['[[', ']]'],
    props: {
        active:    { type: Boolean, default: false },
        csrfToken: { type: String, default: '' },
        author:    { type: String, default: '' },
        parseUrl:  { type: String, default: '/rule/parse_rule' },
    },
    setup(props) {
        const host = ref(null)
        const form = ref(null)
        const content = ref('')
        const loading = ref(false)
        const loadError = ref('')
        const errors = ref(0)
        const warnings = ref(0)
        const ruleCount = ref(0)
        const submitting = ref(false)
        let editor = null

        async function load() {
            if (editor || loading.value) return
            loading.value = true
            loadError.value = ''
            try {
                loadCss()
                const lib = await import(EDITOR_JS)
                await nextTick()
                editor = new lib.RulezetEditor(host.value, {
                    language: 'yara',
                    theme: 'auto',
                    height: '70vh',
                    author: props.author || null,
                    host: new lib.EditorServerHost({ baseUrl: '/editor-api', csrfToken: props.csrfToken, name: 'Rulezet' }),
                    draftKey: 'rulezet-create-yara',
                })
                editor.on('diagnostics', (d) => {
                    errors.value = d.filter(x => x.severity === 'error').length
                    warnings.value = d.filter(x => x.severity === 'warning').length
                    ruleCount.value = editor.getRules().length
                })
                editor.on('save', () => submit())
                // an empty document starts from the rule template (id, author, date filled in)
                if (!editor.getValue().trim()) editor.newRule()
            } catch (e) {
                loadError.value = `The editor could not be loaded (${e.message || e}). Is app/modules/rulezet-editor installed?`
            } finally {
                loading.value = false
            }
        }

        function submit() {
            if (!editor || submitting.value) return
            const text = editor.getValue()
            if (!text.trim()) return
            if (errors.value > 0 && !window.confirm(`The document still has ${errors.value} error(s): Rulezet will refuse the broken rules. Save anyway?`)) return
            content.value = text
            submitting.value = true
            editor.clearDraft()
            nextTick(() => form.value.submit())
        }

        watch(() => props.active, (on) => { if (on) load() })
        onMounted(() => { if (props.active) load() })
        onBeforeUnmount(() => { if (editor) editor.destroy() })

        return { host, form, content, loading, loadError, errors, warnings, ruleCount, submitting, submit }
    },
    template: `
    <div>
        <div class="d-flex align-items-center gap-2 mb-1">
            <i class="fas fa-code text-primary"></i>
            <h5 class="fw-bold mb-0">YARA editor</h5>
            <span class="badge bg-warning-subtle text-warning-emphasis rounded-pill" style="font-size:.6rem;">BETA</span>
        </div>
        <p class="text-muted mb-3" style="font-size:.83rem;">
            Write one or several YARA rules: errors are checked as you type (and by Rulezet's compiler),
            names of existing Rulezet rules are suggested, <kbd>Ctrl+Shift+R</kbd> opens the rule tools
            (date, id, tags, author, references…). Each rule is created with the metadata of its <code>meta:</code> section.
        </p>

        <div v-if="loadError" class="alert alert-danger">[[ loadError ]]</div>
        <div v-if="loading" class="text-muted small mb-2"><i class="fas fa-spinner fa-spin me-1"></i>Loading the editor…</div>
        <div ref="host" style="min-height: 70vh;"></div>

        <form ref="form" method="POST" :action="parseUrl" class="d-flex align-items-center gap-3 mt-3">
            <input type="hidden" name="csrf_token" :value="csrfToken">
            <input type="hidden" name="format" value="yara">
            <input type="hidden" name="content" :value="content">
            <span class="small text-muted">
                [[ ruleCount ]] rule[[ ruleCount === 1 ? '' : 's' ]]
                · <span :class="errors ? 'text-danger fw-semibold' : ''">[[ errors ]] error[[ errors === 1 ? '' : 's' ]]</span>
                · [[ warnings ]] warning[[ warnings === 1 ? '' : 's' ]]
            </span>
            <button type="button" class="btn btn-success px-4 ms-auto" style="border-radius:8px;"
                    :disabled="submitting || !ruleCount" @click="submit">
                <i class="fa-solid fa-floppy-disk me-2"></i>[[ submitting ? 'Saving…' : 'Save rules' ]]
            </button>
        </form>
    </div>`,
}
