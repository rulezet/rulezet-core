/**
 * FolderDialog — create / edit a folder: name, description, icon, color,
 * parent. Icon: the shared IconPicker (tags/utils/iconPicker.js, v-model "fa-<name>",
 * stored as "fa-solid fa-<name>"); colors from the setting `collection`.
 * Props: folder (null = new), parentId (for a new sub-folder), folders, config.
 * Emits: save(payload), delete(folder), close
 */
import { flattenFolders } from '/static/js/components/CollectionPicker.js'
import IconPicker from '/static/js/tags/utils/iconPicker.js'

const FolderDialog = {
    name: 'FolderDialog',
    delimiters: ['[[', ']]'],
    props: {
        folder:   { type: Object, default: null },
        parentId: { type: Number, default: null },
        folders:  { type: Array,  default: () => [] },
        config:   { type: Object, default: () => ({}) },
    },
    components: { 'icon-picker': IconPicker },
    emits: ['save', 'delete', 'close'],
    data() {
        const f = this.folder || {}
        return {
            name: f.name || '', description: f.description || '',
            icon: (f.icon || 'fa-folder').replace(/^fa-(solid|regular|brands) /, ''), color: f.color || '#0d6efd',
            parent: this.folder ? (f.parent_id || '') : (this.parentId || ''),
        }
    },
    computed: {
        colors() { return this.config.colors || ['#0d6efd'] },
        parents() {   // a folder cannot go under itself or its sub-folders
            const flat = flattenFolders(this.folders)
            if (!this.folder) return flat
            const banned = new Set([this.folder.id])
            for (const f of flat) if (banned.has(f.parent_id)) banned.add(f.id)
            return flat.filter(f => !banned.has(f.id))
        },
    },
    methods: {
        submit() {
            if (!this.name.trim()) return
            this.$emit('save', { name: this.name.trim(), description: this.description, icon: 'fa-solid ' + this.icon,
                                 color: this.color, parent_id: this.parent || null })
        },
    },
    template: `
    <teleport to="body">
        <div class="cp-overlay" @click.self="$emit('close')">
            <form class="cp-dialog" @submit.prevent="submit">
                <div class="cp-head">
                    <div class="cp-head__icon" :style="{ background: color }"><i class="fa-solid" :class="icon"></i></div>
                    <div class="cp-head__text">
                        <div class="cp-head__title">[[ folder ? 'Edit folder' : 'New folder' ]]</div>
                        <div class="cp-head__sub">Private — only you see it.</div>
                    </div>
                    <button type="button" class="btn-close" @click="$emit('close')" aria-label="Close"></button>
                </div>
                <div class="cp-body">
                    <div class="cp-label">Name</div>
                    <input v-model="name" maxlength="120" class="form-control form-control-sm" placeholder="e.g. To fix, Incident ACME, CVE-2026-1234" autofocus>
                    <div class="cp-label">Description <span class="cp-opt">optional</span></div>
                    <textarea v-model="description" rows="2" class="form-control form-control-sm"></textarea>
                    <div class="cp-label">Inside</div>
                    <select v-model="parent" class="form-select form-select-sm">
                        <option value="">— top level —</option>
                        <option v-for="f in parents" :key="f.id" :value="f.id">[[ '  '.repeat(f.depth) + f.name ]]</option>
                    </select>
                    <icon-picker v-model="icon" label="Icon" :color="color" all-icons></icon-picker>
                    <div class="cp-label">Color</div>
                    <div class="fd-colors">
                        <button v-for="c in colors" :key="c" type="button" class="fd-color" :class="{ 'fd-color--on': color === c }"
                                :style="{ background: c }" :title="c" @click="color = c"></button>
                    </div>
                </div>
                <div class="cp-foot">
                    <button v-if="folder" type="button" class="btn btn-sm btn-link text-danger me-auto px-0" @click="$emit('delete', folder)">
                        <i class="fa-solid fa-trash me-1"></i>Delete folder</button>
                    <span v-else class="me-auto"></span>
                    <button type="button" class="btn btn-sm btn-light rounded-pill px-3" @click="$emit('close')">Cancel</button>
                    <button type="submit" class="btn btn-sm btn-primary rounded-pill px-3" :disabled="!name.trim()"><i class="fa-solid fa-check"></i> Save</button>
                </div>
            </form>
        </div>
    </teleport>`,
}
export default FolderDialog
