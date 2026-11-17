/**
 * CollectionItem — one rule / bundle of a folder: title, format, pending
 * change requests, personal note, status and reminder, all editable inline.
 * Props: item (from /collection/api/items), statuses, folders (flat, for "move"),
 *        showFolder (smart views list items of several folders), selected.
 * Emits: update(item, patch), remove(item), toggle-select(item)
 */
import { formatWhen, toLocalInput, fromLocalInput, reminderPreset, flattenFolders } from '/static/js/components/CollectionPicker.js'

const CollectionItem = {
    name: 'CollectionItem',
    delimiters: ['[[', ']]'],
    props: {
        item:       { type: Object, required: true },
        statuses:   { type: Array,  default: () => [] },
        folders:    { type: Array,  default: () => [] },
        showFolder: { type: Boolean, default: false },
        selected:   { type: Boolean, default: false },
    },
    emits: ['update', 'remove', 'toggle-select'],
    data() {
        return { editingNote: false, noteDraft: '', remindOpen: false, remindDraft: '' }
    },
    computed: {
        obj() { return this.item.object },
        status() { return this.statuses.find(s => s.key === this.item.status) || this.statuses[0] || {} },
        nextStatus() {
            const i = this.statuses.findIndex(s => s.key === this.item.status)
            return this.statuses[(i + 1) % this.statuses.length]
        },
        flatFolders() { return flattenFolders(this.folders) },
        when() { return formatWhen(this.item.remind_at) },
    },
    methods: {
        startNote() { this.noteDraft = this.item.note || ''; this.editingNote = true; this.$nextTick(() => this.$refs.note?.focus()) },
        saveNote() { this.editingNote = false; if (this.noteDraft !== (this.item.note || '')) this.$emit('update', this.item, { note: this.noteDraft }) },
        cycleStatus() { if (this.nextStatus) this.$emit('update', this.item, { status: this.nextStatus.key }) },
        openRemind() { this.remindDraft = toLocalInput(this.item.remind_at); this.remindOpen = !this.remindOpen },
        preset(k) { this.remindDraft = toLocalInput(reminderPreset(k)) },
        saveRemind() { this.remindOpen = false; this.$emit('update', this.item, { remind_at: fromLocalInput(this.remindDraft) }) },
        clearRemind() { this.remindOpen = false; this.$emit('update', this.item, { remind_at: '' }) },
        move(e) { const id = parseInt(e.target.value); e.target.value = ''; if (id) this.$emit('update', this.item, { collection_id: id }) },
        dragStart(e) { e.dataTransfer.setData('text/x-collection-item', String(this.item.id)); e.dataTransfer.effectAllowed = 'move' },
    },
    template: `
    <div class="ci-card" :class="['ci-card--' + item.status, { 'ci-card--due': item.due, 'ci-card--sel': selected }]"
         draggable="true" @dragstart="dragStart">
        <span class="ci-accent" :style="{ background: status.color }"></span>
        <label class="ci-select" @click.stop><input type="checkbox" :checked="selected" @change="$emit('toggle-select', item)"></label>

        <div class="ci-main">
            <div class="ci-top">
                <span class="ci-kind" :class="'ci-kind--' + item.kind">
                    <i class="fa-solid" :class="item.kind === 'bundle' ? 'fa-layer-group' : 'fa-shield-halved'"></i>
                    [[ item.kind === 'bundle' ? 'Bundle' : (obj && obj.format) || 'Rule' ]]
                </span>
                <a v-if="obj" :href="obj.url" class="ci-title" :class="{ 'ci-title--deleted': obj.deleted }">[[ obj.title ]]</a>
                <span v-else class="ci-title ci-title--deleted">Removed</span>
                <span v-if="obj && obj.deleted" class="ci-flag ci-flag--danger" title="This rule was deleted — your note is kept"><i class="fa-solid fa-trash"></i>Deleted</span>
                <a v-if="obj && obj.pending_proposals" :href="obj.url + '/pull_request'" class="ci-flag ci-flag--warn"
                   title="Open change requests on this rule"><i class="fa-solid fa-code-pull-request"></i>[[ obj.pending_proposals ]] change request[[ obj.pending_proposals > 1 ? 's' : '' ]]</a>
                <span v-if="showFolder && item.folder" class="ci-folder"><i :class="item.folder.icon" :style="{ color: item.folder.color }"></i>[[ item.folder.name ]]</span>
            </div>

            <div class="ci-note" v-if="!editingNote" @click="startNote" :class="{ 'ci-note--empty': !item.note }" title="Click to edit your note">
                <i class="fa-regular fa-note-sticky"></i>
                <span>[[ item.note || 'Add a note — why do you keep it?' ]]</span>
            </div>
            <textarea v-else ref="note" v-model="noteDraft" rows="2" class="form-control form-control-sm"
                      @blur="saveNote" @keydown.ctrl.enter="saveNote" @keydown.esc="editingNote = false"></textarea>

            <div class="ci-bar">
                <button type="button" class="ci-status" :style="{ color: status.color, borderColor: status.color }"
                        @click="cycleStatus" :title="nextStatus ? 'Mark as ' + nextStatus.label : ''">
                    <i :class="status.icon"></i>[[ status.label ]]
                </button>
                <button type="button" class="ci-remind" :class="{ 'ci-remind--due': item.due, 'ci-remind--set': item.remind_at }" @click="openRemind">
                    <i class="fa-bell" :class="item.remind_at ? 'fa-solid' : 'fa-regular'"></i>
                    [[ item.remind_at ? (item.due ? 'Due ' : '') + when : 'Remind me' ]]
                </button>
                <select class="ci-move" @change="move" title="Move to another folder">
                    <option value="">Move…</option>
                    <option v-for="f in flatFolders" :key="f.id" :value="f.id" :disabled="f.id === item.collection_id">[[ '  '.repeat(f.depth) + f.name ]]</option>
                </select>
                <button type="button" class="ci-remove" title="Remove from this folder" @click="$emit('remove', item)"><i class="fa-solid fa-xmark"></i></button>
            </div>

            <div v-if="remindOpen" class="ci-remind-pop">
                <button type="button" class="cp-chip" @click="preset('tomorrow')">Tomorrow</button>
                <button type="button" class="cp-chip" @click="preset('3days')">In 3 days</button>
                <button type="button" class="cp-chip" @click="preset('week')">Next Monday</button>
                <button type="button" class="cp-chip" @click="preset('month')">In a month</button>
                <input type="datetime-local" v-model="remindDraft" class="form-control form-control-sm">
                <button type="button" class="btn btn-sm btn-primary rounded-pill px-3" @click="saveRemind" :disabled="!remindDraft">Set</button>
                <button v-if="item.remind_at" type="button" class="btn btn-sm btn-link text-danger" @click="clearRemind">Clear</button>
            </div>
        </div>
    </div>`,
}
export default CollectionItem
