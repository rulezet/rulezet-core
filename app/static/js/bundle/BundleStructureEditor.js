/**
 * BundleStructureEditor.js
 *
 * Self-contained component for editing a bundle's file structure.
 * Renders:
 *   - Bundle Explorer (drag-and-drop tree)
 *   - A slot "rule-selector" for BundleRuleSelector (the Rule Library)
 *   - Preview / Editor panel
 *   - Overview panel (grid mode only, hidden by default)
 *
 * Props:
 *   bundleId     String|Number  required
 *   csrfToken    String         default ''
 *   focusRuleId  Number         select + reveal this rule once the tree is loaded
 *                               (arriving from the bundle's Health tab)
 *   focusNote    String         the issue to show above that rule's preview
 *   focusPath    String         select + reveal this custom file ("Folder/sub/README.md")
 *                               (the detail page's "Edit" on a file)
 *   layoutUrl    String         when set, the panels (explorer, library, preview,
 *                               overview) sit on a grid the user can rearrange —
 *                               "Customize layout" — saved per user at this URL
 *                               (GET / POST, + /reset). Needs window.GridStack.
 *
 * Emits:
 *   tree-saved — after a successful save
 *
 * Expose:
 *   addRules(rules)  — add an array of rule objects to the selected folder
 */

import SmartEditor from '/static/js/components/smart-editor.js'
import CodeViewer  from '/static/js/components/code-viewer.js'
import { create_message } from '/static/js/toaster.js'
import { editorModeFor, docIcon, RULE_ICON } from '/static/js/bundle/bundleFileTypes.js'

const { ref, computed, onMounted, onUnmounted, nextTick, watch } = Vue

// ── Customizable layout (grid mode) ─────────────────────────────────
// Same panel ids and default as app/features/bundle/bundle_layout_core.py,
// which validates and stores the layout per user. Positions are on a
// 12-column GridStack grid (see the dashboard, same library).

const PANEL_META = [
    { id: 'explorer', label: 'Bundle Explorer', icon: 'fas fa-folder-tree', minW: 3, minH: 4 },
    { id: 'library',  label: 'Rule Library',    icon: 'fas fa-database',    minW: 4, minH: 6, drawer: true },
    { id: 'preview',  label: 'Preview & Editor', icon: 'fas fa-terminal',   minW: 3, minH: 4 },
    { id: 'overview', label: 'Overview',        icon: 'fas fa-chart-simple', minW: 3, minH: 2 },
]

const DEFAULT_PANELS = [
    { id: 'explorer', x: 0, y: 0,  w: 5,  h: 9, hidden: false, mode: 'grid', minimized: false },
    { id: 'library',  x: 5, y: 0,  w: 7,  h: 9, hidden: false, mode: 'grid', minimized: false },
    { id: 'preview',  x: 0, y: 9,  w: 12, h: 7, hidden: false, mode: 'grid', minimized: false },
    { id: 'overview', x: 0, y: 16, w: 12, h: 3, hidden: true,  mode: 'grid', minimized: false },
]

// How a panel can be shown. 'drawer' only for panels flagged drawer: true.
const MODES = [
    { id: 'grid',   label: 'Docked', icon: 'fas fa-table-cells-large',
      description: 'In the page grid, next to the other panels' },
    { id: 'window', label: 'Window', icon: 'fas fa-window-restore',
      description: 'A floating window you can move and resize anywhere' },
    { id: 'drawer', label: 'Drawer', icon: 'fas fa-table-columns',
      description: 'Slides in from the right edge of the screen, opened and closed with a tab' },
]

// A preset keeps which panels are shown. The panels it places are docked
// at those positions; `modes` floats some; any other shown, docked panel
// goes full width at the bottom.
const PRESETS = [
    { id: 'side', label: 'Side by side', icon: 'fas fa-table-columns',
      description: 'Explorer and library side by side, preview below (default)',
      pos: { explorer: [0, 0, 5, 9], library: [5, 0, 7, 9], preview: [0, 9, 12, 7] } },
    { id: 'library', label: 'Wide library', icon: 'fas fa-database',
      description: 'A tall explorer and a wide library to browse many rules',
      pos: { explorer: [0, 0, 4, 13], library: [4, 0, 8, 13], preview: [0, 13, 12, 7] } },
    { id: 'columns', label: 'Three columns', icon: 'fas fa-grip',
      description: 'Explorer, library and preview in one row',
      pos: { explorer: [0, 0, 3, 12], library: [3, 0, 5, 12], preview: [8, 0, 4, 12] } },
    { id: 'editor', label: 'Focus editor', icon: 'fas fa-pen-to-square',
      description: 'Explorer next to a large editor, library below',
      pos: { explorer: [0, 0, 4, 12], preview: [4, 0, 8, 12], library: [0, 12, 12, 9] } },
    { id: 'floating', label: 'Floating library', icon: 'fas fa-window-restore',
      description: 'Explorer and editor side by side, the library in a window you place where you want',
      pos: { explorer: [0, 0, 5, 12], preview: [5, 0, 7, 12] }, modes: { library: 'window' } },
    { id: 'drawer', label: 'Library drawer', icon: 'fas fa-table-columns',
      description: 'Explorer and editor side by side, the library in a drawer on the right',
      pos: { explorer: [0, 0, 5, 12], preview: [5, 0, 7, 12] }, modes: { library: 'drawer' } },
]

const GRID_COLUMNS = 12
const clonePanels = (list) => list.map(p => ({ mode: 'grid', minimized: false, ...p, ...(p.win ? { win: { ...p.win } } : {}) }))

// ── TreeItem sub-component ─────────────────────────────────────────

const TREE_ITEM_TEMPLATE = `
<li class="mb-1 bse-tree-item" style="list-style:none;" :data-id="node.id">
    <div
        class="bse-node-row"
        :class="{
            'bse-node-row--selected': selectedId === node.id,
            'bse-node-row--drop-target': localDropTarget && node.type === 'folder',
            'bse-node-row--multi': multiSet && multiSet.has(node.id),
            'bse-node-row--doc': node.type === 'file' && !isRule(node),
        }"
        :title="multiSet && multiSet.size ? 'Ctrl/Cmd+click to add to selection' : ''"
        @click.stop="onRowClick($event, node)"
        @dragover="onDragOver($event, node)"
        @dragleave="onDragLeave($event)"
        @drop="onDrop($event, node)"
    >
        <span class="bse-node-drag-handle" title="Drag to move">
            <i class="fas fa-grip-vertical"></i>
        </span>

        <!-- Folder: chevron + folder icon -->
        <template v-if="node.type === 'folder'">
            <i class="fas bse-chevron"
               :class="collapsed ? 'fa-chevron-right' : 'fa-chevron-down'"
               style="font-size:.65rem;flex-shrink:0;color:var(--subtle-text-color);">
            </i>
            <i :class="collapsed ? 'fas fa-folder text-warning' : 'fas fa-folder-open text-warning'"
               style="font-size:.78rem;flex-shrink:0;"></i>
        </template>
        <!-- File: rule = blue shield, custom file = per-extension teal icon -->
        <i v-else
            :class="fileIcon(node).icon"
            :style="{ fontSize: '.78rem', flexShrink: 0, color: fileIcon(node).color }">
        </i>

        <input v-if="renamingId === node.id" ref="renameInput" class="bse-node-name-input"
            :value="renameBaseName(node)"
            @click.stop @keydown.stop
            @keyup.enter="$emit('rename-confirm', node, $event.target.value)"
            @keyup.esc="$emit('rename-cancel')"
            @blur="$emit('rename-confirm', node, $event.target.value)">
        <span v-if="renamingId === node.id && renameExtOf(node)" class="bse-node-ext-lock">{{ renameExtOf(node) }}</span>
        <span v-if="renamingId !== node.id" class="bse-node-name" :title="node.name">{{ node.name }}</span>

        <div class="bse-node-actions" :class="{ 'bse-node-actions--force': armed }">
            <button v-if="!isRule(node)" class="bse-node-btn" title="Rename"
                @click.stop="$emit('rename', node)">
                <i class="fas fa-edit"></i>
            </button>
            <button v-if="node.type === 'folder'" class="bse-node-btn bse-node-btn--success" title="Add sub-folder"
                @click.stop="$emit('add-sub', node.children, 'folder')">
                <i class="fas fa-folder-plus"></i>
            </button>
            <button v-if="node.type === 'folder'" class="bse-node-btn" title="Create file"
                @click.stop="$emit('add-sub', node.children, 'file')">
                <i class="fas fa-file-medical"></i>
            </button>
            <span v-if="armed" class="bse-armed-hint">Click again to delete</span>
            <button class="bse-node-btn bse-node-btn--danger"
                :class="{ 'bse-node-btn--armed': armed }"
                :title="armed ? 'Click again to confirm removal' : 'Remove'"
                @click.stop="onDeleteClick(node)">
                <i class="fas fa-trash-alt"></i>
            </button>
        </div>
    </div>

    <div v-if="node.type === 'folder'" v-show="!collapsed"
         class="ps-3 border-start ms-2 mt-1">
        <draggable v-model="node.children" group="bse-tree" :item-key="n => n.id" tag="ul"
            class="ps-0 mb-0 bse-folder-drop-zone" :animation="150" ghost-class="bse-ghost"
            @end="$emit('sort-end', $event)">
            <template #item="{ element }">
                <tree-item
                    :node="element"
                    :selected-id="selectedId"
                    :multi-set="multiSet"
                    :renaming-id="renamingId"
                    @select="n => $emit('select', n)"
                    @rename="n => $emit('rename', n)"
                    @rename-confirm="(n, t) => $emit('rename-confirm', n, t)"
                    @rename-cancel="$emit('rename-cancel')"
                    @add-sub="(arr, kind) => $emit('add-sub', arr, kind)"
                    @remove="n => $emit('remove', n)"
                    @external-drop="(n, rules) => $emit('external-drop', n, rules)"
                    @toggle-multi="n => $emit('toggle-multi', n)"
                    @sort-end="ev => $emit('sort-end', ev)"
                />
            </template>
        </draggable>
    </div>
</li>
`

const TreeItem = {
    name: 'tree-item',
    props: ['node', 'selectedId', 'multiSet', 'renamingId'],
    template: TREE_ITEM_TEMPLATE,
    emits: ['select', 'rename', 'rename-confirm', 'rename-cancel', 'add-sub', 'remove', 'external-drop', 'toggle-multi', 'sort-end'],
    components: { draggable: window.vuedraggable },
    data() { return { localDropTarget: false, _leaveTimer: null, collapsed: false, armed: false, _armTimer: null } },
    updated() {
        // Autofocus the inline rename input the moment it appears.
        if (this.renamingId === this.node.id && this.$refs.renameInput && document.activeElement !== this.$refs.renameInput) {
            this.$refs.renameInput.focus()
            this.$refs.renameInput.select()
        }
    },
    methods: {
        isRule(node) { return node && String(node.id).startsWith('rule_') },
        fileIcon(node) { return this.isRule(node) ? RULE_ICON : docIcon(node.name) },
        toggleCollapse() { this.collapsed = !this.collapsed },

        // Custom (non-rule) files keep a locked extension while renaming —
        // only the base name is editable.
        renameBaseName(node) {
            if (node.type === 'file' && !this.isRule(node)) {
                const dot = node.name.lastIndexOf('.')
                return dot > 0 ? node.name.slice(0, dot) : node.name
            }
            return node.name
        },
        renameExtOf(node) {
            if (node.type === 'file' && !this.isRule(node)) {
                const dot = node.name.lastIndexOf('.')
                return dot > 0 ? node.name.slice(dot) : ''
            }
            return ''
        },

        // Plain click: preview (file) or expand/collapse (folder), as before.
        // Ctrl/Cmd+click: toggle this node in the multi-selection instead —
        // lets the user build up a set of rules/files to move or delete
        // together without touching each one's drag handle individually.
        onRowClick(ev, node) {
            if (ev.ctrlKey || ev.metaKey) {
                this.$emit('toggle-multi', node)
                return
            }
            if (node.type === 'folder') this.toggleCollapse()
            else this.$emit('select', node)
        },

        // First click arms the button (highlighted, no deletion yet); the
        // user must click again within 3s to actually confirm removal.
        // Replaces the old modal confirmation with a lighter two-click one.
        onDeleteClick(node) {
            clearTimeout(this._armTimer)
            if (this.armed) {
                this.armed = false
                this.$emit('remove', node)
            } else {
                this.armed = true
                this._armTimer = setTimeout(() => { this.armed = false }, 3000)
            }
        },

        // Only intercept dragover when an external rule is being dragged.
        // For internal tree reordering (SortableJS), let events propagate freely.
        onDragOver(ev, node) {
            if (!ev.dataTransfer.types.includes('application/rulezet-rule')) return
            if (node.type !== 'folder') return
            ev.preventDefault()
            ev.stopPropagation()
            clearTimeout(this._leaveTimer)
            this.localDropTarget = true
        },

        // Use a small delay to avoid flicker when moving between child elements.
        onDragLeave(ev) {
            this._leaveTimer = setTimeout(() => { this.localDropTarget = false }, 80)
        },

        // Only handle external rule drops; internal drops are handled by SortableJS.
        onDrop(ev, node) {
            this.localDropTarget = false
            const raw = ev.dataTransfer.getData('application/rulezet-rule')
            if (!raw) return               // internal SortableJS drop — ignore
            if (node.type !== 'folder') return
            ev.preventDefault()
            ev.stopPropagation()
            try { this.$emit('external-drop', node, JSON.parse(raw)) } catch {}
        },
    }
}

// ── Main component ─────────────────────────────────────────────────

export default {
    name: 'BundleStructureEditor',

    components: {
        'tree-item': TreeItem,
        'draggable': window.vuedraggable,
        SmartEditor,
        CodeViewer,
    },

    props: {
        bundleId:  { type: [String, Number], required: true },
        csrfToken: { type: String, default: '' },
        focusRuleId: { type: Number, default: null },
        focusNote:   { type: String, default: '' },
        focusPath:   { type: String, default: '' },
        // Set (edit page): panels on a grid the user arranges, layout
        // loaded from / saved to this URL. Unset (the in-modal editors):
        // fixed classic layout, no overview panel.
        layoutUrl:   { type: String, default: '' },
    },

    emits: ['tree-saved', 'tree-ready'],

    expose: ['addRules', 'setPreview', 'focusRule'],

    template: `
    <div class="bse-wrapper" :class="{ 'bse-wrapper--grid': gridMode, 'bse-wrapper--layout-editing': layoutEditing }"
         :style="drawerSpace ? { paddingRight: drawerSpace + 'px' } : null">

        <!-- ── Section header ── -->
        <div class="bse-toolbar">
            <div class="bse-head__accent"></div>
            <span class="bse-head__title"><i class="fas fa-sitemap"></i>Bundle structure</span>
            <span v-if="lastSavedAt" class="bse-last-saved" title="Every change is saved automatically">
                <i class="fas fa-check-circle"></i>Saved {{ lastSavedAt }}
            </span>
            <div class="bse-head__actions">
                <button v-if="gridMode" class="bse-layout-btn" :class="{ 'bse-layout-btn--active': layoutEditing }"
                        @click="toggleLayoutEditing"
                        :title="layoutEditing ? 'Back to editing the bundle' : 'Move, resize, show or hide the panels'">
                    <i :class="layoutEditing ? 'fas fa-check' : 'fas fa-table-cells-large'"></i>
                    {{ layoutEditing ? 'Done' : 'Customize layout' }}
                </button>
                <button class="bse-save-btn" @click="saveNow" :disabled="saving">
                    <i :class="saving ? 'fas fa-spinner fa-spin' : 'fas fa-save'"></i>
                    {{ saving ? 'Saving…' : 'Save' }}
                    <i v-if="saveStatus === 'saved'" class="fas fa-check-circle bse-save-ok ms-1"></i>
                    <i v-else-if="saveStatus === 'error'" class="fas fa-times-circle bse-save-err ms-1"></i>
                </button>
            </div>
        </div>

        <!-- ── Layout toolbar (grid mode, while customizing) ── -->
        <div v-if="gridMode && layoutEditing" class="bse-layout-bar">
            <div class="bse-layout-hint">
                <span class="bse-head__title"><i class="fas fa-table-cells-large"></i>Customize the layout</span>
                <span class="bse-head__help" tabindex="0"
                      title="Show each panel docked in the page, as a floating window, or (Rule Library) as a side drawer · Docked panels: drag to move, pull the bottom-right corner to resize · Dragging rules into the explorer works in every mode · Saved automatically, for every bundle">
                    <i class="fas fa-circle-question"></i>
                </span>
            </div>
            <div class="bse-layout-panels">
                <div v-for="m in PANEL_META" :key="m.id" class="bse-panel-card"
                     :class="{ 'bse-panel-card--off': isPanelHidden(m.id) }">
                    <div class="bse-panel-card-head">
                        <i :class="m.icon"></i>
                        <span>{{ m.label }}</span>
                        <button class="bse-panel-card-eye" @click="togglePanel(m.id)"
                                :title="(isPanelHidden(m.id) ? 'Show ' : 'Hide ') + m.label">
                            <i :class="isPanelHidden(m.id) ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
                        </button>
                    </div>
                    <div class="bse-seg" role="group" :aria-label="m.label + ' display'">
                        <button v-for="mode in modesFor(m)" :key="mode.id"
                                :class="{ 'bse-seg--on': panelMode(m.id) === mode.id }"
                                :disabled="isPanelHidden(m.id)"
                                @click="setPanelMode(m.id, mode.id)" :title="mode.description">
                            <i :class="mode.icon"></i>{{ mode.label }}
                        </button>
                    </div>
                </div>
            </div>
            <div class="bse-layout-groups">
                <div class="bse-layout-group">
                    <span class="bse-layout-label">Presets</span>
                    <button v-for="pr in PRESETS" :key="pr.id" class="bse-chip-btn" @click="applyPreset(pr)" :title="pr.description">
                        <i :class="pr.icon"></i>{{ pr.label }}
                    </button>
                </div>
                <button class="bse-layout-reset" @click="resetLayout" title="Back to the default layout">
                    <i class="fas fa-rotate-left"></i>Reset
                </button>
            </div>
        </div>

        <!-- ── Panels ──
             Grid mode (edit page): a GridStack grid the user arranges.
             Classic mode (the in-modal editors): explorer + library side by
             side, preview below — same markup, laid out by CSS. -->
        <div :class="gridMode ? 'grid-stack bse-grid' : 'bse-classic'" ref="gridEl">
            <!-- One element per panel whatever its mode — switching between
                 docked / window / drawer only changes its classes, so the
                 panel (and the Rule Library's filters) is never remounted.
                 GridStack only manages the .grid-stack-item ones; windows and
                 the drawer are position:fixed and ignore the grid. -->
            <div v-for="p in renderedPanels" :key="p.id"
                 :class="outerClass(p)" :style="outerStyle(p)" v-bind="outerAttrs(p)"
                 @pointerdown="isFloating(p) && raiseWindow(p.id)">

                <!-- Window / drawer title bar -->
                <div v-if="isFloating(p)" class="bse-window-bar"
                     @pointerdown="startWindowDrag($event, p.id)" @dblclick="toggleMinimized(p.id)">
                    <i v-if="p.mode === 'window'" class="fas fa-grip-vertical bse-window-grip"></i>
                    <i :class="panelMeta(p.id).icon" class="bse-window-icon"></i>
                    <span class="bse-window-title">{{ panelMeta(p.id).label }}</span>
                    <div class="bse-window-actions">
                        <button v-if="p.mode === 'drawer'" @click="setPanelMode(p.id, 'window')" title="Float as a window">
                            <i class="fas fa-window-restore"></i>
                        </button>
                        <button v-if="p.mode === 'window' && panelMeta(p.id).drawer" @click="setPanelMode(p.id, 'drawer')" title="Open as a side drawer">
                            <i class="fas fa-table-columns"></i>
                        </button>
                        <button @click="setPanelMode(p.id, 'grid')" title="Dock back into the page">
                            <i class="fas fa-table-cells-large"></i>
                        </button>
                        <button @click="toggleMinimized(p.id)"
                                :title="p.mode === 'drawer' ? 'Close the drawer' : (p.minimized ? 'Expand' : 'Minimize')">
                            <i :class="p.mode === 'drawer' ? 'fas fa-xmark' : (p.minimized ? 'fas fa-window-maximize' : 'fas fa-window-minimize')"></i>
                        </button>
                    </div>
                </div>

                <!-- Closed drawer: a tab on the right edge of the screen -->
                <button v-if="p.mode === 'drawer'" class="bse-drawer-tab" :class="{ 'bse-drawer-tab--open': !p.minimized }"
                        @click="toggleMinimized(p.id)" :title="p.minimized ? 'Open ' + panelMeta(p.id).label : 'Close'">
                    <i :class="p.minimized ? panelMeta(p.id).icon : 'fas fa-chevron-right'"></i>
                    <span v-if="p.minimized">{{ panelMeta(p.id).label }}</span>
                </button>

                <div v-show="!(p.mode === 'window' && p.minimized)" :class="innerClass(p)">

                    <!-- Customizing: a docked panel is a block you move / resize -->
                    <div v-if="layoutEditing && p.mode === 'grid'" class="bse-panel-overlay">
                        <i :class="panelMeta(p.id).icon" class="bse-panel-overlay-icon"></i>
                        <strong>{{ panelMeta(p.id).label }}</strong>
                        <span class="bse-panel-overlay-hint">Drag to move · corner to resize</span>
                        <button class="bse-panel-overlay-hide" @click.stop="togglePanel(p.id)" title="Hide this panel">
                            <i class="fas fa-eye-slash"></i>
                        </button>
                    </div>

                    <template v-if="p.id === 'explorer'">
                    <!-- Bundle Explorer -->
                    <div class="bse-explorer-card">
                        <div class="bse-head">
                            <div class="bse-head__accent"></div>
                            <span class="bse-head__title"><i class="fas fa-folder-tree"></i>Bundle explorer</span>
                            <span class="bse-head__help" tabindex="0"
                                  title="Drag a node to reorganize · Drop rules from the library onto a folder · Ctrl/Cmd+click to select several">
                                <i class="fas fa-circle-question"></i>
                            </span>
                            <div class="bse-head__actions">
                                <button class="bse-action-btn" title="Add Folder"
                                    @click="prepareTarget(treeData, 'folder')">
                                    <i class="fas fa-folder-plus"></i>
                                </button>
                                <button class="bse-action-btn" title="Create File"
                                    @click="prepareTarget(treeData, 'file')">
                                    <i class="fas fa-file-code"></i>
                                </button>
                            </div>
                        </div>

                        <!-- Inline creation panel — replaces the old modal (nesting a
                             Bootstrap modal inside the "Organize Bundle" modal wasn't
                             reliable), opens right under the header instead. -->
                        <div v-if="creationMode === 'folder'" class="bse-create-bar">
                            <i class="fas fa-folder-plus text-warning"></i>
                            <input class="bse-create-input" placeholder="Folder name" v-model="folderText"
                                   @keyup.enter="confirmAddFolder" @keyup.esc="cancelCreation" autofocus>
                            <button class="bse-bulk-btn" @click="confirmAddFolder">Create</button>
                            <button class="bse-bulk-btn bse-bulk-btn--ghost" @click="cancelCreation" title="Cancel">
                                <i class="fas fa-xmark"></i>
                            </button>
                        </div>
                        <div v-if="creationMode === 'file'" class="bse-create-bar">
                            <i class="fas fa-file-code text-success"></i>
                            <input class="bse-create-input" placeholder="File name" v-model="fileNameText"
                                   @keyup.enter="confirmAddFile" @keyup.esc="cancelCreation" autofocus>
                            <select class="bse-create-select" v-model="fileExt">
                                <option value=".txt">.txt</option>
                                <option value=".json">.json</option>
                                <option value=".yaml">.yaml</option>
                                <option value=".md">.md</option>
                            </select>
                            <button class="bse-bulk-btn" @click="confirmAddFile">Create</button>
                            <button class="bse-bulk-btn bse-bulk-btn--ghost" @click="cancelCreation" title="Cancel">
                                <i class="fas fa-xmark"></i>
                            </button>
                        </div>

                        <!-- Bulk action bar — appears once 2+ nodes are Ctrl/Cmd-selected.
                             "Move" is drag-and-drop: grab any selected node's drag
                             handle and the rest of the selection follows it to the
                             drop target (see onTreeSortEnd). -->
                        <div v-if="multiSelected.size > 0" class="bse-bulk-bar">
                            <span class="bse-bulk-count">
                                <i class="fas fa-check-square me-1"></i>{{ multiSelected.size }} selected
                                <span class="bse-bulk-hint">— drag any of them to move the group</span>
                            </span>
                            <button class="bse-bulk-btn bse-bulk-btn--danger" :class="{ 'bse-bulk-btn--armed': bulkDeleteArmed }" @click="confirmBulkDelete">
                                <i class="fas fa-trash-alt me-1"></i>{{ bulkDeleteArmed ? 'Click again to delete' : 'Delete' }}
                            </button>
                            <button class="bse-bulk-btn bse-bulk-btn--ghost" @click="clearMultiSelect" title="Clear selection">
                                <i class="fas fa-xmark"></i>
                            </button>
                        </div>

                        <!-- Tree body with root drop zone -->
                        <div class="bse-tree-body"
                            @dragover.prevent="onRootDragOver"
                            @dragleave="onRootDragLeave"
                            @drop.prevent="onRootDrop">
                            <draggable v-model="treeData" group="bse-tree" :item-key="i => i.id" tag="ul"
                                class="ps-0 mb-0 bse-root-drop-zone" :animation="150" ghost-class="bse-ghost"
                                @end="onTreeSortEnd">
                                <template #item="{ element }">
                                    <tree-item
                                        :node="element"
                                        :selected-id="selectedNode?.id"
                                        :multi-set="multiSelected"
                                        :renaming-id="nodeToRename?.id"
                                        @select="selectNode"
                                        @rename="beginRename"
                                        @rename-confirm="confirmRename"
                                        @rename-cancel="cancelRename"
                                        @add-sub="prepareTarget"
                                        @remove="beginDelete"
                                        @external-drop="onExternalDropOnFolder"
                                        @toggle-multi="toggleMultiSelect"
                                        @sort-end="onTreeSortEnd"
                                    />
                                </template>
                            </draggable>
                            <div v-if="treeData.length === 0" class="bse-empty-tree text-center py-4 text-muted small">
                                <i class="fas fa-folder-open fa-2x opacity-25 d-block mb-2"></i>
                                Empty — add folders or drag rules here
                            </div>
                        </div>
                    </div>
                    </template>

                    <!-- Rule Library (BundleRuleSelector, passed in by the page) -->
                    <slot v-else-if="p.id === 'library'" name="rule-selector" />

                    <!-- Preview / Editor -->
                    <div v-else-if="p.id === 'preview'" class="bse-preview-card" :ref="setPreviewCard">
                        <template v-if="!selectedNode && !previewContent">
                            <div class="bse-head">
                                <div class="bse-head__accent bse-head__accent--orange"></div>
                                <span class="bse-head__title"><i class="fas fa-terminal"></i>Preview</span>
                            </div>
                            <div class="bse-preview-empty">
                                <i class="fas fa-file-lines"></i>
                                <span>Select a file in the explorer or a rule in the library</span>
                            </div>
                        </template>
                        <template v-else>
                            <div class="bse-head">
                                <div class="bse-head__accent bse-head__accent--orange"></div>
                                <span class="bse-head__title"><i class="fas fa-terminal"></i>Preview</span>
                                <span class="bse-preview-filename" :title="selectedNode ? selectedNode.name : previewName">
                                    <i v-if="selectedNode && selectedNode.type === 'folder'" class="fas fa-folder text-warning"></i>
                                    <i v-else-if="selectedNode"
                                       :class="(isRule(selectedNode) ? RULE_ICON : docIcon(selectedNode.name)).icon"
                                       :style="{ color: (isRule(selectedNode) ? RULE_ICON : docIcon(selectedNode.name)).color }"></i>
                                    <i v-else class="fas fa-eye text-success"></i>
                                    <span>{{ selectedNode ? selectedNode.name : previewName }}</span>
                                </span>
                                <div class="bse-head__actions">
                                    <span v-if="!selectedNode || isRule(selectedNode)" class="bse-pill">
                                        <i class="fas fa-lock"></i>Read-only
                                    </span>
                                    <template v-else-if="selectedNode.type === 'file'">
                                        <span class="bse-pill bse-pill--blue"><i class="fas fa-pen"></i>Editable</span>
                                        <button class="bse-editor-save-btn" @click="saveNow" :disabled="saving"
                                                :title="saving ? 'Saving…' : 'Save file'">
                                            <i :class="saving ? 'fas fa-spinner fa-spin' : 'fas fa-save'"></i>
                                            {{ saving ? 'Saving…' : 'Save' }}
                                            <i v-if="saveStatus === 'saved'" class="fas fa-check-circle bse-save-ok ms-1"></i>
                                            <i v-else-if="saveStatus === 'error'" class="fas fa-times-circle bse-save-err ms-1"></i>
                                        </button>
                                    </template>
                                    <button class="bse-preview-close" @click="clearDisplay" title="Close">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                            </div>

                            <div class="bse-preview-body">
                                <!-- Editable custom file -->
                                <template v-if="selectedNode && selectedNode.type === 'file' && !isRule(selectedNode)">
                                    <smart-editor
                                        hardened-preview
                                        :key="selectedNode.id + '|' + selectedNode.name"
                                        :model-value="selectedNode.content ?? ''"
                                        @update:model-value="onContentChange"
                                        :mode="editorModeFor(selectedNode.name).mode"
                                        :language="editorModeFor(selectedNode.name).language"
                                        :min-height="editorHeight"
                                        :max-height="editorHeight">
                                    </smart-editor>
                                    <div class="bse-editor-bottom-bar">
                                        <span v-if="lastSavedAt" class="bse-last-saved">
                                            <i class="fas fa-check-circle"></i>
                                            <span>Last save</span>
                                            <strong>{{ lastSavedAt }}</strong>
                                        </span>
                                        <button class="bse-save-btn ms-auto" @click="saveNow" :disabled="saving">
                                            <i :class="saving ? 'fas fa-spinner fa-spin' : 'fas fa-save'"></i>
                                            {{ saving ? 'Saving…' : 'Save file' }}
                                            <i v-if="saveStatus === 'saved'" class="fas fa-check-circle bse-save-ok ms-1"></i>
                                            <i v-else-if="saveStatus === 'error'" class="fas fa-times-circle bse-save-err ms-1"></i>
                                        </button>
                                    </div>
                                </template>

                                <!-- Rule of the bundle (read-only), with the Health-tab issue above it -->
                                <template v-else-if="selectedNode && isRule(selectedNode)">
                                    <div v-if="focusNote && selectedNode.rule_id === focusRuleId" class="bse-focus-note">
                                        <i class="fa-solid fa-heart-pulse"></i>
                                        <span>{{ focusNote }}</span>
                                    </div>
                                    <code-viewer
                                        :code="selectedNode.content || ''"
                                        :language="selectedNode.format || 'auto'"
                                        :title="selectedNode.name"
                                        :max-height="viewerMaxHeight">
                                    </code-viewer>
                                </template>

                                <!-- Rule preview from the library -->
                                <code-viewer
                                    v-else-if="previewContent"
                                    :code="previewContent"
                                    :language="previewFormat || 'auto'"
                                    :title="previewName"
                                    :max-height="viewerMaxHeight">
                                </code-viewer>

                                <!-- Folder selected -->
                                <div v-else class="bse-preview-folder">
                                    <i class="fas fa-folder-open fa-2x mb-2 opacity-25"></i>
                                    <p class="small mb-0">
                                        Folder <strong>{{ selectedNode.name }}</strong> is selected.<br>
                                        Rules added from the library go into it.
                                    </p>
                                </div>
                            </div>
                        </template>
                    </div>

                    <!-- Overview: what the bundle holds, at a glance -->
                    <div v-else-if="p.id === 'overview'" class="bse-overview-card">
                        <div class="bse-head">
                            <div class="bse-head__accent bse-head__accent--purple"></div>
                            <span class="bse-head__title"><i class="fas fa-chart-simple"></i>Overview</span>
                        </div>
                        <div class="bse-overview-body">
                            <div class="bse-overview-stats">
                                <div class="bse-overview-stat"><strong>{{ overview.rules }}</strong><span>rule{{ overview.rules === 1 ? '' : 's' }}</span></div>
                                <div class="bse-overview-stat"><strong>{{ overview.files }}</strong><span>file{{ overview.files === 1 ? '' : 's' }}</span></div>
                                <div class="bse-overview-stat"><strong>{{ overview.folders }}</strong><span>folder{{ overview.folders === 1 ? '' : 's' }}</span></div>
                            </div>
                            <div v-if="overview.formats.length" class="bse-overview-formats">
                                <span v-for="f in overview.formats" :key="f.name" class="bse-overview-format">
                                    {{ f.name }} <strong>{{ f.count }}</strong>
                                </span>
                            </div>
                        </div>
                    </div>

                </div>

                <!-- Window resize grip / drawer width handle -->
                <div v-if="p.mode === 'window' && !p.minimized" class="bse-window-resize"
                     @pointerdown="startWindowResize($event, p.id)" title="Resize"></div>
                <div v-if="p.mode === 'drawer' && !p.minimized" class="bse-drawer-edge"
                     @pointerdown="startDrawerResize($event, p.id)" title="Drag to resize"></div>
            </div>
        </div>

    </div>
    `,

    setup(props, { emit }) {

        // ── Tree state ─────────────────────────────────────────────
        const treeData    = ref([{ id: 'root', name: 'Main Bundle', type: 'folder', children: [], content: '' }])
        const selectedNode   = ref(null)
        const lastFolder     = ref(null)  // last folder the user selected
        const previewContent = ref('')
        const previewName    = ref('')
        const previewFormat  = ref('')
        const saving         = ref(false)
        const saveStatus     = ref('')    // '' | 'saved' | 'error'
        const lastSavedAt    = ref('')
        const rootDropActive = ref(false)
        let saveStatusTimer  = null
        let autoSaveTimer    = null
        const treeLoaded     = ref(false)

        // Extract all rule_id values from the tree recursively
        function extractRuleIds(nodes) {
            const ids = new Set()
            function walk(list) {
                for (const n of list) {
                    if (n.rule_id) ids.add(n.rule_id)
                    if (n.children?.length) walk(n.children)
                }
            }
            walk(nodes)
            return ids
        }

        // Auto-save: fires 1200ms after any tree change (reorder, rename, content edit)
        watch(treeData, () => {
            if (!treeLoaded.value) return
            clearTimeout(autoSaveTimer)
            autoSaveTimer = setTimeout(() => saveStructure(), 1200)
        }, { deep: true })

        // ── Multi-select (Ctrl/Cmd+click) — move or delete several
        // nodes together instead of one at a time ─────────────────────
        const multiSelected = ref(new Set())
        const bulkDeleteArmed = ref(false)
        let bulkDeleteTimer = null

        function toggleMultiSelect(node) {
            const s = new Set(multiSelected.value)
            if (s.has(node.id)) s.delete(node.id)
            else s.add(node.id)
            multiSelected.value = s
            bulkDeleteArmed.value = false
        }
        function clearMultiSelect() {
            multiSelected.value = new Set()
            bulkDeleteArmed.value = false
        }

        // Remove and return the node with this id from the tree (or null).
        function extractNode(list, id) {
            const idx = list.findIndex(i => i.id === id)
            if (idx > -1) return list.splice(idx, 1)[0]
            for (const item of list) {
                if (item.children) {
                    const found = extractNode(item.children, id)
                    if (found) return found
                }
            }
            return null
        }

        // Which array currently holds this node id (its parent's children,
        // or treeData itself for a root-level node)?
        function findParentList(list, id) {
            if (list.some(n => n.id === id)) return list
            for (const item of list) {
                if (item.children) {
                    const found = findParentList(item.children, id)
                    if (found) return found
                }
            }
            return null
        }

        // Dragging one node when it's part of a multi-selection drags the
        // whole selection: SortableJS only physically moves the one item the
        // user grabbed, so once that drop lands we move every other selected
        // node alongside it into the same destination.
        function onTreeSortEnd(evt) {
            if (multiSelected.value.size < 2) return
            const draggedId = evt?.item?.dataset?.id
            if (!draggedId || !multiSelected.value.has(draggedId)) return
            const destination = findParentList(treeData.value, draggedId)
            if (!destination) return
            for (const id of multiSelected.value) {
                if (id === draggedId) continue
                const node = extractNode(treeData.value, id)
                if (node) destination.push(node)
            }
            clearMultiSelect()
            emit('tree-ready', [...extractRuleIds(treeData.value)])
            saveStructure()
        }

        // Same two-click "arm" pattern as single-node delete.
        function confirmBulkDelete() {
            if (!bulkDeleteArmed.value) {
                bulkDeleteArmed.value = true
                clearTimeout(bulkDeleteTimer)
                bulkDeleteTimer = setTimeout(() => { bulkDeleteArmed.value = false }, 3000)
                return
            }
            const ids = [...multiSelected.value]
            for (const id of ids) extractNode(treeData.value, id)
            if (selectedNode.value && ids.includes(selectedNode.value.id)) clearDisplay()
            clearMultiSelect()
            emit('tree-ready', [...extractRuleIds(treeData.value)])
            saveStructure()
        }

        // ── Inline create/rename state (was modal-based — nesting a
        // Bootstrap modal inside another open modal, like the in-modal
        // "Organize Bundle" view, doesn't reliably show/stack) ──────────
        const folderText    = ref('')
        const fileNameText  = ref('')
        const fileExt       = ref('.txt')
        const nodeToRename  = ref(null)   // node currently being renamed inline
        const currentTarget = ref(null)   // the array we add to
        const creationMode  = ref(null)   // 'folder' | 'file' | null — inline creation panel

        // ── Helpers ────────────────────────────────────────────────
        const isRule = (node) => node && String(node.id).startsWith('rule_')

        // Same rules as the backend (validate_structure): no path separators,
        // no control chars, not '.'/'..', max 255 chars.
        const cleanName = (raw) => {
            const n = String(raw || '').replace(/[\/\\]/g, '_').replace(/[\u0000-\u001f\u007f\u202a-\u202e\u2066-\u2069]/g, '').trim()
            return (n === '.' || n === '..') ? '' : n.slice(0, 240)
        }

        // Highlighting: <code-viewer> is given the raw rule format string
        // directly (:language="rule.format || 'auto'") and resolves it
        // itself via its own LANG_ALIASES map — same convention as the
        // rule detail page — instead of duplicating a second, incomplete
        // format->language table here.

        // Fallback only — rule JSON carries `extension` (Rule.get_extension(),
        // the backend source of truth) and it's used first in _fileName().
        const _ext = (format) => {
            const map = {
                yara: '.yar', sigma: '.yml', suricata: '.rules', sagan: '.rules', snort: '.rules',
                zeek: '.zeek', wazuh: '.xml', nse: '.nse', crs: '.conf', nova: '.nov',
                splunk: '.yml', elastic: '.toml', kql: '.kql', kunai: '.kun', atr: '.yaml', plum: '.yaml',
            }
            return map[(format || '').toLowerCase()] || '.txt'
        }

        // Many rule titles are full sentences ending in a period (most
        // Wazuh titles do, e.g. "Integrity checksum changed.") — appending
        // _ext() straight onto that produced a double dot before the
        // extension ("...changed..xml"). Strip trailing dots first.
        const _fileName = (rule) => (rule.title || '').replace(/\.+$/, '') +
            (rule.extension ? '.' + rule.extension : _ext(rule.format))

        // ── Load / save ────────────────────────────────────────────
        async function loadTree() {
            treeLoaded.value = false
            try {
                const res = await fetch(`/bundle/get_bundle_json/${props.bundleId}`)
                const data = await res.json()
                if (data.success && data.structure) treeData.value = data.structure
            } catch {}
            await nextTick()
            treeLoaded.value = true
            emit('tree-ready', [...extractRuleIds(treeData.value)])
            if (props.focusRuleId) focusRule(props.focusRuleId)
            else if (props.focusPath) focusFile(props.focusPath)
        }

        // Custom file by its path in the tree (names joined with '/')
        function focusFile(path) {
            const find = (nodes, prefix) => {
                for (const n of nodes || []) {
                    const p = prefix ? prefix + '/' + n.name : n.name
                    if (n.type === 'file' && !isRule(n) && p === path) return n
                    const hit = find(n.children, p)
                    if (hit) return hit
                }
                return null
            }
            const node = find(treeData.value, '')
            if (!node) {
                create_message('This file is no longer in the structure', 'warning-subtle')
                return
            }
            _reveal(node)
        }

        // Select a rule of the tree, open its preview and bring its row
        // into view (Health tab → "Edit in the bundle").
        async function focusRule(ruleId) {
            const find = (nodes) => {
                for (const n of nodes || []) {
                    if (n.rule_id === ruleId) return n
                    const hit = find(n.children)
                    if (hit) return hit
                }
                return null
            }
            const node = find(treeData.value)
            if (!node) {
                create_message('This rule is not placed in the structure — drop it into a folder from the library', 'warning-subtle')
                return
            }
            _reveal(node)
        }

        async function _reveal(node) {
            selectNode(node)
            await nextTick()
            const row = document.querySelector(`.bse-tree-item[data-id="${CSS.escape(String(node.id))}"] > .bse-node-row`)
            if (row) {
                row.scrollIntoView({ behavior: 'smooth', block: 'center' })
                row.classList.remove('bse-node-row--flash')
                void row.offsetWidth
                row.classList.add('bse-node-row--flash')
            }
        }

        function _timeStr() {
            return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        }

        let saveQueued = false
        async function saveStructure() {
            if (saving.value) {
                // Don't silently drop this change — a save is already in
                // flight (e.g. two quick drag-drops back to back). Queue one
                // retry so it still gets persisted once the current save ends.
                saveQueued = true
                return false
            }
            clearTimeout(autoSaveTimer)  // cancel pending auto-save; we're saving now
            saving.value = true
            saveStatus.value = ''
            clearTimeout(saveStatusTimer)
            try {
                const res = await fetch(`/bundle/save_workspace/${props.bundleId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ structure: treeData.value }),
                })
                const data = await res.json()
                if (data.success) {
                    saveStatus.value = 'saved'
                    lastSavedAt.value = _timeStr()
                    const ruleIds = [...extractRuleIds(treeData.value)]
                    emit('tree-saved', ruleIds)
                    saveStatusTimer = setTimeout(() => { saveStatus.value = '' }, 2500)
                    return true
                } else {
                    saveStatus.value = 'error'
                    if (data.message) create_message(data.message, data.toast_class || 'danger-subtle')
                    saveStatusTimer = setTimeout(() => { saveStatus.value = '' }, 4000)
                }
            } catch {
                saveStatus.value = 'error'
                saveStatusTimer = setTimeout(() => { saveStatus.value = '' }, 4000)
            } finally {
                saving.value = false
                if (saveQueued) {
                    saveQueued = false
                    saveStructure()
                }
            }
            return false
        }

        // Manual save: cancel any pending auto-save then save immediately
        function saveNow() {
            clearTimeout(autoSaveTimer)
            saveStructure()
        }

        // Traverse treeData and set content on the node matching id
        function _setNodeContent(nodes, id, val) {
            for (const n of nodes) {
                if (n.id === id) { n.content = val; return true }
                if (n.children?.length && _setNodeContent(n.children, id, val)) return true
            }
            return false
        }

        // Called on every SmartEditor keystroke (debounced 800ms for auto-save)
        function onContentChange(val) {
            if (!selectedNode.value) return
            _setNodeContent(treeData.value, selectedNode.value.id, val)
            if (!treeLoaded.value) return
            clearTimeout(autoSaveTimer)
            autoSaveTimer = setTimeout(() => saveStructure(), 800)
        }

        // ── Node actions ───────────────────────────────────────────
        function selectNode(node) {
            previewContent.value = ''
            previewFormat.value  = ''
            previewName.value    = ''
            selectedNode.value   = node
            if (node && node.type === 'folder') lastFolder.value = node
            // Light tree: rule content is fetched on first selection
            if (node && isRule(node) && node.lazy && node.rule_id) {
                node.lazy = false
                node.content = ''
                fetch(`/bundle/${props.bundleId}/rule_content/${node.rule_id}`)
                    .then(r => r.json())
                    .then(d => { if (d.success) { node.content = d.content; node.format = node.format || d.format } })
                    .catch(() => { node.lazy = true })
            }
        }

        function clearDisplay() {
            selectedNode.value   = null
            previewContent.value = ''
            previewName.value    = ''
            previewFormat.value  = ''
        }

        function setPreview(rule) {
            selectedNode.value   = null
            previewContent.value = rule.to_string || ''
            previewName.value    = rule.title || ''
            previewFormat.value  = rule.format || ''
        }

        // arr = the children array to create into; kind = 'folder' | 'file'
        // (undefined when triggered from the explorer header — defaults to
        // whichever the caller sets right after via creationMode.value = ...)
        function prepareTarget(arr, kind) {
            currentTarget.value = arr
            folderText.value    = ''
            fileNameText.value  = ''
            fileExt.value       = '.txt'
            if (kind) creationMode.value = kind
        }

        function cancelCreation() {
            creationMode.value = null
            folderText.value   = ''
            fileNameText.value = ''
        }

        // Add folder
        function confirmAddFolder() {
            const name = cleanName(folderText.value)
            if (!name) { create_message('Folder name required', 'warning-subtle'); return }
            const target = currentTarget.value || treeData.value
            const node = { id: 'f_' + Date.now(), name, type: 'folder', children: [], content: '' }
            target.push(node)
            selectNode(node)
            cancelCreation()
            saveStructure()
        }

        // Add file
        function confirmAddFile() {
            const base = cleanName(fileNameText.value)
            if (!base) { create_message('File name required', 'warning-subtle'); return }
            const target = currentTarget.value || treeData.value
            const fullName = base.endsWith(fileExt.value) ? base : base + fileExt.value
            const node = { id: 'fi_' + Date.now(), name: fullName, type: 'file', children: [], content: '' }
            target.push(node)
            selectNode(node)
            cancelCreation()
            saveStructure()
        }

        // Rename — inline on the row itself (see TreeItem's renameBaseName /
        // renameExtOf: custom files keep their extension locked while the
        // base name is edited).
        function beginRename(node) {
            nodeToRename.value = node
        }

        function cancelRename() {
            nodeToRename.value = null
        }

        function confirmRename(node, text) {
            // Guards against a stale/duplicate event (Enter fires
            // rename-confirm, then unmounting the input on the next render
            // fires a native blur which fires rename-confirm again).
            if (!nodeToRename.value || nodeToRename.value.id !== node.id) return
            const base = cleanName(text)
            if (base) {
                const dot = (node.type === 'file' && !isRule(node)) ? node.name.lastIndexOf('.') : -1
                const ext = dot > 0 ? node.name.slice(dot) : ''
                node.name = base + ext
            }
            nodeToRename.value = null
            saveStructure()
        }

        // Delete
        function beginDelete(node) {
            if (!node) return
            const id = node.id
            const findAndRemove = (list) => {
                const idx = list.findIndex(i => i.id === id)
                if (idx > -1) { list.splice(idx, 1); return true }
                for (const item of list)
                    if (item.children && findAndRemove(item.children)) return true
                return false
            }
            if (findAndRemove(treeData.value)) {
                if (selectedNode.value?.id === id) clearDisplay()
            }
            emit('tree-ready', [...extractRuleIds(treeData.value)])
            saveStructure()
        }

        // ── Add rules from BundleRuleSelector ─────────────────────
        // Priority: selected folder > last clicked folder > first root folder > tree root
        function _targetFolder() {
            if (selectedNode.value?.type === 'folder') return selectedNode.value.children
            if (lastFolder.value) return lastFolder.value.children
            const first = treeData.value[0]
            if (first?.type === 'folder') return first.children
            return treeData.value
        }

        function addRules(rules) {
            const target = _targetFolder()
            for (const rule of rules) {
                target.push({
                    id:       'rule_' + rule.id + '_' + Date.now(),
                    rule_id:  rule.id,
                    name:     _fileName(rule),
                    type:     'file',
                    format:   rule.format || '',
                    content:  rule.to_string || '',
                    children: [],
                })
            }
            emit('tree-ready', [...extractRuleIds(treeData.value)])
            saveStructure()
        }

        // ── External DnD (rules dragged from BundleRuleSelector) ──
        // payload is always an array of rule objects
        function _pushRules(target, rules) {
            for (const rule of rules) {
                target.push({
                    id:       'rule_' + rule.id + '_' + Date.now(),
                    rule_id:  rule.id,
                    name:     _fileName(rule),
                    type:     'file',
                    format:   rule.format || '',
                    content:  rule.to_string || '',
                    children: [],
                })
            }
        }

        function onExternalDropOnFolder(folderNode, rawPayload) {
            const rules = Array.isArray(rawPayload) ? rawPayload : [rawPayload]
            _pushRules(folderNode.children, rules)
            // Tell the rule library what's now in the tree BEFORE the network
            // save resolves — otherwise a second quick drop of the same rule
            // (dropped while the first save is still in flight) creates a
            // duplicate node instead of being excluded from the library.
            emit('tree-ready', [...extractRuleIds(treeData.value)])
            saveStructure()
        }

        // DnD on tree root
        function onRootDragOver(ev) {
            if (ev.dataTransfer.types.includes('application/rulezet-rule')) {
                ev.preventDefault()
                rootDropActive.value = true
            }
        }
        function onRootDragLeave() { rootDropActive.value = false }
        function onRootDrop(ev) {
            rootDropActive.value = false
            const raw = ev.dataTransfer.getData('application/rulezet-rule')
            if (!raw) return
            try {
                const parsed = JSON.parse(raw)
                const rules = Array.isArray(parsed) ? parsed : [parsed]
                _pushRules(treeData.value, rules)
                emit('tree-ready', [...extractRuleIds(treeData.value)])
                saveStructure()
            } catch {}
        }

        // ── Layout: grid mode ─────────────────────────────────────
        const gridMode      = !!props.layoutUrl && !!window.GridStack
        const gridEl        = ref(null)
        const panels        = ref(clonePanels(DEFAULT_PANELS))
        const layoutEditing = ref(false)
        let grid = null
        let layoutSaveTimer = null

        const panelMeta = (id) => PANEL_META.find(m => m.id === id) || { label: id, icon: 'fas fa-square' }
        const isPanelHidden = (id) => !!panels.value.find(p => p.id === id)?.hidden

        // What the v-for renders: every visible panel (docked, window or
        // drawer), or the fixed three of the classic layout.
        const renderedPanels = computed(() => gridMode
            ? panels.value.filter(p => !p.hidden)
            : DEFAULT_PANELS.filter(p => !p.hidden))

        const panelMode = (id) => panels.value.find(p => p.id === id)?.mode || 'grid'
        const modesFor  = (meta) => MODES.filter(m => m.id !== 'drawer' || meta.drawer)
        const isFloating = (p) => gridMode && (p.mode === 'window' || p.mode === 'drawer')

        function outerClass(p) {
            if (!gridMode) return 'bse-classic-cell bse-classic-cell--' + p.id
            if (p.mode === 'window') return ['bse-window', { 'bse-window--minimized': p.minimized }]
            if (p.mode === 'drawer') return ['bse-drawer', { 'bse-drawer--closed': p.minimized }]
            return 'grid-stack-item'
        }
        function innerClass(p) {
            if (!gridMode) return 'bse-classic-inner'
            return p.mode === 'grid' ? 'grid-stack-item-content bse-grid-cell' : 'bse-window-body'
        }
        function outerAttrs(p) {
            if (!gridMode || p.mode !== 'grid') return {}
            const m = panelMeta(p.id)
            return { 'gs-id': p.id, 'gs-x': p.x, 'gs-y': p.y, 'gs-w': p.w, 'gs-h': p.h,
                     'gs-min-w': m.minW, 'gs-min-h': m.minH }
        }
        function outerStyle(p) {
            if (!isFloating(p) || !p.win) return null
            const z = 1041 + (topWindow.value === p.id ? 1 : 0)
            if (p.mode === 'drawer') return { width: p.win.w + 'px', zIndex: z }
            return { left: p.win.x + 'px', top: p.win.y + 'px', width: p.win.w + 'px',
                     height: p.minimized ? 'auto' : p.win.h + 'px', zIndex: z }
        }

        async function loadLayout() {
            try {
                const res = await fetch(props.layoutUrl)
                if (res.ok) {
                    const data = await res.json()
                    if (Array.isArray(data.panels)) panels.value = clonePanels(data.panels)
                }
            } catch {}
        }

        function scheduleLayoutSave() {
            clearTimeout(layoutSaveTimer)
            layoutSaveTimer = setTimeout(saveLayout, 600)
        }

        async function saveLayout() {
            try {
                const res = await fetch(props.layoutUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ panels: panels.value }),
                })
                if (!res.ok) {
                    const data = await res.json().catch(() => ({}))
                    create_message(data.message || 'Could not save the layout', 'danger-subtle')
                }
            } catch {
                create_message('Could not save the layout', 'danger-subtle')
            }
        }

        // GridStack → state. Skipped while the grid is in its one-column
        // (narrow screen) mode, so a phone never overwrites the real layout.
        function syncFromGrid() {
            if (!grid || grid.getColumn() !== GRID_COLUMNS) return
            grid.compact()
            const byId = new Map(grid.save(false).map(n => [n.id, n]))
            for (const p of panels.value) {
                const n = byId.get(p.id)
                if (n && p.mode === 'grid') Object.assign(p, { x: n.x, y: n.y, w: n.w, h: n.h })
            }
            scheduleLayoutSave()
        }

        function initGrid() {
            grid = window.GridStack.init({
                column: GRID_COLUMNS,
                cellHeight: 56,
                margin: 6,
                float: false,
                staticGrid: !layoutEditing.value,
                handle: '.bse-panel-overlay',
                draggable: { cancel: '.bse-panel-overlay-hide' },
                resizable: { handles: 'se' },
                columnOpts: { breakpoints: [{ w: 768, c: 1 }] },
            }, gridEl.value)
            grid.on('change', syncFromGrid)
        }

        // Any change of which elements are docked (show / hide, a mode
        // change, a preset): release them from GridStack first, apply the
        // change, then let GridStack take the new set of docked panels.
        // Vue owns the elements; GridStack only positions them.
        async function relayout(mutate) {
            if (grid) { grid.destroy(false); grid = null }
            const next = clonePanels(panels.value)
            mutate(next)
            panels.value = next
            await nextTick()
            if (gridEl.value && gridEl.value.offsetWidth > 0) initGrid()
            syncFromGrid()
            scheduleLayoutSave()
        }

        function toggleLayoutEditing() {
            layoutEditing.value = !layoutEditing.value
            if (grid) grid.setStatic(!layoutEditing.value)
        }

        function _bottom(list) {
            return list.filter(p => !p.hidden).reduce((m, p) => Math.max(m, p.y + p.h), 0)
        }

        function togglePanel(id) {
            const target = panels.value.find(p => p.id === id)
            if (!target) return
            if (!target.hidden && renderedPanels.value.length === 1) {
                create_message('At least one panel must stay visible', 'warning-subtle')
                return
            }
            relayout(next => {
                const p = next.find(q => q.id === id)
                if (p.hidden) {
                    // Comes back where it was shown; docked ones full width under the others
                    p.hidden = false
                    p.minimized = false
                    if (p.mode === 'grid') Object.assign(p, { x: 0, y: _bottom(next), w: GRID_COLUMNS })
                } else {
                    p.hidden = true
                }
            })
        }

        function _defaultWin(id, mode) {
            const vw = window.innerWidth, vh = window.innerHeight
            const w = Math.min(mode === 'drawer' ? 600 : (id === 'library' ? 640 : 520), vw - 40)
            const h = Math.min(680, vh - 140)
            return { x: Math.max(0, id === 'library' ? vw - w - 24 : 24), y: 110, w, h }
        }

        function _applyMode(p, mode) {
            p.mode = mode
            p.minimized = false
            if (mode === 'grid') return
            if (!p.win) p.win = _defaultWin(p.id, mode)
            if (mode === 'drawer') p.win.w = Math.max(p.win.w, 420)
            p.win = _clampWin(p.win)
            topWindow.value = p.id
        }

        // A docked panel leaving the grid would leave a hole: the docked
        // panels on the same rows grow sideways to take its place.
        function _fillHole(next, gone) {
            const rowsOverlap = (p) => p.y < gone.y + gone.h && gone.y < p.y + p.h
            const docked = next.filter(p => p !== gone && !p.hidden && p.mode === 'grid' && rowsOverlap(p))
            const left  = docked.filter(p => p.x + p.w === gone.x)
            const right = docked.filter(p => p.x === gone.x + gone.w)
            if (left.length)       left.forEach(p => { p.w += gone.w })
            else if (right.length) right.forEach(p => { p.x = gone.x; p.w += gone.w })
        }

        function setPanelMode(id, mode) {
            const meta = panelMeta(id)
            if (mode === 'drawer' && !meta.drawer) return
            if (panelMode(id) === mode) return
            relayout(next => {
                const p = next.find(q => q.id === id)
                if (p.mode === 'grid' && !p.hidden) _fillHole(next, p)
                _applyMode(p, mode)
            })
        }

        function toggleMinimized(id) {
            const p = panels.value.find(q => q.id === id)
            if (!p || p.mode === 'grid') return
            p.minimized = !p.minimized
            if (!p.minimized) topWindow.value = id
            scheduleLayoutSave()
        }

        function applyPreset(preset) {
            relayout(next => {
                let bottom = Math.max(0, ...Object.values(preset.pos).map(([, y, , h]) => y + h))
                for (const p of next) {
                    const pos = preset.pos[p.id]
                    const mode = (preset.modes || {})[p.id]
                    if (pos) { [p.x, p.y, p.w, p.h] = pos; if (p.mode !== 'grid') _applyMode(p, 'grid') }
                    else if (mode) { if (p.hidden) p.hidden = false; _applyMode(p, mode) }
                    else if (!p.hidden && p.mode === 'grid') { Object.assign(p, { x: 0, y: bottom, w: GRID_COLUMNS }); bottom += p.h }
                }
            })
        }

        // ── Floating windows / drawer: move, resize, stacking ──────
        const topWindow = ref(null)
        const raiseWindow = (id) => { topWindow.value = id }

        function _clampWin(win) {
            const vw = window.innerWidth, vh = window.innerHeight
            const w = Math.min(Math.max(win.w, 320), Math.max(320, vw))
            const h = Math.min(Math.max(win.h, 220), Math.max(220, vh))
            const x = Math.min(Math.max(0, win.x), Math.max(0, vw - 120))
            const y = Math.min(Math.max(0, win.y), Math.max(0, vh - 44))
            return { x: Math.round(x), y: Math.round(y), w: Math.round(w), h: Math.round(h) }
        }

        // Shared pointer-drag plumbing: onMove(dx, dy) on each move, saves at the end.
        function _track(ev, onMove) {
            ev.preventDefault()
            const sx = ev.clientX, sy = ev.clientY
            const move = (e) => onMove(e.clientX - sx, e.clientY - sy)
            const up = () => {
                window.removeEventListener('pointermove', move)
                window.removeEventListener('pointerup', up)
                document.body.classList.remove('bse-moving')
                scheduleLayoutSave()
            }
            document.body.classList.add('bse-moving')
            window.addEventListener('pointermove', move)
            window.addEventListener('pointerup', up)
        }

        const _panel = (id) => panels.value.find(q => q.id === id)

        function startWindowDrag(ev, id) {
            const p = _panel(id)
            if (!p || p.mode !== 'window' || ev.button !== 0 || ev.target.closest('button')) return
            const start = { ...p.win }
            _track(ev, (dx, dy) => { p.win = _clampWin({ ...start, x: start.x + dx, y: start.y + dy }) })
        }

        function startWindowResize(ev, id) {
            const p = _panel(id)
            if (!p || ev.button !== 0) return
            const start = { ...p.win }
            _track(ev, (dx, dy) => { p.win = _clampWin({ ...start, w: start.w + dx, h: start.h + dy }) })
        }

        function startDrawerResize(ev, id) {
            const p = _panel(id)
            if (!p || ev.button !== 0) return
            const start = { ...p.win }
            _track(ev, (dx) => {
                const w = Math.min(Math.max(360, start.w - dx), window.innerWidth - 160)
                p.win = { ...p.win, w: Math.round(w) }
            })
        }

        // The page makes room for an open drawer instead of hiding under it
        const drawerSpace = computed(() => {
            const d = panels.value.find(p => !p.hidden && p.mode === 'drawer' && !p.minimized)
            return gridMode && d && d.win ? d.win.w : 0
        })

        function onViewportResize() {
            for (const p of panels.value) if (p.win && p.mode === 'window') p.win = _clampWin(p.win)
        }

        async function resetLayout() {
            let fresh = DEFAULT_PANELS
            try {
                const res = await fetch(props.layoutUrl + '/reset', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': props.csrfToken },
                })
                const data = await res.json()
                if (Array.isArray(data.panels)) fresh = data.panels
            } catch {}
            if (grid) { grid.destroy(false); grid = null }
            panels.value = clonePanels(fresh)
            await nextTick()
            initGrid()
            create_message('Layout reset', 'success-subtle')
        }

        // ── Preview sizing: in grid mode the editor fills its panel ──
        const previewCardHeight = ref(0)
        let previewObserver = null
        let previewCardEl = null
        function setPreviewCard(el) {
            if (el === previewCardEl) return
            if (previewObserver) previewObserver.disconnect()
            previewCardEl = el
            if (el && gridMode && window.ResizeObserver) {
                previewObserver = new ResizeObserver(entries => {
                    previewCardHeight.value = Math.round(entries[0].contentRect.height)
                })
                previewObserver.observe(el)
            }
        }
        // header (~44px) + save bar (~48px) + padding
        const editorHeight = computed(() => gridMode && previewCardHeight.value
            ? Math.max(160, previewCardHeight.value - 104) + 'px'
            : '300px')
        const viewerMaxHeight = computed(() => gridMode ? 'none' : '32vh')

        // ── Overview panel ──────────────────────────────────────────
        const overview = computed(() => {
            let rules = 0, files = 0, folders = 0
            const formats = {}
            const walk = (list) => {
                for (const n of list || []) {
                    if (n.type === 'folder') { if (n.id !== 'root') folders++; walk(n.children) }
                    else if (isRule(n)) {
                        rules++
                        const f = (n.format || 'other').toUpperCase()
                        formats[f] = (formats[f] || 0) + 1
                    } else files++
                }
            }
            walk(treeData.value)
            return {
                rules, files, folders,
                formats: Object.entries(formats).map(([name, count]) => ({ name, count }))
                    .sort((a, b) => b.count - a.count),
            }
        })

        // ── Lifecycle ──────────────────────────────────────────────
        onMounted(async () => {
            loadTree()
            if (gridMode) {
                await loadLayout()
                await nextTick()
                initGridWhenVisible()
                window.addEventListener('resize', onViewportResize)
            }
        })

        // The editor may be mounted in a hidden tab (the page opened on
        // ?tab=settings): GridStack would measure a 0px-wide grid and fall
        // back to one column. Wait until the grid actually has a width.
        let visibilityObserver = null
        function initGridWhenVisible() {
            const el = gridEl.value
            if (!el) return
            if (el.offsetWidth > 0 || !window.ResizeObserver) { initGrid(); return }
            visibilityObserver = new ResizeObserver(() => {
                if (el.offsetWidth === 0 || grid) return
                visibilityObserver.disconnect()
                visibilityObserver = null
                initGrid()
            })
            visibilityObserver.observe(el)
        }
        onUnmounted(() => {
            clearTimeout(saveStatusTimer); clearTimeout(autoSaveTimer); clearTimeout(layoutSaveTimer)
            if (previewObserver) previewObserver.disconnect()
            if (visibilityObserver) visibilityObserver.disconnect()
            window.removeEventListener('resize', onViewportResize)
            if (grid) { grid.destroy(false); grid = null }
        })

        return {
            treeData, selectedNode, previewContent, previewName, previewFormat,
            saving, saveStatus, lastSavedAt, rootDropActive,
            folderText, fileNameText, fileExt, nodeToRename, creationMode,
            isRule, selectNode, clearDisplay, setPreview, prepareTarget,
            editorModeFor, docIcon, RULE_ICON,
            confirmAddFolder, confirmAddFile, cancelCreation,
            beginRename, confirmRename, cancelRename,
            beginDelete, saveStructure, saveNow, onContentChange,
            addRules, setPreview, focusRule,
            onExternalDropOnFolder, onRootDragOver, onRootDragLeave, onRootDrop, onTreeSortEnd,
            multiSelected, toggleMultiSelect, clearMultiSelect,
            bulkDeleteArmed, confirmBulkDelete,
            gridMode, gridEl, layoutEditing, renderedPanels, panelMeta, isPanelHidden,
            PANEL_META, PRESETS, toggleLayoutEditing, togglePanel, applyPreset, resetLayout,
            panelMode, modesFor, isFloating, outerClass, innerClass, outerAttrs, outerStyle,
            setPanelMode, toggleMinimized, raiseWindow, startWindowDrag, startWindowResize, startDrawerResize,
            drawerSpace,
            setPreviewCard, editorHeight, viewerMaxHeight, overview,
        }
    },
}
