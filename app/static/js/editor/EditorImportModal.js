/**
 * EditorImportModal.js — the one modal of the editor's "create" flows (create page tab and
 * /editor), styled like the detail pages (css/editor/editor-ui.css):
 *
 *   preview    the bundle's folders and files, before creating it
 *   planning   quick check running
 *   confirm    what happens to each rule (new / in Rulezet / update / proposal), the bundle form
 *              and structure when making a bundle — the user confirms
 *   running    the background job's steps, live
 *   done       what was written (rules, bundle), with links
 *   failed     nothing written: the rules to fix (the editor shows them on their lines)
 *
 * Props:
 *   state       { phase, kind: 'rules' | 'create-bundle' | 'save-bundle', rules, job, rows }
 *   bundleForm  { name, description, public } (create-bundle)
 *   bundleName  name of the bundle being saved (save-bundle)
 * Emits: close, confirm, fix, create-bundle (from the preview)
 */
const { computed } = Vue

export const STATUS = {
    new:      { label: 'New',           text: '' },
    exists:   { label: 'In Rulezet',    text: 'Already in Rulezet, unchanged: not imported again, used for the links' },
    update:   { label: 'Update',        text: 'Already in Rulezet and changed: a new version will be saved' },
    proposal: { label: 'Proposal',      text: 'Not yours: an edit proposal will be sent to its owner' },
    error:    { label: 'Error',         text: '' },
    blocked:  { label: 'Blocked',       text: '' },
    created:  { label: 'Created',       text: '' },
    updated:  { label: 'Updated',       text: 'New version saved' },
    proposed: { label: 'Proposal sent', text: 'The owner reviews it' },
}

const STEP_ICON = { pending: 'fa-regular fa-circle', running: 'fa-solid fa-spinner fa-spin', ok: 'fa-solid fa-check',
                    error: 'fa-solid fa-xmark', skipped: 'fa-solid fa-minus' }

export default {
    name: 'EditorImportModal',
    delimiters: ['[[', ']]'],
    props: {
        state:      { type: Object, required: true },
        bundleForm: { type: Object, default: () => ({ name: '', description: '', public: true }) },
        bundleName: { type: String, default: '' },
    },
    emits: ['close', 'confirm', 'fix', 'create-bundle'],
    setup(props, { emit }) {
        const phase = computed(() => props.state.phase)
        const kind = computed(() => props.state.kind || 'rules')
        const job = computed(() => props.state.job || null)
        const rules = computed(() => {
            const fromJob = job.value && job.value.rules && job.value.rules.length ? job.value.rules : null
            return fromJob || props.state.rules || []
        })
        const count = (s) => rules.value.filter(r => r.status === s).length
        const counts = computed(() => Object.fromEntries(Object.keys(STATUS).map(s => [s, count(s)])))
        const toFix = computed(() => rules.value.filter(r => r.status === 'error' || r.status === 'blocked'))
        const written = computed(() => ['created', 'updated', 'proposed', 'exists']
            .map(s => ({ status: s, rules: rules.value.filter(r => r.status === s) })).filter(g => g.rules.length))
        const busy = computed(() => phase.value === 'planning' || phase.value === 'running')

        const head = computed(() => {
            const n = rules.value.length
            const plural = (k, word) => `${k} ${word}${k === 1 ? '' : 's'}`
            switch (phase.value) {
                case 'preview': return { icon: 'fa-folder-tree', tone: '', title: 'Bundle preview', sub: 'What "Create bundle" makes from the explorer' }
                case 'planning': return { icon: 'fa-spinner fa-spin', tone: '', title: 'Preparing', sub: 'Looking for these rules in Rulezet…' }
                case 'confirm':
                    if (kind.value === 'create-bundle') return { icon: 'fa-box-archive', tone: 'success', title: 'Create a bundle', sub: `${plural(n, 'rule')}, checked again before anything is written` }
                    if (kind.value === 'save-bundle') return { icon: 'fa-floppy-disk', tone: 'warning', title: `Save "${props.bundleName}"`, sub: `${plural(n, 'rule')}, checked again before anything is written` }
                    return { icon: 'fa-file-import', tone: '', title: `Create ${plural(n, 'rule')}`, sub: 'Every rule is checked again before anything is written' }
                case 'running': return { icon: 'fa-spinner fa-spin', tone: '', title: 'Checking and writing', sub: 'Runs in the background, the editor is read-only meanwhile' }
                case 'done': return { icon: 'fa-check', tone: 'success', title: 'Done', sub: summary.value }
                default: return { icon: 'fa-xmark', tone: 'danger', title: 'Nothing was written', sub: `${plural(toFix.value.length, 'rule')} to fix, shown in the editor on their lines` }
            }
        })
        const summary = computed(() => {
            const parts = []
            if (counts.value.created) parts.push(`${counts.value.created} created`)
            if (counts.value.updated) parts.push(`${counts.value.updated} updated`)
            if (counts.value.proposed) parts.push(`${counts.value.proposed} proposed`)
            if (counts.value.exists) parts.push(`${counts.value.exists} already in Rulezet`)
            return parts.join(' · ') || 'Nothing to write'
        })
        const confirmClass = computed(() => counts.value.update ? 'ed-btn--warning' : kind.value === 'rules' ? 'ed-btn--primary' : 'ed-btn--success')
        const confirmLabel = computed(() => kind.value === 'rules' ? 'Check and create' : kind.value === 'save-bundle' ? 'Check and save' : 'Check and create the bundle')

        const close = () => { if (!busy.value) emit('close') }
        return { STATUS, STEP_ICON, phase, kind, job, rules, counts, toFix, written, busy, head, confirmClass, confirmLabel, close, emit }
    },
    template: `
    <div class="ed-modal" @click.self="close">
        <div class="ed-modal__box" role="dialog" aria-modal="true">
            <div class="ed-modal__head">
                <div class="ed-modal__icon" :class="head.tone ? 'ed-modal__icon--' + head.tone : ''"><i class="fas" :class="head.icon"></i></div>
                <div>
                    <h5 class="ed-modal__title">[[ head.title ]]</h5>
                    <p class="ed-modal__sub">[[ head.sub ]]</p>
                </div>
                <button v-if="!busy" type="button" class="ed-modal__close" aria-label="Close" @click="close"><i class="fas fa-xmark"></i></button>
            </div>

            <div class="ed-modal__body">
                <!-- bundle form -->
                <div v-if="phase === 'confirm' && kind === 'create-bundle'" class="ed-card">
                    <div class="ed-card__header"><span class="ed-card__accent ed-card__accent--green"></span><span class="ed-card__title">Bundle</span></div>
                    <div class="ed-card__body">
                        <div class="ed-field">
                            <label for="ed-bundle-name">Name</label>
                            <input id="ed-bundle-name" v-model="bundleForm.name" class="form-control" maxlength="255" placeholder="My detection bundle">
                        </div>
                        <div class="ed-field">
                            <label for="ed-bundle-desc">Description</label>
                            <textarea id="ed-bundle-desc" v-model="bundleForm.description" class="form-control" rows="2" placeholder="What these rules detect"></textarea>
                        </div>
                        <div class="form-check form-switch ed-switch mb-0">
                            <input id="ed-bundle-public" v-model="bundleForm.public" class="form-check-input" type="checkbox">
                            <label for="ed-bundle-public" class="form-check-label">[[ bundleForm.public ? 'Public: everyone can see it' : 'Private: only you' ]]</label>
                        </div>
                    </div>
                </div>

                <div v-if="phase === 'confirm' && kind === 'save-bundle'" class="ed-note ed-note--warning">
                    <i class="fas fa-box-archive"></i><span>The folders and files of <b>[[ bundleName ]]</b> will be replaced by the explorer's.</span>
                </div>

                <!-- structure -->
                <div v-if="(phase === 'preview' || phase === 'confirm') && state.rows" class="ed-card">
                    <div class="ed-card__header">
                        <span class="ed-card__accent"></span><span class="ed-card__title">Structure</span>
                        <span class="ed-card__count">a file with several rules becomes a folder</span>
                    </div>
                    <div class="ed-card__body ed-card__body--flush">
                        <ul class="ed-tree">
                            <li v-for="(row, i) in state.rows" :key="i" class="ed-tree__row" :class="{ 'ed-tree__row--empty': row.kind === 'empty' }"
                                :style="{ paddingLeft: (1 + row.depth * 1.25) + 'rem' }">
                                <i class="ed-tree__icon fas" :class="{
                                    'fa-folder ed-tree__icon--folder': row.kind === 'folder',
                                    'fa-shield-halved ed-tree__icon--rule': row.kind === 'rule',
                                    'fa-file-lines ed-tree__icon--text': row.kind === 'text' || row.kind === 'empty' }"></i>
                                <span class="ed-tree__name">[[ row.name ]][[ row.kind === 'folder' ? '/' : '' ]]</span>
                                <span v-if="row.note" class="ed-tree__note" :class="{ 'ed-tree__note--split': row.split }">[[ row.note ]]</span>
                            </li>
                        </ul>
                    </div>
                </div>

                <div v-if="phase === 'planning'" class="ed-note ed-note--info"><i class="fas fa-spinner fa-spin"></i><span>Checking each rule against Rulezet…</span></div>

                <!-- confirm: what happens to each rule -->
                <template v-if="phase === 'confirm'">
                    <div v-if="counts.update" class="ed-note ed-note--warning">
                        <i class="fas fa-triangle-exclamation"></i>
                        <span><b>[[ counts.update ]] rule[[ counts.update === 1 ? '' : 's' ]] already in Rulezet will be updated</b> with the content of the editor (a new version, history kept).</span>
                    </div>
                    <div v-if="counts.proposal" class="ed-note ed-note--proposal">
                        <i class="fas fa-code-pull-request"></i>
                        <span>[[ counts.proposal ]] rule[[ counts.proposal === 1 ? '' : 's' ]] of other users: an edit proposal will be sent to [[ counts.proposal === 1 ? 'its owner' : 'their owners' ]].</span>
                    </div>
                    <div class="ed-card">
                        <div class="ed-card__header">
                            <span class="ed-card__accent"></span><span class="ed-card__title">Rules</span>
                            <span class="ed-card__count d-flex gap-1">
                                <span v-for="s in ['new', 'update', 'proposal', 'exists']" v-show="counts[s]" :key="s" class="ed-pill" :class="'ed-pill--' + s">[[ counts[s] ]] [[ STATUS[s].label ]]</span>
                            </span>
                        </div>
                        <div class="ed-card__body ed-card__body--flush">
                            <ul class="ed-rules">
                                <li v-for="r in rules" :key="r.name" class="ed-rule">
                                    <div class="ed-rule__status"><span class="ed-pill" :class="'ed-pill--' + r.status">[[ STATUS[r.status].label ]]</span></div>
                                    <div>
                                        <div class="ed-rule__name">[[ r.name ]]</div>
                                        <div v-if="r.path" class="ed-rule__path">[[ r.path ]]</div>
                                    </div>
                                    <div class="ed-rule__side">
                                        <a v-if="r.existing" :href="r.existing.url" target="_blank"><i class="fas fa-arrow-up-right-from-square me-1"></i>current rule</a>
                                        <span v-else-if="r.line">line [[ r.line ]]</span>
                                    </div>
                                    <div v-if="STATUS[r.status].text" class="ed-rule__detail" :class="'ed-rule__detail--' + r.status">[[ STATUS[r.status].text ]]</div>
                                    <div v-if="r.open_proposal" class="ed-rule__detail">You already proposed this content: <a :href="r.open_proposal.url" target="_blank">see it</a>.</div>
                                    <div v-if="(r.depends_on || []).length" class="ed-rule__deps">
                                        <template v-for="d in r.depends_on" :key="d.name">
                                            <a v-if="d.url" :href="d.url" target="_blank" class="ed-dep"><i class="fas fa-link"></i>[[ d.name ]] · Rulezet</a>
                                            <span v-else class="ed-dep"><i class="fas fa-link"></i>[[ d.name ]]</span>
                                        </template>
                                    </div>
                                </li>
                            </ul>
                        </div>
                    </div>
                </template>

                <!-- steps of the job -->
                <div v-if="['running', 'done', 'failed'].includes(phase) && job && (job.steps || []).length" class="ed-card">
                    <div class="ed-card__header"><span class="ed-card__accent"></span><span class="ed-card__title">Checks</span></div>
                    <div class="ed-card__body">
                        <ul class="ed-steps">
                            <li v-for="s in job.steps" :key="s.id" class="ed-step" :class="'ed-step--' + s.status">
                                <span class="ed-step__icon"><i :class="STEP_ICON[s.status] || STEP_ICON.pending"></i></span>
                                <span class="ed-step__label">[[ s.label ]]</span>
                                <span class="ed-step__detail">[[ s.detail ]]</span>
                            </li>
                        </ul>
                    </div>
                </div>
                <div v-if="phase === 'running' && (!job || !(job.steps || []).length)" class="ed-note ed-note--info">
                    <i class="fas fa-hourglass-half"></i><span>Waiting for the worker…</span>
                </div>
                <div v-if="job && job.error" class="ed-note ed-note--danger"><i class="fas fa-circle-exclamation"></i><span>[[ job.error ]]</span></div>

                <!-- done -->
                <template v-if="phase === 'done'">
                    <div v-if="job && job.bundle" class="ed-note ed-note--success">
                        <i class="fas fa-box-archive"></i>
                        <span>Bundle [[ job.bundle.mode === 'update' ? 'updated' : 'created' ]]: <a :href="job.bundle.url" class="fw-semibold">[[ job.bundle.name ]]</a></span>
                    </div>
                    <div v-for="g in written" :key="g.status" class="ed-card">
                        <div class="ed-card__header">
                            <span class="ed-card__accent" :class="g.status === 'exists' ? '' : 'ed-card__accent--green'"></span>
                            <span class="ed-card__title">[[ g.status === 'exists' ? 'Already in Rulezet (reused)' : STATUS[g.status].label ]]</span>
                            <span class="ed-card__count">[[ g.rules.length ]]</span>
                        </div>
                        <div class="ed-card__body ed-card__body--flush">
                            <ul class="ed-rules">
                                <li v-for="r in g.rules" :key="r.name" class="ed-rule">
                                    <div class="ed-rule__status"><span class="ed-pill" :class="'ed-pill--' + r.status">[[ STATUS[r.status].label ]]</span></div>
                                    <div>
                                        <a :href="(r.created || r.existing || {}).url" target="_blank" class="ed-rule__name text-decoration-none">[[ r.name ]]</a>
                                        <div v-if="r.path" class="ed-rule__path">[[ r.path ]]</div>
                                    </div>
                                    <div class="ed-rule__side">
                                        <a v-if="r.proposal" :href="r.proposal.url" target="_blank">see the proposal</a>
                                        <a v-else :href="(r.created || r.existing || {}).url" target="_blank"><i class="fas fa-arrow-up-right-from-square"></i></a>
                                    </div>
                                </li>
                            </ul>
                        </div>
                    </div>
                </template>

                <!-- failed -->
                <div v-if="phase === 'failed' && toFix.length" class="ed-card">
                    <div class="ed-card__header">
                        <span class="ed-card__accent ed-card__accent--red"></span><span class="ed-card__title">To fix</span>
                        <span class="ed-card__count">[[ toFix.length ]]</span>
                    </div>
                    <div class="ed-card__body ed-card__body--flush">
                        <ul class="ed-rules">
                            <li v-for="r in toFix" :key="r.name" class="ed-rule">
                                <div class="ed-rule__status"><span class="ed-pill" :class="'ed-pill--' + r.status">[[ STATUS[r.status].label ]]</span></div>
                                <div>
                                    <div class="ed-rule__name">[[ r.name ]]</div>
                                    <div v-if="r.path" class="ed-rule__path">[[ r.path ]]</div>
                                </div>
                                <div class="ed-rule__side"></div>
                                <div v-for="(e, i) in r.errors" :key="i" class="ed-rule__error">
                                    <i class="fas fa-circle-exclamation me-1"></i><span v-if="e.line">line [[ e.line ]] of the rule: </span>[[ e.message ]]
                                </div>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>

            <div class="ed-modal__foot">
                <template v-if="phase === 'preview'">
                    <button type="button" class="ed-btn ed-btn--ghost" @click="close">Close</button>
                    <button type="button" class="ed-btn ed-btn--success" @click="emit('create-bundle')"><i class="fas fa-box-archive"></i>[[ bundleName ? 'Save the bundle' : 'Create the bundle' ]]</button>
                </template>
                <template v-else-if="phase === 'confirm'">
                    <button type="button" class="ed-btn ed-btn--ghost" @click="close">Cancel</button>
                    <button type="button" class="ed-btn" :class="confirmClass"
                            :disabled="kind === 'create-bundle' && !(bundleForm.name || '').trim()" @click="emit('confirm')">
                        <i class="fas fa-check"></i>[[ confirmLabel ]]
                    </button>
                </template>
                <span v-else-if="busy" class="ed-modal__foot-note"><i class="fas fa-lock me-1"></i>The editor is read-only until the job ends.</span>
                <template v-else-if="phase === 'done'">
                    <button type="button" class="ed-btn ed-btn--ghost" @click="close">Keep editing</button>
                    <a v-if="job && job.bundle" :href="job.bundle.url" class="ed-btn ed-btn--success"><i class="fas fa-box-archive"></i>Open the bundle</a>
                    <a v-else-if="job && job.result_url" :href="job.result_url" class="ed-btn ed-btn--primary"><i class="fas fa-list"></i>See the summary</a>
                </template>
                <template v-else>
                    <button type="button" class="ed-btn ed-btn--ghost" @click="close">Close</button>
                    <button type="button" class="ed-btn ed-btn--danger" @click="emit('fix')"><i class="fas fa-wrench"></i>Fix the errors</button>
                </template>
            </div>
        </div>
    </div>`,
}
