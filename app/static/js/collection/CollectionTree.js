/**
 * CollectionTree — recursive folder tree of the Collections browser.
 * Props: folders (flat list with parent_id, count, open, due), parentId,
 *        selected (folder id), depth.
 * Emits: select(id), edit(folder), add-sub(folder), drop-item({ itemId, folderId })
 * Items dragged from the list (dataTransfer 'text/x-collection-item') can be
 * dropped on a folder to move them.
 */
const CollectionTree = {
    name: 'CollectionTree',
    delimiters: ['[[', ']]'],
    props: {
        folders:  { type: Array,  default: () => [] },
        parentId: { type: Number, default: null },
        selected: { type: [Number, String], default: null },
        depth:    { type: Number, default: 0 },
    },
    emits: ['select', 'edit', 'add-sub', 'drop-item'],
    data() { return { collapsed: {}, dragOver: null } },
    computed: {
        children() {
            return this.folders
                .filter(f => (f.parent_id || null) === this.parentId)
                .sort((a, b) => a.position - b.position || a.id - b.id)
        },
    },
    methods: {
        hasChildren(f) { return this.folders.some(c => c.parent_id === f.id) },
        onDrop(e, f) {
            this.dragOver = null
            const itemId = parseInt(e.dataTransfer.getData('text/x-collection-item'))
            if (itemId) this.$emit('drop-item', { itemId, folderId: f.id })
        },
    },
    template: `
    <ul class="ct-list" :class="{ 'ct-list--root': depth === 0 }">
        <li v-for="f in children" :key="f.id">
            <div class="ct-node" :class="{ 'ct-node--active': selected === f.id, 'ct-node--drop': dragOver === f.id }"
                 :style="{ paddingLeft: (0.5 + depth * 0.95) + 'rem' }"
                 @click="$emit('select', f.id)"
                 @dragover.prevent="dragOver = f.id" @dragleave="dragOver = null" @drop.prevent="onDrop($event, f)">
                <button v-if="hasChildren(f)" type="button" class="ct-caret" @click.stop="collapsed[f.id] = !collapsed[f.id]">
                    <i class="fa-solid" :class="collapsed[f.id] ? 'fa-caret-right' : 'fa-caret-down'"></i>
                </button>
                <span v-else class="ct-caret"></span>
                <i class="ct-icon" :class="f.icon || 'fa-solid fa-folder'" :style="{ color: f.color }"></i>
                <span class="ct-name" :title="f.description || f.name">[[ f.name ]]</span>
                <span v-if="f.due" class="ct-due" :title="f.due + ' reminder(s) due'"><i class="fa-solid fa-bell"></i>[[ f.due ]]</span>
                <span class="ct-count" :title="f.open + ' open / ' + f.count">[[ f.count ]]</span>
                <span class="ct-actions">
                    <button type="button" title="New sub-folder" @click.stop="$emit('add-sub', f)"><i class="fa-solid fa-plus"></i></button>
                    <button type="button" title="Edit folder" @click.stop="$emit('edit', f)"><i class="fa-solid fa-pen"></i></button>
                </span>
            </div>
            <collection-tree v-if="hasChildren(f) && !collapsed[f.id]" :folders="folders" :parent-id="f.id"
                             :selected="selected" :depth="depth + 1"
                             @select="$emit('select', $event)" @edit="$emit('edit', $event)"
                             @add-sub="$emit('add-sub', $event)" @drop-item="$emit('drop-item', $event)"></collection-tree>
        </li>
    </ul>`,
}
CollectionTree.components = { 'collection-tree': CollectionTree }
export default CollectionTree
