import { ColPicker } from './TagTable.js';

const TagFilterBar = {
    components: { 'col-picker': ColPicker },
    props: {
        modelValue: { type: Object, required: true },
        total: { type: Number, default: 0 },
        selectedCount: { type: Number, default: 0 },
        columns: { type: Array, required: true },
        visibleCols: { type: Object, required: true },
    },
    emits: [
        'update:modelValue',
        'search',
        'export-selected', 'export-all',
        'delete-selected',
        'clear-selection',
        'select-all-visible',
        'set-public-selected', 'set-private-selected',
        'activate-selected', 'deactivate-selected',
        'toggle-col', 'show-all-cols', 'hide-all-cols',
    ],
    setup(props, { emit }) {
        const { ref, computed } = Vue;
        const showAdvanced = ref(false);

        const sourceOptions = [
            { value: 'all', label: 'All', icon: 'fa-layer-group', color: '#6c757d' },
            { value: 'Taxonomy', label: 'Taxonomy', icon: 'fa-list', color: '#0d6efd' },
            { value: 'Galaxy', label: 'Galaxy', icon: 'fa-atom', color: '#9b7ede' },
            { value: 'Manual', label: 'Manual', icon: 'fa-tag', color: '#198754' },
        ];

        const activeChips = computed(() => {
            const chips = [];
            const v = props.modelValue;
            if (v.source !== 'all') chips.push({ key: 'source', label: v.source });
            if (v.visibility !== 'all') chips.push({ key: 'visibility', label: v.visibility === 'public' ? 'Public' : 'Private' });
            if (v.is_active !== 'all') chips.push({ key: 'is_active', label: v.is_active === 'active' ? 'Active only' : 'Inactive only' });
            if (v.show_namespace === false) chips.push({ key: 'show_namespace', label: 'No namespace' });
            return chips;
        });

        function update(key, value) {
            emit('update:modelValue', { ...props.modelValue, [key]: value });
            if (key !== 'search') emit('search');
        }

        function removeChip(key) {
            const defaults = { source: 'all', visibility: 'all', is_active: 'all', show_namespace: true };
            update(key, defaults[key]);
        }

        function onInput(e) {
            update('search', e.target.value);
            if (!e.target.value.trim()) emit('search');
        }

        function onEnter(e) {
            if (e.key === 'Enter') emit('search');
        }

        return { showAdvanced, sourceOptions, activeChips, update, removeChip, onInput, onEnter };
    },
    template: `
        <div class="tag-filter-bar mb-3">

            <!-- Search + count on the left, everything else pushed right —
                 same split as RuleList's toolbar (rl-toolbar-left/right). -->
            <div class="d-flex align-items-center justify-content-between gap-2 mb-2 flex-wrap">
                <div class="d-flex align-items-center gap-2">
                    <div class="dt-search" style="min-width:200px; max-width:420px;">
                        <i class="fas fa-magnifying-glass dt-search-icon"></i>
                        <input
                            type="text"
                            :value="modelValue.search"
                            class="dt-search-input"
                            placeholder="Search tags…"
                            @keyup="onEnter"
                            @input="onInput"
                        >
                    </div>
                    <span class="text-muted small text-nowrap">
                        <strong>{{ total }}</strong> tag<span v-if="total !== 1">s</span>
                    </span>
                </div>

                <div class="d-flex align-items-center gap-2 flex-wrap">
                <button
                    class="dt-toolbar-btn position-relative"
                    :class="{ 'dt-toolbar-btn--active': showAdvanced }"
                    @click="showAdvanced = !showAdvanced"
                >
                    <i class="fa-solid fa-sliders"></i><span>Filters</span>
                    <span
                        v-if="activeChips.length"
                        class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger"
                        style="font-size:0.55rem;"
                    >{{ activeChips.length }}</span>
                </button>

                <!-- Export -->
                <div class="dropdown">
                    <button class="dt-toolbar-btn dropdown-toggle" data-bs-toggle="dropdown">
                        <i class="fa-solid fa-download"></i><span>Export</span>
                    </button>
                    <ul class="dropdown-menu shadow border-0 rounded-3">
                        <li>
                            <button class="dropdown-item small" @click="$emit('export-all')">
                                <i class="fas fa-tags me-2 text-primary"></i>All tags ({{ total }})
                            </button>
                        </li>
                        <li v-if="selectedCount > 0">
                            <button class="dropdown-item small" @click="$emit('export-selected')">
                                <i class="fas fa-check-square me-2 text-success"></i>Selected ({{ selectedCount }})
                            </button>
                        </li>
                    </ul>
                </div>

                <!-- Columns -->
                <col-picker :cols="columns" :visible="visibleCols"
                            @toggle="key => $emit('toggle-col', key)"
                            @show-all="$emit('show-all-cols')"
                            @hide-all="$emit('hide-all-cols')">
                </col-picker>

                <!-- Add New Tag — same primary-button convention as RuleList's "New Rule" -->
                <button class="dt-toolbar-btn dt-toolbar-btn--primary"
                        data-bs-toggle="modal" data-bs-target="#add_tag_modal_">
                    <i class="fas fa-plus"></i><span>Add New Tag</span>
                </button>
                </div>
            </div>

            <!-- Bulk actions — the same sticky floating bar used everywhere else
                 a selection is made (dt-bulk-bar), not an inline dropdown row.
                 Teleported to <body> so position:fixed can't get clipped by an
                 ancestor's stacking context. -->
            <teleport to="body">
                <transition name="dt-bulk-slide">
                    <div v-if="selectedCount > 0" class="dt-bulk-bar">
                        <span class="dt-bulk-count">{{ selectedCount }} tag<span v-if="selectedCount !== 1">s</span> selected</span>
                        <div class="dt-bulk-actions">
                            <button class="dt-bulk-btn" @click="$emit('set-public-selected')">
                                <i class="fas fa-eye"></i> Make public
                            </button>
                            <button class="dt-bulk-btn" @click="$emit('set-private-selected')">
                                <i class="fas fa-eye-slash"></i> Make private
                            </button>
                            <button class="dt-bulk-btn" @click="$emit('activate-selected')">
                                <i class="fas fa-check-circle"></i> Activate
                            </button>
                            <button class="dt-bulk-btn" @click="$emit('deactivate-selected')">
                                <i class="fas fa-ban"></i> Deactivate
                            </button>
                            <button class="dt-bulk-btn dt-bulk-btn--danger" @click="$emit('delete-selected')">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                        <button class="dt-bulk-clear" @click="$emit('clear-selection')">
                            <i class="fas fa-xmark"></i> Clear
                        </button>
                    </div>
                </transition>
            </teleport>

            <!-- Filters panel — collapsible, RuleList-style. Source (Taxonomy/
                 Galaxy/Manual) lives here now instead of its own always-visible
                 row, alongside visibility/status/per-page/namespace. -->
            <transition name="slide-down">
                <div v-if="showAdvanced" class="advanced-filters border rounded-3 p-3 mb-2">
                    <div class="mb-3">
                        <label class="form-label small fw-semibold mb-1 d-block">Type</label>
                        <div class="d-flex gap-2 flex-wrap">
                            <button
                                v-for="opt in sourceOptions" :key="opt.value"
                                class="btn btn-sm source-chip"
                                :class="modelValue.source === opt.value ? 'active' : ''"
                                :style="modelValue.source === opt.value ? { background: opt.color, borderColor: opt.color, color: '#fff' } : {}"
                                @click="update('source', opt.value)"
                            >
                                <i :class="'fa-solid ' + opt.icon + ' me-1'"></i>{{ opt.label }}
                            </button>
                        </div>
                    </div>
                    <div class="row g-2 align-items-end">
                        <div class="col-6 col-md-3">
                            <label class="form-label small fw-semibold mb-1">Visibility</label>
                            <select class="form-select form-select-sm" :value="modelValue.visibility" @change="update('visibility', $event.target.value)">
                                <option value="all">All</option>
                                <option value="public">Public</option>
                                <option value="private">Private</option>
                            </select>
                        </div>
                        <div class="col-6 col-md-3">
                            <label class="form-label small fw-semibold mb-1">Status</label>
                            <select class="form-select form-select-sm" :value="modelValue.is_active" @change="update('is_active', $event.target.value)">
                                <option value="all">All</option>
                                <option value="active">Active</option>
                                <option value="inactive">Inactive</option>
                            </select>
                        </div>
                        <div class="col-6 col-md-3">
                            <label class="form-label small fw-semibold mb-1">Per page</label>
                            <select class="form-select form-select-sm" :value="modelValue.per_page" @change="update('per_page', parseInt($event.target.value))">
                                <option value="20">20</option>
                                <option value="50">50</option>
                                <option value="100">100</option>
                            </select>
                        </div>
                        <div class="col-12 col-md-6">
                            <label class="form-check small fw-semibold mb-0 d-flex align-items-center gap-2 mt-2">
                                <input
                                    type="checkbox" class="form-check-input m-0"
                                    :checked="modelValue.show_namespace"
                                    @change="update('show_namespace', $event.target.checked)"
                                >
                                Show namespace prefix in tag display
                            </label>
                        </div>
                    </div>
                </div>
            </transition>

            <!-- Active filter chips -->
            <div v-if="activeChips.length" class="d-flex align-items-center gap-2 flex-wrap">
                <span
                    v-for="chip in activeChips" :key="chip.key"
                    class="badge rounded-pill border px-2 py-1 filter-chip"
                    @click="removeChip(chip.key)" style="cursor:pointer; color: var(--text-color);"
                >
                    {{ chip.label }} <i class="fas fa-times ms-1"></i>
                </span>
            </div>
        </div>
    `
};

export default TagFilterBar;
