/**
 * attackDisplayList.js — Inline ATT&CK technique chip list for rule cards/table.
 *
 * Props:
 *   initialAttacks  Array<{technique_id, name, tactic_keys}>  — data from data_table batch fetch
 *   maxVisible      Number — max chips shown before "+N more"
 */

const TACTIC_BG = {
    'reconnaissance':       '#e7f0ff',
    'resource-development': '#ede9fe',
    'initial-access':       '#fce7f3',
    'execution':            '#fef3c7',
    'persistence':          '#d1fae5',
    'privilege-escalation': '#ffedd5',
    'defense-evasion':      '#f3f4f6',
    'credential-access':    '#fee2e2',
    'discovery':            '#e0f2fe',
    'lateral-movement':     '#fdf4ff',
    'collection':           '#ecfdf5',
    'command-and-control':  '#fff1f2',
    'exfiltration':         '#fff7ed',
    'impact':               '#fef2f2',
};
const TACTIC_TEXT = {
    'reconnaissance':       '#1d4ed8',
    'resource-development': '#6d28d9',
    'initial-access':       '#be185d',
    'execution':            '#92400e',
    'persistence':          '#065f46',
    'privilege-escalation': '#9a3412',
    'defense-evasion':      '#374151',
    'credential-access':    '#991b1b',
    'discovery':            '#0c4a6e',
    'lateral-movement':     '#86198f',
    'collection':           '#064e3b',
    'command-and-control':  '#881337',
    'exfiltration':         '#7c2d12',
    'impact':               '#7f1d1d',
};
const TACTIC_BORDER = {
    'reconnaissance':       '#bfdbfe',
    'resource-development': '#ddd6fe',
    'initial-access':       '#fbcfe8',
    'execution':            '#fde68a',
    'persistence':          '#a7f3d0',
    'privilege-escalation': '#fed7aa',
    'defense-evasion':      '#d1d5db',
    'credential-access':    '#fecaca',
    'discovery':            '#bae6fd',
    'lateral-movement':     '#f0abfc',
    'collection':           '#6ee7b7',
    'command-and-control':  '#fda4af',
    'exfiltration':         '#fdba74',
    'impact':               '#fca5a5',
};

function chipStyle(tacticKeys) {
    const first = (tacticKeys || [])[0] || '';
    return {
        background:   TACTIC_BG[first]     || '#f3f4f6',
        color:        TACTIC_TEXT[first]    || '#374151',
        borderColor:  TACTIC_BORDER[first]  || '#d1d5db',
    };
}

const AttackDisplayList = {
    name: 'AttackDisplayList',
    props: {
        initialAttacks: { type: Array,  default: () => [] },
        maxVisible:     { type: Number, default: 4 },
    },
    delimiters: ['[[', ']]'],
    setup(props) {
        const { ref, computed, watch } = Vue;

        const attacks     = ref([...(props.initialAttacks || [])]);
        const showingAll  = ref(false);

        watch(() => props.initialAttacks, v => { attacks.value = [...(v || [])]; }, { deep: true });

        const visible = computed(() =>
            showingAll.value ? attacks.value : attacks.value.slice(0, props.maxVisible)
        );
        const remaining = computed(() => attacks.value.length - props.maxVisible);

        return { attacks, visible, remaining, showingAll, chipStyle };
    },
    template: `
<div v-if="attacks.length" class="adl-root">
    <a v-for="t in visible" :key="t.technique_id"
       :href="'https://attack.mitre.org/techniques/' + t.technique_id.replace('.', '/')"
       target="_blank" rel="noopener"
       class="adl-chip"
       :style="chipStyle(t.tactic_keys)"
       :title="t.name">
        <span class="adl-tid">[[ t.technique_id ]]</span>
        <span class="adl-sep">·</span>
        <span class="adl-name">[[ t.name ]]</span>
    </a>
    <button v-if="!showingAll && remaining > 0"
            class="adl-more"
            @click.prevent.stop="showingAll = true">
        +[[ remaining ]]
    </button>
</div>
`,
};

export default AttackDisplayList;
