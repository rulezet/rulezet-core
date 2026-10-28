/**
 * YaraEditRulePanel.js — "YARA editor" tab of the edit page (YARA rules only), next to the classic
 * editor, which stays as it is. The rule editor from app/modules/rulezet-editor, with:
 *
 *   - the rule being edited, free to edit;
 *   - every rule it needs (GET /editor-api/yara/rules/<id>/dependencies, transitively, in compile
 *     order) above it, LOCKED: they are other Rulezet rules, shown so the document compiles and
 *     tests as a whole. A dependency can be unlocked only by its owner or an admin (`can_edit`);
 *   - the Test panel (rulezet-tester): the whole document runs, dependencies included.
 *
 * The form still posts one field, `to_string`: this panel keeps it (v-model) equal to the edited
 * rule alone, with the imports it uses. Dependencies that were unlocked and changed are saved too,
 * through the YARA editor's import (POST /editor-api/yara/import: owner/admin -> new version),
 * after a confirmation, when the form is submitted (beforeSubmit()).
 *
 * Fields panel (open): the rule's Rulezet fields (title, CVE, tags, ATT&CK, linked rules...), read
 * from the edit form (setFromForm) and sent back to it on every change (`fields` event); nothing is
 * written into the rule text unless the user ticks it (editing the text stops GitHub updates).
 *
 * Props:  active, ruleId, modelValue (the form's to_string), csrfToken, author
 * Emits:  update:modelValue, fields (values of the edited rule's fields), ready
 */
import { linkedRulesPicker } from '/static/js/rule_relation/rulePicker.js'
import { RULEZET_EDITOR_CREDITS } from '/static/js/editor/editorCredits.js'
import { create_message } from '/static/js/toaster.js'

const { ref, watch, onMounted, onBeforeUnmount, nextTick } = Vue

const EDITOR_JS = '/editor-api/assets/rulezet-editor.js'
const EDITOR_CSS = '/editor-api/assets/rulezet-editor.css'
const IMPORT_LINE = /^\s*import\s+"([^"]+)"\s*$/gm

function loadCss() {
    if (document.querySelector(`link[href^="${EDITOR_CSS}"]`)) return
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = EDITOR_CSS
    document.head.appendChild(link)
}

const norm = (s) => (s || '').replace(/\s+/g, '')
const importsOf = (text) => [...(text || '').matchAll(IMPORT_LINE)].map(m => m[1])
const withoutImports = (text) => (text || '').replace(IMPORT_LINE, '').trim()

export default {
    name: 'YaraEditRulePanel',
    delimiters: ['[[', ']]'],
    props: {
        active:     { type: Boolean, default: false },
        ruleId:     { type: [String, Number], required: true },
        modelValue: { type: String, default: '' },
        csrfToken:  { type: String, default: '' },
        tests:      { type: Boolean, default: false },
        author:     { type: String, default: '' },
    },
    emits: ['update:modelValue', 'fields', 'ready'],
    setup(props, { emit, expose }) {
        const host = ref(null)
        const loading = ref(false)
        const loadError = ref('')
        const deps = ref([])                 // [{ id, name, content, can_edit, url }]
        const unlocked = ref([])             // names of dependencies unlocked by the user
        const problem = ref('')              // why the edited rule cannot be read from the document
        let editor = null
        let lastEmitted = null
        let applyingForm = false
        let pendingForm = null

        /** The edited rule's name in the document (the one that is not a dependency). */
        function mainName() {
            if (!editor) return null
            const depNames = new Set(deps.value.map(d => d.name))
            const mine = editor.getRules().filter(r => !depNames.has(r.name))
            return mine.length === 1 ? mine[0].name : null
        }

        /** The edit form's values -> the Fields panel (on load, and when the classic tab changed them). */
        function setFromForm(values) {
            const name = mainName()
            if (!editor || !name) { pendingForm = values; return }
            editor.pickFieldsRule(name)          // the edited rule, not a dependency above it
            applyingForm = true
            try { editor.setFieldValues(name, values, { report: false }) } finally { applyingForm = false }
        }

        /** The document: every import, the dependencies (compile order), then the edited rule. */
        function buildDocument(mainText, depTexts) {
            const imports = [...new Set([...depTexts.flatMap(importsOf), ...importsOf(mainText)])]
            const head = imports.map(m => `import "${m}"`).join('\n')
            const parts = [...depTexts.map(withoutImports), withoutImports(mainText)].filter(Boolean)
            return (head ? head + '\n\n' : '') + parts.join('\n\n') + '\n'
        }

        /** The edited rule alone (with the imports it uses), or null when it cannot be told apart. */
        function editedRule() {
            const depNames = new Set(deps.value.map(d => d.name))
            const mine = editor.getRules().filter(r => !depNames.has(r.name))
            if (mine.length !== 1) {
                problem.value = mine.length
                    ? `The document holds ${mine.length} rules besides the dependencies: keep only the rule you are editing (the others belong in their own rule page).`
                    : 'The rule you are editing is no longer in the document.'
                return null
            }
            problem.value = ''
            const text = mine[0].text.trim()
            const used = (editor.getModel().imports || []).map(i => i.name).filter(m => new RegExp(`\\b${m}\\s*\\.`).test(text))
            return (used.length ? used.map(m => `import "${m}"`).join('\n') + '\n\n' : '') + text + '\n'
        }

        function sync() {
            if (!editor) return
            const text = editedRule()
            if (text === null || norm(text) === norm(props.modelValue)) return
            lastEmitted = text
            emit('update:modelValue', text)
        }

        function depText(name) {
            const r = editor.getRules().find(x => x.name === name)
            return r ? r.text : null
        }

        function changedDeps() {
            if (!editor) return []
            return deps.value.filter(d => unlocked.value.includes(d.name))
                .map(d => ({ dep: d, text: depText(d.name) }))
                .filter(x => x.text !== null && norm(x.text) !== norm(withoutImports(x.dep.content)))
        }

        function lockDeps(keepUnlocked = []) {
            for (const d of deps.value) {
                if (keepUnlocked.includes(d.name)) continue
                editor.lockRule(d.name, { label: 'Rulezet (dependency)', canUnlock: !!d.can_edit, url: d.url })
            }
        }

        async function load() {
            if (editor || loading.value) return
            loading.value = true
            loadError.value = ''
            try {
                loadCss()
                const [lib, res] = await Promise.all([
                    import(EDITOR_JS).catch(e => { throw new Error(`${EDITOR_JS} could not be loaded (${e.message || e})`) }),
                    fetch(`/editor-api/yara/rules/${props.ruleId}/dependencies`),
                ])
                const data = await res.json().catch(() => ({}))
                if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
                deps.value = data.dependencies || []
                await nextTick()
                editor = new lib.RulezetEditor(host.value, {
                    language: 'yara',
                    theme: 'auto',
                    height: '75vh',
                    outline: deps.value.length ? true : 'auto',
                    author: props.author || null,
                    host: new lib.EditorServerHost({ baseUrl: '/editor-api', csrfToken: props.csrfToken, name: 'Rulezet' }),
                    value: buildDocument(props.modelValue, deps.value.map(d => d.content)),
                    // an existing rule: fields are stored by Rulezet, the rule text is only touched on request
                    fieldsReport: false,
                    credits: RULEZET_EDITOR_CREDITS,   // Rulezet's section of the Credits & licences page
                    pickValues: linkedRulesPicker(props.csrfToken, [Number(props.ruleId)]),   // "Linked rules" → Browse: Rulezet's rule list in a modal
                    tests: props.tests ? 'auto' : false,      // tests on samples: Rulezet setting editor.test_access
                    toast: (message, tone) => create_message(message, { success: 'success', warning: 'warning', error: 'danger' }[tone] || 'info'),
                })
                editor.on('fields', (payload) => {
                    const name = mainName()
                    if (applyingForm || !payload || payload.rule !== name || !payload.values) return
                    emit('fields', payload.values)
                })
                lockDeps()
                editor.on('locks', (locks) => {
                    const locked = new Set(locks.map(l => l.name))
                    unlocked.value = deps.value.map(d => d.name).filter(n => !locked.has(n))
                })
                editor.on('change', sync)
                editor.on('save', sync)
                sync()
                if (pendingForm) { const v = pendingForm; pendingForm = null; setFromForm(v) }
                emit('ready')
            } catch (e) {
                loadError.value = `The YARA editor could not start: ${e.message || e}`
            } finally {
                loading.value = false
            }
        }

        // the classic tab changed the rule: put its version in the document, dependencies kept
        function pullFromForm() {
            if (!editor || props.modelValue === lastEmitted) return
            const current = editedRule()
            if (current !== null && norm(current) === norm(props.modelValue)) return
            const keep = unlocked.value.slice()
            const depTexts = deps.value.map(d => depText(d.name) ?? d.content)
            editor.setValue(buildDocument(props.modelValue, depTexts))
            lockDeps(keep)
            sync()
        }

        /** Called by the page before the form is posted: false = do not post. */
        async function beforeSubmit() {
            if (!editor) return true
            if (editedRule() === null) {
                create_message(problem.value, 'danger')
                return false
            }
            const changed = changedDeps()
            if (!changed.length) return true
            const names = changed.map(c => c.dep.name).join(', ')
            if (!window.confirm(`You also changed ${changed.length} dependency rule(s): ${names}.\n\nSave them too (a new version of each)? Cancel keeps the page open.`)) return false
            try {
                const res = await fetch('/editor-api/yara/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({
                        imports: (editor.getModel().imports || []).map(i => i.name),
                        rules: changed.map(c => ({ id: c.dep.id, name: c.dep.name, text: c.text })),
                    }),
                })
                const data = await res.json().catch(() => ({}))
                const bad = (data.rules || []).filter(r => !['updated', 'exists'].includes(r.status))
                if (!res.ok || !data.ok || bad.length) {
                    const why = bad.map(r => `${r.name}: ${(r.errors || []).map(e => e.message).join('; ') || r.status}`).join(' — ')
                    create_message(`The dependencies were not saved: ${why || data.error || res.status}`, 'danger')
                    return false
                }
                return true
            } catch (e) {
                create_message(`The dependencies were not saved: ${e.message || e}`, 'danger')
                return false
            }
        }

        expose({ beforeSubmit, setFromForm })
        watch(() => props.active, (on) => { if (on) { load(); pullFromForm() } })
        watch(() => props.modelValue, () => { if (!props.active) return; pullFromForm() })
        onMounted(() => { if (props.active) load() })
        onBeforeUnmount(() => { if (editor) editor.destroy() })

        return { host, loading, loadError, deps, unlocked, problem }
    },
    template: `
    <div class="yara-edit-panel">
        <div class="d-flex align-items-start gap-2 mb-2 small text-muted">
            <i class="fas fa-circle-info mt-1"></i>
            <div>
                The rule and <b>the [[ deps.length ]] rule(s) it needs</b>, so the whole thing compiles and can be tested
                (Test button). The rules it needs are <b>locked</b>: unlock one only if it is yours (or you are an admin)
                and you mean to change it too — it is then saved with this rule. The classic editor tab edits the same rule.
            </div>
        </div>
        <div v-if="loadError" class="alert alert-danger py-2 small">[[ loadError ]]</div>
        <div v-if="loading" class="text-muted small py-2"><i class="fas fa-spinner fa-spin me-1"></i>Loading the editor…</div>
        <div v-if="problem" class="alert alert-warning py-2 small mb-2"><i class="fas fa-triangle-exclamation me-1"></i>[[ problem ]]</div>
        <div v-if="unlocked.length" class="alert alert-info py-2 small mb-2">
            <i class="fas fa-unlock me-1"></i>Unlocked: <b>[[ unlocked.join(', ') ]]</b> — if you change them, they are saved with this rule (you will be asked).
        </div>
        <div ref="host" style="min-height: 75vh;"></div>
    </div>`,
}
