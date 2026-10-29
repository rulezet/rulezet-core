/**
 * formatChip.js — a rule's format badge that opens a small menu, like the
 * CVE chips (vulnerabilityDisplayList.js): filter the list you're on by that
 * format, open every rule of that format, or read what the format is
 * (/rule/formats#<format>, with a link to its official site). Menu styles: .vdl-* in
 * css/rule/ruleList.css.
 *
 * The badge shows the format's logo and colour (setting formats.catalog: logo, color), read once
 * for the whole page from /api/config/settings/formats.catalog — the chip is shown on every row,
 * so it never fetches on its own (one shared promise). Unknown format: a grey badge with its name.
 *
 * Props:
 *   format     the rule's format ('yara', 'sigma', …)
 *   canFilter  show "Add to filter" (emits `filter` with the format) — for
 *              a page holding a filterable rule list (RuleList)
 *   active     this format is already the list's filter
 * Emits:
 *   filter(format)
 */
const { reactive } = Vue

// the catalogue, fetched once for every chip of the page
const catalog = reactive({ formats: null })
let catalogPromise = null
function loadCatalog() {
    if (!catalogPromise) {
        catalogPromise = fetch('/api/config/settings/formats.catalog')
            .then(r => (r.ok ? r.json() : null))
            .then(d => { catalog.formats = (d && d.value) || {} })
            .catch(() => { catalog.formats = {} })
    }
    return catalogPromise
}

const SAFE_COLOR = /^#[0-9a-fA-F]{3,8}$/
const SAFE_LOGO = /^[\w.-]+\.(png|svg|webp|jpg)$/i

/** A format's look from the shared catalogue: { title, color, logo } (also used by formatSelect.js). */
export function formatLook(format) {
    loadCatalog()
    const entry = (catalog.formats || {})[(format || '').toLowerCase()] || null
    const color = entry && entry.color && SAFE_COLOR.test(entry.color) ? entry.color : '#6C757D'
    const logo = entry && entry.logo && SAFE_LOGO.test(entry.logo) ? `/static/images/formats/${entry.logo}` : null
    return { title: (entry && entry.title) || (format || '?').toUpperCase(), color, logo }
}

export default {
    name: 'FormatChip',
    delimiters: ['[[', ']]'],
    props: {
        format:    { type: String, default: '' },
        canFilter: { type: Boolean, default: false },
        active:    { type: Boolean, default: false },
    },
    emits: ['filter'],
    created() { loadCatalog() },
    computed: {
        label()   { return (this.format || '?').toUpperCase(); },
        listUrl() { return `/rule/rules_list?rule_type=${encodeURIComponent(this.format || '')}`; },
        // Anchor = card id on the formats page (lowercase, spaces → dashes).
        infoUrl() { return `/rule/formats#${encodeURIComponent(this.format.trim().toLowerCase().replace(/ /g, '-'))}`; },
        entry()   { return (catalog.formats || {})[(this.format || '').toLowerCase()] || null; },
        color()   { const c = this.entry && this.entry.color; return c && SAFE_COLOR.test(c) ? c : '#6C757D'; },
        logo()    { const l = this.entry && this.entry.logo; return l && SAFE_LOGO.test(l) ? `/static/images/formats/${l}` : null; },
        title()   { return (this.entry && this.entry.title) || this.label; },
    },
    template: `
<span v-if="!format" class="badge rounded-pill bg-dark pt-1 shadow-sm">?</span>
<div v-else class="dropdown vdl-item d-inline-block" @click.stop>
    <button type="button" data-bs-toggle="dropdown" aria-expanded="false"
            class="fmt-chip fmt-chip--brand" :style="{ '--fmt': color }"
            :title="'Format: ' + title + ' — click for options'">
        <span class="fmt-chip__logo" v-if="logo"><img :src="logo" alt="" loading="lazy"></span>
        <span class="fmt-chip__label">[[ title ]]</span><i class="fa-solid fa-caret-down fmt-chip__caret"></i>
    </button>
    <ul class="dropdown-menu vdl-menu">
        <li v-if="canFilter">
            <button type="button" class="vdl-menu-item w-100 border-0 bg-transparent text-start"
                    :disabled="active" @click="$emit('filter', format)">
                <i class="fas fa-filter"></i>
                <span v-if="active">Already filtering on [[ title ]]</span>
                <span v-else>Add to filter</span>
            </button>
        </li>
        <li>
            <a class="vdl-menu-item" :href="listUrl">
                <i class="fas fa-list"></i> View all [[ title ]] rules
            </a>
        </li>
        <li>
            <a class="vdl-menu-item" :href="infoUrl">
                <i class="fas fa-circle-info"></i> More details about [[ title ]]
            </a>
        </li>
    </ul>
</div>
`,
};
