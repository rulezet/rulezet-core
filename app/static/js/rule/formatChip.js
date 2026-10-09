/**
 * formatChip.js — a rule's format badge that opens a small menu, like the
 * CVE chips (vulnerabilityDisplayList.js): filter the list you're on by that
 * format, open every rule of that format, or read what the format is
 * (/rule/formats#<format>, with a link to its official site). Menu styles: .vdl-* in
 * css/rule/ruleList.css.
 *
 * Props:
 *   format     the rule's format ('yara', 'sigma', …)
 *   canFilter  show "Add to filter" (emits `filter` with the format) — for
 *              a page holding a filterable rule list (RuleList)
 *   active     this format is already the list's filter
 * Emits:
 *   filter(format)
 */
export default {
    name: 'FormatChip',
    delimiters: ['[[', ']]'],
    props: {
        format:    { type: String, default: '' },
        canFilter: { type: Boolean, default: false },
        active:    { type: Boolean, default: false },
    },
    emits: ['filter'],
    computed: {
        label()   { return (this.format || '?').toUpperCase(); },
        listUrl() { return `/rule/rules_list?rule_type=${encodeURIComponent(this.format || '')}`; },
        // Anchor = card id on the formats page (lowercase, spaces → dashes).
        infoUrl() { return `/rule/formats#${encodeURIComponent(this.format.trim().toLowerCase().replace(/ /g, '-'))}`; },
    },
    template: `
<span v-if="!format" class="badge rounded-pill bg-dark pt-1 shadow-sm">?</span>
<div v-else class="dropdown vdl-item d-inline-block" @click.stop>
    <button type="button" data-bs-toggle="dropdown" aria-expanded="false"
            class="badge rounded-pill bg-dark pt-1 shadow-sm border-0 fmt-chip"
            :title="'Format: ' + label + ' — click for options'">
        [[ label ]]<i class="fa-solid fa-caret-down ms-1" style="font-size:.6rem;opacity:.7;"></i>
    </button>
    <ul class="dropdown-menu vdl-menu">
        <li v-if="canFilter">
            <button type="button" class="vdl-menu-item w-100 border-0 bg-transparent text-start"
                    :disabled="active" @click="$emit('filter', format)">
                <i class="fas fa-filter"></i>
                <span v-if="active">Already filtering on [[ label ]]</span>
                <span v-else>Add to filter</span>
            </button>
        </li>
        <li>
            <a class="vdl-menu-item" :href="listUrl">
                <i class="fas fa-list"></i> View all [[ label ]] rules
            </a>
        </li>
        <li>
            <a class="vdl-menu-item" :href="infoUrl">
                <i class="fas fa-circle-info"></i> More details about [[ label ]]
            </a>
        </li>
    </ul>
</div>
`,
};
