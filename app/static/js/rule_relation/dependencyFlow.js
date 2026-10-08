/**
 * dependencyFlow.js — left-to-right dependency diagram of a rule.
 *
 *   Needed by (level n) … → Needed by → [ This rule ] → Needs → … Needs (level n)
 *
 * One column per level, one card per rule (full title, format, link), an
 * arrow from each rule to the rule it needs, labelled with the relation
 * type. Hovering a card highlights its whole chain back to this rule.
 *
 * Big graphs (a base rule needed by 150+ rules): each column shows its first
 * COLUMN_LIMIT cards and a "+N more" card to expand it; arrows arrive at /
 * leave from their own point along a card's edge instead of all piling up
 * on its middle; `search` highlights matching rules (and opens the columns
 * holding them).
 *
 * Props:
 *   nodes   [{id, title, format, role: self|requires|required_by, depth, via}]
 *   edges   [{from, to, type}]   — `from` needs `to`
 *   rootId  id of the rule the page is about
 *   search  optional text — rules whose title contains it are highlighted
 */
const { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } = Vue;

const COLUMN_LIMIT = 8;
const DENSE_EDGES = 40;         // above: faint arrows, long ones replaced by a "needs:" line
const LONG_EDGE_PX = 450;       // vertical run past which an arrow counts as long

const RELATION_LABELS = {
    yara_condition_ref: 'YARA condition',
    depends_on:         'depends on',
    if_sid:             'if_sid',
    if_matched_sid:     'if_matched_sid',
    if_group:           'if_group',
    if_matched_group:   'if_matched_group',
    rule_ref:           'rule()',
};

export default {
    name: 'DependencyFlow',
    delimiters: ['[[', ']]'],
    props: {
        nodes:  { type: Array, required: true },
        edges:  { type: Array, required: true },
        rootId: { type: Number, required: true },
        search: { type: String, default: '' },
    },
    setup(props) {
        const canvas  = ref(null);
        const cols    = ref(null);
        const nodeEls = new Map();
        const paths   = ref([]);
        const size    = ref({ w: 0, h: 0 });
        const hovered = ref(null);
        const expanded = ref(new Set());          // column keys shown in full
        let observer  = null;

        // ── Columns: needed-by levels on the left, needs levels on the right ──
        const byId = computed(() => Object.fromEntries(props.nodes.map(n => [n.id, n])));
        const columnKey = (n) => n.role === 'self' ? 0 : (n.role === 'requires' ? n.depth : -n.depth);

        const columns = computed(() => {
            const groups = {};
            for (const n of props.nodes) (groups[columnKey(n)] = groups[columnKey(n)] || []).push(n);
            const keys = Object.keys(groups).map(Number).sort((a, b) => a - b);
            // Order each column after its "via" (the rule it hangs from, one
            // column closer to the centre) — keeps arrows from crossing.
            const position = {};
            const ordered = {};
            const centreOut = [...keys].sort((a, b) => Math.abs(a) - Math.abs(b));
            for (const k of centreOut) {
                ordered[k] = [...groups[k]].sort((a, b) =>
                    ((position[a.via] ?? 0) - (position[b.via] ?? 0)) || a.title.localeCompare(b.title));
                ordered[k].forEach((n, i) => { position[n.id] = i; });
            }
            return keys.map(k => {
                const all = ordered[k];
                const open = expanded.value.has(k) || all.length <= COLUMN_LIMIT + 1;
                return {
                    key: k,
                    label: k === 0 ? 'This rule' : (k > 0 ? (k === 1 ? 'Needs' : `Needs · level ${k}`)
                                                      : (k === -1 ? 'Needed by' : `Needed by · level ${-k}`)),
                    side: k === 0 ? 'self' : (k > 0 ? 'requires' : 'required_by'),
                    nodes: all,
                    visible: open ? all : all.slice(0, COLUMN_LIMIT),
                    hidden: open ? 0 : all.length - COLUMN_LIMIT,
                    collapsible: all.length > COLUMN_LIMIT + 1,
                };
            });
        });

        function toggleColumn(key) {
            const next = new Set(expanded.value);
            const collapsing = next.has(key);
            collapsing ? next.delete(key) : next.add(key);
            expanded.value = next;
            // Collapsing shrinks the content under the current scroll
            // position — go back to the top instead of an empty area.
            if (collapsing) nextTick(() => { if (canvas.value) canvas.value.scrollTop = 0; });
        }

        // ── Search: matching rules, and open the columns that hold them ──
        const matches = computed(() => {
            const q = (props.search || '').trim().toLowerCase();
            if (!q) return null;
            return new Set(props.nodes.filter(n => n.title.toLowerCase().includes(q) || String(n.id) === q).map(n => n.id));
        });
        watch(matches, (m) => {
            if (!m || !m.size) return;
            const next = new Set(expanded.value);
            for (const c of columns.value) if (c.nodes.some(n => m.has(n.id))) next.add(c.key);
            expanded.value = next;
        });
        const columnOf = computed(() => {
            const m = {};
            columns.value.forEach((c, i) => c.nodes.forEach(n => { m[n.id] = i; }));
            return m;
        });

        // ── Hover: the hovered rule's chain back to this rule ────────────────
        const highlighted = computed(() => {
            if (hovered.value == null) return null;
            const set = new Set([hovered.value]);
            let cur = byId.value[hovered.value];
            while (cur && cur.via != null) { set.add(cur.via); cur = byId.value[cur.via]; }
            for (const e of props.edges) {                 // + its direct neighbours
                if (e.from === hovered.value) set.add(e.to);
                if (e.to === hovered.value) set.add(e.from);
            }
            return set;
        });
        const isDim = (id) => (highlighted.value && !highlighted.value.has(id))
            || (!highlighted.value && matches.value && !matches.value.has(id));
        const isMatch = (id) => !!(matches.value && matches.value.has(id));
        const edgeActive = (e) => highlighted.value && highlighted.value.has(e.from) && highlighted.value.has(e.to)
            && (e.from === hovered.value || e.to === hovered.value
                || byId.value[e.from]?.via === e.to || byId.value[e.to]?.via === e.from);

        // ── Arrows, measured from the rendered cards ─────────────────────────
        function setRef(id, el) { if (el) nodeEls.set(id, el); else nodeEls.delete(id); }

        function layoutEdges() {
            const root = canvas.value;
            if (!root) return;
            // Card rects are viewport-relative; the SVG scrolls with the
            // content — so convert with the canvas' own scroll offset, or
            // every arrow drifts once the canvas is scrolled (e.g. after
            // "+N more" made a column taller than the visible area).
            const box = root.getBoundingClientRect();
            const base = { left: box.left - root.scrollLeft, top: box.top - root.scrollTop };
            size.value = { w: root.scrollWidth, h: root.scrollHeight };
            // Each arrow gets its own point along the card edge it touches
            // (sorted by where the other end sits) — dozens of arrows on one
            // card no longer pile up into a single block.
            const drawn = [];
            for (const e of props.edges) {
                const a = nodeEls.get(e.from), b = nodeEls.get(e.to);
                if (!a || !b) continue;
                const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
                const forward = (columnOf.value[e.from] ?? 0) <= (columnOf.value[e.to] ?? 0);
                drawn.push({ e, ra, rb, forward });
            }
            const port = {};           // "id:side" -> [edge entries] sorted by the other end's y
            const addPort = (key, entry, otherY) => (port[key] = port[key] || []).push({ entry, otherY });
            for (const d of drawn) {
                addPort(`${d.e.from}:${d.forward ? 'r' : 'l'}`, d, d.rb.top + d.rb.height / 2);
                addPort(`${d.e.to}:${d.forward ? 'l' : 'r'}`, d, d.ra.top + d.ra.height / 2);
            }
            const offset = new Map();  // `${key}|${edgeKey}` -> y
            for (const [key, list] of Object.entries(port)) {
                const rect = key.split(':')[0] == list[0].entry.e.from ? list[0].entry.ra : list[0].entry.rb;
                list.sort((x, y) => x.otherY - y.otherY);
                const top = rect.top + rect.height * 0.2, span = rect.height * 0.6;
                list.forEach((it, i) => {
                    const y = list.length === 1 ? rect.top + rect.height / 2 : top + span * (i / (list.length - 1));
                    offset.set(`${key}|${it.entry.e.from}-${it.entry.e.to}`, y);
                });
            }
            const out = [];
            for (const { e, ra, rb, forward } of drawn) {
                const ek = `${e.from}-${e.to}`;
                const x1 = (forward ? ra.right : ra.left) - base.left;
                const x2 = (forward ? rb.left : rb.right) - base.left;
                const y1 = offset.get(`${e.from}:${forward ? 'r' : 'l'}|${ek}`) - base.top;
                const y2 = offset.get(`${e.to}:${forward ? 'l' : 'r'}|${ek}`) - base.top;
                const dx = Math.max(40, Math.abs(x2 - x1) / 2) * (forward ? 1 : -1);
                const side = byId.value[e.from]?.role === 'required_by' || byId.value[e.to]?.role === 'required_by'
                    ? 'required_by' : 'requires';
                out.push({
                    key: ek, edge: e, side, long: Math.abs(y2 - y1) > LONG_EDGE_PX,
                    d: `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`,
                    mx: (x1 + x2) / 2, my: (y1 + y2) / 2,
                    label: RELATION_LABELS[e.type] || e.type,
                });
            }
            paths.value = out;
        }

        const relayout = () => nextTick(() => requestAnimationFrame(layoutEdges));
        watch(() => [props.nodes, props.edges, expanded.value], relayout, { deep: true });
        onMounted(() => {
            relayout();
            observer = new ResizeObserver(relayout);
            if (canvas.value) observer.observe(canvas.value);   // frame: resize / full screen
            if (cols.value) observer.observe(cols.value);       // content: columns growing / shrinking
            window.addEventListener('resize', relayout);
        });
        onBeforeUnmount(() => {
            observer && observer.disconnect();
            window.removeEventListener('resize', relayout);
        });

        // Dense graph: arrows faint by default, a hovered chain at full strength,
        // and a long arrow (a rule far below the one it hangs from) not drawn
        // unless its chain is hovered — its card says "needs: …" instead.
        const dense = computed(() => paths.value.length > DENSE_EDGES);
        const shownPaths = computed(() => dense.value
            ? paths.value.filter(p => !p.long || edgeActive(p.edge)) : paths.value);
        const hiddenLinks = computed(() => {
            const m = {};
            if (!dense.value) return m;
            for (const p of paths.value) {
                if (!p.long || edgeActive(p.edge)) continue;
                const other = byId.value[p.edge.to];
                if (other) (m[p.edge.from] = m[p.edge.from] || []).push(other.title);
            }
            return m;
        });

        return { dense, shownPaths, hiddenLinks, canvas, cols, columns, paths, size, hovered, setRef, isDim, isMatch, edgeActive, highlighted, toggleColumn };
    },
    template: `
<div class="dflow" :class="{ 'dflow--dense': dense }">
  <div class="dflow__canvas" ref="canvas" @mouseleave="hovered = null">
    <svg class="dflow__edges" :width="size.w" :height="size.h" aria-hidden="true">
      <defs>
        <marker id="dflow-arrow-requires" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" class="dflow__arrow dflow__arrow--requires"></path>
        </marker>
        <marker id="dflow-arrow-required_by" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" class="dflow__arrow dflow__arrow--required_by"></path>
        </marker>
      </defs>
      <g v-for="p in shownPaths" :key="p.key">
        <path :d="p.d" :class="['dflow__edge', 'dflow__edge--' + p.side,
                                { 'is-active': edgeActive(p.edge), 'is-dim': highlighted && !edgeActive(p.edge) }]"
              :marker-end="'url(#dflow-arrow-' + p.side + ')'">
          <title>[[ p.label ]]</title>
        </path>
        <g v-if="edgeActive(p.edge) || paths.length <= 12" class="dflow__edge-label"
           :class="{ 'is-dim': highlighted && !edgeActive(p.edge) }"
           :transform="'translate(' + p.mx + ',' + p.my + ')'">
          <rect :x="-(p.label.length * 3.3 + 8)" y="-9" :width="p.label.length * 6.6 + 16" height="18" rx="9"></rect>
          <text text-anchor="middle" dy="4">[[ p.label ]]</text>
        </g>
      </g>
    </svg>

    <div class="dflow__cols" ref="cols">
      <div v-for="col in columns" :key="col.key" class="dflow__col" :class="'dflow__col--' + col.side">
        <div class="dflow__col-head">
          <i v-if="col.side === 'required_by'" class="fa-solid fa-arrow-right-to-bracket me-1"></i>
          <i v-else-if="col.side === 'requires'" class="fa-solid fa-arrow-right-from-bracket me-1"></i>
          <i v-else class="fa-solid fa-crosshairs me-1"></i>
          [[ col.label ]] <span class="dflow__col-count">[[ col.nodes.length ]]</span>
        </div>
        <a v-for="n in col.visible" :key="n.id" :ref="el => setRef(n.id, el)"
           :href="'/rule/detail_rule/' + n.id"
           class="dflow__node" :class="['dflow__node--' + n.role, { 'is-dim': isDim(n.id), 'is-hovered': hovered === n.id, 'is-match': isMatch(n.id) }]"
           :title="n.title"
           @mouseenter="hovered = n.id" @focus="hovered = n.id">
          <span class="dflow__node-format">[[ n.format ]]</span>
          <span class="dflow__node-title">[[ n.title ]]</span>
          <span v-if="hiddenLinks[n.id]" class="dflow__node-link" :title="'Needs: ' + hiddenLinks[n.id].join(', ')">
            <i class="fa-solid fa-arrow-right-long me-1"></i>needs: [[ hiddenLinks[n.id][0] ]]<template v-if="hiddenLinks[n.id].length > 1"> +[[ hiddenLinks[n.id].length - 1 ]]</template>
          </span>
        </a>
        <button v-if="col.hidden" type="button" class="dflow__more" @click="toggleColumn(col.key)">
          <i class="fa-solid fa-angles-down me-1"></i>+[[ col.hidden ]] more
        </button>
        <button v-else-if="col.collapsible" type="button" class="dflow__more" @click="toggleColumn(col.key)">
          <i class="fa-solid fa-angles-up me-1"></i>Show less
        </button>
      </div>
    </div>
  </div>
  <div class="dflow__legend">
    <span><i class="dflow__dot dflow__dot--required_by"></i>Needs this rule</span>
    <span><i class="dflow__dot dflow__dot--self"></i>This rule</span>
    <span><i class="dflow__dot dflow__dot--requires"></i>Needed by this rule</span>
    <span class="ms-auto"><i class="fa-solid fa-arrow-right-long me-1"></i>points to the rule it needs · hover a rule to follow its chain</span>
  </div>
</div>
`,
};
