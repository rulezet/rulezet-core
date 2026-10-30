/**
 * BundleForkPanel.js — forks and merge requests on the bundle detail page (bundle_fork_routes.py).
 *
 *   BundleForkBar (default export) — under the banner: where you are (Original → this fork), one sentence
 *       on how it stands, and the one thing to do (Propose my changes / Get the updates / Review).
 *       (The Fork button itself sits with Edit / Share in the bundle's action row, detail_bundle.html.)
 *   BundleForksPanel — the "Forks" tab: how forks work in 3 steps; in a fork, its changes compared with
 *       the original like a pull request (BundleChangeList.js); merge requests; forks; graph; owner switch.
 *   BundleForkGraph — the family of a bundle drawn like a git graph (same look as the rule proposal
 *       threads): one coloured column per bundle, forks branching off, merges joining back.
 *
 * The bar and the tab share one /fork_info request per page (module-level promise, refreshed after an
 * action). Props: bundleId (Number|String, required), csrfToken (String).
 */
import SmartEditor from '/static/js/components/smart-editor.js'
import BundleChangeList from '/static/js/bundle/BundleChangeList.js'
import { create_message } from '/static/js/toaster.js'

const { ref, reactive, computed, watch, onMounted } = Vue

if (!document.querySelector('link[data-bundle-fork-css]')) {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.dataset.bundleForkCss = '1'
    link.href = '/static/css/bundle/bundle-fork.css' + (new URL(import.meta.url).search || '')
    document.head.appendChild(link)
}

// One /fork_info per page, shared by the bar and the tab; reload() after an action
const shared = { promise: null, info: ref(null), panel: ref(null) }   // panel: asked by the bar's buttons
function loadInfo(bundleId, force = false) {
    if (!shared.promise || force) {
        shared.promise = fetch(`/bundle/${bundleId}/fork_info`).then(r => (r.ok ? r.json() : null))
            .then(d => { shared.info.value = d; return d }).catch(() => null)
    }
    return shared.promise
}

async function post(url, csrfToken, body = {}) {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                                   body: JSON.stringify(body) })
    const out = await res.json().catch(() => ({}))
    if (out.message) create_message(out.message, out.toast_class || (res.ok ? 'success-subtle' : 'danger-subtle'))
    return res.ok ? out : null
}

const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + 's')}`

// ── Graph ─────────────────────────────────────────────────────────────────
const COLORS = ['#0d6efd', '#6f42c1', '#d63384', '#fd7e14', '#20c997', '#0dcaf0', '#198754', '#b08800']
const LANE = 26, ROW = 42, DOT = 6

export const BundleForkGraph = {
    name: 'BundleForkGraph',
    props: { bundleId: { type: [Number, String], required: true } },
    delimiters: ['[[', ']]'],
    setup(props) {
        const data = ref(null)
        onMounted(async () => {
            const r = await fetch(`/bundle/${props.bundleId}/fork_network`).catch(() => null)
            data.value = r && r.ok ? await r.json().catch(() => null) : null
        })
        const lanes = computed(() => (data.value ? data.value.bundles : []))
        const laneOf = computed(() => Object.fromEntries(lanes.value.map((b, i) => [b.id, i])))
        const color = (id) => COLORS[(laneOf.value[id] ?? 0) % COLORS.length]
        const x = (id) => (laneOf.value[id] ?? 0) * LANE + LANE / 2
        const width = computed(() => Math.max(1, lanes.value.length) * LANE)
        // rows: the root's creation, then every event oldest first; a lane exists from its fork on
        const rows = computed(() => {
            if (!data.value) return []
            const root = lanes.value[0]
            const out = [{ type: 'root', bundle_id: root.id, label: 'Created', at: root.created_at }]
            return out.concat(data.value.events)
        })
        const startRow = computed(() => {
            const s = {}
            rows.value.forEach((e, i) => {
                if (e.type === 'root' || e.type === 'fork') s[e.bundle_id] = s[e.bundle_id] ?? i
            })
            return s
        })
        function cell(e, i) {
            // vertical lines of the lanes alive at this row
            const lines = lanes.value.filter(b => (startRow.value[b.id] ?? 0) <= i).map(b => ({
                x: x(b.id), y1: startRow.value[b.id] === i ? ROW / 2 : 0, y2: ROW, color: color(b.id) }))
            const curve = (from, to, dashed) => ({
                d: `M ${x(from)} 0 C ${x(from)} ${ROW / 2}, ${x(to)} 0, ${x(to)} ${ROW / 2}`,
                color: color(to), dashed })
            const curves = []
            if (e.type === 'fork') curves.push(curve(e.from_id, e.bundle_id, false))
            if (e.type === 'mr_merged') curves.push({ ...curve(e.from_id, e.bundle_id, false), color: color(e.from_id) })
            if (e.type === 'mr_open') curves.push({ ...curve(e.bundle_id, e.to_id, true), color: color(e.bundle_id) })
            return { lines, curves, dot: { x: x(e.bundle_id), color: color(e.bundle_id),
                     hollow: e.type === 'mr_open', closed: e.type === 'mr_closed' } }
        }
        const nameOf = (id) => (lanes.value[laneOf.value[id]] || {}).name || '?'
        const ICON = { root: 'fa-solid fa-flag', fork: 'fa-solid fa-code-fork', mr_open: 'fa-solid fa-code-pull-request',
                       mr_merged: 'fa-solid fa-code-merge', mr_closed: 'fa-solid fa-circle-xmark' }
        const go = (id) => { if (data.value && id !== data.value.current_id) window.location.href = '/bundle/detail/' + id }
        return { data, lanes, rows, width, cell, color, nameOf, go, ICON, ROW, DOT }
    },
    template: `
    <div class="bf-graph">
        <div v-if="!data" class="text-muted small">Loading the graph…</div>
        <template v-else>
            <div class="bf-graph__legend">
                <a v-for="b in lanes" :key="b.id" :href="'/bundle/detail/' + b.id" class="bf-graph__lane"
                   :class="{ 'is-current': b.id === data.current_id }" :style="{ '--lane': color(b.id) }">
                    <span class="bf-graph__swatch"></span>[[ b.name ]]<small v-if="b.owner"> · [[ b.owner ]]</small>
                    <small v-if="b.id === data.current_id"> · you are here</small>
                </a>
            </div>
            <div v-for="(e, i) in rows" :key="i" class="bf-graph__row" :style="{ height: ROW + 'px' }">
                <svg :width="width" :height="ROW" class="bf-graph__svg" aria-hidden="true">
                    <template v-for="(c, k) in [cell(e, i)]" :key="k">
                        <line v-for="(l, j) in c.lines" :key="'l' + j" :x1="l.x" :x2="l.x" :y1="l.y1" :y2="l.y2" :stroke="l.color" stroke-width="2"/>
                        <path v-for="(p, j) in c.curves" :key="'c' + j" :d="p.d" :stroke="p.color" stroke-width="2" fill="none"
                              :stroke-dasharray="p.dashed ? '4 3' : null"/>
                        <circle v-if="e.bundle_id === data.current_id" :cx="c.dot.x" :cy="ROW / 2" :r="DOT + 6" fill="none"
                                :stroke="c.dot.color" stroke-width="2" stroke-opacity=".35"/>
                        <circle :cx="c.dot.x" :cy="ROW / 2" :r="e.bundle_id === data.current_id ? DOT + 3 : DOT"
                                :fill="c.dot.hollow ? 'var(--card-bg-color)' : (c.dot.closed ? '#adb5bd' : c.dot.color)"
                                :stroke="c.dot.closed ? '#adb5bd' : c.dot.color" stroke-width="2"
                                class="bf-graph__dot" @click="go(e.bundle_id)">
                            <title>[[ nameOf(e.bundle_id) ]] — open it</title>
                        </circle>
                    </template>
                </svg>
                <div class="bf-graph__text">
                    <i :class="ICON[e.type]" :style="{ color: color(e.bundle_id) }"></i>
                    <a v-if="e.uuid" :href="'/bundle/merge_request/' + e.uuid" class="bf-graph__label">[[ e.label ]]</a>
                    <span v-else class="bf-graph__label">[[ e.label ]]</span>
                    <span class="bf-graph__where">[[ e.type === 'mr_open' ? nameOf(e.bundle_id) + ' → ' + nameOf(e.to_id)
                        : (e.type === 'mr_merged' || e.type === 'mr_closed') ? nameOf(e.from_id) + ' → ' + nameOf(e.bundle_id)
                        : nameOf(e.bundle_id) ]]</span>
                    <span class="bf-graph__at">[[ e.at ]]</span>
                    <span v-if="e.bundle_id === data.current_id" class="bf-graph__here"><i class="fa-solid fa-location-dot"></i>you are here</span>
                </div>
            </div>
        </template>
    </div>`,
}

// ── The "Forks" tab ───────────────────────────────────────────────────────
export const BundleForksPanel = {
    name: 'BundleForksPanel',
    components: { SmartEditor, BundleForkGraph, BundleChangeList },   // + BundleProposeCard, set at the end of the file
    props: { bundleId: { type: [Number, String], required: true }, csrfToken: { type: String, default: '' },
             active: { type: Boolean, default: false } },
    emits: ['changed'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const info = shared.info
        const status = ref('open')
        const mrs = ref([])
        const counts = ref({})
        const forks = ref({ forks: [], hidden: 0, total: 0 })
        const loaded = ref(false)
        const rules = ref([])
        const editing = reactive({ ruleId: '', rule: null, content: '', saving: false })
        const compare = reactive({ side: 'mine', items: [], summary: null, loading: false })
        const panel = ref('mrs')
        watch(shared.panel, p => { if (p) { panel.value = p; shared.panel.value = null } })

        async function loadCompare() {
            if (!(info.value && info.value.is_fork && info.value.upstream)) return
            compare.loading = true
            const r = await fetch(`/bundle/${props.bundleId}/compare_upstream?side=${compare.side}`).catch(() => null)
            const d = r && r.ok ? await r.json().catch(() => null) : null
            compare.items = (d && d.items) || []
            compare.summary = d && d.summary
            compare.loading = false
        }
        watch(() => compare.side, loadCompare)

        async function load() {
            await loadInfo(props.bundleId)
            const [m, f] = await Promise.all([
                fetch(`/bundle/${props.bundleId}/merge_requests?status=${status.value}`).then(r => r.ok ? r.json() : null),
                fetch(`/bundle/${props.bundleId}/forks`).then(r => r.ok ? r.json() : null),
            ])
            if (!loaded.value && shared.panel.value) { panel.value = shared.panel.value; shared.panel.value = null }
            else if (!loaded.value) {      // first open: the panel that matters most here
                panel.value = (info.value && info.value.is_fork && info.value.upstream) ? 'compare'
                    : (m && m.counts && m.counts.open) ? 'mrs' : (f && f.total) ? 'forks' : 'help'
            }
            mrs.value = (m && m.merge_requests) || []
            counts.value = (m && m.counts) || {}
            forks.value = f || { forks: [], hidden: 0, total: 0 }
            loadCompare()
            if (info.value && info.value.is_fork && info.value.is_manager && !rules.value.length) {
                const r = await fetch(`/bundle/${props.bundleId}/fork_rules`).catch(() => null)
                const d = r && r.ok ? await r.json().catch(() => null) : null
                rules.value = (d && d.rules) || []
            }
            loaded.value = true
        }
        watch(() => props.active, a => { if (a && !loaded.value) load() }, { immediate: true })
        watch(status, load)

        async function setAccepts(v) {
            const out = await post(`/bundle/${props.bundleId}/accepts_proposals`, props.csrfToken, { value: v })
            if (out) loadInfo(props.bundleId, true)
        }
        const otherRules = computed(() => rules.value.filter(r => !r.is_mine))
        async function editCopy(rule) {
            if (!rule) return
            const r = await fetch(`/bundle/${props.bundleId}/rule_content/${rule.id}`).catch(() => null)
            const d = r && r.ok ? await r.json().catch(() => null) : null
            editing.rule = rule
            editing.content = (d && (d.content || d.to_string)) || ''
        }
        async function saveCopy() {
            editing.saving = true
            const out = await post(`/bundle/${props.bundleId}/fork_rule/${editing.rule.id}`, props.csrfToken, { content: editing.content })
            editing.saving = false
            if (out) { editing.rule = null; editing.ruleId = ''; rules.value = []; await loadInfo(props.bundleId, true); load() }
        }
        const STATUS = { open: 'fa-solid fa-code-pull-request', merged: 'fa-solid fa-code-merge', closed: 'fa-solid fa-circle-xmark', stale: 'fa-solid fa-hourglass-end' }
        const STATUS_LABEL = { open: 'Open', merged: 'Merged', closed: 'Closed', stale: 'Stale' }
        const direction = (m) => (String(m.target && m.target.id) === String(props.bundleId) ? 'in' : 'out')
        return { info, panel, status, mrs, counts, forks, loaded, rules, otherRules, editing, compare, setAccepts, editCopy, saveCopy,
                 STATUS, STATUS_LABEL, direction, plural }
    },
    template: `
    <div class="bf-panel">
        <div v-if="!loaded" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary"></div></div>
        <template v-else>
            <!-- One panel at a time -->
            <div class="bf-tabs" role="tablist">
                <button v-if="info && info.is_fork && info.upstream" type="button" :class="{ 'is-on': panel === 'compare' }" @click="panel = 'compare'">
                    <i class="fa-solid fa-code-compare"></i>Compare with the original <span>[[ (info.ahead || 0) + (info.behind || 0) ]]</span></button>
                <button type="button" :class="{ 'is-on': panel === 'mrs' }" @click="panel = 'mrs'">
                    <i class="fa-solid fa-code-pull-request"></i>Merge requests <span>[[ counts.open || 0 ]]</span></button>
                <button type="button" :class="{ 'is-on': panel === 'forks' }" @click="panel = 'forks'">
                    <i class="fa-solid fa-code-fork"></i>Forks <span>[[ forks.total ]]</span></button>
                <button type="button" :class="{ 'is-on': panel === 'graph' }" @click="panel = 'graph'">
                    <i class="fa-solid fa-diagram-project"></i>Graph</button>
                <button type="button" :class="{ 'is-on': panel === 'help' }" @click="panel = 'help'">
                    <i class="fa-solid fa-circle-question"></i>How it works</button>
            </div>

            <!-- How it works, in 3 steps -->
            <div v-if="panel === 'help'" class="bf-steps mb-4">
                <div class="bf-step"><span class="bf-step__n">1</span><div><b>Fork</b><small>Make your own copy of a bundle. It stays linked to the original.</small></div></div>
                <div class="bf-step"><span class="bf-step__n">2</span><div><b>Change your copy</b><small>Add or remove rules, files, tags. A rule you don't own: edit your own copy of it.</small></div></div>
                <div class="bf-step"><span class="bf-step__n">3</span><div><b>Propose it back</b><small>Open a merge request. The owner reviews each change and merges what they want.</small></div></div>
            </div>

            <!-- A fork compared with the original, like the "Files changed" of a pull request -->
            <div v-if="panel === 'compare' && info && info.is_fork && info.upstream">
                <bundle-propose-card :bundle-id="bundleId" :csrf-token="csrfToken"></bundle-propose-card>
                <div class="bf-block__head">
                    <div class="bf-section-title mb-0"><i class="fa-solid fa-code-compare"></i>Compare with the original</div>
                    <div class="bf-seg">
                        <button type="button" :class="{ 'is-on': compare.side === 'mine' }" @click="compare.side = 'mine'">
                            Changed here <span>[[ info.ahead ]]</span></button>
                        <button type="button" :class="{ 'is-on': compare.side === 'theirs' }" @click="compare.side = 'theirs'">
                            New in the original <span>[[ info.behind ]]</span></button>
                    </div>
                </div>
                <p class="small text-muted mb-3">
                    <template v-if="compare.side === 'mine'">What this fork changed since it was made (or last synced) — what a merge request to
                        <b>[[ info.upstream.name ]]</b> would propose.</template>
                    <template v-else>What changed in <b>[[ info.upstream.name ]]</b> since — what Sync would bring here.</template>
                </p>
                <div v-if="compare.loading" class="text-muted small">Comparing…</div>
                <bundle-change-list v-else :items="compare.items"
                    :left-label="compare.side === 'mine' ? info.upstream.name : 'This fork'"
                    :right-label="compare.side === 'mine' ? 'This fork' : info.upstream.name"></bundle-change-list>

                <!-- Change a rule you don't own: one picker, the change becomes a copy used here only -->
                <details v-if="info.is_manager && otherRules.length" class="bf-copy">
                    <summary><i class="fa-solid fa-pen-to-square"></i>Change a rule you don't own</summary>
                    <p class="small text-muted my-2">Your change goes into a copy used by this fork only; the rule itself stays as it is.
                        It then shows above as a change to propose.</p>
                    <div class="d-flex flex-wrap gap-2 align-items-center">
                        <select class="form-select form-select-sm bf-copy__select" v-model="editing.ruleId"
                                @change="editCopy(otherRules.find(r => String(r.id) === String(editing.ruleId)))">
                            <option value="">Pick a rule…</option>
                            <option v-for="r in otherRules" :key="r.id" :value="r.id">[[ r.title ]] ([[ r.format ]])[[ r.is_copy ? ' — your copy' : '' ]]</option>
                        </select>
                    </div>
                    <div v-if="editing.rule" class="bf-edit mt-3">
                        <smart-editor v-model="editing.content" mode="code" :language="(editing.rule.format || 'text').toLowerCase()" min-height="240px" max-height="60vh"></smart-editor>
                        <div class="d-flex gap-2 mt-2">
                            <button type="button" class="btn btn-sm btn-primary rounded-pill" :disabled="editing.saving" @click="saveCopy">
                                <i class="fa-solid fa-floppy-disk me-1"></i>Save in this fork</button>
                            <button type="button" class="btn btn-sm btn-light rounded-pill" @click="editing.rule = null; editing.ruleId = ''">Cancel</button>
                        </div>
                    </div>
                </details>
            </div>

            <!-- Merge requests -->
            <div v-if="panel === 'mrs'">
                <div class="bf-section-title"><i class="fa-solid fa-code-pull-request"></i>Merge requests
                    <small class="text-muted fw-normal">— changes proposed to this bundle, or from it</small></div>
                <div class="bf-filter mb-2">
                    <button v-for="s in ['open', 'merged', 'closed', 'stale']" :key="s" type="button" :class="{ 'is-on': status === s }" @click="status = s">
                        <i :class="STATUS[s]"></i>[[ STATUS_LABEL[s] ]] <span>[[ counts[s] || 0 ]]</span></button>
                </div>
                <div v-if="!mrs.length" class="bf-empty">No [[ STATUS_LABEL[status].toLowerCase() ]] merge request.</div>
                <a v-for="m in mrs" :key="m.uuid" :href="'/bundle/merge_request/' + m.uuid" class="bf-mr">
                    <i :class="STATUS[m.status]" class="bf-mr__icon" :data-status="m.status"></i>
                    <span class="bf-mr__body">
                        <span class="bf-mr__title">[[ m.title ]]</span>
                        <span class="bf-mr__sub">
                            <span class="bf-dir" :class="'bf-dir--' + direction(m)">[[ direction(m) === 'in' ? 'To this bundle' : 'From this bundle' ]]</span>
                            · [[ m.source ? m.source.name : '?' ]] → [[ m.target ? m.target.name : '?' ]] · by [[ m.user ? m.user.name : '?' ]] · [[ m.created_at ]]
                        </span>
                    </span>
                    <span class="bf-mr__counts">[[ plural(m.counts.total, 'change') ]]<template v-if="m.counts.conflicts"> · <b class="text-danger">[[ plural(m.counts.conflicts, 'conflict') ]]</b></template></span>
                </a>
            </div>

            <!-- Forks -->
            <div v-if="panel === 'forks'">
                <div class="bf-section-title"><i class="fa-solid fa-code-fork"></i>Forks of this bundle <span class="text-muted fw-normal">([[ forks.total ]])</span></div>
                <div v-if="!forks.forks.length" class="bf-empty">[[ forks.hidden ? plural(forks.hidden, 'private fork') + '.' : 'Nobody forked this bundle yet.' ]]</div>
                <div v-else class="bf-forks">
                    <a v-for="f in forks.forks" :key="f.id" :href="'/bundle/detail/' + f.id" class="bf-fork">
                        <i class="fa-solid fa-code-fork"></i>
                        <span class="bf-fork__name">[[ f.name ]]</span>
                        <span class="bf-fork__sub">[[ f.owner ]] · updated [[ f.updated_at ]]<template v-if="!f.access"> · private</template></span>
                        <span v-if="f.open_merge_request" class="bf-pill"><i class="fa-solid fa-code-pull-request"></i>open merge request</span>
                    </a>
                    <div v-if="forks.hidden" class="text-muted small mt-1">+ [[ plural(forks.hidden, 'private fork') ]]</div>
                </div>
            </div>

            <!-- Graph -->
            <div v-if="panel === 'graph'">
                <div class="bf-section-title"><i class="fa-solid fa-diagram-project"></i>Graph
                    <small class="text-muted fw-normal">— the original, its forks and what went between them</small></div>
                <bundle-fork-graph :bundle-id="bundleId"></bundle-fork-graph>
            </div>

            <!-- Owner: take merge requests or not -->
            <div v-if="panel === 'mrs' && info && info.is_manager" class="bf-setting">
                <div class="form-check form-switch mb-0">
                    <input class="form-check-input" type="checkbox" id="bfAccepts" :checked="info.accepts_proposals" @change="setAccepts($event.target.checked)">
                    <label class="form-check-label" for="bfAccepts">Take merge requests from forks</label>
                </div>
                <small class="text-muted">Off: people can still fork this bundle, but can't propose their changes here.</small>
            </div>
        </template>
    </div>`,
}

// ── The bar under the banner: where you are, how it stands, the one thing to do ──

export default {
    name: 'BundleForkBar',
    props: { bundleId: { type: [Number, String], required: true }, csrfToken: { type: String, default: '' },
             authenticated: { type: Boolean, default: false } },
    emits: ['loaded', 'changed', 'open-tab'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const info = shared.info
        const busy = ref(false)
        onMounted(async () => {
            emit('loaded', await loadInfo(props.bundleId))
            // back on the page (after editing the fork elsewhere): counts and sentence refresh by themselves
            document.addEventListener('visibilitychange', async () => {
                if (document.visibilityState === 'visible') emit('loaded', await loadInfo(props.bundleId, true))
            })
        })
        // Only where there is something to say: a fork, a bundle with forks, or open merge requests
        const shown = computed(() => info.value && info.value.enabled !== false
            && (info.value.is_fork || info.value.forks_count || info.value.open_incoming || info.value.my_fork))
        // the one sentence of the bar
        const stateKind = computed(() => {
            const i = info.value || {}
            if (i.is_fork && !i.upstream) return 'muted'
            if (i.is_fork) return (i.ahead || i.behind) ? 'news' : 'ok'
            return i.open_incoming ? 'news' : 'muted'
        })
        const stateText = computed(() => {
            const i = info.value
            if (!i) return ''
            const who = i.is_manager ? 'You' : 'This fork'
            if (i.is_fork) {
                if (!i.upstream) return 'The original is not available anymore: this copy lives on its own.'
                if (i.ahead && i.behind) return `${who} changed ${plural(i.ahead, 'thing')} not in the original, and the original has ${plural(i.behind, 'update')} not here.`
                if (i.ahead) return `${who} changed ${plural(i.ahead, 'thing')} that the original does not have yet.`
                if (i.behind) return `The original has ${plural(i.behind, 'update')} that ${i.is_manager ? 'you do' : 'this fork does'} not have yet.`
                return 'Same content as the original — nothing to propose, nothing to get.'
            }
            if (i.open_incoming) return `${plural(i.open_incoming, 'proposal')} from a fork ${i.open_incoming === 1 ? 'is' : 'are'} waiting for review.`
            if (i.my_fork) return 'You have a fork of this bundle.'
            return 'People who fork this bundle can propose their changes here.'
        })

        async function sync() {
            busy.value = true
            const out = await post(`/bundle/${props.bundleId}/sync`, props.csrfToken, {})
            busy.value = false
            if (!out) return
            if (out.conflicts && out.url) { window.location.href = out.url; return }
            emit('loaded', await loadInfo(props.bundleId, true)); emit('changed')
        }
        const goTab = (panel) => { shared.panel.value = panel; emit('open-tab') }
        const welcome = ref(new URLSearchParams(location.search).get('fork_welcome') === '1')
        function closeWelcome() {
            welcome.value = false
            const url = new URL(location.href)
            url.searchParams.delete('fork_welcome')
            history.replaceState(history.state, '', url)
        }
        return { info, busy, shown, stateKind, stateText, sync, plural, goTab, welcome, closeWelcome }
    },
    template: `
    <div v-if="shown" class="bf-where">
        <!-- Just landed on your fork (Fork / Suggest changes): where to start -->
        <div v-if="welcome && info.is_fork && info.is_manager" class="bf-welcome">
            <button type="button" class="bf-welcome__x" @click="closeWelcome" aria-label="Close">×</button>
            <div class="bf-welcome__title"><i class="fa-solid fa-champagne-glasses me-2"></i>This is your copy — change it freely, the original is not touched.</div>
            <ol class="bf-welcome__steps">
                <li><b>Change it</b> — add or remove rules (Edit), arrange files and folders (Structure tab). To change a rule you don't own:
                    <a href="#" @click.prevent="goTab('compare')">Forks › Compare › “Change a rule you don't own”</a>.</li>
                <li><b>Check what you changed</b> — the sentence just below counts your changes; <a href="#" @click.prevent="goTab('compare')">Details</a> shows each one.</li>
                <li><b>Propose it</b> — click <b>Propose my changes</b>: the owner of the original reviews and merges what they want.</li>
            </ol>
        </div>
        <!-- Where you are: the family path, this bundle highlighted -->
        <div class="bf-where__path">
            <i class="fa-solid fa-code-fork bf-where__icon"></i>
            <template v-if="info.is_fork">
                <a v-if="info.upstream" :href="'/bundle/detail/' + info.upstream.id" class="bf-node">
                    <span class="bf-node__kind">Original</span><span class="bf-node__name">[[ info.upstream.name ]]</span>
                    <span class="bf-node__who">[[ info.upstream.owner ]]</span></a>
                <span v-else class="bf-node is-gone"><span class="bf-node__kind">Original</span><span class="bf-node__name">[[ info.upstream_hidden ? 'private' : 'deleted' ]]</span></span>
                <i class="fa-solid fa-arrow-right bf-where__arrow"></i>
            </template>
            <span class="bf-node is-here">
                <span class="bf-node__kind">[[ info.is_fork ? 'Fork' : 'Original' ]] · you are here</span>
                <span class="bf-node__name">this bundle</span>
                <span class="bf-node__who">[[ info.is_manager ? 'yours' : info.owner_name ]]</span></span>
            <template v-if="!info.is_fork && info.forks_count">
                <i class="fa-solid fa-arrow-right bf-where__arrow"></i>
                <button type="button" class="bf-node is-link" @click="goTab('forks')">
                    <span class="bf-node__kind">Forks</span><span class="bf-node__name">[[ plural(info.forks_count, 'copy', 'copies') ]]</span></button>
            </template>
        </div>

        <!-- One sentence: how it stands, and the one thing to do -->
        <div class="bf-where__state">
            <span class="bf-where__text" :class="'is-' + stateKind">[[ stateText ]]</span>
            <div class="bf-where__actions">
                <button v-if="info.is_fork && info.is_manager && info.behind" type="button" class="btn btn-sm btn-outline-primary rounded-pill" :disabled="busy" @click="sync">
                    <i class="fa-solid fa-download me-1"></i>Get the [[ plural(info.behind, 'update') ]]</button>
                <button v-if="info.is_fork && info.is_manager && info.ahead" type="button" class="btn btn-sm btn-primary rounded-pill"
                        :title="info.can_open_mr ? 'Write the merge request' : info.why_not_mr" @click="goTab('compare')">
                    <i class="fa-solid fa-paper-plane me-1"></i>[[ info.open_mr ? 'See my merge request' : 'Propose my changes' ]]</button>
                <button v-if="!info.is_fork && info.open_incoming" type="button" class="btn btn-sm btn-primary rounded-pill" @click="goTab('mrs')">
                    <i class="fa-solid fa-code-pull-request me-1"></i>Review</button>
                <button type="button" class="bf-link" @click="goTab(info.is_fork ? 'compare' : 'forks')">Details <i class="fa-solid fa-arrow-right"></i></button>
            </div>
        </div>

    </div>`,
}


// ── "Propose a merge request" card: in the page body and in Compare (like rule proposals) ──
export const BundleProposeCard = {
    name: 'BundleProposeCard',
    components: { SmartEditor },
    props: { bundleId: { type: [Number, String], required: true }, csrfToken: { type: String, default: '' } },
    emits: ['open-tab'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const info = shared.info
        const form = reactive({ title: '', message: '', busy: false })
        onMounted(() => loadInfo(props.bundleId))
        const shown = computed(() => {
            const i = info.value
            return !!(i && i.is_fork && i.upstream && i.is_manager && (i.ahead || i.open_mr))
        })
        const KIND_TEXT = { rule_added: 'Added rule', rule_removed: 'Removed rule', rule_modified: 'Changed rule', rule_moved: 'Moved rule',
                            file_added: 'Added file', file_removed: 'Removed file', file_modified: 'Changed file',
                            folder_added: 'Added folder', folder_removed: 'Removed folder', meta_description: 'Changed',
                            meta_tags: 'Changed', meta_vulnerabilities: 'Changed' }
        async function submit() {
            form.busy = true
            const out = await post(`/bundle/${props.bundleId}/merge_requests`, props.csrfToken, { title: form.title, message: form.message })
            form.busy = false
            if (out && out.url) window.location.href = out.url
        }
        const details = () => { shared.panel.value = 'compare'; emit('open-tab') }
        return { info, form, shown, submit, details, KIND_TEXT, plural }
    },
    template: `
    <div v-if="shown" class="bf-propose-card">
        <div class="bf-propose-card__icon"><i class="fa-solid fa-code-pull-request"></i></div>
        <div class="bf-propose-card__body">
            <!-- already proposed -->
            <template v-if="info.open_mr">
                <div class="bf-propose-card__title">Your merge request is waiting for review</div>
                <p class="bf-propose-card__text">« [[ info.open_mr.title ]] » — [[ plural(info.open_mr.counts.total, 'change') ]] proposed to
                    <b>[[ info.upstream.name ]]</b> on [[ info.open_mr.created_at ]]. Changes you make now are added to it.</p>
                <a :href="'/bundle/merge_request/' + info.open_mr.uuid" class="btn btn-primary rounded-pill px-4">
                    <i class="fa-solid fa-arrow-right me-1"></i>Go to the merge request</a>
            </template>
            <!-- changes to propose -->
            <template v-else>
                <div class="bf-propose-card__title">Propose your changes to the original</div>
                <p class="bf-propose-card__text">You changed <b>[[ plural(info.ahead, 'thing') ]]</b> in your copy. Send them to the owner of
                    <b>[[ info.upstream.name ]]</b>: they review each change and merge what they want.</p>
                <ul class="bf-propose-card__list">
                    <li v-for="c in info.ahead_items" :key="c.kind + c.label"><span class="bf-propose-card__kind">[[ KIND_TEXT[c.kind] || 'Changed' ]]</span>[[ c.label ]]</li>
                    <li v-if="info.ahead > info.ahead_items.length" class="text-muted">and [[ info.ahead - info.ahead_items.length ]] more —
                        <a href="#" @click.prevent="details">see them all</a></li>
                </ul>
                <label class="form-label fw-bold small mb-1">Title</label>
                <input class="form-control mb-2" v-model="form.title" maxlength="255" placeholder="What you changed — e.g. “Add the Tycoon 2FA kit, update the README”">
                <label class="form-label fw-bold small mb-1">Why <span class="text-muted fw-normal">— for the owner (Markdown)</span></label>
                <smart-editor v-model="form.message" mode="markdown" placeholder="Explain the changes, link reports…" min-height="110px" max-height="320px" :hardened-preview="true"></smart-editor>
                <div class="d-flex flex-wrap align-items-center gap-3 mt-3">
                    <button type="button" class="btn btn-primary btn-lg rounded-pill px-4" :disabled="form.busy || !info.can_open_mr" @click="submit">
                        <i class="fa-solid fa-paper-plane me-2"></i>Propose the merge request</button>
                    <a href="#" class="small" @click.prevent="details"><i class="fa-solid fa-code-compare me-1"></i>Review my changes first</a>
                    <small v-if="!info.can_open_mr" class="text-danger">[[ info.why_not_mr ]]</small>
                </div>
            </template>
        </div>
    </div>`,
}


BundleForksPanel.components.BundleProposeCard = BundleProposeCard
