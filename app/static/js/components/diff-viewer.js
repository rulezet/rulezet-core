/**
 * diff-viewer.js — Rich diff viewer component
 *
 * Props:
 *   initialLeft    String  initial content left pane   (default: '')
 *   initialRight   String  initial content right pane  (default: '')
 *   leftLabel      String  left pane label             (default: 'Original')
 *   rightLabel     String  right pane label            (default: 'Modified')
 *
 * Features:
 *   - Split (side-by-side) and unified view modes
 *   - Line-level LCS diff with intraline character highlighting
 *   - Synchronized scrolling in split mode
 *   - Hunk navigation (prev / next change block)
 *   - Customizable highlight colors + opacity sliders
 *   - JSON pretty-print helper per pane
 *   - File import via button or drag & drop
 *   - Copy diff as unified patch
 *   - Stats bar (additions, deletions, unchanged)
 *   - All colors via CSS custom properties — adapts to every theme
 *
 * Usage:
 *   import DiffViewer from '/static/js/components/diff-viewer.js'
 *
 *   <diff-viewer
 *       left-label="v1"
 *       right-label="v2"
 *       :initial-left="old_text"
 *       :initial-right="new_text">
 *   </diff-viewer>
 */

const { ref, computed, watch, onMounted, onUnmounted, nextTick } = Vue

// ── Escape helper ──────────────────────────────────────────────────────────────

function esc(s) {
    return String(s ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
}

function hex_to_rgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `rgba(${r},${g},${b},${alpha})`
}

// ── LCS diff engine ────────────────────────────────────────────────────────────

function lcs_diff(a, b) {
    const n = a.length, m = b.length
    if (n === 0 && m === 0) return []

    // Safety cap to avoid O(n*m) on huge inputs
    if (n * m > 500000) {
        return [
            ...a.map(v => ({ type: 'delete', v })),
            ...b.map(v => ({ type: 'insert', v })),
        ]
    }

    const dp = new Array(n + 1)
    for (let i = 0; i <= n; i++) dp[i] = new Int32Array(m + 1)
    for (let i = 1; i <= n; i++)
        for (let j = 1; j <= m; j++)
            dp[i][j] = a[i - 1] === b[j - 1]
                ? dp[i - 1][j - 1] + 1
                : Math.max(dp[i - 1][j], dp[i][j - 1])

    const ops = []
    let i = n, j = m
    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
            ops.unshift({ type: 'equal', v: a[i - 1] })
            i--; j--
        } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
            ops.unshift({ type: 'insert', v: b[j - 1] })
            j--
        } else {
            ops.unshift({ type: 'delete', v: a[i - 1] })
            i--
        }
    }
    return ops
}

function diff_lines(text_a, text_b, ignore_ws) {
    const a = text_a === '' ? [] : text_a.split('\n')
    const b = text_b === '' ? [] : text_b.split('\n')
    if (ignore_ws) {
        const na = a.map(l => l.trim())
        const nb = b.map(l => l.trim())
        const ops = lcs_diff(na, nb)
        let ai = 0, bi = 0
        return ops.map(op => {
            if (op.type === 'delete') return { type: 'delete', v: a[ai++] }
            if (op.type === 'insert') return { type: 'insert', v: b[bi++] }
            return { type: 'equal', v: a[ai++], vb: b[bi++] }
        })
    }
    return lcs_diff(a, b)
}

function diff_chars(a, b) {
    if (a.length * b.length > 30000) return null
    return lcs_diff([...a], [...b])
}

// Render one line as HTML, optionally with intraline char highlights
// function render_line_html(line, char_ops, side) {
//     if (!char_ops) return esc(line)
//     const parts = []
//     let run_type = null, run_buf = []

//     function flush() {
//         if (!run_buf.length) return
//         const text = esc(run_buf.join(''))
//         if (run_type === 'equal') {
//             parts.push(text)
//         } else if (run_type === 'insert' && side === 'right') {
//             parts.push(`<mark class="dv-mark-add">${text}</mark>`)
//         } else if (run_type === 'delete' && side === 'left') {
//             parts.push(`<mark class="dv-mark-del">${text}</mark>`)
//         } else {
//             parts.push(text)
//         }
//         run_type = null; run_buf = []
//     }

//     for (const op of char_ops) {
//         if (op.type !== run_type) flush()
//         run_type = op.type
//         run_buf.push(op.v)
//     }
//     flush()
//     return parts.join('')
// }

function render_line_html(line, char_ops, side) {
    if (!char_ops) return esc(line)

    const parts = []
    let run_type = null, run_buf = []

    function flush() {
        if (!run_buf.length) return
        const text = esc(run_buf.join(''))

        if (run_type === 'insert' && side === 'right') {
            parts.push(`<mark class="dv-mark-add">${text}</mark>`)
        } else if (run_type === 'delete' && side === 'left') {
            parts.push(`<mark class="dv-mark-del">${text}</mark>`)
        } else if (run_type === 'equal') {
            parts.push(text)
        }
        run_type = null; run_buf = []
    }

    for (const op of char_ops) {
        if (op.type !== run_type) flush()
        run_type = op.type
        run_buf.push(op.v)
    }
    flush()
    return parts.join('')
}

// ── Row builders ───────────────────────────────────────────────────────────────

function build_split_rows(ops) {
    const rows = []
    let ln = 1, rn = 1
    let i = 0

    while (i < ops.length) {
        const op = ops[i]

        if (op.type === 'equal') {
            rows.push({
                left_num: ln++, left_type: 'equal', left_marker: ' ', left_html: esc(op.v),
                right_num: rn++, right_type: 'equal', right_marker: ' ', right_html: esc(op.vb ?? op.v),
                is_hunk_start: false,
            })
            i++
            continue
        }

        const dels = [], ins = []
        while (i < ops.length && ops[i].type === 'delete') dels.push(ops[i++])
        while (i < ops.length && ops[i].type === 'insert') ins.push(ops[i++])

        const count = Math.max(dels.length, ins.length)
        for (let k = 0; k < count; k++) {
            const d = dels[k], ins_op = ins[k]
            const char_ops = (d && ins_op) ? diff_chars(d.v, ins_op.v) : null

            rows.push({
                left_num: d ? ln++ : null,
                left_type: d ? 'del' : 'empty',
                left_marker: d ? '-' : '',
                left_html: d ? render_line_html(d.v, char_ops, 'left') : '',

                right_num: ins_op ? rn++ : null,
                right_type: ins_op ? 'add' : 'empty',
                right_marker: ins_op ? '+' : '',
                right_html: ins_op ? render_line_html(ins_op.v, char_ops, 'right') : '',

                is_hunk_start: k === 0,
            })
        }
    }
    return rows
}

function build_unified_rows(ops) {
    const rows = []
    let ln = 1, rn = 1
    let i = 0

    while (i < ops.length) {
        const op = ops[i]

        if (op.type === 'equal') {
            rows.push({ type: 'equal', left_num: ln++, right_num: rn++, marker: ' ', html: esc(op.v) })
            i++
            continue
        }

        const dels = [], ins = []
        while (i < ops.length && ops[i].type === 'delete') dels.push(ops[i++])
        while (i < ops.length && ops[i].type === 'insert') ins.push(ops[i++])

        dels.forEach((d, k) => {
            const char_ops = ins[k] ? diff_chars(d.v, ins[k].v) : null
            rows.push({ type: 'del', left_num: ln++, right_num: null, marker: '-', html: render_line_html(d.v, char_ops, 'left') })
        })
        ins.forEach((ins_op, k) => {
            const char_ops = dels[k] ? diff_chars(dels[k].v, ins_op.v) : null
            rows.push({ type: 'add', left_num: null, right_num: rn++, marker: '+', html: render_line_html(ins_op.v, char_ops, 'right') })
        })
    }
    return rows
}

// ── Component ──────────────────────────────────────────────────────────────────

const DEFAULT_ADD = '#22c55e'
const DEFAULT_DEL = '#ef4444'

export default {
    name: 'DiffViewer',

    props: {
        initialLeft: { type: String, default: '' },
        initialRight: { type: String, default: '' },
        leftLabel: { type: String, default: 'Original' },
        rightLabel: { type: String, default: 'Modified' },
        mode: { type: String, default: 'read' },
    },

    template: `
    <div class="dv-root" :style="color_vars">

        <!-- ── Toolbar ─────────────────────────────────────────────────── -->
        <div class="dv-toolbar">

            <div class="dv-toolbar-left">
                <button class="dv-btn dv-btn--icon" :class="{ 'is-active': show_input }"
                    @click="show_input = !show_input" title="Toggle input panes">
                    <i class="fas fa-keyboard"></i>
                </button>
                <div class="dv-stats" v-if="stats.added || stats.removed">
                    <span class="dv-stat dv-stat--add"><i class="fas fa-plus"></i>{{ stats.added }}</span>
                    <span class="dv-stat dv-stat--del"><i class="fas fa-minus"></i>{{ stats.removed }}</span>
                    <span class="dv-stat dv-stat--eq"  v-if="stats.unchanged"><i class="fas fa-minus" style="opacity:.35"></i>{{ stats.unchanged }}</span>
                </div>
            </div>

            <div class="dv-toolbar-center">
                <div class="dv-view-toggle">
                    <button :class="['dv-view-btn', { 'is-active': view_mode === 'split' }]"
                        @click="view_mode = 'split'">
                        <i class="fas fa-table-columns"></i><span>Split</span>
                    </button>
                    <button :class="['dv-view-btn', { 'is-active': view_mode === 'unified' }]"
                        @click="view_mode = 'unified'">
                        <i class="fas fa-bars-staggered"></i><span>Unified</span>
                    </button>
                </div>
            </div>

            <div class="dv-toolbar-right">

                <button class="dv-btn dv-btn--sm" :class="{ 'is-active': ignore_ws }"
                    @click="ignore_ws = !ignore_ws" title="Ignore leading/trailing whitespace">
                    <i class="fas fa-text-width"></i><span>±ws</span>
                </button>

                <div class="dv-hunk-nav" v-if="hunk_positions.length">
                    <button class="dv-btn dv-btn--icon" @click="go_prev_hunk" title="Previous change">
                        <i class="fas fa-chevron-up"></i>
                    </button>
                    <span class="dv-hunk-counter">{{ cur_hunk + 1 }} / {{ hunk_positions.length }}</span>
                    <button class="dv-btn dv-btn--icon" @click="go_next_hunk" title="Next change">
                        <i class="fas fa-chevron-down"></i>
                    </button>
                </div>

                <div class="dv-settings-wrap" ref="settings_anchor">
                    <button class="dv-btn dv-btn--icon" :class="{ 'is-active': show_settings }"
                        @click="show_settings = !show_settings" title="Color settings">
                        <i class="fas fa-palette"></i>
                    </button>
                    <div v-if="show_settings" class="dv-settings-panel">
                        <div class="dv-sp-title">Highlight Colors</div>
                        <div class="dv-sp-row">
                            <label>Additions</label>
                            <input type="color" :value="add_hex" @input="add_hex = $event.target.value" />
                        </div>
                        <div class="dv-sp-row">
                            <label>Deletions</label>
                            <input type="color" :value="del_hex" @input="del_hex = $event.target.value" />
                        </div>
                        <div class="dv-sp-sep"></div>
                        <div class="dv-sp-title">Opacity</div>
                        <div class="dv-sp-row dv-sp-row--range">
                            <label>Line bg</label>
                            <input type="range" min="2" max="35" v-model.number="bg_opacity" class="dv-range" />
                            <span class="dv-sp-val">{{ bg_opacity }}%</span>
                        </div>
                        <div class="dv-sp-row dv-sp-row--range">
                            <label>Inline hl</label>
                            <input type="range" min="10" max="85" v-model.number="inline_opacity" class="dv-range" />
                            <span class="dv-sp-val">{{ inline_opacity }}%</span>
                        </div>
                        <button class="dv-btn dv-btn--sm dv-btn--block" @click="reset_colors">
                            <i class="fas fa-rotate-left"></i> Reset defaults
                        </button>
                    </div>
                </div>

                <button class="dv-btn dv-btn--icon" @click="copy_patch" title="Copy as unified patch">
                    <i class="fas fa-copy"></i>
                </button>

                <button class="dv-btn dv-btn--icon" @click="swap_sides" title="Swap left ↔ right">
                    <i class="fas fa-right-left"></i>
                </button>

            </div>
        </div>
        <template v-if="modes.includes('input')">
            <!-- ── Input panes ──────────────────────────────────────────────── -->
            <div class="dv-inputs" v-show="show_input">
                <!-- Left -->
                <div class="dv-input-pane">
                    <div class="dv-input-header">
                        <span class="dv-input-label">
                            <i class="fas fa-circle dv-dot dv-dot--del"></i>
                            {{ leftLabel }}
                        </span>
                        <div class="dv-input-actions">
                            <button class="dv-btn dv-btn--sm" @click="format_json('left')" title="Format as JSON">
                                <i class="fa-solid fa-code"></i>
                            </button>
                            <label class="dv-btn dv-btn--sm" title="Import file">
                                <i class="fas fa-file-import"></i>
                                <input type="file" style="display:none" @change="load_file('left', $event)" />
                            </label>
                            <button class="dv-btn dv-btn--sm" @click="left_text = ''" title="Clear">
                                <i class="fas fa-xmark"></i>
                            </button>
                        </div>
                    </div>
                    <textarea class="dv-textarea"
                        v-model="left_text"
                        :placeholder="'Paste ' + leftLabel + ' here or drop a file…'"
                        spellcheck="false"
                        @dragover.prevent="drag_left = true"
                        @dragleave.prevent="drag_left = false"
                        @drop.prevent="drop_file('left', $event)"
                        :class="{ 'dv-textarea--drag': drag_left }">
                    </textarea>
                    <div class="dv-input-footer">
                        <span>{{ line_count(left_text) }} lines</span>
                        <span>{{ left_text.length.toLocaleString() }} chars</span>
                    </div>
                </div>

                <!-- Right -->
                <div class="dv-input-pane">
                    <div class="dv-input-header">
                        <span class="dv-input-label">
                            <i class="fas fa-circle dv-dot dv-dot--add"></i>
                            {{ rightLabel }}
                        </span>
                        <div class="dv-input-actions">
                            <button class="dv-btn dv-btn--sm" @click="format_json('right')" title="Format as JSON">
                                <i class="fas fa-code"></i>
                            </button>
                            <label class="dv-btn dv-btn--sm" title="Import file">
                                <i class="fas fa-file-import"></i>
                                <input type="file" style="display:none" @change="load_file('right', $event)" />
                            </label>
                            <button class="dv-btn dv-btn--sm" @click="right_text = ''" title="Clear">
                                <i class="fas fa-xmark"></i>
                            </button>
                        </div>
                    </div>
                    <textarea class="dv-textarea"
                        v-model="right_text"
                        :placeholder="'Paste ' + rightLabel + ' here or drop a file…'"
                        spellcheck="false"
                        @dragover.prevent="drag_right = true"
                        @dragleave.prevent="drag_right = false"
                        @drop.prevent="drop_file('right', $event)"
                        :class="{ 'dv-textarea--drag': drag_right }">
                    </textarea>
                    <div class="dv-input-footer">
                        <span>{{ line_count(right_text) }} lines</span>
                        <span>{{ right_text.length.toLocaleString() }} chars</span>
                    </div>
                </div>
            </div>
        </template>

        <!-- ── Empty states ─────────────────────────────────────────────── -->
        <div v-if="is_empty" class="dv-empty">
            <i class="fas fa-code-compare dv-empty-icon"></i>
            <p class="dv-empty-title">No content yet</p>
            <p class="dv-empty-sub">Open the input panel <i class="fas fa-keyboard"></i> to paste or import texts</p>
        </div>

        <div v-else-if="is_identical" class="dv-empty dv-empty--ok">
            <i class="fas fa-circle-check dv-empty-icon"></i>
            <p class="dv-empty-title">Identical</p>
            <p class="dv-empty-sub">Both texts are exactly the same</p>
        </div>

        <!-- ── Split view ────────────────────────────────────────────────── -->
        <div v-else-if="view_mode === 'split'" class="dv-split-wrap">

            <div class="dv-pane" ref="left_pane_ref" @scroll="sync_scroll('left', $event)">
                <div class="dv-pane-label">
                    <i class="fas fa-circle dv-dot dv-dot--del"></i>{{ leftLabel }}
                </div>
                <div v-for="(row, idx) in split_rows" :key="'l'+idx"
                    class="dv-row"
                    :class="'dv-row--' + row.left_type"
                    :data-row-idx="idx">
                    <span class="dv-lnum">{{ row.left_num !== null ? row.left_num : '' }}</span>
                    <span class="dv-marker">{{ row.left_marker }}</span>
                    <pre class="dv-code" v-html="row.left_html"></pre>
                </div>
            </div>

            <div class="dv-split-gutter"></div>

            <div class="dv-pane" ref="right_pane_ref" @scroll="sync_scroll('right', $event)">
                <div class="dv-pane-label">
                    <i class="fas fa-circle dv-dot dv-dot--add"></i>{{ rightLabel }}
                </div>
                <div v-for="(row, idx) in split_rows" :key="'r'+idx"
                    class="dv-row"
                    :class="'dv-row--' + row.right_type">
                    <span class="dv-lnum">{{ row.right_num !== null ? row.right_num : '' }}</span>
                    <span class="dv-marker">{{ row.right_marker }}</span>
                    <pre class="dv-code" v-html="row.right_html"></pre>
                </div>
            </div>

        </div>

        <!-- ── Unified view ──────────────────────────────────────────────── -->
        <div v-else class="dv-unified-wrap" ref="unified_pane_ref">
            <div class="dv-unified-header">
                <span><i class="fas fa-circle dv-dot dv-dot--del"></i>{{ leftLabel }}</span>
                <span><i class="fas fa-circle dv-dot dv-dot--add"></i>{{ rightLabel }}</span>
            </div>
            <div v-for="(row, idx) in unified_rows" :key="idx"
                class="dv-row dv-unified-row"
                :class="'dv-row--' + row.type"
                :data-row-idx="idx">
                <span class="dv-lnum dv-lnum--a">{{ row.left_num  !== null ? row.left_num  : '' }}</span>
                <span class="dv-lnum dv-lnum--b">{{ row.right_num !== null ? row.right_num : '' }}</span>
                <span class="dv-marker">{{ row.marker }}</span>
                <pre class="dv-code" v-html="row.html"></pre>
            </div>
        </div>

    </div>
    `,

    setup(props) {

        // Mode
        // modes can be read only or input editable

        const modes = ref(props.mode)

        // ── Text state ────────────────────────────────────────────────────
        const left_text = ref(props.initialLeft)
        const right_text = ref(props.initialRight)
        const drag_left = ref(false)
        const drag_right = ref(false)

        // ── UI state ──────────────────────────────────────────────────────
        const view_mode = ref('split')
        const ignore_ws = ref(false)
        const show_input = ref(true)
        const show_settings = ref(false)
        const cur_hunk = ref(0)

        // ── Color customization ───────────────────────────────────────────
        const add_hex = ref(DEFAULT_ADD)
        const del_hex = ref(DEFAULT_DEL)
        const bg_opacity = ref(12)
        const inline_opacity = ref(42)

        const color_vars = computed(() => ({
            '--dv-add-bg': hex_to_rgba(add_hex.value, bg_opacity.value / 100),
            '--dv-add-inline': hex_to_rgba(add_hex.value, inline_opacity.value / 100),
            '--dv-add-text': add_hex.value,
            '--dv-del-bg': hex_to_rgba(del_hex.value, bg_opacity.value / 100),
            '--dv-del-inline': hex_to_rgba(del_hex.value, inline_opacity.value / 100),
            '--dv-del-text': del_hex.value,
        }))

        // ── Diff core ─────────────────────────────────────────────────────
        const raw_ops = computed(() => {
            if (!left_text.value && !right_text.value) return []
            return diff_lines(left_text.value, right_text.value, ignore_ws.value)
        })

        const split_rows = computed(() => build_split_rows(raw_ops.value))
        const unified_rows = computed(() => build_unified_rows(raw_ops.value))

        const stats = computed(() => {
            let added = 0, removed = 0, unchanged = 0
            for (const op of raw_ops.value) {
                if (op.type === 'insert') added++
                else if (op.type === 'delete') removed++
                else unchanged++
            }
            return { added, removed, unchanged }
        })

        const hunk_positions = computed(() =>
            split_rows.value
                .map((r, i) => r.is_hunk_start ? i : -1)
                .filter(i => i >= 0)
        )

        const is_empty = computed(() => left_text.value === '' && right_text.value === '')
        const is_identical = computed(() =>
            !is_empty.value &&
            raw_ops.value.length > 0 &&
            raw_ops.value.every(op => op.type === 'equal')
        )

        // ── Scroll sync ───────────────────────────────────────────────────
        const left_pane_ref = ref(null)
        const right_pane_ref = ref(null)
        const unified_pane_ref = ref(null)
        const settings_anchor = ref(null)
        const syncing = ref(false)

        function sync_scroll(side, e) {
            if (syncing.value) return
            syncing.value = true
            const other = side === 'left' ? right_pane_ref.value : left_pane_ref.value
            if (other) {
                other.scrollTop = e.target.scrollTop
                other.scrollLeft = e.target.scrollLeft
            }
            nextTick(() => { syncing.value = false })
        }

        // ── Hunk navigation ───────────────────────────────────────────────
        function go_next_hunk() {
            if (!hunk_positions.value.length) return
            cur_hunk.value = (cur_hunk.value + 1) % hunk_positions.value.length
            scroll_to_cur_hunk()
        }

        function go_prev_hunk() {
            if (!hunk_positions.value.length) return
            cur_hunk.value = (cur_hunk.value - 1 + hunk_positions.value.length) % hunk_positions.value.length
            scroll_to_cur_hunk()
        }

        async function scroll_to_cur_hunk() {
            await nextTick()
            const row_idx = hunk_positions.value[cur_hunk.value]
            if (row_idx === undefined) return

            const is_split = view_mode.value === 'split'
            const pane = is_split ? left_pane_ref.value : unified_pane_ref.value
            if (!pane) return

            const el = pane.querySelector(`[data-row-idx="${row_idx}"]`)
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }

        watch(raw_ops, () => { cur_hunk.value = 0 })

        // ── File I/O ──────────────────────────────────────────────────────
        function load_file(side, event) {
            const file = event.target.files?.[0]
            if (file) read_file(side, file)
            event.target.value = ''
        }

        function drop_file(side, event) {
            const file = event.dataTransfer?.files?.[0]
            if (file) read_file(side, file)
            drag_left.value = false
            drag_right.value = false
        }

        function read_file(side, file) {
            const reader = new FileReader()
            reader.onload = e => {
                if (side === 'left') left_text.value = e.target.result
                else right_text.value = e.target.result
            }
            reader.readAsText(file)
        }

        // ── JSON helper ───────────────────────────────────────────────────
        function format_json(side) {
            const text = side === 'left' ? left_text.value : right_text.value
            try {
                const pretty = JSON.stringify(JSON.parse(text), null, 2)
                if (side === 'left') left_text.value = pretty
                else right_text.value = pretty
            } catch { /* not valid JSON, silent */ }
        }

        // ── Utilities ─────────────────────────────────────────────────────
        function line_count(text) {
            return text === '' ? 0 : text.split('\n').length
        }

        function swap_sides() {
            const tmp = left_text.value
            left_text.value = right_text.value
            right_text.value = tmp
        }

        function reset_colors() {
            add_hex.value = DEFAULT_ADD
            del_hex.value = DEFAULT_DEL
            bg_opacity.value = 12
            inline_opacity.value = 42
        }

        function copy_patch() {
            const lines = [
                `--- ${props.leftLabel}`,
                `+++ ${props.rightLabel}`,
            ]
            for (const row of unified_rows.value) {
                const plain = row.html.replace(/<[^>]+>/g, '')
                lines.push(row.marker + plain)
            }
            navigator.clipboard?.writeText(lines.join('\n'))
        }

        // ── Outside click (close settings) ────────────────────────────────
        function on_doc_click(e) {
            if (settings_anchor.value && !settings_anchor.value.contains(e.target)) {
                show_settings.value = false
            }
        }

        onMounted(() => document.addEventListener('click', on_doc_click))
        onUnmounted(() => document.removeEventListener('click', on_doc_click))

        return {
            left_text, right_text, drag_left, drag_right,
            view_mode, ignore_ws, show_input, show_settings, modes,
            add_hex, del_hex, bg_opacity, inline_opacity, color_vars,
            raw_ops, split_rows, unified_rows, stats,
            hunk_positions, cur_hunk,
            is_empty, is_identical,
            left_pane_ref, right_pane_ref, unified_pane_ref, settings_anchor,
            sync_scroll, go_next_hunk, go_prev_hunk,
            load_file, drop_file, format_json,
            line_count, swap_sides, reset_colors, copy_patch,
        }
    },
}
