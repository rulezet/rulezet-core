/**
 * iconPicker.js — the icon field of the tag create / edit windows.
 * Offers the icons of the setting tags.icon_choices (by group, searchable, fetched once per page);
 * any other Font Awesome 7 name can be typed (preview shown). Brand icons (claude, openai, windows…)
 * render through fontawesome-7.3.1/css/rulezet-brands-shim.css even where tags are drawn with 'fas'.
 * v-model: the icon as "fa-<name>" (what tags already store).
 * Props: label ('' = none), color (preview colour), all-icons (also offer every icon of the bundled
 * Font Awesome, ~2 000, read from its stylesheet — nothing to keep in step when Font Awesome is upgraded).
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

// Every icon name of the bundled Font Awesome, read once from its stylesheet (already in the browser cache)
let allPromise = null;
const allIcons = Vue.ref([]);
function loadAllIcons() {
    if (!allPromise) {
        // fontawesome.css (loaded by base.html) holds every icon name; its versioned URL is in the browser cache
        const link = document.querySelector('link[href*="fontawesome"][href*="/fontawesome."]');
        const url = link ? link.href : '/static/fontawesome-7.3.1/css/fontawesome.css';
        allPromise = fetch(url).then(r => (r.ok ? r.text() : ''))
            .then(css => {
                const names = new Set();
                for (const m of css.matchAll(/\.fa-([a-z][a-z0-9-]*)\s*\{\s*--fa\s*:/g)) names.add(m[1]);
                allIcons.value = [...names].sort();
            })
            .catch(() => {});
    }
    return allPromise;
}
const ALL_GROUP = 'Every icon';
const MAX_SHOWN = 400;          // a search over every icon shows at most this many

const IconPicker = {
    props: {
        modelValue: { type: String, default: 'fa-tag' },
        label: { type: String, default: 'Icon' },          // '' = no label (the form has its own)
        color: { type: String, default: '' },              // preview colour (e.g. a workflow's colour)
        allIcons: { type: Boolean, default: false },       // also offer every Font Awesome icon
    },
    emits: ['update:modelValue'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const searchQuery = Vue.ref('');
        const isOpen = Vue.ref(false);
        // The panel is teleported to <body> with position:fixed so a modal (overflow / z-index) never hides it
        const fieldEl = Vue.ref(null);
        const panelEl = Vue.ref(null);
        const panelStyle = Vue.ref({});
        const place = () => {
            if (!fieldEl.value) return;
            const r = fieldEl.value.getBoundingClientRect();
            const h = props.allIcons ? 460 : 360;
            const below = window.innerHeight - r.bottom;
            const up = below < h && r.top > below;
            panelStyle.value = {
                position: 'fixed', zIndex: 2100, left: r.left + 'px', width: Math.max(r.width, 260) + 'px',
                ...(up ? { bottom: (window.innerHeight - r.top + 4) + 'px' } : { top: (r.bottom + 4) + 'px' }),
            };
        };
        const onDocDown = (e) => {
            if (fieldEl.value?.contains(e.target) || panelEl.value?.contains(e.target)) return;
            isOpen.value = false;
        };
        Vue.watch(isOpen, (open) => {
            if (open) {
                place();
                window.addEventListener('scroll', place, true);
                window.addEventListener('resize', place);
                document.addEventListener('mousedown', onDocDown);
            } else {
                window.removeEventListener('scroll', place, true);
                window.removeEventListener('resize', place);
                document.removeEventListener('mousedown', onDocDown);
            }
        });
        Vue.onBeforeUnmount(() => { isOpen.value = false; });
        const group = Vue.ref('');
        loadChoices();
        if (props.allIcons) loadAllIcons();

        const clean = (q) => q.trim().toLowerCase().replace(/^fa-/, '').replace(/[^a-z0-9-]/g, '');
        const groups = Vue.computed(() => [...choices.value.map(g => g.group), ...(props.allIcons ? [ALL_GROUP] : [])]);
        const more = Vue.ref(0);         // icons of "Every icon" hidden by MAX_SHOWN
        const filtered = Vue.computed(() => {
            const q = clean(searchQuery.value);
            const out = [];
            if (group.value !== ALL_GROUP) {
                for (const g of choices.value) {
                    if (group.value && g.group !== group.value) continue;
                    const icons = g.icons.filter(i => !q || i.includes(q));
                    if (icons.length) out.push({ group: g.group, icons });
                }
            }
            more.value = 0;
            // Every icon: when its group is chosen, or when searching (after the curated ones)
            if (props.allIcons && (group.value === ALL_GROUP || q)) {
                const shown = new Set(out.flatMap(g => g.icons));
                const icons = allIcons.value.filter(i => !shown.has(i) && (!q || i.includes(q)));
                more.value = Math.max(0, icons.length - MAX_SHOWN);
                if (icons.length) out.push({ group: ALL_GROUP, icons: icons.slice(0, MAX_SHOWN) });
            }
            return out;
        });
        // A name typed that is not in the list: offered as is (Font Awesome has ~2 000 free icons)
        const typed = Vue.computed(() => {
            const q = clean(searchQuery.value);
            if (!q || choices.value.some(g => g.icons.includes(q)) || allIcons.value.includes(q)) return null;
            return q;
        });

        const selectIcon = (name) => {
            emit('update:modelValue', 'fa-' + name);
            isOpen.value = false;
            searchQuery.value = '';
        };
        const current = Vue.computed(() => (props.modelValue || 'fa-tag').replace(/^fa-/, ''));

        return { fieldEl, panelEl, panelStyle, searchQuery, isOpen, group, groups, filtered, typed, selectIcon, current, more, total: Vue.computed(() => allIcons.value.length) };
    },
    template: `
    <div class="icon-picker-container position-relative">
        <label v-if="label" class="form-label fw-bold small text-muted text-uppercase mb-1">[[ label ]]</label>
        <button ref="fieldEl" type="button" class="icon-picker-field" :class="{ 'is-open': isOpen }" @click="isOpen = !isOpen" :aria-expanded="isOpen">
            <span class="icon-picker-preview" :style="color ? { '--ip-color': color } : {}"><i :class="['fas', 'fa-' + current]"></i></span>
            <span class="icon-picker-name">fa-[[ current ]]</span>
            <i class="fas icon-picker-caret" :class="isOpen ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
        </button>

        <teleport to="body">
        <div v-if="isOpen" ref="panelEl" class="card shadow-lg border-0 rounded-4 overflow-hidden icon-picker-panel"
             :style="panelStyle" @click.stop>
            <div class="p-2 border-bottom icon-picker-head">
                <div class="input-group input-group-sm mb-2">
                    <span class="input-group-text icon-picker-search-icon"><i class="fas fa-search opacity-50"></i></span>
                    <input type="text" v-model="searchQuery" class="form-control icon-picker-search"
                        placeholder="Search, or type any Font Awesome name…">
                </div>
                <div class="icon-picker-groups">
                    <button type="button" :class="{ 'is-on': !group }" @click="group = ''">All</button>
                    <button v-for="g in groups" :key="g" type="button" :class="{ 'is-on': group === g }" @click="group = g">[[ g ]]</button>
                </div>
            </div>
            <div class="p-2 overflow-y-auto" :style="{ maxHeight: allIcons ? '340px' : '240px' }">
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
                <div v-if="more" class="text-center py-2 text-muted small">+ [[ more ]] more — type to narrow ([[ total ]] icons in all)</div>
                <div v-if="!filtered.length && !typed" class="text-center py-3 text-muted small">No icons found.</div>
            </div>
        </div>
        </teleport>
    </div>
    `
};
export default IconPicker;
