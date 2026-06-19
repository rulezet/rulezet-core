/**
 * BundleStructureEditor.js
 *
 * Self-contained component for editing a bundle's file structure.
 * Renders:
 *   - Bundle Explorer (drag-and-drop tree, left panel)
 *   - A slot "rule-selector" for BundleRuleSelector (right panel)
 *   - Preview / Editor panel (full width below)
 *
 * Props:
 *   bundleId   String|Number  required
 *   csrfToken  String         default ''
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

const { ref, computed, onMounted, onUnmounted, nextTick, watch } = Vue

// ── TreeItem sub-component ─────────────────────────────────────────

const TREE_ITEM_TEMPLATE = `
<li class="mb-1 bse-tree-item" style="list-style:none;">
    <div
        class="bse-node-row"
        :class="{
            'bse-node-row--selected': selectedId === node.id,
            'bse-node-row--drop-target': localDropTarget && node.type === 'folder',
        }"
        @click.stop="$emit('select', node)"
        @dragover="onDragOver($event, node)"
        @dragleave="onDragLeave($event)"
        @drop="onDrop($event, node)"
    >
        <!-- Drag handle — SortableJS grabs the whole <li>,
             but the handle icon gives a clear visual affordance -->
        <span class="bse-node-drag-handle" title="Drag to move">
            <i class="fas fa-grip-vertical"></i>
        </span>

        <i
            :class="[
                node.type === 'folder'
                    ? 'fas fa-folder text-warning'
                    : (isRule(node) ? 'fas fa-file-code text-primary' : 'fas fa-file-signature text-success'),
            ]"
            style="font-size:.78rem;flex-shrink:0;"
        ></i>

        <span class="bse-node-name" :title="node.name">{{ node.name }}</span>

        <div class="bse-node-actions">
            <button v-if="!isRule(node)" class="bse-node-btn" title="Rename"
                data-bs-toggle="modal" data-bs-target="#bse-rename-modal"
                @click.stop="$emit('rename', node)">
                <i class="fas fa-edit"></i>
            </button>
            <button v-if="node.type === 'folder'" class="bse-node-btn bse-node-btn--success" title="Add sub-folder"
                data-bs-toggle="modal" data-bs-target="#bse-folder-modal"
                @click.stop="$emit('add-sub', node.children)">
                <i class="fas fa-folder-plus"></i>
            </button>
            <button v-if="node.type === 'folder'" class="bse-node-btn" title="Create file"
                data-bs-toggle="modal" data-bs-target="#bse-file-modal"
                @click.stop="$emit('add-sub', node.children)">
                <i class="fas fa-file-medical"></i>
            </button>
            <button class="bse-node-btn bse-node-btn--danger" title="Remove"
                data-bs-toggle="modal" data-bs-target="#bse-remove-modal"
                @click.stop="$emit('remove', node)">
                <i class="fas fa-trash-alt"></i>
            </button>
        </div>
    </div>

    <div v-if="node.type === 'folder'" class="ps-3 border-start ms-2 mt-1">
        <draggable v-model="node.children" group="bse-tree" :item-key="n => n.id" tag="ul"
            class="ps-0 mb-0 bse-folder-drop-zone" :animation="150" ghost-class="bse-ghost">
            <template #item="{ element }">
                <tree-item
                    :node="element"
                    :selected-id="selectedId"
                    @select="n => $emit('select', n)"
                    @rename="n => $emit('rename', n)"
                    @add-sub="arr => $emit('add-sub', arr)"
                    @remove="n => $emit('remove', n)"
                    @external-drop="(n, rules) => $emit('external-drop', n, rules)"
                />
            </template>
        </draggable>
    </div>
</li>
`

const TreeItem = {
    name: 'tree-item',
    props: ['node', 'selectedId'],
    template: TREE_ITEM_TEMPLATE,
    emits: ['select', 'rename', 'add-sub', 'remove', 'external-drop'],
    components: { draggable: window.vuedraggable },
    data() { return { localDropTarget: false, _leaveTimer: null } },
    methods: {
        isRule(node) { return node && String(node.id).startsWith('rule_') },

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
    },

    emits: ['tree-saved', 'tree-ready'],

    expose: ['addRules', 'setPreview'],

    template: `
    <div class="bse-wrapper">

        <!-- ── Section header ── -->
        <div class="bse-section-header">
            <div class="bse-section-title">
                <i class="fas fa-sitemap text-primary"></i>
                Bundle Structure
            </div>
            <div class="d-flex align-items-center gap-2 flex-wrap">
                <div v-if="lastSavedAt" class="bse-last-saved">
                    <i class="fas fa-check-circle"></i>
                    <span>Last save</span>
                    <strong>{{ lastSavedAt }}</strong>
                </div>
                <button class="bse-save-btn" @click="saveNow" :disabled="saving">
                    <i :class="saving ? 'fas fa-spinner fa-spin' : 'fas fa-save'"></i>
                    {{ saving ? 'Saving…' : 'Save' }}
                    <i v-if="saveStatus === 'saved'" class="fas fa-check-circle bse-save-ok ms-1"></i>
                    <i v-else-if="saveStatus === 'error'" class="fas fa-times-circle bse-save-err ms-1"></i>
                </button>
            </div>
        </div>

        <!-- ── Top row: explorer + rule selector slot ── -->
        <div class="bse-top-row">

            <!-- Left: Bundle Explorer -->
            <div class="bse-explorer-card">
                <div class="bse-explorer-header">
                    <div class="bse-explorer-header-left">
                        <div class="bse-title"><i class="fas fa-folder-tree me-2"></i>Bundle Explorer</div>
                        <div class="bse-subtitle">
                            <i class="fas fa-up-down-left-right me-1 opacity-50"></i>Drag to reorganize ·
                            <i class="fas fa-grip-lines me-1 opacity-50"></i>Drop rules from the library onto a folder
                        </div>
                    </div>
                    <div class="bse-explorer-actions">
                        <button class="bse-action-btn" title="Add Folder"
                            @click="prepareTarget(treeData)"
                            data-bs-toggle="modal" data-bs-target="#bse-folder-modal">
                            <i class="fas fa-folder-plus"></i>
                        </button>
                        <button class="bse-action-btn" title="Create File"
                            @click="prepareTarget(treeData)"
                            data-bs-toggle="modal" data-bs-target="#bse-file-modal">
                            <i class="fas fa-file-code"></i>
                        </button>
                    </div>
                </div>

                <!-- Tree body with root drop zone -->
                <div class="bse-tree-body"
                    @dragover.prevent="onRootDragOver"
                    @dragleave="onRootDragLeave"
                    @drop.prevent="onRootDrop">
                    <draggable v-model="treeData" group="bse-tree" :item-key="i => i.id" tag="ul"
                        class="ps-0 mb-0 bse-root-drop-zone" :animation="150" ghost-class="bse-ghost">
                        <template #item="{ element }">
                            <tree-item
                                :node="element"
                                :selected-id="selectedNode?.id"
                                @select="selectNode"
                                @rename="beginRename"
                                @add-sub="prepareTarget"
                                @remove="beginDelete"
                                @external-drop="onExternalDropOnFolder"
                            />
                        </template>
                    </draggable>
                    <div v-if="treeData.length === 0" class="bse-empty-tree text-center py-4 text-muted small">
                        <i class="fas fa-folder-open fa-2x opacity-25 d-block mb-2"></i>
                        Empty — add folders or drag rules here
                    </div>
                </div>
            </div>

            <!-- Right: rule selector slot -->
            <slot name="rule-selector" />
        </div>

        <!-- ── Preview / Editor panel ── -->
        <div class="bse-preview-card">
            <div v-if="!selectedNode && !previewContent" class="bse-preview-empty">
                <i class="fas fa-terminal fa-2x"></i>
                <strong>Preview &amp; Editor</strong>
                <span class="small">Select a file in the explorer or drag a rule from the right panel</span>
            </div>
            <template v-else>
                <div class="bse-preview-header">
                    <span class="bse-preview-filename">
                        <i v-if="selectedNode"
                           :class="selectedNode.type === 'folder' ? 'fas fa-folder text-warning' : 'fas fa-file-code text-primary'"
                           class="me-2"></i>
                        <i v-else class="fas fa-eye text-success me-2"></i>
                        {{ selectedNode ? selectedNode.name : 'Preview: ' + previewName }}
                    </span>
                    <div class="d-flex align-items-center gap-2">
                        <span v-if="!selectedNode || isRule(selectedNode)"
                              class="badge bg-secondary" style="font-size:.7rem;">Read-Only</span>
                        <template v-else>
                            <span class="badge bg-primary" style="font-size:.7rem;">Editable</span>
                            <button class="bse-editor-save-btn" @click="saveNow" :disabled="saving"
                                    :title="saving ? 'Saving…' : 'Save file'">
                                <i :class="saving ? 'fas fa-spinner fa-spin' : 'fas fa-save'"></i>
                                {{ saving ? 'Saving…' : 'Save' }}
                                <i v-if="saveStatus === 'saved'" class="fas fa-check-circle bse-save-ok ms-1"></i>
                                <i v-else-if="saveStatus === 'error'" class="fas fa-times-circle bse-save-err ms-1"></i>
                            </button>
                        </template>
                        <button class="btn btn-sm btn-outline-secondary py-0 px-2" @click="clearDisplay">
                            <i class="fas fa-times" style="font-size:.7rem;"></i>
                        </button>
                    </div>
                </div>

                <!-- Editable custom file -->
                <smart-editor
                    v-if="selectedNode && selectedNode.type === 'file' && !isRule(selectedNode)"
                    v-model="selectedNode.content"
                    mode="code"
                    language="text"
                    min-height="300px"
                    max-height="300px">
                </smart-editor>

                <!-- Save bar below the editor -->
                <div v-if="selectedNode && selectedNode.type === 'file' && !isRule(selectedNode)"
                     class="bse-editor-bottom-bar">
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

                <!-- Read-only rule node -->
                <code-viewer
                    v-else-if="selectedNode && isRule(selectedNode)"
                    :code="selectedNode.content || ''"
                    :language="hlxLang(selectedNode.format)"
                    :title="selectedNode.name"
                    max-height="32vh">
                </code-viewer>

                <!-- Rule preview from selector panel -->
                <code-viewer
                    v-else-if="previewContent"
                    :code="previewContent"
                    :language="hlxLang(previewFormat)"
                    :title="previewName"
                    max-height="32vh">
                </code-viewer>

                <!-- Folder selected -->
                <div v-else class="p-5 text-center text-muted d-flex flex-column justify-content-center"
                     style="min-height:32vh;">
                    <i class="fas fa-folder-open fa-2x mb-2 opacity-25"></i>
                    <p class="small mb-0">
                        Folder <strong>{{ selectedNode.name }}</strong> is selected.<br>
                        Click a file to edit, or drop a rule here.
                    </p>
                </div>
            </template>
        </div>

        <!-- ══════════ MODALS ══════════ -->

        <!-- Add Folder -->
        <div class="modal fade" id="bse-folder-modal" tabindex="-1" aria-hidden="true" style="z-index:2000;">
            <div class="modal-dialog modal-dialog-centered modal-sm">
                <div class="modal-content border-0 shadow-lg" style="border-radius:14px;">
                    <div class="modal-header border-0 pb-0">
                        <h6 class="modal-title fw-bold">Add Folder</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body py-3">
                        <input class="form-control form-control-sm rounded-pill"
                               placeholder="Folder name" v-model="folderText" @keyup.enter="confirmAddFolder">
                    </div>
                    <div class="modal-footer border-0 pt-0 justify-content-center pb-4">
                        <button class="btn btn-sm btn-light rounded-pill px-4" data-bs-dismiss="modal">Cancel</button>
                        <button class="btn btn-sm btn-success rounded-pill px-4" @click="confirmAddFolder">Create</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Create File -->
        <div class="modal fade" id="bse-file-modal" tabindex="-1" aria-hidden="true" style="z-index:2000;">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow-lg" style="border-radius:14px;">
                    <div class="modal-header border-0 pb-0">
                        <h6 class="modal-title fw-bold">Create File</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body py-3">
                        <div class="row g-2">
                            <div class="col-8">
                                <input class="form-control form-control-sm rounded-pill" placeholder="File name"
                                       v-model="fileNameText" @keyup.enter="confirmAddFile">
                            </div>
                            <div class="col-4">
                                <select class="form-select form-select-sm rounded-pill" v-model="fileExt">
                                    <option value=".txt">.txt</option>
                                    <option value=".json">.json</option>
                                    <option value=".yaml">.yaml</option>
                                    <option value=".md">.md</option>
                                </select>
                            </div>
                        </div>
                        <div class="text-center mt-2">
                            <small class="text-muted">Final: <strong>{{ fileNameText }}{{ fileExt }}</strong></small>
                        </div>
                    </div>
                    <div class="modal-footer border-0 pt-0 justify-content-center pb-4">
                        <button class="btn btn-sm btn-light rounded-pill px-4" data-bs-dismiss="modal">Cancel</button>
                        <button class="btn btn-sm btn-success rounded-pill px-4" @click="confirmAddFile">Create</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Rename -->
        <div class="modal fade" id="bse-rename-modal" tabindex="-1" aria-hidden="true" style="z-index:2000;">
            <div class="modal-dialog modal-dialog-centered modal-sm">
                <div class="modal-content border-0 shadow-lg" style="border-radius:14px;">
                    <div class="modal-header border-0 pb-0">
                        <h6 class="modal-title fw-bold">Rename</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body py-3">
                        <div class="input-group input-group-sm">
                            <input class="form-control rounded-start-pill"
                                   v-model="renameText" @keyup.enter="confirmRename"
                                   placeholder="Name">
                            <span v-if="renameExt" class="input-group-text rounded-end-pill"
                                  style="font-size:.75rem;font-weight:600;background:var(--card-bg-color);border-color:var(--border-color);">
                                {{ renameExt }}
                            </span>
                        </div>
                        <div v-if="renameExt" class="text-center mt-2">
                            <small class="text-muted">Result: <strong>{{ renameText }}{{ renameExt }}</strong></small>
                        </div>
                    </div>
                    <div class="modal-footer border-0 pt-0 justify-content-center pb-4">
                        <button class="btn btn-sm btn-light rounded-pill px-4" data-bs-dismiss="modal">Cancel</button>
                        <button class="btn btn-sm btn-primary rounded-pill px-4" @click="confirmRename">Rename</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Remove -->
        <div class="modal fade" id="bse-remove-modal" tabindex="-1" aria-hidden="true" style="z-index:2000;">
            <div class="modal-dialog modal-dialog-centered modal-sm">
                <div class="modal-content border-0 shadow-lg" style="border-radius:14px;">
                    <div class="modal-header border-0 pb-0">
                        <h6 class="modal-title fw-bold">Remove Item</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body py-3 text-center">
                        <i class="fas fa-exclamation-triangle fa-2x text-warning mb-2"></i>
                        <p class="mb-0 small">Remove <strong>{{ nodeToDelete?.name }}</strong>?</p>
                        <small v-if="nodeToDelete?.type === 'folder'" class="text-muted">
                            This also deletes all items inside.
                        </small>
                    </div>
                    <div class="modal-footer border-0 pt-0 justify-content-center pb-4">
                        <button class="btn btn-sm btn-light rounded-pill px-4" data-bs-dismiss="modal">Cancel</button>
                        <button class="btn btn-sm btn-danger rounded-pill px-4" @click="confirmDelete">Remove</button>
                    </div>
                </div>
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

        // ── Modal state ────────────────────────────────────────────
        const folderText    = ref('')
        const fileNameText  = ref('')
        const fileExt       = ref('.txt')
        const renameText    = ref('')
        const renameExt     = ref('')   // extension locked during rename of custom files
        const nodeToDelete  = ref(null)
        const nodeToRename  = ref(null)
        const currentTarget = ref(null)   // the array we add to

        // ── Helpers ────────────────────────────────────────────────
        const isRule = (node) => node && String(node.id).startsWith('rule_')

        // Map Rulezet format names to highlight.js language identifiers
        function hlxLang(format) {
            const map = {
                sigma: 'yaml', wazuh: 'xml', elastic: 'json',
                nova: 'yaml', crs: 'nginx',
            }
            return map[(format || '').toLowerCase()] || 'plaintext'
        }

        const _closeModal = (id) => {
            const el = document.getElementById(id)
            if (el) { const m = bootstrap.Modal.getInstance(el); if (m) m.hide() }
        }

        const _ext = (format) => {
            const map = {
                yara: '.yar', sigma: '.yaml', nova: '.yaml', suricata: '.rules',
                zeek: '.zeek', wazuh: '.xml', nse: '.nse', crs: '.conf',
            }
            return map[(format || '').toLowerCase()] || '.txt'
        }

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
        }

        function _timeStr() {
            return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        }

        async function saveStructure() {
            if (saving.value) return false
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
                    saveStatusTimer = setTimeout(() => { saveStatus.value = '' }, 4000)
                }
            } catch {
                saveStatus.value = 'error'
                saveStatusTimer = setTimeout(() => { saveStatus.value = '' }, 4000)
            } finally {
                saving.value = false
            }
            return false
        }

        // Manual save: cancel any pending auto-save then save immediately
        function saveNow() {
            clearTimeout(autoSaveTimer)
            saveStructure()
        }

        // ── Node actions ───────────────────────────────────────────
        function selectNode(node) {
            previewContent.value = ''
            previewFormat.value  = ''
            previewName.value    = ''
            selectedNode.value   = node
            if (node && node.type === 'folder') lastFolder.value = node
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

        function prepareTarget(arr) {
            currentTarget.value = arr
            folderText.value    = ''
            fileNameText.value  = ''
            fileExt.value       = '.txt'
        }

        // Add folder
        function confirmAddFolder() {
            const name = folderText.value.trim()
            if (!name) { create_message('Folder name required', 'warning-subtle'); return }
            const target = currentTarget.value || treeData.value
            const node = { id: 'f_' + Date.now(), name, type: 'folder', children: [], content: '' }
            target.push(node)
            selectNode(node)
            _closeModal('bse-folder-modal')
            folderText.value = ''
            saveStructure()
        }

        // Add file
        function confirmAddFile() {
            const base = fileNameText.value.trim()
            if (!base) { create_message('File name required', 'warning-subtle'); return }
            const target = currentTarget.value || treeData.value
            const fullName = base.endsWith(fileExt.value) ? base : base + fileExt.value
            const node = { id: 'fi_' + Date.now(), name: fullName, type: 'file', children: [], content: '' }
            target.push(node)
            selectNode(node)
            _closeModal('bse-file-modal')
            fileNameText.value = ''
            fileExt.value      = '.txt'
            saveStructure()
        }

        // Rename
        function beginRename(node) {
            nodeToRename.value = node
            // For custom files, lock the extension and only edit the base name
            if (node.type === 'file' && !isRule(node)) {
                const dot = node.name.lastIndexOf('.')
                if (dot > 0) {
                    renameExt.value  = node.name.slice(dot)   // e.g. ".txt"
                    renameText.value = node.name.slice(0, dot) // base name only
                } else {
                    renameExt.value  = ''
                    renameText.value = node.name
                }
            } else {
                renameExt.value  = ''
                renameText.value = node.name
            }
        }

        function confirmRename() {
            const base = renameText.value.trim()
            if (!base || !nodeToRename.value) return
            nodeToRename.value.name = base + renameExt.value
            _closeModal('bse-rename-modal')
            nodeToRename.value = null
            renameText.value   = ''
            renameExt.value    = ''
            saveStructure()
        }

        // Delete
        function beginDelete(node) { nodeToDelete.value = node }

        function confirmDelete() {
            if (!nodeToDelete.value) { _closeModal('bse-remove-modal'); return }
            const id = nodeToDelete.value.id
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
            _closeModal('bse-remove-modal')
            nodeToDelete.value = null
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
                const ext = _ext(rule.format)
                target.push({
                    id:       'rule_' + rule.id + '_' + Date.now(),
                    rule_id:  rule.id,
                    name:     rule.title + ext,
                    type:     'file',
                    format:   rule.format || '',
                    content:  rule.to_string || '',
                    children: [],
                })
            }
            saveStructure()
        }

        // ── External DnD (rules dragged from BundleRuleSelector) ──
        // payload is always an array of rule objects
        function _pushRules(target, rules) {
            for (const rule of rules) {
                target.push({
                    id:       'rule_' + rule.id + '_' + Date.now(),
                    rule_id:  rule.id,
                    name:     rule.title + _ext(rule.format),
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
                saveStructure()
            } catch {}
        }

        // ── Lifecycle ──────────────────────────────────────────────
        onMounted(() => loadTree())
        onUnmounted(() => { clearTimeout(saveStatusTimer); clearTimeout(autoSaveTimer) })

        return {
            treeData, selectedNode, previewContent, previewName, previewFormat,
            saving, saveStatus, lastSavedAt, rootDropActive,
            folderText, fileNameText, fileExt, renameText, renameExt, nodeToDelete,
            isRule, hlxLang, selectNode, clearDisplay, setPreview, prepareTarget,
            confirmAddFolder, confirmAddFile, beginRename, confirmRename,
            beginDelete, confirmDelete, saveStructure, saveNow,
            addRules, setPreview,
            onExternalDropOnFolder, onRootDragOver, onRootDragLeave, onRootDrop,
        }
    },
}
