/**
 * WorkspacePicker — "Add to a workspace": tick the user's workspaces that
 * should hold the rule(s); one rule → its current workspaces are pre-ticked
 * and unticking removes it. "New workspace" opens the same window as the
 * Workspaces page (WorkspaceCreateModal).
 *
 * Props:
 *   ruleIds     Array<Number>
 *   csrfToken   String
 *   showButton  Boolean  render the trigger button (false: call open() via a ref)
 *   compact     Boolean  icon-only trigger
 * Emits: saved({ added, removed })
 *
 * Backend: /workspace/of_rule/<id>, /workspace/create, POST|DELETE /workspace/<uuid>/rules.
 * Dialog chrome shared with CollectionPicker: css/components/collection-picker.css (.cp-*).
 */
import { create_message } from '/static/js/toaster.js'
import WorkspaceCreateModal from '/static/js/components/WorkspaceCreateModal.js'
const { ref, computed } = Vue

const WorkspacePicker = {
    name: 'WorkspacePicker',
    delimiters: ['[[', ']]'],
    props: {
        ruleIds:    { type: Array,   default: () => [] },
        csrfToken:  { type: String,  default: '' },
        showButton: { type: Boolean, default: true },
        compact:    { type: Boolean, default: false },
    },
    components: { 'workspace-create-modal': WorkspaceCreateModal },
    emits: ['saved'],
    setup(props, { emit, expose }) {
        const visible    = ref(false)
        const loading    = ref(false)
        const saving     = ref(false)
        const workspaces = ref([])
        const checked    = ref(new Set())
        const initial    = ref(new Set())
        const search     = ref('')
        const createModal = ref(null)

        const single = computed(() => props.ruleIds.length === 1)
        const what   = computed(() => single.value ? 'this rule' : `${props.ruleIds.length} rules`)
        const shown  = computed(() => {
            const s = search.value.trim().toLowerCase()
            return s ? workspaces.value.filter(w => w.name.toLowerCase().includes(s)) : workspaces.value
        })
        const iconClass = icon => (icon || 'fa-folder').includes(' ') ? icon : 'fa-solid ' + (icon || 'fa-folder')
        // Same token source as the workspace pages: the page's hidden csrf_token field first
        const token = () => document.getElementById('csrf_token')?.value || props.csrfToken
        const headers = () => ({ 'Content-Type': 'application/json', 'X-CSRFToken': token() })

        async function open() {
            if (!props.ruleIds.length) return
            visible.value = true; loading.value = true
            search.value = ''
            try {
                const d = await fetch(`/workspace/of_rule/${props.ruleIds[0]}`).then(r => r.json())
                workspaces.value = d.workspaces || []
                initial.value = new Set(single.value ? (d.member_ids || []) : [])
                checked.value = new Set(initial.value)
            } catch (e) {
                create_message('Could not load your workspaces.', 'danger'); visible.value = false
            } finally { loading.value = false }
        }
        function close() { visible.value = false }
        function toggle(id) {
            const s = new Set(checked.value); s.has(id) ? s.delete(id) : s.add(id); checked.value = s
        }

        function openCreate() { createModal.value?.open() }
        function onCreated(ws) {
            workspaces.value = [...workspaces.value, ws]
            toggle(ws.id)          // ticked: Save adds the rule to it
        }

        async function save() {
            saving.value = true
            const byId = Object.fromEntries(workspaces.value.map(w => [w.id, w]))
            const toAdd = [...checked.value].filter(id => !initial.value.has(id))
            const toRemove = [...initial.value].filter(id => !checked.value.has(id))
            let added = 0, removed = 0
            try {
                for (const id of toAdd) {
                    const r = await fetch(`/workspace/${byId[id].uuid}/rules`, { method: 'POST', headers: headers(), body: JSON.stringify({ rule_ids: props.ruleIds }) })
                    const d = await r.json().catch(() => ({}))
                    if (r.ok && d.success) added += d.added || 0
                }
                for (const id of toRemove) {
                    const r = await fetch(`/workspace/${byId[id].uuid}/rules/${props.ruleIds[0]}`, { method: 'DELETE', headers: headers() })
                    if (r.ok) removed++
                }
                const names = toAdd.map(id => byId[id].name)
                create_message(toAdd.length || toRemove.length
                    ? (toAdd.length ? `Added to ${names.length === 1 ? names[0] : names.length + ' workspaces'}.` : 'Removed from the workspace.')
                    : 'Nothing changed.', 'success')
                emit('saved', { added, removed })
                visible.value = false
            } catch (e) {
                create_message('Could not save.', 'danger')
            } finally { saving.value = false }
        }

        expose({ open })
        return { visible, loading, saving, shown, checked, initial, search, createModal, single, what,
                 iconClass, open, close, toggle, openCreate, onCreated, save }
    },
    template: `
    <span class="cp-root">
        <button v-if="showButton" type="button" @click="open"
                :class="compact ? 'vote-pill__btn btn-animate' : 'btn btn-sm btn-outline-primary rounded-pill px-3'"
                title="Add to a workspace" aria-label="Add to a workspace">
            <i class="fa-solid fa-briefcase" :class="{ 'me-1': !compact }"></i><span v-if="!compact">Add to a workspace</span>
        </button>

        <teleport to="body">
            <div v-if="visible" class="cp-overlay" @click.self="close">
                <div class="cp-dialog" role="dialog" aria-modal="true">
                    <div class="cp-head">
                        <div class="cp-head__icon"><i class="fa-solid fa-briefcase"></i></div>
                        <div class="cp-head__text">
                            <div class="cp-head__title">Add [[ what ]] to a workspace</div>
                            <div class="cp-head__sub">Your workspaces<span v-if="initial.size"> — already in [[ initial.size ]]</span>.</div>
                        </div>
                        <button type="button" class="btn-close" @click="close" aria-label="Close"></button>
                    </div>

                    <div v-if="loading" class="cp-body"><div class="cp-skel" v-for="n in 4" :key="n"></div></div>
                    <div v-else class="cp-body">
                        <input v-if="shown.length > 6 || search" v-model="search" class="form-control form-control-sm mb-2" placeholder="Filter workspaces…">
                        <div class="cp-folders">
                            <button v-for="w in shown" :key="w.id" type="button" class="cp-folder"
                                    :class="{ 'cp-folder--on': checked.has(w.id) }" @click="toggle(w.id)">
                                <i class="cp-folder__check" :class="checked.has(w.id) ? 'fa-solid fa-square-check' : 'fa-regular fa-square'"></i>
                                <i :class="iconClass(w.icon)" :style="{ color: w.color }"></i>
                                <span class="cp-folder__name" :title="w.description || w.name">[[ w.name ]]</span>
                                <span class="cp-folder__count" title="Rules in this workspace">[[ w.rule_count ]]</span>
                            </button>
                            <div v-if="!shown.length" class="cp-empty">No workspace yet — create one below.</div>
                        </div>
                        <button type="button" class="cp-new cp-new--btn" @click="openCreate">
                            <i class="fa-solid fa-plus"></i><span>New workspace…</span>
                        </button>
                    </div>

                    <div class="cp-foot">
                        <a href="/workspace" class="cp-foot__link"><i class="fa-solid fa-briefcase me-1"></i>My workspaces</a>
                        <button type="button" class="btn btn-sm btn-light rounded-pill px-3" @click="close">Cancel</button>
                        <button type="button" class="btn btn-sm btn-primary rounded-pill px-3" :disabled="saving || loading" @click="save">
                            <i class="fa-solid" :class="saving ? 'fa-spinner fa-spin' : 'fa-check'"></i> Save
                        </button>
                    </div>
                </div>
            </div>
        </teleport>
        <workspace-create-modal ref="createModal" :csrf-token="csrfToken" @created="onCreated"></workspace-create-modal>
    </span>`,
}
export default WorkspacePicker
