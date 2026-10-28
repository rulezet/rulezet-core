/**
 * ruleOwnerPicker.js — who the new rules found by a GitHub update belong to.
 *
 * Three choices: Auto (the owner of most rules of the same source — the server decides,
 * rule_core.resolve_new_rule_owner), Me, or another user searched by name. Shown to admins and
 * GitHub Managers only; anyone else always owns the rules they add.
 *
 * Props:
 *   modelValue   null (auto) | { id, name }       the chosen owner
 *   me           { id, name }                      the current user (the "Me" shortcut)
 *   suggestion   { id, name, count } | null        who "Auto" means for this source, when known
 *   compact      Boolean                           one line, for a table cell
 * Emits update:modelValue.
 * The value to send to the server: ownerParam(modelValue) → 'auto' | user id.
 */
const { ref, computed, watch } = Vue;

export function ownerParam(value) {
    return value && value.id ? value.id : 'auto';
}

export default {
    name: 'RuleOwnerPicker',
    delimiters: ['[[', ']]'],
    props: {
        modelValue: { type: Object, default: null },
        me:         { type: Object, required: true },
        suggestion: { type: Object, default: null },
        compact:    { type: Boolean, default: false },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
        const mode = computed(() => !props.modelValue ? 'auto'
            : props.modelValue.id === props.me.id ? 'me' : 'user');
        const searching = ref(false);
        const query = ref('');
        const results = ref([]);
        let timer = null;

        function pick(m) {
            searching.value = false;
            if (m === 'auto') emit('update:modelValue', null);
            else if (m === 'me') emit('update:modelValue', { id: props.me.id, name: props.me.name || 'Me' });
            else { searching.value = true; query.value = ''; results.value = []; }
        }
        watch(query, (q) => {
            clearTimeout(timer);
            if ((q || '').trim().length < 2) { results.value = []; return; }
            timer = setTimeout(async () => {
                try {
                    const res = await fetch('/account/search_mentionable_users?q=' + encodeURIComponent(q.trim()));
                    results.value = res.ok ? ((await res.json()).users || []) : [];
                } catch { results.value = []; }
            }, 250);
        });
        function choose(u) {
            emit('update:modelValue', { id: u.id, name: u.username });
            searching.value = false;
        }
        const autoLabel = computed(() => props.suggestion
            ? `Auto: ${props.suggestion.name} (${props.suggestion.count} rule${props.suggestion.count === 1 ? '' : 's'} of this source)`
            : 'Auto: owner of this source’s rules, else you');

        return { mode, searching, query, results, pick, choose, autoLabel };
    },
    template: `
<div class="rop" :class="{ 'rop--compact': compact }">
  <div class="rop-modes" role="radiogroup" aria-label="New rules owner">
    <button type="button" class="rop-mode" :class="{ on: mode === 'auto' && !searching }" @click="pick('auto')"
            :title="autoLabel"><i class="fa-solid fa-wand-magic-sparkles"></i><span>Auto</span></button>
    <button type="button" class="rop-mode" :class="{ on: mode === 'me' && !searching }" @click="pick('me')"
            title="Me"><i class="fa-solid fa-user"></i><span>Me</span></button>
    <button type="button" class="rop-mode" :class="{ on: mode === 'user' || searching }" @click="pick('user')"
            title="Another user"><i class="fa-solid fa-user-pen"></i><span>User…</span></button>
  </div>
  <div v-if="!compact && mode === 'auto' && !searching" class="rop-hint">[[ autoLabel ]]</div>
  <span v-if="mode === 'user' && !searching" class="rop-chosen" :title="'New rules go to ' + modelValue.name">
    <i class="fa-solid fa-user-check"></i>[[ modelValue.name ]]
  </span>
  <div v-if="searching" class="rop-search">
    <input type="search" class="form-control form-control-sm" v-model="query" placeholder="Search a user (2+ letters)…" autofocus>
    <ul v-if="results.length" class="rop-results">
      <li v-for="u in results" :key="u.id" @click="choose(u)">
        <img v-if="u.avatar" :src="u.avatar" alt="" class="rop-avatar"><span>[[ u.username ]]</span>
      </li>
    </ul>
  </div>
</div>
`,
};
