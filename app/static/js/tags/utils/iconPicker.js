/**
 * iconPicker.js — the icon field of the tag create / edit windows.
 * Offers the icons of the setting tags.icon_choices (by group, searchable, fetched once per page);
 * any other Font Awesome 7 name can be typed (preview shown). Brand icons (claude, openai, windows…)
 * render through fontawesome-7.3.1/css/rulezet-brands-shim.css even where tags are drawn with 'fas'.
 * v-model: the icon as "fa-<name>" (what tags already store).
 */
// Its stylesheet, added once (the page versions this module's URL: reuse its ?v= to bust the CSS cache too)
if (!document.querySelector('link[data-icon-picker-css]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.dataset.iconPickerCss = '1';
    link.href = '/static/css/tags/iconPicker.css' + (new URL(import.meta.url).search || '');
    document.head.appendChild(link);
}

let choicesPromise = null;
const choices = Vue.ref([]);
function loadChoices() {
    if (!choicesPromise) {
        choicesPromise = fetch('/api/config/settings/tags.icon_choices')
            .then(r => (r.ok ? r.json() : null))
            .then(d => { choices.value = (d && d.value) || []; })
            .catch(() => {});
    }
    return choicesPromise;
}

const IconPicker = {
    props: {
        modelValue: { type: String, default: 'fa-tag' }
    },
    emits: ['update:modelValue'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const searchQuery = Vue.ref('');
        const isOpen = Vue.ref(false);
        const group = Vue.ref('');
        loadChoices();

        const clean = (q) => q.trim().toLowerCase().replace(/^fa-/, '').replace(/[^a-z0-9-]/g, '');
        const groups = Vue.computed(() => choices.value.map(g => g.group));
        const filtered = Vue.computed(() => {
            const q = clean(searchQuery.value);
            const out = [];
            for (const g of choices.value) {
                if (group.value && g.group !== group.value) continue;
                const icons = g.icons.filter(i => !q || i.includes(q));
                if (icons.length) out.push({ group: g.group, icons });
            }
            return out;
        });
        // A name typed that is not in the list: offered as is (Font Awesome has ~2 000 free icons)
        const typed = Vue.computed(() => {
            const q = clean(searchQuery.value);
            if (!q || choices.value.some(g => g.icons.includes(q))) return null;
            return q;
        });

        const selectIcon = (name) => {
            emit('update:modelValue', 'fa-' + name);
            isOpen.value = false;
            searchQuery.value = '';
        };
        const current = Vue.computed(() => (props.modelValue || 'fa-tag').replace(/^fa-/, ''));

        return { searchQuery, isOpen, group, groups, filtered, typed, selectIcon, current };
    },
    template: `
    <div class="icon-picker-container position-relative">
        <label class="form-label fw-bold small text-muted text-uppercase mb-1">Icon</label>
        <div class="input-group shadow-sm rounded-3 cursor-pointer" @click="isOpen = !isOpen">
            <span class="input-group-text border-0 bg-light">
                <i :class="['fas', 'fa-' + current]" class="text-primary"></i>
            </span>
            <input type="text" class="form-control border-0 bg-light cursor-pointer"
                :value="modelValue" readonly style="height: 45px;">
            <span class="input-group-text border-0 bg-light">
                <i class="fas" :class="isOpen ? 'fa-chevron-up' : 'fa-chevron-down'" style="font-size: 0.8rem;"></i>
            </span>
        </div>

        <div v-if="isOpen" class="card shadow-lg border-0 position-absolute w-100 mt-1 z-3 rounded-4 overflow-hidden icon-picker-panel"
             style="min-width: 260px;" @click.stop>
            <div class="p-2 border-bottom icon-picker-head">
                <div class="input-group input-group-sm mb-2">
                    <span class="input-group-text border-0 bg-light"><i class="fas fa-search opacity-50"></i></span>
                    <input type="text" v-model="searchQuery" class="form-control border-0 bg-light"
                        placeholder="Search, or type any Font Awesome name…">
                </div>
                <div class="icon-picker-groups">
                    <button type="button" :class="{ 'is-on': !group }" @click="group = ''">All</button>
                    <button v-for="g in groups" :key="g" type="button" :class="{ 'is-on': group === g }" @click="group = g">[[ g ]]</button>
                </div>
            </div>
            <div class="p-2 overflow-y-auto" style="max-height: 240px;">
                <button v-if="typed" type="button" class="icon-picker-typed" @click="selectIcon(typed)">
                    <i :class="['fas', 'fa-' + typed]"></i><span>Use <code>fa-[[ typed ]]</code></span>
                    <small>blank preview = no such free icon</small>
                </button>
                <div v-for="g in filtered" :key="g.group" class="mb-2">
                    <div class="icon-picker-group-name">[[ g.group ]]</div>
                    <div class="icon-picker-grid">
                        <button v-for="icon in g.icons" :key="g.group + icon" type="button" class="icon-picker-btn"
                                :class="{ 'is-on': current === icon }" @click="selectIcon(icon)" :title="'fa-' + icon">
                            <i :class="['fas', 'fa-' + icon]"></i>
                        </button>
                    </div>
                </div>
                <div v-if="!filtered.length && !typed" class="text-center py-3 text-muted small">No icons found.</div>
            </div>
        </div>
    </div>
    `
};
export default IconPicker;
