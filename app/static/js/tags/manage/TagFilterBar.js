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

        const visibilityLabel = computed(() => {
            const v = props.modelValue.visibility;
            return v === 'public' ? 'Public' : v === 'private' ? 'Private' : 'Visibility';
        });
        const statusLabel = computed(() => {
            const v = props.modelValue.is_active;
            return v === 'active' ? 'Active' : v === 'inactive' ? 'Inactive' : 'Status';
        });

        function update(key, value) {
            emit('update:modelValue', { ...props.modelValue, [key]: value });
            if (key !== 'search') emit('search');
        }

        function removeChip(key) {
            const defaults = { source: 'all', visibility: 'all', is_active: 'all', show_namespace: true };
            update(key, defaults[key]);
        }

        function resetFilters() {
            emit('update:modelValue', {
                ...props.modelValue,
                search: '', source: 'all', visibility: 'all', is_active: 'all', show_namespace: true,
            });
            emit('search');
        }

        function onInput(e) {
            update('search', e.target.value);
            if (!e.target.value.trim()) emit('search');
        }

        function onEnter(e) {
            if (e.key === 'Enter') emit('search');
        }

        return { showAdvanced, sourceOptions, activeChips, visibilityLabel, statusLabel, update, removeChip, resetFilters, onInput, onEnter };
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

            <!-- Filters panel — same rl-filter-panel/rl-fp-row treatment as
                 RuleList's own filter panel (badge-style selects for Visibility/
                 Status, a plain select for Per page, a switch for Namespace). -->
            <transition name="slide-down">
                <div v-if="showAdvanced" class="rl-filter-panel">
                    <div class="rl-fp-row">

                        <!-- Type -->
                        <div class="rl-fp-item d-flex gap-2 flex-wrap">
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

                        <!-- Visibility -->
                        <div class="rl-fp-fmt-wrap">
                            <div class="rl-fmt-badge" :class="{ 'rl-fmt-badge--set': modelValue.visibility !== 'all' }">
                                <i class="fa-solid fa-eye" style="font-size:.7rem;opacity:.6;"></i>
                                <span>{{ visibilityLabel }}</span>
                                <i class="fa-solid fa-chevron-down" style="font-size:.6rem;opacity:.5;"></i>
                            </div>
                            <select class="rl-fmt-select-overlay" :value="modelValue.visibility"
                                    @change="update('visibility', $event.target.value)" aria-label="Visibility">
                                <option value="all">All visibility</option>
                                <option value="public">Public</option>
                                <option value="private">Private</option>
                            </select>
                        </div>

                        <!-- Status -->
                        <div class="rl-fp-fmt-wrap">
                            <div class="rl-fmt-badge" :class="{ 'rl-fmt-badge--set': modelValue.is_active !== 'all' }">
                                <i class="fa-solid fa-toggle-on" style="font-size:.7rem;opacity:.6;"></i>
                                <span>{{ statusLabel }}</span>
                                <i class="fa-solid fa-chevron-down" style="font-size:.6rem;opacity:.5;"></i>
                            </div>
                            <select class="rl-fmt-select-overlay" :value="modelValue.is_active"
                                    @change="update('is_active', $event.target.value)" aria-label="Status">
                                <option value="all">All statuses</option>
                                <option value="active">Active</option>
                                <option value="inactive">Inactive</option>
                            </select>
                        </div>

                        <!-- Per page -->
                        <div class="rl-fp-item">
                            <select class="rl-fp-select" :value="modelValue.per_page"
                                    @change="update('per_page', parseInt($event.target.value))" aria-label="Rows per page">
                                <option value="20">20 / page</option>
                                <option value="50">50 / page</option>
                                <option value="100">100 / page</option>
                            </select>
                        </div>

                        <!-- Show namespace -->
                        <label class="rl-fp-switch" title="Show namespace prefix in tag display">
                            <input type="checkbox" :checked="modelValue.show_namespace"
                                   @change="update('show_namespace', $event.target.checked)">
                            <span>Namespace prefix</span>
                        </label>

                        <button v-if="activeChips.length || modelValue.search"
                                class="rl-fp-reset" @click="resetFilters">
                            <i class="fas fa-rotate-left"></i> Reset
                        </button>

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
