import TagBadge from './TagBadge.js';
import { mapIcon, getTextColor } from '../utils/galaxie.js';


function familyOf(tag) {
    if (!tag || !tag.name || !tag.name.includes(':')) return null;
    if (tag.name.startsWith('misp-galaxy:') && tag.name.includes('=')) {
        return tag.name.split('=')[0];
    }
    return tag.name.split(':')[0];
}

function familyLabel(family) {
    if (!family) return '—';
    if (family.startsWith('misp-galaxy:')) return family.split(':')[1];
    return family;
}

function sourceColor(source) {
    if (source === 'Galaxy') return '#8b5cf6';
    if (source === 'Taxonomy') return '#0d6efd';
    return '#198754';
}

function sourceIconClass(source) {
    if (source === 'Galaxy') return 'fas fa-atom';
    if (source === 'Taxonomy') return 'fas fa-list';
    return 'fas fa-tag';
}


// ─── TagRow ──────────────────────────────────────────────────────────────────

const TagRow = {
    props: {
        tag: { type: Object, required: true },
        selected: { type: Boolean, default: false },
        csrfToken: { type: String, required: true },
        showNamespace: { type: Boolean, default: true },
    },
    emits: ['toggle-select', 'view-family', 'toggle-visibility', 'toggle-status', 'delete', 'refresh', 'notify'],
    components: { TagBadge },
    setup(props, { emit }) {
        const { ref, computed } = Vue;
        const editDraft = ref(null);
        const detailOpen = ref(false);
        const deleteOpen = ref(false);
        const editOpen = ref(false);

        const tagFamily = computed(() => familyOf(props.tag));

        function openEdit() {
            editDraft.value = { ...props.tag };
            editOpen.value = true;
        }

        async function saveEdit() {
            const tag = editDraft.value;
            const res = await fetch(`/tags/edit_tag/${tag.id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                body: JSON.stringify({
                    name: tag.name, description: tag.description,
                    color: tag.color, icon: tag.icon, external_id: tag.external_id,
                })
            });
            const data = await res.json();
            emit('notify', data.message, res.ok ? 'success-subtle' : 'danger-subtle');
            if (res.ok) { editOpen.value = false; emit('refresh'); }
        }

        function confirmDelete() {
            if (confirm(`Are you sure you want to permanently delete "${props.tag.name}"? This action cannot be undone.`)) {
                emit('delete');
                deleteOpen.value = false;
            }
        }

        // ── pretty JSON for galaxy_meta — basic syntax highlight ───────────────
        function highlightJson(obj) {
            if (!obj) return '';
            const json = JSON.stringify(obj, null, 2)
                .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return json
                .replace(/("(?:\\.|[^"\\])*")(\s*:)/g, '<span style="color:#0d6efd">$1</span>$2')
                .replace(/:\s*("(?:\\.|[^"\\])*")/g, ': <span style="color:#198754">$1</span>')
                .replace(/:\s*(true|false|null)/g, ': <span style="color:#dc3545">$1</span>')
                .replace(/:\s*(-?\d+\.?\d*)/g, ': <span style="color:#fd7e14">$1</span>');
        }

        return {
            editDraft, detailOpen, deleteOpen, editOpen,
            tagFamily, familyLabel, sourceColor, sourceIconClass,
            openEdit, saveEdit, confirmDelete, highlightJson,
        };
    },
    template: `
        <tr :class="{ 'table-active': selected }">
            <td>
                <input type="checkbox" class="form-check-input" :checked="selected" @change="$emit('toggle-select')">
            </td>
            <td><tag-badge :tag="tag" :show-namespace="showNamespace"></tag-badge></td>
            <td>
                <button
                    v-if="tagFamily"
                    class="btn btn-xs btn-outline-secondary family-chip"
                    @click="$emit('view-family')"
                    :title="'Browse all tags in family: ' + tagFamily"
                >
                    <i class="fas fa-folder me-1"></i>{{ familyLabel(tagFamily) }}
                </button>
                <span v-else class="text-muted small">—</span>
            </td>
            <td class="text-muted small text-truncate" style="max-width:200px" :title="tag.description">
                {{ tag.description || '—' }}
            </td>
            <td>
                <button
                    class="btn btn-xs rounded-pill"
                    :class="tag.visibility === 'public' ? 'btn-primary' : 'btn-outline-secondary'"
                    @click="$emit('toggle-visibility')"
                >
                    <i :class="tag.visibility === 'public' ? 'fas fa-eye me-1' : 'fas fa-eye-slash me-1'"></i>
                    {{ tag.visibility }}
                </button>
            </td>
            <td>
                <button
                    class="btn btn-xs rounded-pill"
                    :class="tag.is_active ? 'btn-success' : 'btn-danger'"
                    @click="$emit('toggle-status')"
                >
                    <i :class="tag.is_active ? 'fas fa-check me-1' : 'fas fa-ban me-1'"></i>
                    {{ tag.is_active ? 'Active' : 'Inactive' }}
                </button>
            </td>
            <td class="text-end">
                <div class="d-inline-flex gap-1">
                    <button class="btn btn-xs btn-outline-secondary icon-btn" @click="openEdit" title="Edit">
                        <i class="fas fa-pen"></i>
                    </button>
                    <button class="btn btn-xs btn-outline-secondary icon-btn" @click="detailOpen = true" title="Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-xs btn-outline-danger icon-btn" @click="deleteOpen = true" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>

        <teleport to="body">

            <!-- ── Edit Modal ───────────────────────────────────────────────── -->
            <div v-if="editOpen" class="modal fade show d-block" tabindex="-1" @click.self="editOpen=false" style="background:rgba(0,0,0,0.5)">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content border-0 shadow rounded-4" style="background: var(--card-bg-color)">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title fw-bold">
                                <i class="fas fa-pen me-2 text-primary"></i>Edit Tag
                            </h5>
                            <button class="btn-close" @click="editOpen=false"></button>
                        </div>
                        <div class="modal-body" v-if="editDraft">
                            <div class="row g-3">
                                <div class="col-md-8">
                                    <label class="form-label small fw-semibold">Name</label>
                                    <input type="text" class="form-control" v-model="editDraft.name">
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label small fw-semibold">Color</label>
                                    <div class="d-flex gap-2 align-items-center">
                                        <input type="color" class="form-control form-control-color" v-model="editDraft.color" style="width:48px">
                                        <input type="text" class="form-control form-control-sm font-monospace" v-model="editDraft.color" placeholder="#FFFFFF">
                                    </div>
                                </div>
                                <div class="col-12">
                                    <label class="form-label small fw-semibold">Description</label>
                                    <textarea class="form-control" rows="2" v-model="editDraft.description"></textarea>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small fw-semibold">Icon (FontAwesome)</label>
                                    <div class="input-group input-group-sm">
                                        <span class="input-group-text"><i :class="'fa ' + (editDraft.icon || 'fa-tag')"></i></span>
                                        <input type="text" class="form-control" v-model="editDraft.icon" placeholder="bug, shield-alt, ...">
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label small fw-semibold">External UUID</label>
                                    <input type="text" class="form-control form-control-sm font-monospace" v-model="editDraft.external_id" placeholder="Optional">
                                </div>
                                <div class="col-12">
                                    <div class="rounded-3 p-2 small text-muted" style="background: var(--light-bg-color)">
                                        UUID: {{ tag.uuid }} · Created by {{ tag.created_by_user_name || 'Unknown' }} · {{ tag.created_at }}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer border-0 pt-0">
                            <button class="btn btn-sm btn-light rounded-pill px-4" @click="editOpen=false">Cancel</button>
                            <button class="btn btn-sm btn-primary rounded-pill px-4" @click="saveEdit">
                                <i class="fas fa-save me-1"></i>Save
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ── Detail Modal (polished) ──────────────────────────────────── -->
            <div v-if="detailOpen" class="modal fade show d-block" tabindex="-1" @click.self="detailOpen=false" style="background:rgba(0,0,0,0.5)">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content border-0 shadow-lg rounded-4 overflow-hidden" style="background: var(--card-bg-color)">

                        <!-- Banner header with source-tinted background -->
                        <div
                            class="position-relative px-4 pt-4 pb-3"
                            :style="{
                                background: 'linear-gradient(135deg, ' + sourceColor(tag.source) + '15, ' + sourceColor(tag.source) + '05)',
                                borderBottom: '1px solid var(--border-color)'
                            }"
                        >
                            <button
                                class="btn-close position-absolute"
                                style="top:1rem; right:1rem;"
                                @click="detailOpen=false"
                            ></button>

                            <div class="d-flex align-items-center gap-3">
                                <div
                                    class="d-flex align-items-center justify-content-center flex-shrink-0 shadow-sm"
                                    :style="{
                                        background: tag.color || sourceColor(tag.source),
                                        width: '64px', height: '64px',
                                        borderRadius: '16px',
                                        color: '#fff', fontSize: '1.6rem',
                                    }"
                                >
                                    <i :class="'fa ' + (tag.icon ? (tag.icon.startsWith('fa-') ? tag.icon : 'fa-' + tag.icon) : 'fa-tag')"></i>
                                </div>
                                <div class="flex-grow-1 min-w-0">
                                    <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
                                        <span
                                            class="badge rounded-pill px-2 py-1"
                                            :style="{ background: sourceColor(tag.source), color: '#fff' }"
                                        >
                                            <i :class="sourceIconClass(tag.source) + ' me-1'"></i>{{ tag.source || 'Manual' }}
                                        </span>
                                        <span class="badge rounded-pill"
                                            :class="tag.is_active ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'"
                                        >
                                            <i :class="tag.is_active ? 'fas fa-check me-1' : 'fas fa-ban me-1'"></i>
                                            {{ tag.is_active ? 'Active' : 'Inactive' }}
                                        </span>
                                        <span class="badge rounded-pill"
                                            :class="tag.visibility === 'public' ? 'bg-primary-subtle text-primary' : 'bg-secondary-subtle text-secondary'"
                                        >
                                            <i :class="tag.visibility === 'public' ? 'fas fa-eye me-1' : 'fas fa-eye-slash me-1'"></i>
                                            {{ tag.visibility }}
                                        </span>
                                    </div>
                                    <h5 class="mb-0 fw-bold font-monospace text-break" style="color: var(--text-color)">
                                        {{ tag.name }}
                                    </h5>
                                </div>
                            </div>
                        </div>

                        <!-- Body -->
                        <div class="p-4">

                            <!-- Description -->
                            <div class="mb-4">
                                <label class="text-uppercase fw-semibold small mb-2" style="color: var(--subtle-text-color); letter-spacing:0.05em; font-size:0.7rem">
                                    <i class="fas fa-align-left me-1"></i>Description
                                </label>
                                <p class="mb-0" style="color: var(--text-color); line-height:1.6">
                                    {{ tag.description || 'No description provided.' }}
                                </p>
                            </div>

                            <!-- Metadata table -->
                            <table class="detail-table mb-4">
                                <tbody>
                                    <tr>
                                        <th><i class="fas fa-fingerprint me-2"></i>UUID</th>
                                        <td><code class="font-monospace small">{{ tag.uuid }}</code></td>
                                    </tr>
                                    <tr>
                                        <th><i class="fas fa-link me-2"></i>External ID</th>
                                        <td>
                                            <code v-if="tag.external_id" class="font-monospace small">{{ tag.external_id }}</code>
                                            <span v-else class="text-muted small">—</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <th><i class="fas fa-user me-2"></i>Created by</th>
                                        <td>
                                            <a :href="'/account/detail_user/' + tag.created_by_user_id" class="fw-semibold text-decoration-none">
                                                {{ tag.created_by_user_name || 'Unknown' }}
                                            </a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <th><i class="fas fa-clock me-2"></i>Created at</th>
                                        <td><strong class="small">{{ tag.created_at }}</strong></td>
                                    </tr>
                                    <tr v-if="tag.updated_at && tag.updated_at !== tag.created_at">
                                        <th><i class="fas fa-pen me-2"></i>Updated at</th>
                                        <td><strong class="small">{{ tag.updated_at }}</strong></td>
                                    </tr>
                                </tbody>
                            </table>

                            <!-- Galaxy metadata -->
                            <template v-if="tag.galaxy_meta">
                                <label class="text-uppercase fw-semibold small mb-2 d-block" style="color: var(--subtle-text-color); letter-spacing:0.05em; font-size:0.7rem">
                                    <i class="fas fa-database me-1"></i>Galaxy Metadata
                                </label>
                                <div
                                    class="rounded-3 border p-3 font-monospace"
                                    style="background: var(--code-bg-color, #1e1e1e); color: var(--text-color); max-height:240px; overflow:auto; font-size:0.78rem; line-height:1.5;"
                                >
                                    <pre style="margin:0; white-space:pre-wrap; word-break:break-word;" v-html="highlightJson(tag.galaxy_meta)"></pre>
                                </div>
                            </template>

                            <!-- Family link -->
                            <div v-if="tagFamily" class="mt-4 pt-3 border-top">
                                <button
                                    class="btn btn-sm btn-outline-primary rounded-pill px-3"
                                    @click="$emit('view-family'); detailOpen=false"
                                >
                                    <i class="fas fa-folder-open me-1"></i>
                                    Browse all tags in <strong>{{ familyLabel(tagFamily) }}</strong>
                                </button>
                            </div>
                        </div>

                        <!-- Footer -->
                        <div class="modal-footer border-0 pt-0 px-4 pb-3">
                            <button class="btn btn-sm btn-outline-secondary rounded-pill px-4" @click="detailOpen=false">
                                Close
                            </button>
                            <button class="btn btn-sm btn-primary rounded-pill px-4" @click="detailOpen=false; openEdit()">
                                <i class="fas fa-pen me-1"></i>Edit
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ── Delete Modal ──────────────────────────────────────────────── -->
            <div v-if="deleteOpen" class="modal fade show d-block" tabindex="-1" @click.self="deleteOpen=false" style="background:rgba(0,0,0,0.5)">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content border-0 shadow rounded-4" style="background: var(--card-bg-color)">
                        <div class="modal-header border-0">
                            <h5 class="modal-title fw-bold text-danger">
                                <i class="fas fa-exclamation-triangle me-2"></i>Delete tag?
                            </h5>
                            <button class="btn-close" @click="deleteOpen=false"></button>
                        </div>
                        <div class="modal-body text-center py-3">
                            <p class="mb-1">Are you sure you want to permanently delete <strong class="font-monospace">{{ tag.name }}</strong>?</p>
                            <small class="text-muted">This action cannot be undone. Consider deactivating the tag instead.</small>
                        </div>
                        <div class="modal-footer border-0">
                            <button class="btn btn-sm btn-light rounded-pill px-4" @click="deleteOpen=false">Cancel</button>
                            <button class="btn btn-sm btn-danger rounded-pill px-4" @click="$emit('delete'); deleteOpen=false">
                                <i class="fas fa-trash me-1"></i>Delete
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </teleport>
    `
};


// ─── TagTable ────────────────────────────────────────────────────────────────

const TagTable = {
    components: { 'tag-row': TagRow },
    props: {
        tags: { type: Array, required: true },
        groupedTags: { type: Object, default: null },
        showGrouped: { type: Boolean, default: true },
        selected: { type: Array, default: () => [] },
        csrfToken: { type: String, required: true },
        loading: { type: Boolean, default: false },
        showNamespace: { type: Boolean, default: true },
    },
    emits: ['toggle-select', 'toggle-all', 'refresh', 'view-family', 'notify'],
    setup(props, { emit }) {
        function isSelected(id) { return props.selected.includes(id); }

        function sourceIcon(source) {
            if (source === 'Galaxy') return 'fas fa-atom text-purple';
            if (source === 'Taxonomy') return 'fas fa-list text-primary';
            return 'fas fa-tag text-secondary';
        }

        async function toggleVisibility(tag) {
            const res = await fetch('/tags/toggle_visibility?' + new URLSearchParams({ tag_uuid: tag.uuid }));
            const data = await res.json();
            emit('notify', data.message, res.ok ? 'success-subtle' : 'danger-subtle');
            if (res.ok) emit('refresh');
        }

        async function toggleStatus(tag) {
            const res = await fetch('/tags/toggle_status?' + new URLSearchParams({ tag_uuid: tag.uuid }));
            const data = await res.json();
            emit('notify', data.message, res.ok ? 'success-subtle' : 'danger-subtle');
            if (res.ok) emit('refresh');
        }

        async function deleteTag(tag) {
            const res = await fetch('/tags/remove_tag?' + new URLSearchParams({ tag_id: tag.id }));
            const data = await res.json();
            emit('notify', data.message, res.ok ? 'success-subtle' : 'danger-subtle');
            if (res.ok) emit('refresh');
        }

        return {
            isSelected, sourceIcon, familyOf,
            toggleVisibility, toggleStatus, deleteTag,
            mapIcon, getTextColor,
        };
    },
    template: `
        <div class="tag-table-wrapper">
            <div v-if="loading" class="d-flex align-items-center justify-content-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
            </div>

            <template v-else-if="showGrouped && groupedTags">
                <div v-for="(group, source) in groupedTags" :key="source" class="mb-4">
                    <div class="group-header d-flex align-items-center gap-2 mb-2 pb-1 border-bottom">
                        <i :class="sourceIcon(source)"></i>
                        <span class="fw-semibold" style="color: var(--text-color)">{{ source }}</span>
                        <span class="badge bg-secondary rounded-pill">{{ group.length }}</span>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-sm align-middle mb-0 tag-table">
                            <thead>
                                <tr>
                                    <th style="width:36px">
                                        <input type="checkbox" class="form-check-input"
                                            :checked="group.every(t => isSelected(t.id))"
                                            @change="$emit('toggle-all', group.map(t => t.id), $event.target.checked)">
                                    </th>
                                    <th>Tag</th>
                                    <th>Namespace</th>
                                    <th>Description</th>
                                    <th>Visibility</th>
                                    <th>Status</th>
                                    <th class="text-end">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tag-row
                                    v-for="tag in group" :key="tag.uuid"
                                    :tag="tag"
                                    :selected="isSelected(tag.id)"
                                    :csrf-token="csrfToken"
                                    :show-namespace="showNamespace"
                                    @toggle-select="$emit('toggle-select', tag.id)"
                                    @view-family="$emit('view-family', tag.source, familyOf(tag))"
                                    @toggle-visibility="toggleVisibility(tag)"
                                    @toggle-status="toggleStatus(tag)"
                                    @delete="deleteTag(tag)"
                                    @refresh="$emit('refresh')"
                                    @notify="(m,c) => $emit('notify', m, c)"
                                ></tag-row>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div v-if="Object.keys(groupedTags).length === 0" class="text-center text-muted py-5">
                    <i class="fas fa-tags fa-2x mb-2 d-block opacity-25"></i>No tags found
                </div>
            </template>

            <template v-else>
                <div class="table-responsive">
                    <table class="table table-sm align-middle tag-table">
                        <thead>
                            <tr>
                                <th style="width:36px">
                                    <input type="checkbox" class="form-check-input"
                                        :checked="tags.length > 0 && tags.every(t => isSelected(t.id))"
                                        @change="$emit('toggle-all', tags.map(t => t.id), $event.target.checked)">
                                </th>
                                <th>Tag</th>
                                <th>Family</th>
                                <th>Description</th>
                                <th>Visibility</th>
                                <th>Status</th>
                                <th class="text-end">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tag-row
                                v-for="tag in tags" :key="tag.uuid"
                                :tag="tag"
                                :selected="isSelected(tag.id)"
                                :csrf-token="csrfToken"
                                :show-namespace="showNamespace"
                                @toggle-select="$emit('toggle-select', tag.id)"
                                @view-family="$emit('view-family', tag.source, familyOf(tag))"
                                @toggle-visibility="toggleVisibility(tag)"
                                @toggle-status="toggleStatus(tag)"
                                @delete="deleteTag(tag)"
                                @refresh="$emit('refresh')"
                                @notify="(m,c) => $emit('notify', m, c)"
                            ></tag-row>
                            <tr v-if="tags.length === 0">
                                <td colspan="7" class="text-center text-muted py-5">
                                    <i class="fas fa-tags fa-2x mb-2 d-block opacity-25"></i>No tags found
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </template>
        </div>
    `
};

export { TagTable, TagRow, familyOf, familyLabel };
export default TagTable;