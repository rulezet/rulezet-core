/**
 * multiPlatformFilter.js — "Platforms" filter of the rules list (same look and behaviour as the
 * Licenses / Tags filters): the platforms named in the rules' metadata, each with its logo and
 * colour (Windows, Linux, AWS…), and once one is opened, its details (Windows → Sysmon,
 * PowerShell…). Picking a platform keeps every rule of it; picking a detail keeps only those.
 *
 * Values: "Windows" or "Windows:Sysmon" (rule.platforms). Counts come from
 * /rule/get_rules_platforms_usage, scoped to every other active filter (filterContext).
 * Logos, colours and details: setting rule.metadata_display (platforms).
 */
const MultiPlatformFilter = {
    props: {
        modelValue: { type: Array, default: () => [] },
        placeholder: { type: String, default: 'Windows, Linux…' },
        apiEndpoint: { type: String, default: '/rule/get_rules_platforms_usage' },
        userId: { type: Number, default: null },
        sourceRules: { type: String, default: '' },
        filterContext: { type: String, default: '' },
    },
    emits: ['update:modelValue', 'change'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const platforms = Vue.ref([])
        const search = Vue.ref('')
        const selected = Vue.ref([...props.modelValue])
        const opened = Vue.ref(null)            // the platform whose details are shown
        const isLoading = Vue.ref(false)

        Vue.watch(() => props.modelValue, v => { selected.value = [...v] }, { deep: true })

        async function load() {
            isLoading.value = true
            try {
                const params = new URLSearchParams(props.filterContext)
                if (props.userId !== null && !isNaN(props.userId)) params.append('user_id', String(props.userId))
                if (props.sourceRules && !params.has('sources')) params.append('sources', props.sourceRules)
                const url = props.apiEndpoint + (params.toString() ? (props.apiEndpoint.includes('?') ? '&' : '?') + params : '')
                const res = await fetch(url)
                if (res.ok) {
                    platforms.value = await res.json()
                    if (opened.value && !platforms.value.some(p => p.name === opened.value)) opened.value = null
                }
            } catch (e) {
                console.error('Error loading the platforms', e)
            } finally {
                isLoading.value = false
            }
        }
        Vue.watch(() => props.filterContext, load)
        Vue.watch(() => props.sourceRules, load)
        Vue.onMounted(load)

        const byName = Vue.computed(() => Object.fromEntries(platforms.value.map(p => [p.name, p])))
        const current = Vue.computed(() => byName.value[opened.value] || null)
        const filtered = Vue.computed(() => {
            const q = search.value.trim().toLowerCase()
            if (!q) return null
            const out = []
            for (const p of platforms.value) {
                if (p.label.toLowerCase().includes(q)) out.push({ ...p, isDetail: false })
                for (const d of p.details || []) if (d.label.toLowerCase().includes(q)) out.push({ ...p, ...d, isDetail: true, parent: p.label })
            }
            return out
        })

        // a value's look: its platform's logo and colour ("Windows:Sysmon" → Windows)
        const look = (value) => byName.value[String(value).split(':')[0]] || { icon: 'fa-solid fa-desktop', color: '#6c757d' }
        const labelOf = (value) => String(value).replace(':', ' · ')

        function toggle(value) {
            const i = selected.value.indexOf(value)
            if (i > -1) selected.value.splice(i, 1)
            else selected.value.push(value)
            emit('update:modelValue', [...selected.value])
            emit('change', [...selected.value])
        }
        function clearAll() {
            selected.value = []
            emit('update:modelValue', [])
            emit('change', [])
        }

        return { platforms, search, selected, opened, current, filtered, isLoading, look, labelOf, toggle, clearAll }
    },
    template: `
    <div class="dropdown mf-dropdown w-100 multi-platform-filter">
        <div class="form-control mf-trigger d-flex flex-wrap gap-2 align-items-center p-2 shadow-sm border-secondary-subtle"
             data-bs-toggle="dropdown" data-bs-auto-close="outside" data-bs-popper-config='{"strategy":"fixed"}'
             style="cursor: pointer; min-height: 48px; border-radius: 12px;">
            <i class="fa-solid fa-desktop text-primary opacity-75 ms-1 me-1"></i>
            <span v-if="!selected.length" class="text-muted small fw-bold">[[ placeholder ]]</span>
            <span v-for="v in selected.slice(0, 2)" :key="v" class="mpf-chip" :style="{ '--brand': look(v).color }">
                <i :class="look(v).icon"></i><span>[[ labelOf(v) ]]</span>
                <i class="fa-solid fa-circle-xmark mpf-chip__x" @click.stop="toggle(v)"></i>
            </span>
            <span v-if="selected.length > 2" class="mf-more" :title="selected.slice(2).map(labelOf).join(', ')">+[[ selected.length - 2 ]]</span>
            <i class="fa-solid fa-chevron-down ms-auto me-1 text-muted small"></i>
        </div>

        <div class="dropdown-menu mf-menu shadow-lg border-0 p-3 mt-2">
            <div v-if="selected.length" class="mf-selected">
                <div class="mf-selected__head">
                    <span>Selected · [[ selected.length ]]</span>
                    <button type="button" class="mf-selected__clear" @click.stop="clearAll">Clear all</button>
                </div>
                <div class="mf-selected__list">
                    <span v-for="v in selected" :key="v" class="mf-selected__chip" :title="labelOf(v)">
                        <i :class="look(v).icon" :style="{ color: look(v).color }" class="me-1"></i>
                        <span class="mf-selected__label">[[ labelOf(v) ]]</span>
                        <button type="button" class="mf-selected__x" @click.stop="toggle(v)" :aria-label="'Remove ' + labelOf(v)"><i class="fa-solid fa-xmark"></i></button>
                    </span>
                </div>
            </div>

            <div class="d-flex align-items-center mb-3">
                <button v-if="opened && !search" @click="opened = null" type="button"
                        class="btn btn-sm btn-outline-primary border-0 me-2 rounded-circle d-flex align-items-center justify-content-center"
                        style="width: 30px; height: 30px;" aria-label="Back to the platforms">
                    <i class="fa-solid fa-arrow-left"></i>
                </button>
                <div class="input-group input-group-sm">
                    <span class="input-group-text bg-light border-0"><i class="fa-solid fa-magnifying-glass"></i></span>
                    <input type="text" v-model="search" class="form-control bg-light border-0 shadow-none" placeholder="Search a platform…">
                </div>
            </div>

            <div class="custom-tag-scroll pe-2" style="max-height: 420px; overflow-y: auto;">
                <div v-if="isLoading && !platforms.length" class="text-center py-3 text-muted small"><i class="fa-solid fa-spinner fa-spin me-1"></i>Loading…</div>
                <div v-else-if="!platforms.length || (filtered && !filtered.length)" class="text-center py-4">
                    <i class="fa-solid fa-desktop fa-2x text-muted opacity-25 mb-2"></i>
                    <h6 class="text-muted fw-bold">No platform found</h6>
                    <p class="small text-muted opacity-75 mb-0">Platforms come from the rules' metadata (os, platform, integration, log source…).</p>
                </div>

                <!-- search: platforms and details together -->
                <div v-else-if="filtered" class="d-flex flex-column gap-1">
                    <div v-for="p in filtered" :key="p.name" @click="toggle(p.name)" class="mpf-row tag-item-hover"
                         :class="{ 'mpf-row--on': selected.includes(p.name) }" :style="{ '--brand': p.color }">
                        <span class="mpf-logo"><i :class="p.icon"></i></span>
                        <span class="mpf-name">[[ p.isDetail ? p.parent + ' · ' + p.label : p.label ]]</span>
                        <span class="mpf-count">[[ p.count ]]</span>
                    </div>
                </div>

                <!-- the platforms -->
                <div v-else-if="!current" class="d-flex flex-column gap-2">
                    <div v-for="p in platforms" :key="p.name" class="mpf-row mpf-row--big tag-item-hover"
                         :class="{ 'mpf-row--on': selected.includes(p.name) }" :style="{ '--brand': p.color }"
                         @click="p.details && p.details.length ? (opened = p.name) : toggle(p.name)">
                        <span class="mpf-logo mpf-logo--big"><i :class="p.icon"></i></span>
                        <span class="mpf-name">[[ p.label ]]<small v-if="p.details && p.details.length">[[ p.details.length ]] detail[[ p.details.length > 1 ? 's' : '' ]]</small></span>
                        <span class="mpf-count">[[ p.count ]]</span>
                        <i v-if="p.details && p.details.length" class="fa-solid fa-chevron-right opacity-50 small" style="color: var(--text-color);"></i>
                        <i v-else-if="selected.includes(p.name)" class="fa-solid fa-check-circle" :style="{ color: p.color }"></i>
                    </div>
                </div>

                <!-- one platform: all of it, or one of its details -->
                <div v-else :style="{ '--brand': current.color }">
                    <div class="mpf-head">
                        <span class="mpf-logo mpf-logo--big"><i :class="current.icon"></i></span>
                        <strong>[[ current.label ]]</strong>
                        <small class="ms-auto">[[ current.count ]] rules</small>
                    </div>
                    <div class="mpf-row tag-item-hover" :class="{ 'mpf-row--on': selected.includes(current.name) }" @click="toggle(current.name)">
                        <span class="mpf-logo"><i :class="current.icon"></i></span>
                        <span class="mpf-name">All of [[ current.label ]]</span>
                        <span class="mpf-count">[[ current.count ]]</span>
                        <i v-if="selected.includes(current.name)" class="fa-solid fa-check-circle" :style="{ color: current.color }"></i>
                    </div>
                    <div v-for="d in current.details" :key="d.name" class="mpf-row mpf-row--detail tag-item-hover"
                         :class="{ 'mpf-row--on': selected.includes(d.name) }" @click="toggle(d.name)">
                        <span class="mpf-dot"></span>
                        <span class="mpf-name">[[ d.label ]]</span>
                        <span class="mpf-count">[[ d.count ]]</span>
                        <i v-if="selected.includes(d.name)" class="fa-solid fa-check-circle" :style="{ color: current.color }"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>`,
}

export default MultiPlatformFilter
