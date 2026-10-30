/**
 * BundleChangeList.js — the changes between two bundles, like the "Files changed" view of a pull request
 * (bundle_fork_core.compute_changes items). Used by the merge request page and by the "Compare with the
 * original" section of a fork.
 *
 * Props:
 *   items        [{ id, kind, key, label, conflict, conflict_kind, decision, rule_mode?, source, target, base_folder? }]
 *   reviewable   Boolean  — show accept / reject / pick-a-side controls
 *   leftLabel    String   — name of the side changes go to   (default "Original")
 *   rightLabel   String   — name of the side they come from  (default "Fork")
 * Emits: decide({ item, decision, rule_mode })
 */
import DiffViewer from '/static/js/components/diff-viewer.js'

const { reactive, computed } = Vue

const GROUPS = [
    { key: 'rule', label: 'Rules', icon: 'fa-solid fa-shield-halved' },
    { key: 'file', label: 'Files', icon: 'fa-solid fa-file-lines' },
    { key: 'folder', label: 'Folders', icon: 'fa-solid fa-folder' },
    { key: 'meta', label: 'Details', icon: 'fa-solid fa-circle-info' },
]
const KIND = { added: 'Added', removed: 'Removed', modified: 'Changed', moved: 'Moved', description: 'Changed',
               tags: 'Tags', vulnerabilities: 'CVEs' }
const CONFLICT = { content: 'changed on both sides', modify_delete: 'removed on one side, changed on the other',
                   delete_modify: 'changed on one side, removed on the other', move: 'moved differently on both sides',
                   delete_move: 'moved on one side, removed on the other' }

export default {
    name: 'BundleChangeList',
    components: { DiffViewer },
    props: {
        items: { type: Array, default: () => [] },
        reviewable: { type: Boolean, default: false },
        leftLabel: { type: String, default: 'Original' },
        rightLabel: { type: String, default: 'Fork' },
    },
    emits: ['decide'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const open = reactive({})
        const groups = computed(() => GROUPS.map(g => ({ ...g, items: props.items.filter(i => i.kind.split('_')[0] === g.key) }))
                                            .filter(g => g.items.length))
        const hasDiff = (it) => (it.source && it.source.content !== undefined) || (it.target && it.target.content !== undefined)
        const kind = (it) => it.kind.split('_')[1]
        const decide = (item, decision, rule_mode) => emit('decide', { item, decision, rule_mode })
        const allOpen = computed(() => props.items.filter(hasDiff).every(i => open[i.id]))
        const toggleAll = () => { const v = !allOpen.value; props.items.filter(hasDiff).forEach(i => { open[i.id] = v }) }
        return { open, groups, hasDiff, kind, decide, allOpen, toggleAll, KIND, CONFLICT }
    },
    template: `
    <div class="bcl">
        <div v-if="!items.length" class="bf-empty">No difference.</div>
        <div v-if="items.some(hasDiff)" class="bcl__tools">
            <button type="button" class="bf-link" @click="toggleAll"><i class="fa-solid" :class="allOpen ? 'fa-compress' : 'fa-expand'"></i>[[ allOpen ? 'Collapse all' : 'Expand all' ]]</button>
        </div>
        <section v-for="g in groups" :key="g.key" class="bcl__group">
            <h6 class="bcl__group-title"><i :class="g.icon"></i>[[ g.label ]] <span>[[ g.items.length ]]</span></h6>
            <div v-for="it in g.items" :key="it.id" class="bcl__item"
                 :class="['bcl__item--' + kind(it), { 'is-conflict': it.conflict, 'is-left-out': it.decision === 'reject' || it.decision === 'target' }]">
                <div class="bcl__row" :class="{ 'is-clickable': hasDiff(it) }" @click="hasDiff(it) && (open[it.id] = !open[it.id])">
                    <span class="bcl__badge">[[ KIND[kind(it)] || it.kind ]]</span>
                    <span class="bcl__label">[[ it.label ]]</span>
                    <span v-if="it.kind === 'rule_moved'" class="bcl__path">[[ it.base_folder || '/' ]] → [[ it.source.folder || '/' ]]</span>
                    <span v-else-if="it.source && it.source.folder" class="bcl__path">[[ it.source.folder ]]</span>
                    <span v-if="it.conflict" class="bcl__conflict"><i class="fa-solid fa-triangle-exclamation"></i>Conflict: [[ CONFLICT[it.conflict_kind] || 'both sides' ]]</span>
                    <span class="bcl__spacer"></span>
                    <span v-if="reviewable" class="bcl__decide" @click.stop>
                        <template v-if="it.conflict">
                            <button type="button" :class="{ 'is-on': it.decision === 'source' }" @click="decide(it, 'source')">Take [[ rightLabel ]]</button>
                            <button type="button" :class="{ 'is-on': it.decision === 'target' }" @click="decide(it, 'target')">Keep [[ leftLabel ]]</button>
                        </template>
                        <template v-else>
                            <button type="button" class="is-yes" :class="{ 'is-on': it.decision === 'accept' }" @click="decide(it, 'accept')" title="Take this change"><i class="fa-solid fa-check"></i></button>
                            <button type="button" class="is-no" :class="{ 'is-on': it.decision === 'reject' }" @click="decide(it, 'reject')" title="Leave it out"><i class="fa-solid fa-xmark"></i></button>
                        </template>
                    </span>
                    <i v-if="hasDiff(it)" class="fa-solid bcl__chev" :class="open[it.id] ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
                </div>
                <div v-if="reviewable && it.kind === 'rule_modified' && it.target && (it.decision === 'accept' || it.decision === 'source')" class="bcl__mode" @click.stop>
                    <span>Apply it by</span>
                    <select class="form-select form-select-sm" :value="it.rule_mode || ''" @change="decide(it, it.decision, $event.target.value)">
                        <option value="">default — update the rule if you may, else use the fork's copy</option>
                        <option value="update">updating the rule itself (new version, everywhere it is used)</option>
                        <option value="link">using the fork's copy in this bundle only</option>
                        <option value="propose">opening an edit proposal on the rule</option>
                    </select>
                </div>
                <div v-if="it.kind === 'meta_tags' || it.kind === 'meta_vulnerabilities'" class="bcl__chips">
                    <span v-for="v in it.source.add" :key="'a' + v" class="bcl__chip is-add">+ [[ v ]]</span>
                    <span v-for="v in it.source.remove" :key="'r' + v" class="bcl__chip is-remove">− [[ v ]]</span>
                </div>
                <div v-if="open[it.id]" class="bcl__diff">
                    <diff-viewer :initial-left="(it.target && it.target.content) || ''" :initial-right="(it.source && it.source.content) || ''"
                                 :left-label="leftLabel" :right-label="rightLabel"></diff-viewer>
                </div>
            </div>
        </section>
    </div>`,
}
