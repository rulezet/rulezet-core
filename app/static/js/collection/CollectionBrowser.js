/**
 * CollectionBrowser — the user's private folders: tree on the left (with the
 * smart views All / Reminders due / Upcoming), items of the selected folder
 * on the right (note, status, reminder, move, remove), filters, bulk actions.
 * Used in the "My Folders" tab of My rules (/rule/owner_rules?tab=folders).
 *
 * Props: csrfToken, initialFolder (id), initialView (all|due|upcoming),
 *        initialItem (id, scrolled to / highlighted)
 * Backend: /collection/api/* (features/collection/collection.py)
 */
import { create_message } from '/static/js/toaster.js'
import { loadCollectionConfig } from '/static/js/components/CollectionPicker.js'
import CollectionTree from '/static/js/collection/CollectionTree.js'
import CollectionItem from '/static/js/collection/CollectionItem.js'
import FolderDialog from '/static/js/collection/FolderDialog.js'
import PaginationComponent from '/static/js/rule/paginationComponent.js'

const VIEWS = [
    { key: 'all',      label: 'All items',      icon: 'fa-solid fa-inbox' },
    { key: 'due',      label: 'Reminders due',  icon: 'fa-solid fa-bell' },
    { key: 'upcoming', label: 'Upcoming',       icon: 'fa-regular fa-calendar' },
]

const CollectionBrowser = {
    name: 'CollectionBrowser',
    delimiters: ['[[', ']]'],
    components: { 'collection-tree': CollectionTree, 'collection-item': CollectionItem,
                  'folder-dialog': FolderDialog, 'pagination-component': PaginationComponent },
    props: {
        csrfToken:     { type: String, default: '' },
        initialFolder: { type: Number, default: null },
        initialItem:   { type: Number, default: null },
        initialView:   { type: String, default: null },   // all | due | upcoming
    },
    data() {
        return {
            views: VIEWS, config: {}, folders: [], summary: {}, loadingTree: true,
            selected: this.initialFolder || (VIEWS.some(v => v.key === this.initialView) ? this.initialView : 'all'),
            items: [], total: 0, totalPages: 1, page: 1, loadingItems: false,
            status: '', kind: '', search: '', searchTimer: null,
            selection: new Set(), dialog: null, sidebarOpen: false,
        }
    },
    computed: {
        statuses() { return this.config.statuses || [] },
        currentFolder() { return typeof this.selected === 'number' ? this.folders.find(f => f.id === this.selected) : null },
        currentView() { return VIEWS.find(v => v.key === this.selected) },
        heading() { return this.currentFolder ? this.currentFolder.name : (this.currentView ? this.currentView.label : '') },
        breadcrumb() {
            const out = []
            let f = this.currentFolder
            while (f) { out.unshift(f); f = this.folders.find(p => p.id === f.parent_id) }
            return out
        },
        subFolders() { return this.currentFolder ? this.folders.filter(f => f.parent_id === this.currentFolder.id) : [] },
        allSelected() { return this.items.length && this.items.every(i => this.selection.has(i.id)) },
    },
    watch: {
        selected() { this.page = 1; this.selection = new Set(); this.sidebarOpen = false; this.syncUrl(); this.loadItems() },
        status() { this.page = 1; this.loadItems() },
        kind() { this.page = 1; this.loadItems() },
        search() { clearTimeout(this.searchTimer); this.searchTimer = setTimeout(() => { this.page = 1; this.loadItems() }, 300) },
        page() { this.loadItems() },
    },
    async mounted() {
        this.config = await loadCollectionConfig()
        await this.loadTree()
        await this.loadItems()
        if (this.initialItem) this.$nextTick(() => {
            const el = document.getElementById('ci-' + this.initialItem)
            if (el) { el.scrollIntoView({ block: 'center', behavior: 'smooth' }); el.classList.add('ci-flash') }
        })
    },
    methods: {
        headers() { return { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrfToken } },
        async api(url, method = 'GET', body) {
            const res = await fetch(url, { method, headers: this.headers(), body: body ? JSON.stringify(body) : undefined })
            const data = await res.json().catch(() => ({}))
            if (!res.ok) throw new Error(data.message || 'Request failed.')
            return data
        },
        syncUrl() {
            const u = new URL(window.location)
            if (u.searchParams.get('tab') !== 'folders') return   // another tab of My rules is shown
            if (typeof this.selected === 'number') { u.searchParams.set('folder', this.selected); u.searchParams.delete('view') }
            else { u.searchParams.set('view', this.selected); u.searchParams.delete('folder') }
            u.searchParams.delete('item')
            history.replaceState(null, '', u)
        },
        async loadTree() {
            try {
                const d = await this.api('/collection/api/tree')
                this.folders = d.folders; this.summary = d.summary
                if (typeof this.selected === 'number' && !this.folders.some(f => f.id === this.selected)) this.selected = 'all'
            } catch (e) { create_message(e.message, 'danger') }
            finally { this.loadingTree = false }
        },
        async loadItems() {
            this.loadingItems = true
            const p = new URLSearchParams({ page: this.page, per_page: 20 })
            if (typeof this.selected === 'number') p.set('folder', this.selected)
            else p.set('view', this.selected)
            if (this.status) p.set('status', this.status)
            if (this.kind) p.set('kind', this.kind)
            if (this.search.trim()) p.set('search', this.search.trim())
            try {
                const d = await this.api('/collection/api/items?' + p)
                this.items = d.items; this.total = d.total; this.totalPages = d.total_pages || 1
            } catch (e) { create_message(e.message, 'danger') }
            finally { this.loadingItems = false }
        },
        refresh() { this.loadTree(); this.loadItems() },

        async updateItem(item, patch) {
            try {
                await this.api(`/collection/api/items/${item.id}`, 'PATCH', patch)
                if (patch.collection_id) create_message('Moved.', 'success')
                this.refresh()
            } catch (e) { create_message(e.message, 'danger') }
        },
        async removeItems(ids) {
            if (!ids.length) return
            try {
                await this.api('/collection/api/items/remove', 'POST', { ids })
                create_message(ids.length > 1 ? `${ids.length} items removed.` : 'Removed from the folder.', 'success')
                this.selection = new Set(); this.refresh()
            } catch (e) { create_message(e.message, 'danger') }
        },
        async bulkStatus(key) {
            await Promise.all([...this.selection].map(id => this.api(`/collection/api/items/${id}`, 'PATCH', { status: key })))
            this.selection = new Set(); this.refresh()
        },
        async bulkMove(e) {
            const fid = parseInt(e.target.value); e.target.value = ''
            if (!fid) return
            const results = await Promise.allSettled([...this.selection].map(id => this.api(`/collection/api/items/${id}`, 'PATCH', { collection_id: fid })))
            const failed = results.filter(r => r.status === 'rejected').length
            create_message(failed ? `${failed} already in that folder.` : 'Moved.', failed ? 'warning' : 'success')
            this.selection = new Set(); this.refresh()
        },
        toggleSelect(item) {
            const s = new Set(this.selection); s.has(item.id) ? s.delete(item.id) : s.add(item.id); this.selection = s
        },
        toggleAll() { this.selection = this.allSelected ? new Set() : new Set(this.items.map(i => i.id)) },
        onDropItem({ itemId, folderId }) { this.updateItem({ id: itemId }, { collection_id: folderId }) },

        async downloadFolder() {
            const d = await this.api(`/collection/api/folders/${this.selected}/rule_ids`)
            if (!d.ids.length) return create_message('No rule in this folder.', 'warning')
            window.location.href = '/rule/export/download?export_format=ext_each&ids=' + d.ids.join(',')
        },

        openNew(parent) { this.dialog = { folder: null, parentId: parent ? parent.id : null } },
        openEdit(folder) { this.dialog = { folder, parentId: null } },
        async saveFolder(payload) {
            try {
                if (this.dialog.folder) {
                    await this.api(`/collection/api/folders/${this.dialog.folder.id}`, 'PATCH', payload)
                } else {
                    const d = await this.api('/collection/api/folders', 'POST', payload)
                    this.selected = d.folder.id
                }
                this.dialog = null; this.loadTree()
            } catch (e) { create_message(e.message, 'danger') }
        },
        async deleteFolder(folder) {
            const sub = this.folders.filter(f => f.parent_id === folder.id).length
            const msg = `Delete the folder "${folder.name}"${sub ? ' and its sub-folders' : ''}? The rules themselves are not touched — only your notes and reminders in it.`
            if (!(await window.rzConfirm(msg))) return
            try {
                await this.api(`/collection/api/folders/${folder.id}`, 'DELETE')
                this.dialog = null
                if (this.selected === folder.id) this.selected = 'all'
                this.loadTree(); this.loadItems()
            } catch (e) { create_message(e.message, 'danger') }
        },
    },
    template: `
    <div class="cb-root">
        <!-- KPIs -->
        <div class="cb-kpis">
            <button type="button" class="cb-kpi" @click="selected = 'all'"><i class="fa-solid fa-folder-tree"></i><b>[[ folders.length ]]</b><span>folders</span></button>
            <button type="button" class="cb-kpi" @click="selected = 'all'"><i class="fa-solid fa-inbox"></i><b>[[ summary.items || 0 ]]</b><span>items</span></button>
            <button type="button" class="cb-kpi cb-kpi--blue" @click="selected = 'all'; status = 'todo'"><i class="fa-regular fa-circle"></i><b>[[ summary.open || 0 ]]</b><span>open</span></button>
            <button type="button" class="cb-kpi" :class="{ 'cb-kpi--alert': summary.due }" @click="selected = 'due'"><i class="fa-solid fa-bell"></i><b>[[ summary.due || 0 ]]</b><span>reminders due</span></button>
            <button type="button" class="cb-kpi" @click="selected = 'upcoming'"><i class="fa-regular fa-calendar"></i><b>[[ summary.upcoming || 0 ]]</b><span>upcoming</span></button>
        </div>

        <div class="cb-layout">
            <!-- Sidebar -->
            <aside class="cb-side" :class="{ 'cb-side--open': sidebarOpen }">
                <div class="cb-side__views">
                    <button v-for="v in views" :key="v.key" type="button" class="cb-view" :class="{ 'cb-view--active': selected === v.key }" @click="selected = v.key">
                        <i :class="v.icon"></i><span>[[ v.label ]]</span>
                        <span v-if="v.key === 'due' && summary.due" class="cb-view__badge cb-view__badge--alert">[[ summary.due ]]</span>
                        <span v-else-if="v.key === 'upcoming' && summary.upcoming" class="cb-view__badge">[[ summary.upcoming ]]</span>
                        <span v-else-if="v.key === 'all'" class="cb-view__badge">[[ summary.items || 0 ]]</span>
                    </button>
                </div>
                <div class="cb-side__head">
                    <span>My folders</span>
                    <button type="button" class="cb-side__add" title="New folder" @click="openNew(null)"><i class="fa-solid fa-folder-plus"></i></button>
                </div>
                <div v-if="loadingTree" class="cb-skel" v-for="n in 4" :key="n"></div>
                <collection-tree v-else :folders="folders" :selected="selected"
                                 @select="selected = $event" @edit="openEdit" @add-sub="openNew" @drop-item="onDropItem"></collection-tree>
                <div v-if="!loadingTree && !folders.length" class="cb-empty-side">No folder yet.</div>
                <p class="cb-side__tip"><i class="fa-solid fa-lightbulb"></i> Drag an item onto a folder to move it.</p>
            </aside>

            <!-- Main -->
            <section class="cb-main">
                <div class="cb-main__head">
                    <button type="button" class="btn btn-sm btn-outline-secondary d-lg-none" @click="sidebarOpen = !sidebarOpen"><i class="fa-solid fa-folder-tree"></i></button>
                    <div class="cb-title">
                        <div v-if="breadcrumb.length > 1" class="cb-crumbs">
                            <a v-for="f in breadcrumb.slice(0, -1)" :key="f.id" href="#" @click.prevent="selected = f.id">[[ f.name ]] <i class="fa-solid fa-chevron-right"></i></a>
                        </div>
                        <h4>
                            <i v-if="currentFolder" :class="currentFolder.icon" :style="{ color: currentFolder.color }"></i>
                            <i v-else-if="currentView" :class="currentView.icon"></i>
                            [[ heading ]] <span class="cb-total">[[ total ]]</span>
                        </h4>
                        <div v-if="currentFolder && currentFolder.description" class="cb-desc">[[ currentFolder.description ]]</div>
                    </div>
                    <div v-if="currentFolder" class="cb-main__actions">
                        <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill" @click="downloadFolder" title="Download the rules of this folder"><i class="fa-solid fa-download"></i></button>
                        <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill" @click="openNew(currentFolder)" title="New sub-folder"><i class="fa-solid fa-folder-plus"></i></button>
                        <button type="button" class="btn btn-sm btn-outline-primary rounded-pill" @click="openEdit(currentFolder)"><i class="fa-solid fa-pen me-1"></i>Edit</button>
                    </div>
                </div>

                <div v-if="subFolders.length" class="cb-subs">
                    <button v-for="f in subFolders" :key="f.id" type="button" class="cb-sub" @click="selected = f.id">
                        <i :class="f.icon" :style="{ color: f.color }"></i>[[ f.name ]]<span>[[ f.count ]]</span>
                    </button>
                </div>

                <div class="cb-filters">
                    <div class="cb-search"><i class="fa-solid fa-magnifying-glass"></i><input v-model="search" placeholder="Search title, format or note…"></div>
                    <div class="cb-seg">
                        <button type="button" :class="{ on: !status }" @click="status = ''">All</button>
                        <button v-for="s in statuses" :key="s.key" type="button" :class="{ on: status === s.key }" @click="status = s.key"><i :class="s.icon" :style="{ color: s.color }"></i> [[ s.label ]]</button>
                    </div>
                    <select v-model="kind" class="form-select form-select-sm cb-kind">
                        <option value="">Rules & bundles</option><option value="rule">Rules</option><option value="bundle">Bundles</option>
                    </select>
                </div>

                <div v-if="selection.size" class="cb-bulk">
                    <span><b>[[ selection.size ]]</b> selected</span>
                    <button v-for="s in statuses" :key="s.key" type="button" class="btn btn-sm btn-light rounded-pill" @click="bulkStatus(s.key)"><i :class="s.icon" :style="{ color: s.color }"></i> [[ s.label ]]</button>
                    <select class="form-select form-select-sm cb-bulk__move" @change="bulkMove">
                        <option value="">Move to…</option>
                        <option v-for="f in folders" :key="f.id" :value="f.id">[[ f.name ]]</option>
                    </select>
                    <button type="button" class="btn btn-sm btn-outline-danger rounded-pill" @click="removeItems([...selection])"><i class="fa-solid fa-xmark me-1"></i>Remove</button>
                    <button type="button" class="btn btn-sm btn-link ms-auto" @click="selection = new Set()">Clear</button>
                </div>
                <label v-else-if="items.length" class="cb-selall"><input type="checkbox" :checked="allSelected" @change="toggleAll"> Select all on this page</label>

                <div v-if="loadingItems && !items.length" class="cb-items"><div class="cb-skel cb-skel--card" v-for="n in 3" :key="n"></div></div>
                <div v-else-if="!items.length" class="cb-empty">
                    <i class="fa-solid" :class="selected === 'due' ? 'fa-mug-hot' : 'fa-folder-open'"></i>
                    <div v-if="selected === 'due'">No reminder due — all good.</div>
                    <div v-else-if="search || status || kind">Nothing matches these filters.</div>
                    <div v-else>
                        This folder is empty.<br>
                        <span>Use <b><i class="fa-solid fa-folder-plus"></i> Add to folder</b> on a rule or a bundle, or select rules in <a href="/rule/owner_rules">My rules</a> and pick "Add to folder".</span>
                    </div>
                </div>
                <div v-else class="cb-items" :class="{ 'cb-items--loading': loadingItems }">
                    <collection-item v-for="it in items" :key="it.id" :id="'ci-' + it.id" :item="it" :statuses="statuses"
                                     :folders="folders" :show-folder="typeof selected !== 'number'" :selected="selection.has(it.id)"
                                     @update="updateItem" @remove="i => removeItems([i.id])" @toggle-select="toggleSelect"></collection-item>
                </div>
                <pagination-component v-if="totalPages > 1" :current-page="page" :total-pages="totalPages" @change-page="p => page = p"></pagination-component>
            </section>
        </div>

        <folder-dialog v-if="dialog" :folder="dialog.folder" :parent-id="dialog.parentId" :folders="folders" :config="config"
                       @save="saveFolder" @delete="deleteFolder" @close="dialog = null"></folder-dialog>
    </div>`,
}
export default CollectionBrowser
