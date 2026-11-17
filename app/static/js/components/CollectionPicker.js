/**
 * CollectionPicker — "Add to folder": put rules / bundles in the user's
 * private folders (Collections), with a note, a status and a reminder.
 *
 * Props:
 *   kind        'rule' | 'bundle'
 *   objectIds   Array<Number>  one id → shows/edits the folders it is already in;
 *                              several (bulk) → adds to the folders ticked
 *   csrfToken   String
 *   showButton  Boolean  render the trigger button (false: call open() via a ref)
 *   compact     Boolean  icon-only trigger (detail-page pill row)
 * Emits: saved({ added, removed })
 *
 * Backend: /collection/api/* (features/collection). Statuses / icons / colors
 * come from the public setting `collection` (fetched once per page).
 */
import { create_message } from '/static/js/toaster.js'
const { ref, computed } = Vue

let configPromise = null
export function loadCollectionConfig() {
    if (!configPromise) {
        configPromise = fetch('/api/config/settings/collection')
            .then(r => (r.ok ? r.json() : null))
            .then(d => (d && d.value) || {})
            .catch(() => ({}))
    }
    return configPromise
}

/** Folders (flat, parent_id) → depth-first list with `depth`, for indented lists. */
export function flattenFolders(folders) {
    const byParent = {}
    for (const f of folders) (byParent[f.parent_id || 0] ||= []).push(f)
    const out = []
    const walk = (pid, depth) => {
        for (const f of (byParent[pid] || []).sort((a, b) => a.position - b.position || a.id - b.id)) {
            out.push({ ...f, depth })
            walk(f.id, depth + 1)
        }
    }
    walk(0, 0)
    return out
}

/** Reminder presets → ISO string (local time → UTC). */
export function reminderPreset(key) {
    const d = new Date()
    if (key === 'tomorrow') { d.setDate(d.getDate() + 1); d.setHours(9, 0, 0, 0) }
    else if (key === '3days') { d.setDate(d.getDate() + 3); d.setHours(9, 0, 0, 0) }
    else if (key === 'week') { d.setDate(d.getDate() + ((8 - d.getDay()) % 7 || 7)); d.setHours(9, 0, 0, 0) }
    else if (key === 'month') { d.setMonth(d.getMonth() + 1); d.setHours(9, 0, 0, 0) }
    return d.toISOString()
}

/** ISO (UTC) → value for <input type="datetime-local"> (local time). */
export function toLocalInput(iso) {
    if (!iso) return ''
    const d = new Date(iso)
    const pad = n => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
export function fromLocalInput(v) { return v ? new Date(v).toISOString() : '' }

export function formatWhen(iso) {
    if (!iso) return ''
    const d = new Date(iso), now = new Date()
    const days = Math.round((d - now) / 86400000)
    const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    if (Math.abs(days) < 1 && d.getDate() === now.getDate()) return `today ${time}`
    if (days === 1 || (days < 2 && d.getDate() === now.getDate() + 1)) return `tomorrow ${time}`
    return d.toLocaleDateString([], { day: 'numeric', month: 'short', year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined }) + ` ${time}`
}

const CollectionPicker = {
    name: 'CollectionPicker',
    delimiters: ['[[', ']]'],
    props: {
        kind:       { type: String, default: 'rule' },
        objectIds:  { type: Array,  default: () => [] },
        csrfToken:  { type: String, default: '' },
        showButton: { type: Boolean, default: true },
        compact:    { type: Boolean, default: false },
    },
    emits: ['saved'],
    setup(props, { emit, expose }) {
        const visible   = ref(false)
        const loading   = ref(false)
        const saving    = ref(false)
        const folders   = ref([])
        const checked   = ref(new Set())
        const initial   = ref(new Set())
        const note      = ref('')
        const status    = ref('todo')
        const remindAt  = ref('')         // datetime-local value
        const config    = ref({})
        const newName   = ref('')
        const creating  = ref(false)
        const search    = ref('')

        const single   = computed(() => props.objectIds.length === 1)
        const flat     = computed(() => flattenFolders(folders.value))
        const shown    = computed(() => {
            const s = search.value.trim().toLowerCase()
            return s ? flat.value.filter(f => f.name.toLowerCase().includes(s)) : flat.value
        })
        const statuses = computed(() => config.value.statuses || [
            { key: 'todo', label: 'To do', icon: 'fa-regular fa-circle' },
            { key: 'doing', label: 'In progress', icon: 'fa-solid fa-circle-half-stroke' },
            { key: 'done', label: 'Done', icon: 'fa-solid fa-circle-check' },
        ])
        const inCount  = computed(() => initial.value.size)
        const what     = computed(() => single.value
            ? (props.kind === 'bundle' ? 'this bundle' : 'this rule')
            : `${props.objectIds.length} ${props.kind}s`)

        const token = () => document.getElementById('csrf_token')?.value || props.csrfToken
        const headers = () => ({ 'Content-Type': 'application/json', 'X-CSRFToken': token() })

        async function open() {
            if (!props.objectIds.length) return
            visible.value = true
            loading.value = true
            search.value = ''; newName.value = ''
            note.value = ''; status.value = 'todo'; remindAt.value = ''
            config.value = await loadCollectionConfig()
            try {
                const res = await fetch(`/collection/api/membership/${props.kind}/${props.objectIds[0]}`)
                const data = await res.json()
                folders.value = data.folders || []
                const mem = single.value ? (data.membership || []) : []
                initial.value = new Set(mem.map(m => m.collection_id))
                checked.value = new Set(initial.value)
                if (mem.length) {          // one rule in folders already: show what was written
                    note.value = mem[0].note || ''
                    status.value = mem[0].status || 'todo'
                    remindAt.value = toLocalInput(mem.find(m => m.remind_at)?.remind_at)
                }
            } catch (e) {
                create_message('Could not load your folders.', 'danger')
                visible.value = false
            } finally {
                loading.value = false
            }
        }
        function close() { visible.value = false }

        function toggle(id) {
            const s = new Set(checked.value)
            s.has(id) ? s.delete(id) : s.add(id)
            checked.value = s
        }
        function preset(key) { remindAt.value = toLocalInput(reminderPreset(key)) }

        async function createFolder() {
            const name = newName.value.trim()
            if (!name || creating.value) return
            creating.value = true
            try {
                const res = await fetch('/collection/api/folders', { method: 'POST', headers: headers(), body: JSON.stringify({ name }) })
                const data = await res.json().catch(() => ({}))
                if (!res.ok || !data.folder) return create_message(data.message || `Could not create the folder (HTTP ${res.status}).`, 'danger')
                folders.value = [...folders.value, { ...data.folder, count: 0, open: 0, due: 0 }]
                toggle(data.folder.id)
                newName.value = ''
            } catch (e) {
                create_message('Could not create the folder.', 'danger')
            } finally { creating.value = false }
        }

        async function save() {
            saving.value = true
            const ids = props.kind === 'bundle' ? { bundle_ids: props.objectIds } : { rule_ids: props.objectIds }
            const toAdd = [...checked.value].filter(id => !initial.value.has(id))
            const kept = [...checked.value].filter(id => initial.value.has(id))
            const toRemove = [...initial.value].filter(id => !checked.value.has(id))
            const payload = { note: note.value, status: status.value, remind_at: fromLocalInput(remindAt.value) }
            let added = 0, removed = 0
            try {
                if (toAdd.length) {
                    const r = await fetch('/collection/api/items', { method: 'POST', headers: headers(), body: JSON.stringify({ folder_ids: toAdd, ...ids, ...payload }) })
                    const d = await r.json()
                    if (!r.ok) { create_message(d.message, 'danger'); return }
                    added = d.added || 0
                }
                if (single.value && kept.length) {   // note / status / reminder edited on the existing items
                    const r = await fetch(`/collection/api/membership/${props.kind}/${props.objectIds[0]}`)
                    const mem = (await r.json()).membership || []
                    await Promise.all(mem.filter(m => kept.includes(m.collection_id)).map(m =>
                        fetch(`/collection/api/items/${m.item_id}`, { method: 'PATCH', headers: headers(), body: JSON.stringify(payload) })))
                }
                for (const fid of toRemove) {
                    await fetch(`/collection/api/membership/${props.kind}/${props.objectIds[0]}/${fid}`, { method: 'DELETE', headers: headers() })
                    removed++
                }
                create_message(added || removed || kept.length ? 'Folders updated.' : 'Nothing changed.', 'success')
                emit('saved', { added, removed })
                visible.value = false
            } catch (e) {
                create_message('Could not save.', 'danger')
            } finally { saving.value = false }
        }

        expose({ open })
        return { visible, loading, saving, shown, checked, note, status, remindAt, statuses, newName, creating,
                 search, single, inCount, what, open, close, toggle, preset, createFolder, save }
    },
    template: `
    <span class="cp-root">
        <button v-if="showButton" type="button" @click="open"
                :class="compact ? 'vote-pill__btn btn-animate' : 'btn btn-sm btn-outline-primary rounded-pill px-3'"
                title="Add to a folder" aria-label="Add to a folder">
            <i class="fa-solid fa-folder-plus" :class="{ 'me-1': !compact }"></i><span v-if="!compact">Add to folder</span>
        </button>

        <teleport to="body">
            <div v-if="visible" class="cp-overlay" @click.self="close">
                <div class="cp-dialog" role="dialog" aria-modal="true">
                    <div class="cp-head">
                        <div class="cp-head__icon"><i class="fa-solid fa-folder-tree"></i></div>
                        <div class="cp-head__text">
                            <div class="cp-head__title">Add [[ what ]] to my folders</div>
                            <div class="cp-head__sub">Private — only you see your folders.
                                <span v-if="inCount"> Already in [[ inCount ]] folder(s).</span></div>
                        </div>
                        <button type="button" class="btn-close" @click="close" aria-label="Close"></button>
                    </div>

                    <div v-if="loading" class="cp-body"><div class="cp-skel" v-for="n in 4" :key="n"></div></div>
                    <div v-else class="cp-body">
                        <div class="cp-label">Folders</div>
                        <input v-if="shown.length > 6 || search" v-model="search" class="form-control form-control-sm mb-2" placeholder="Filter folders…">
                        <div class="cp-folders">
                            <button v-for="f in shown" :key="f.id" type="button" class="cp-folder"
                                    :class="{ 'cp-folder--on': checked.has(f.id) }"
                                    :style="{ paddingLeft: (0.6 + f.depth * 1.1) + 'rem' }" @click="toggle(f.id)">
                                <i class="cp-folder__check" :class="checked.has(f.id) ? 'fa-solid fa-square-check' : 'fa-regular fa-square'"></i>
                                <i :class="f.icon || 'fa-solid fa-folder'" :style="{ color: f.color }"></i>
                                <span class="cp-folder__name">[[ f.name ]]</span>
                                <span class="cp-folder__count">[[ f.count ]]</span>
                            </button>
                            <div v-if="!shown.length" class="cp-empty">No folder yet — create one below.</div>
                        </div>
                        <div class="cp-new">
                            <i class="fa-solid fa-plus"></i>
                            <input v-model="newName" maxlength="120" placeholder="New folder…" @keydown.enter.prevent="createFolder">
                            <button type="button" class="btn btn-sm btn-link" :disabled="!newName.trim() || creating" @click="createFolder">
                                <i v-if="creating" class="fa-solid fa-spinner fa-spin me-1"></i>Create</button>
                        </div>

                        <div class="cp-label">Why do you keep it? <span class="cp-opt">optional</span></div>
                        <textarea v-model="note" rows="2" class="form-control form-control-sm"
                                  placeholder="e.g. Change request pending — check the answer of the author on Monday"></textarea>

                        <div class="cp-row">
                            <div>
                                <div class="cp-label">Status</div>
                                <div class="cp-status">
                                    <button v-for="s in statuses" :key="s.key" type="button" class="cp-status__btn"
                                            :class="{ 'cp-status__btn--on': status === s.key }"
                                            :style="status === s.key ? { borderColor: s.color, color: s.color } : {}"
                                            @click="status = s.key"><i :class="s.icon"></i> [[ s.label ]]</button>
                                </div>
                            </div>
                        </div>

                        <div class="cp-label"><i class="fa-regular fa-bell me-1"></i>Remind me <span class="cp-opt">a notification on that date</span></div>
                        <div class="cp-remind">
                            <button type="button" class="cp-chip" @click="preset('tomorrow')">Tomorrow</button>
                            <button type="button" class="cp-chip" @click="preset('3days')">In 3 days</button>
                            <button type="button" class="cp-chip" @click="preset('week')">Next Monday</button>
                            <button type="button" class="cp-chip" @click="preset('month')">In a month</button>
                            <input type="datetime-local" v-model="remindAt" class="form-control form-control-sm cp-remind__input">
                            <button v-if="remindAt" type="button" class="cp-chip cp-chip--clear" @click="remindAt = ''" title="No reminder"><i class="fa-solid fa-xmark"></i></button>
                        </div>
                    </div>

                    <div class="cp-foot">
                        <a href="/rule/owner_rules?tab=folders" class="cp-foot__link"><i class="fa-solid fa-folder-open me-1"></i>My folders</a>
                        <button type="button" class="btn btn-sm btn-light rounded-pill px-3" @click="close">Cancel</button>
                        <button type="button" class="btn btn-sm btn-primary rounded-pill px-3" :disabled="saving || loading" @click="save">
                            <i class="fa-solid" :class="saving ? 'fa-spinner fa-spin' : 'fa-check'"></i> Save
                        </button>
                    </div>
                </div>
            </div>
        </teleport>
    </span>`,
}

export default CollectionPicker
