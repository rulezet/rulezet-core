/**
 * alertCriteriaChips.js — read-only chips for an alert's criteria, grouped
 * by kind and joined by the alert's match mode ("or" / "and").
 *
 * Props:
 *   criteria   Object  { cves, tags, attacks, keywords, formats, users, github_repos,
 *                         cve_any, tag_any, attack_any, github_any }
 *   matchMode  String  'any' | 'all'
 *   users      Array   [{ id, username }] — labels for criteria.users (ids alone otherwise)
 *   limit      Number  max chips shown before a "+N more" chip (0 = no limit)
 */

export const CRITERIA_KINDS = [
    { key: 'cves',         label: 'CVE',       icon: 'fa-shield-virus',   cls: 'al-chip--cve al-chip--mono' },
    { key: 'tags',         label: 'Tag',       icon: 'fa-tag',            cls: 'al-chip--tag' },
    { key: 'attacks',      label: 'ATT&CK',    icon: 'fa-crosshairs',     cls: 'al-chip--attack al-chip--mono' },
    { key: 'keywords',     label: 'Keyword',   icon: 'fa-magnifying-glass', cls: 'al-chip--keyword' },
    { key: 'formats',      label: 'Format',    icon: 'fa-file-code',      cls: 'al-chip--format' },
    { key: 'users',        label: 'User',      icon: 'fa-user',           cls: 'al-chip--user' },
    { key: 'github_repos', label: 'Repo',      icon: 'fa-brands fa-github', cls: 'al-chip--github al-chip--mono' },
]

export const ANY_FLAGS = [
    { key: 'cve_any',    list: 'cves',         label: 'any CVE' },
    { key: 'tag_any',    list: 'tags',         label: 'any tag' },
    { key: 'attack_any', list: 'attacks',      label: 'any ATT&CK technique' },
    { key: 'github_any', list: 'github_repos', label: 'any GitHub import' },
]

export default {
    name: 'AlertCriteriaChips',
    delimiters: ['[[', ']]'],

    props: {
        criteria:  { type: Object, default: () => ({}) },
        matchMode: { type: String, default: 'any' },
        users:     { type: Array,  default: () => [] },
        limit:     { type: Number, default: 0 },
    },

    template: `
        <div class="al-chips">
            <template v-for="(group, gi) in visibleGroups" :key="group.key">
                <span v-if="gi > 0" class="al-mode-sep">[[ matchMode === 'all' ? 'and' : 'or' ]]</span>
                <span v-for="chip in group.chips" :key="group.key + chip.value"
                      class="al-chip" :class="group.cls" :title="group.label + ': ' + chip.label">
                    <i :class="group.icon.startsWith('fa-brands') ? group.icon : 'fa-solid ' + group.icon"></i>[[ chip.label ]]
                </span>
            </template>
            <span v-if="hiddenCount > 0" class="al-chip al-chip--muted">+[[ hiddenCount ]] more</span>
        </div>
    `,

    setup(props) {
        const { computed } = Vue

        // One group per kind, in CRITERIA_KINDS order; an "any ..." switch
        // replaces that kind's list with a single chip.
        const groups = computed(() => {
            const c = props.criteria || {}
            const userNames = Object.fromEntries((props.users || []).map(u => [String(u.id), u.username]))
            const out = []
            for (const kind of CRITERIA_KINDS) {
                const any = ANY_FLAGS.find(f => f.list === kind.key)
                if (any && c[any.key]) {
                    out.push({ ...kind, chips: [{ value: 'any', label: any.label }] })
                } else if ((c[kind.key] || []).length) {
                    out.push({ ...kind, chips: c[kind.key].map(v => ({
                        value: String(v),
                        label: kind.key === 'users' ? (userNames[String(v)] || `user #${v}`) : String(v),
                    })) })
                }
            }
            return out
        })

        // Trim whole chips (not groups) once the limit is reached.
        const visibleGroups = computed(() => {
            if (!props.limit) return groups.value
            let left = props.limit
            const out = []
            for (const g of groups.value) {
                if (left <= 0) break
                out.push({ ...g, chips: g.chips.slice(0, left) })
                left -= g.chips.length
            }
            return out
        })

        const hiddenCount = computed(() => {
            const total = groups.value.reduce((n, g) => n + g.chips.length, 0)
            const shown = visibleGroups.value.reduce((n, g) => n + g.chips.length, 0)
            return total - shown
        })

        return { visibleGroups, hiddenCount }
    },
}
