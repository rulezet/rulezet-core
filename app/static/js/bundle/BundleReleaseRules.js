/**
 * BundleReleaseRules.js — Rules tab when the detail page shows a frozen release.
 *
 * Lists the rules exactly as released, with what happened to each since:
 * unchanged / updated (author edited it) / deleted (removed from the library),
 * and whether it is still in the live bundle. Never needs the live rule —
 * content is served from the release snapshot.
 *
 * Props:
 *   rules    Array   release_rule_statuses() rows
 *   version  String  release version (labels)
 *
 * Emits:
 *   open(rule)             — view the frozen content
 *   diff(rule)             — compare frozen content with the current rule
 *   show-structure(ruleId)
 */

import PaginationComponent from '/static/js/rule/paginationComponent.js'

const { ref, computed, watch } = Vue
const PER_PAGE = 15

const STATUS = {
    unchanged: { label: 'Unchanged',     icon: 'fa-solid fa-check',        cls: 'ok' },
    updated:   { label: 'Updated since', icon: 'fa-solid fa-pen-to-square', cls: 'warning' },
    deleted:   { label: 'Deleted since', icon: 'fa-solid fa-trash',        cls: 'error' },
}

export default {
    name: 'BundleReleaseRules',
    components: { PaginationComponent },

    props: {
        rules:   { type: Array,  default: () => [] },
        version: { type: String, default: '' },
    },

    emits: ['open', 'diff', 'show-structure'],

    template: `
    <div class="brr-root">
        <div class="bfp-toolbar">
            <div class="bfp-search">
                <i class="fa-solid fa-magnifying-glass"></i>
                <input type="text" v-model="query" placeholder="Search rules of this release…">
                <button v-if="query" type="button" class="bfp-search-clear" @click="query = ''"><i class="fa-solid fa-xmark"></i></button>
            </div>
        </div>
        <div class="bfp-chips">
            <button v-for="f in filters" :key="f.key" type="button" class="bfp-chip"
                    :class="{ active: filter === f.key }" @click="filter = f.key" :disabled="!f.count && f.key !== 'all'">
                <i v-if="f.icon" :class="f.icon"></i>{{ f.label }} <span class="bfp-chip-count">{{ f.count }}</span>
            </button>
        </div>

        <div v-if="!filtered.length" class="bfp-empty"><i class="fa-regular fa-folder-open"></i> No rule matches.</div>

        <ul v-else class="bh-items brr-list">
            <li v-for="r in pageItems" :key="r.rule_id" class="bh-item">
                <div class="bh-item-main">
                    <span class="bh-item-name" :title="r.title"><i class="fa-solid fa-shield-halved"></i>{{ r.title }}</span>
                    <span class="bh-item-detail">
                        {{ r.format || 'unknown' }}<template v-if="r.license"> · {{ r.license }}</template>
                        <span :class="'brr-status brr-status--' + STATUS[r.status].cls"><i :class="STATUS[r.status].icon"></i>{{ STATUS[r.status].label }}</span>
                        <span v-if="!r.in_bundle_now" class="brr-status brr-status--info"><i class="fa-solid fa-box-open"></i>No longer in the bundle</span>
                    </span>
                </div>
                <div class="bh-item-actions">
                    <button type="button" class="am-rule-act" @click="$emit('open', r)" :title="'Content as released in ' + version">
                        <i class="fa-solid fa-eye"></i><span>View</span>
                    </button>
                    <button v-if="r.status === 'updated'" type="button" class="am-rule-act" @click="$emit('diff', r)"
                            title="Compare the released content with the current rule">
                        <i class="fa-solid fa-code-compare"></i><span>Diff</span>
                    </button>
                    <a v-if="r.rule_exists" :href="'/rule/detail_rule/' + r.rule_id" target="_blank" rel="noopener" class="am-rule-act" title="Current rule page">
                        <i class="fa-solid fa-arrow-up-right-from-square"></i><span>Rule page</span>
                    </a>
                    <button type="button" class="am-rule-act" @click="$emit('show-structure', r.rule_id)" title="Where it was in this release's structure">
                        <i class="fa-solid fa-folder-tree"></i><span>In structure</span>
                    </button>
                </div>
            </li>
        </ul>

        <div v-if="totalPages > 1" class="bfp-footer">
            <pagination-component :current-page="page" :total-pages="totalPages" @change-page="p => page = p"></pagination-component>
            <span class="bfp-range">{{ (page - 1) * PER_PAGE + 1 }}–{{ Math.min(page * PER_PAGE, filtered.length) }} of {{ filtered.length }}</span>
        </div>
    </div>
    `,

    setup(props) {
        const query  = ref('')
        const filter = ref('all')
        const page   = ref(1)

        const filters = computed(() => {
            const n = (fn) => props.rules.filter(fn).length
            return [
                { key: 'all',     label: 'All',           count: props.rules.length },
                { key: 'updated', label: 'Updated since', icon: 'fa-solid fa-pen-to-square', count: n(r => r.status === 'updated') },
                { key: 'deleted', label: 'Deleted since', icon: 'fa-solid fa-trash',         count: n(r => r.status === 'deleted') },
                { key: 'gone',    label: 'No longer in the bundle', icon: 'fa-solid fa-box-open', count: n(r => !r.in_bundle_now) },
            ]
        })
        const filtered = computed(() => {
            const q = query.value.trim().toLowerCase()
            return props.rules.filter(r =>
                (filter.value === 'all' || (filter.value === 'gone' ? !r.in_bundle_now : r.status === filter.value)) &&
                (!q || (r.title || '').toLowerCase().includes(q) || (r.format || '').toLowerCase().includes(q)))
        })
        const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / PER_PAGE)))
        const pageItems  = computed(() => filtered.value.slice((page.value - 1) * PER_PAGE, page.value * PER_PAGE))
        watch([query, filter, () => props.rules], () => { page.value = 1 })

        return { query, filter, page, filters, filtered, totalPages, pageItems, STATUS, PER_PAGE }
    },
}
