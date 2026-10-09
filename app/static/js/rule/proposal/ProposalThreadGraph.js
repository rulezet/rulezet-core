/**
 * ProposalThreadGraph — the versions of an edit-proposal thread drawn like
 * a git graph (VS Code "Git Graph"): every version is a branch of its own,
 * in its own column and colour, forking from the version it revises.
 *
 *   R─╮            Rule — state when the thread started  (rule column)
 *   │ ●─╮          v1  superseded
 *   │   ●─╮        v2  rejected   (revises v1)
 *   │     ●        v3  accepted   (revises v2)
 *   R─────╯        Merged into the rule
 *
 * Each node shows what happened to that version (rejected by…, merged
 * by…, superseded); clicking a version in the legend highlights its
 * lineage. Long threads are collapsed: a chain of intermediate decided
 * versions folds into one dashed "N versions" column.
 *
 * Used on the proposal discussion page (Thread section) and in the
 * "Threads" view of the Proposals page.
 *
 * Props:
 *   versions        [{ id, version, previous_proposal_id, status, user_id,
 *                      user_name, timestamp, discuss_url, message?,
 *                      reviewed_by_name?, reviewed_at?, rejection_reason?,
 *                      comment_count?, in_filter? }]
 *   current-id      the version being viewed → "You are here"
 *   current-user-id marks the viewer's own versions "you"
 *   rule-url        link of the rule rows (start / merge)
 *   compact         tighter rows, no justification line
 *   collapse-after  collapse when the thread has more versions than this
 *
 * Slot "row" (scoped { v }) — extra content at the end of a version's card.
 */

const BASE = '__base';
const MERGE = '__merge';
const PALETTE_SIZE = 8;

const time = v => new Date(v.timestamp || 0).getTime();

// Segments a lane cell can draw (all relative to the node's dot height):
// vfull (top→bottom), vtop (top→dot), vbot (dot→bottom),
// hleft (left edge→centre), hright (centre→right edge), hfull.
const seg = (k, c, dashed = false) => ({ k, c, dashed });

/**
 * Rows of the graph — { type: 'base' | 'version' | 'merge', v?, branch?,
 * cells: [{ segs, dot? }] } — and the branches.
 */
export function layoutThread(versions, { withRule = true } = {}) {
    const byId = new Map(versions.map(v => [v.id, v]));
    const children = new Map();
    const roots = [];
    for (const v of versions) {
        const parent = v.previous_proposal_id;
        if (parent && parent !== v.id && byId.has(parent)) {
            if (!children.has(parent)) children.set(parent, []);
            children.get(parent).push(v);
        } else {
            roots.push(v);
        }
    }
    const accepted = versions.find(v => v.status === 'accepted') || null;

    // ── Branches (one per version) and display order: depth-first, a
    //    version then the revisions made from it, oldest first
    const branches = [];
    const branchOf = new Map();
    const order = [];
    const visited = new Set();
    function newBranch(first, from) {
        const b = { index: branches.length, first, from, versions: [] };
        b.name = first.isGap ? `v${first.version}–v${first.lastVersion}` : `v${first.version}`;
        branches.push(b);
        return b;
    }
    function walk(v, branch) {
        if (visited.has(v.id)) return;
        visited.add(v.id);
        branchOf.set(v.id, branch);
        branch.versions.push(v);
        const forks = (children.get(v.id) || []).slice().sort((a, b) => time(a) - time(b));
        order.push({ v, main: null, forks, branch });
        forks.forEach(f => walk(f, newBranch(f, v)));
    }
    const sortedRoots = roots.slice().sort((a, b) => time(a) - time(b));
    sortedRoots.forEach(r => walk(r, newBranch(r, null)));
    // a cycle in corrupted links: show the leftovers as their own branches
    versions.filter(v => !visited.has(v.id)).forEach(v => walk(v, newBranch(v, null)));

    // ── Lanes. active[col] = key of the node the edge in that column leads
    //    to; colour[col] = colour of that edge (branch index, 'rule').
    const active = [];
    const colour = [];
    const firstLane = withRule ? 1 : 0;
    const freeCol = (min) => { let c = min; while (active[c] !== undefined) c++; return c; };
    const snapshot = () => active.map((k, c) => (k !== undefined ? { c, colour: colour[c] } : null)).filter(Boolean);
    const rows = [];
    let width = 1;

    // cells of a row: the node's dot in `col`, lines passing through, and
    // horizontal links from the dot to `links` (forks out / joins in)
    function buildCells({ col, dot, passing, forks = [], joins = [] }) {
        const linkCols = [...forks.map(f => f.c), ...joins.map(j => j.c)];
        const far = linkCols.length ? Math.max(...linkCols) : -1;
        const pass = new Map(passing.map(p => [p.c, p.colour]));
        const maxCol = Math.max(col, far, ...pass.keys(), 0);
        const linkColour = (c) => {           // colour of the link crossing column c
            const l = [...forks, ...joins].filter(x => x.c >= c).sort((a, b) => a.c - b.c)[0];
            return l ? l.colour : dot.colour;
        };
        const cells = [];
        for (let c = 0; c <= maxCol; c++) {
            const segs = [];
            let dotHere = null;
            const fork = forks.find(f => f.c === c);
            const join = joins.find(j => j.c === c);
            if (c === col) {
                if (dot.up) segs.push(seg('vtop', dot.upColour ?? dot.colour));
                if (dot.down) segs.push(seg('vbot', dot.downColour ?? dot.colour));
                if (far > col) segs.push(seg('hright', linkColour(c + 1)));
                dotHere = dot;
            } else if (fork) {
                segs.push(seg('hleft', fork.colour), seg('vbot', fork.colour));
                if (c < far) segs.push(seg('hright', linkColour(c + 1)));
                if (pass.has(c)) segs.push(seg('vtop', pass.get(c)));
            } else if (join) {
                segs.push(seg('vtop', join.colour), seg('hleft', join.colour));
                if (c < far) segs.push(seg('hright', linkColour(c + 1)));
            } else {
                if (pass.has(c)) segs.push(seg('vfull', pass.get(c)));
                if (c > col && c < far) segs.push(seg('hfull', linkColour(c)));
            }
            cells.push({ segs, dot: dotHere });
        }
        width = Math.max(width, cells.length);
        return cells;
    }

    if (withRule) {
        const forks = sortedRoots.map(r => {
            const c = freeCol(firstLane);
            active[c] = r.id;
            colour[c] = branchOf.get(r.id).index;
            return { c, colour: colour[c] };
        });
        if (accepted) { active[0] = MERGE; colour[0] = 'rule'; }
        rows.push({ type: 'base', key: BASE, cells: buildCells({
            col: 0, passing: [], forks,
            dot: { colour: 'rule', kind: 'rule', up: false, down: !!accepted },
        }) });
    }

    for (const { v, main, forks, branch } of order) {
        const incoming = active.map((k, c) => (k === v.id ? c : -1)).filter(c => c >= 0);
        const col = incoming.length ? incoming[0] : freeCol(firstLane);
        const upColour = incoming.length ? colour[col] : null;
        incoming.forEach(c => { active[c] = undefined; });
        const passing = snapshot();

        let down = false;
        if (main) {
            active[col] = main.id; colour[col] = branch.index; down = true;
        } else if (withRule && accepted && v.id === accepted.id) {
            active[col] = MERGE; colour[col] = branch.index; down = true;
        }
        const forkLinks = forks.map(f => {
            const c = freeCol(col + 1);
            active[c] = f.id;
            colour[c] = branchOf.get(f.id).index;
            return { c, colour: colour[c] };
        });
        rows.push({
            type: 'version', key: v.id, v, branch,
            cells: buildCells({
                col, passing, forks: forkLinks,
                dot: { colour: branch.index, kind: 'version', status: v.status,
                       up: incoming.length > 0, upColour, down },
            }),
        });
    }

    if (withRule && accepted) {
        const incoming = active.map((k, c) => (k === MERGE ? c : -1)).filter(c => c >= 0);
        const joins = incoming.filter(c => c !== 0).map(c => ({ c, colour: colour[c] }));
        incoming.forEach(c => { active[c] = undefined; });
        rows.push({ type: 'merge', key: MERGE, v: accepted, branch: branchOf.get(accepted.id), cells: buildCells({
            col: 0, passing: snapshot(), joins,
            dot: { colour: 'rule', kind: 'rule', up: true, down: false },
        }) });
    }
    return { rows, width, branches };
}

// Long threads: a chain of ≥2 intermediate versions — decided (not pending
// or accepted), not the current one, revised exactly once — folds into one
// "gap" version standing for the whole chain.
function collapseVersions(versions, currentId, statusKey) {
    const byId = new Map(versions.map(v => [v.id, v]));
    const kids = new Map();
    for (const v of versions) {
        if (byId.has(v.previous_proposal_id)) {
            if (!kids.has(v.previous_proposal_id)) kids.set(v.previous_proposal_id, []);
            kids.get(v.previous_proposal_id).push(v);
        }
    }
    const foldable = v => v.id !== currentId && byId.has(v.previous_proposal_id)
        && !['pending', 'accepted'].includes(statusKey(v)) && (kids.get(v.id) || []).length === 1;
    const hidden = new Set();
    const reparent = new Map();          // id → gap id it now revises
    const gaps = [];
    for (const v of versions) {
        if (!foldable(v) || foldable(byId.get(v.previous_proposal_id))) continue;   // start of a chain only
        const run = [v];
        while (foldable(kids.get(run[run.length - 1].id)[0])) run.push(kids.get(run[run.length - 1].id)[0]);
        if (run.length < 2) continue;
        const last = run[run.length - 1];
        const gap = {
            id: -v.id, isGap: true, count: run.length,
            version: v.version, lastVersion: last.version,
            previous_proposal_id: v.previous_proposal_id, timestamp: v.timestamp,
            status: 'gap', authors: [...new Set(run.map(x => x.user_name))],
        };
        run.forEach(x => hidden.add(x.id));
        reparent.set(kids.get(last.id)[0].id, gap.id);
        gaps.push(gap);
    }
    if (!gaps.length) return versions;
    return [
        ...versions.filter(v => !hidden.has(v.id))
            .map(v => (reparent.has(v.id) ? { ...v, previous_proposal_id: reparent.get(v.id) } : v)),
        ...gaps,
    ];
}

const ProposalThreadGraph = {
    name: 'ProposalThreadGraph',
    delimiters: ['[[', ']]'],
    props: {
        versions:      { type: Array, required: true },
        currentId:     { type: Number, default: null },
        currentUserId: { type: Number, default: null },
        ruleUrl:       { type: String, default: null },
        compact:       { type: Boolean, default: false },
        collapseAfter: { type: Number, default: 6 },
    },
    data() {
        return { expandedAll: false, focus: null };
    },
    computed: {
        collapsible() { return this.versions.length > this.collapseAfter; },
        graphVersions() {
            return this.collapsible && !this.expandedAll
                ? collapseVersions(this.versions, this.currentId, v => this.statusKey(v))
                : this.versions;
        },
        layout() { return layoutThread(this.graphVersions); },
        displayRows() { return this.layout.rows; },
        versionById() { return new Map(this.graphVersions.map(v => [v.id, v])); },
        // Focused version: its ancestors and descendants stay bright.
        lineage() {
            if (this.focus === null) return null;
            const ids = new Set([this.focus]);
            let v = this.versionById.get(this.focus);
            while (v && this.versionById.has(v.previous_proposal_id) && !ids.has(v.previous_proposal_id)) {
                ids.add(v.previous_proposal_id);
                v = this.versionById.get(v.previous_proposal_id);
            }
            let grew = true;
            while (grew) {
                grew = false;
                for (const x of this.graphVersions) {
                    if (!ids.has(x.id) && ids.has(x.previous_proposal_id) && this.isDescendant(x.id)) { ids.add(x.id); grew = true; }
                }
            }
            return ids;
        },
    },
    methods: {
        colourClass(c) { return c === 'rule' ? 'ptg-c-rule' : 'ptg-c-' + (c % PALETTE_SIZE); },
        statusKey(v) {
            if (!v) return 'pending';
            if (v.status === 'superseded'
                || (v.status === 'rejected' && (v.revisions || []).some(r => r.status === 'accepted'))) return 'superseded';
            return ['pending', 'accepted', 'rejected'].includes(v.status) ? v.status : 'pending';
        },
        parentVersion(v) {
            const p = this.versionById.get(v.previous_proposal_id);
            return p ? (p.isGap ? p.lastVersion : `${p.version} #${p.id}`) : null;
        },
        firstLine(text) {
            const line = String(text || '').split('\n').map(l => l.replace(/^[#>*\-\s]+/, '').trim()).find(Boolean) || '';
            return line.replace(/(\*\*|`|~~)/g, '');
        },
        date(ts) {
            return ts ? new Date(ts).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '';
        },
        go(v) {
            if (v && v.id !== this.currentId && v.discuss_url) window.location.href = v.discuss_url;
        },
        goRule() { if (this.ruleUrl) window.location.href = this.ruleUrl; },
        toggleFocus(id) { this.focus = this.focus === id ? null : id; },
        isDescendant(id) {
            let v = this.versionById.get(id);
            const seen = new Set();
            while (v && !seen.has(v.id)) {
                if (v.id === this.focus) return true;
                seen.add(v.id);
                v = this.versionById.get(v.previous_proposal_id);
            }
            return false;
        },
        isFaded(row) {
            if (row.type === 'version' && row.v.in_filter === false) return true;
            if (!this.lineage) return false;
            if (row.type === 'version') return !this.lineage.has(row.v.id);
            return row.type === 'merge' ? !this.lineage.has(row.v.id) : false;
        },
    },
    template: `
    <div class="ptg" :class="{ 'ptg--compact': compact }">

        <!-- Legend: one chip per branch (version) — click to highlight its lineage -->
        <div v-if="layout.branches.length > 1 || collapsible" class="ptg-legend">
            <button v-for="b in layout.branches" :key="b.index" type="button" class="ptg-branch-chip"
                :class="[colourClass(b.index), { 'is-focus': focus === b.first.id, 'is-dim': lineage && !lineage.has(b.first.id) }]"
                @click="b.first.isGap ? (expandedAll = true) : toggleFocus(b.first.id)"
                :title="b.first.isGap ? 'Show these versions' : 'Highlight the lineage of ' + b.name">
                <span class="ptg-branch-swatch"></span>
                <span class="fw-bold">[[ b.name ]]</span>
                <span v-if="!b.first.isGap" class="ptg-id ptg-branch-info">#[[ b.first.id ]]</span>
                <template v-if="b.first.isGap"><span class="ptg-branch-info">[[ b.first.count ]] versions folded</span></template>
                <template v-else>
                    <span class="ptg-status" :class="'ptg-status--' + statusKey(b.first)">[[ statusKey(b.first) ]]</span>
                    <span class="ptg-branch-info">[[ b.first.user_name ]]<template v-if="b.from"> · from [[ b.from.isGap ? 'v' + b.from.lastVersion : 'v' + b.from.version + ' #' + b.from.id ]]</template></span>
                </template>
            </button>
            <button v-if="collapsible" type="button" class="ptg-expand-all" @click="expandedAll = !expandedAll">
                <i class="fa-solid" :class="expandedAll ? 'fa-compress' : 'fa-expand'"></i>
                [[ expandedAll ? 'Collapse' : 'Show every version' ]]
            </button>
        </div>

        <div v-for="row in displayRows" :key="row.key" class="ptg-row" :class="['ptg-row--' + row.type, {
                'is-current': row.v && row.type === 'version' && row.v.id === currentId, 'is-faded': isFaded(row) }]">
            <div class="ptg-lanes" :style="{ width: 'calc(var(--ptg-cell) * ' + layout.width + ')' }">
                <span v-for="(cell, c) in row.cells" :key="c" class="ptg-cell">
                    <span v-for="(s, i) in cell.segs" :key="i" class="ptg-seg"
                        :class="['ptg-seg--' + s.k, colourClass(s.c), { 'is-dashed': s.dashed }]"></span>
                    <span v-if="cell.dot" class="ptg-dot"
                        :class="[colourClass(cell.dot.colour), cell.dot.kind === 'rule' ? 'ptg-dot--rule' : row.v.isGap ? 'ptg-dot--gap' : 'ptg-dot--' + statusKey(row.v)]">
                        <i v-if="cell.dot.kind === 'rule'" class="fa-solid" :class="row.type === 'merge' ? 'fa-code-merge' : 'fa-file-code'"></i>
                    </span>
                </span>
            </div>

            <!-- Rule at thread start -->
            <div v-if="row.type === 'base'" class="ptg-card ptg-card--rule" :class="{ 'is-link': ruleUrl }" @click="goRule">
                <div class="ptg-head">
                    <span class="ptg-version">Rule</span>
                    <span class="ptg-meta">state when the thread started — every branch starts from here</span>
                </div>
            </div>

            <!-- Merge back into the rule -->
            <div v-else-if="row.type === 'merge'" class="ptg-card ptg-card--rule" :class="{ 'is-link': ruleUrl }" @click="goRule">
                <div class="ptg-head">
                    <span class="ptg-version ptg-merged-title"><i class="fa-solid fa-code-merge me-1"></i>Merged into the rule</span>
                    <span class="ptg-meta">
                        v[[ row.v.version ]]
                        <template v-if="row.v.reviewed_by_name"> · by [[ row.v.reviewed_by_name ]]</template>
                        <template v-if="row.v.reviewed_at"> · [[ date(row.v.reviewed_at) ]]</template>
                    </span>
                </div>
            </div>

            <!-- Folded chain of versions -->
            <div v-else-if="row.v.isGap" class="ptg-card ptg-card--gap" @click="expandedAll = true">
                <i class="fa-solid fa-ellipsis me-1"></i>
                v[[ row.v.version ]] → v[[ row.v.lastVersion ]]: [[ row.v.count ]] versions rejected or closed
                · [[ row.v.authors.join(', ') ]]
                <span class="ptg-gap-link">Show</span>
            </div>

            <!-- A version -->
            <div v-else class="ptg-card" role="link" tabindex="0" @click="go(row.v)" @keydown.enter="go(row.v)"
                 :title="row.v.id === currentId ? 'You are here' : 'Open v' + row.v.version + ' (#' + row.v.id + ')'">
                <div class="ptg-head">
                    <span class="ptg-version">v[[ row.v.version ]]</span>
                    <span class="ptg-status" :class="'ptg-status--' + statusKey(row.v)">[[ statusKey(row.v) ]]</span>
                    <span v-if="row.v.id === currentId" class="ptg-here"><i class="fa-solid fa-location-dot"></i>You are here</span>
                    <span v-if="currentUserId && row.v.user_id === currentUserId" class="ptg-tag ptg-tag--you">you</span>
                    <span class="ptg-meta">
                        <span class="ptg-author">[[ row.v.user_name ]]</span>
                        · [[ date(row.v.timestamp) ]]
                        <template v-if="parentVersion(row.v)"> · revises v[[ parentVersion(row.v) ]]</template>
                        · <span class="ptg-id">#[[ row.v.id ]]</span>
                        <template v-if="row.v.comment_count"> · <i class="fa-regular fa-comment"></i> [[ row.v.comment_count ]]</template>
                    </span>
                </div>
                <div v-if="!compact && firstLine(row.v.message)" class="ptg-message">[[ firstLine(row.v.message) ]]</div>

                <!-- What happened to this version -->
                <div class="ptg-event" :class="'ptg-event--' + statusKey(row.v)">
                    <template v-if="statusKey(row.v) === 'pending'"><i class="fa-solid fa-hourglass-half"></i>Waiting for review</template>
                    <template v-else-if="statusKey(row.v) === 'accepted'">
                        <i class="fa-solid fa-code-merge"></i>Merged<template v-if="row.v.reviewed_by_name"> by [[ row.v.reviewed_by_name ]]</template>
                        <template v-if="row.v.reviewed_at"> · [[ date(row.v.reviewed_at) ]]</template>
                        <span v-if="row.v.rejection_reason" class="ptg-reason" :title="row.v.rejection_reason">— “[[ row.v.rejection_reason ]]”</span>
                    </template>
                    <template v-else-if="statusKey(row.v) === 'superseded'"><i class="fa-solid fa-ban"></i>Closed — another version of the thread was merged</template>
                    <template v-else>
                        <i class="fa-solid fa-circle-xmark"></i>Rejected<template v-if="row.v.reviewed_by_name"> by [[ row.v.reviewed_by_name ]]</template>
                        <template v-if="row.v.reviewed_at"> · [[ date(row.v.reviewed_at) ]]</template>
                        <span v-if="row.v.rejection_reason" class="ptg-reason" :title="row.v.rejection_reason">— “[[ row.v.rejection_reason ]]”</span>
                    </template>
                </div>
                <div v-if="$slots.row" class="ptg-extra" @click.stop><slot name="row" :v="row.v"></slot></div>
            </div>
        </div>
    </div>
    `,
};

export default ProposalThreadGraph;
