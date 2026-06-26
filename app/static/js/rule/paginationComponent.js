// ── Inject styles once ────────────────────────────────────────────────────────
const _PAGINATION_STYLE_ID = 'rz-pagination-css'
if (!document.getElementById(_PAGINATION_STYLE_ID)) {
    const s = document.createElement('style')
    s.id = _PAGINATION_STYLE_ID
    s.textContent = `
.rz-pagination {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: .55rem;
    padding: 1rem 0;
    user-select: none;
}

/* ── Button row ── */
.rz-pg-row {
    display: flex;
    align-items: center;
    gap: 3px;
}

/* ── Base button ── */
.rz-pg-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 34px;
    height: 34px;
    padding: 0 10px;
    border-radius: 8px;
    border: 1px solid var(--border-color);
    background: var(--card-bg-color);
    color: var(--text-color);
    font-size: .8rem;
    font-weight: 500;
    cursor: pointer;
    transition: background .15s, border-color .15s, color .15s, transform .1s, box-shadow .15s;
    text-decoration: none;
    outline: none;
    font-family: inherit;
    line-height: 1;
    white-space: nowrap;
}
.rz-pg-btn:hover:not(.rz-pg-btn--active):not(.rz-pg-btn--disabled) {
    background: rgba(13,110,253,.09);
    border-color: rgba(13,110,253,.3);
    color: #0d6efd;
}
.rz-pg-btn:active:not(.rz-pg-btn--active):not(.rz-pg-btn--disabled) {
    transform: scale(.95);
}

/* ── Active page ── */
.rz-pg-btn--active {
    background: linear-gradient(135deg, #0d6efd, #0a58ca);
    border-color: transparent;
    color: #fff;
    font-weight: 700;
    box-shadow: 0 3px 10px rgba(13,110,253,.35);
    cursor: default;
}

/* ── Disabled (prev/next at bounds) ── */
.rz-pg-btn--disabled {
    opacity: .35;
    cursor: not-allowed;
    pointer-events: none;
}

/* ── Ellipsis ── */
.rz-pg-btn--ellipsis {
    border-color: transparent;
    background: transparent;
    color: var(--subtle-text-color);
    min-width: 28px;
    padding: 0 4px;
    letter-spacing: .1em;
}
.rz-pg-btn--ellipsis:hover {
    background: var(--light-bg-color) !important;
    border-color: var(--border-color) !important;
    color: #0d6efd !important;
}

/* ── Prev / Next wider pills ── */
.rz-pg-btn--nav {
    gap: 5px;
    padding: 0 14px;
    font-size: .78rem;
    border-radius: 10px;
}
.rz-pg-btn--nav i { font-size: .7rem; }

/* ── Separator dot between nav and numbers ── */
.rz-pg-sep {
    width: 1px;
    height: 18px;
    background: var(--border-color);
    margin: 0 5px;
    border-radius: 1px;
    flex-shrink: 0;
}

/* ── Info row (Page X of Y) ── */
.rz-pg-info {
    font-size: .72rem;
    color: var(--subtle-text-color);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: color .15s;
}
.rz-pg-info:hover { color: #0d6efd; }
.rz-pg-info i { font-size: .65rem; }

/* ── Jump input ── */
.rz-pg-jump {
    display: flex;
    align-items: center;
    gap: 6px;
    animation: rzPgFadeIn .15s ease;
}
@keyframes rzPgFadeIn {
    from { opacity: 0; transform: translateY(-4px); }
    to   { opacity: 1; transform: translateY(0); }
}
.rz-pg-jump-input {
    width: 60px;
    height: 30px;
    border: 1px solid rgba(13,110,253,.4);
    border-radius: 7px;
    background: var(--card-bg-color);
    color: var(--text-color);
    font-size: .8rem;
    text-align: center;
    outline: none;
    padding: 0 6px;
    font-family: inherit;
    transition: border-color .15s, box-shadow .15s;
}
.rz-pg-jump-input:focus {
    border-color: #0d6efd;
    box-shadow: 0 0 0 3px rgba(13,110,253,.15);
}
/* hide number spinners */
.rz-pg-jump-input::-webkit-outer-spin-button,
.rz-pg-jump-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.rz-pg-jump-input[type=number] { -moz-appearance: textfield; }

.rz-pg-jump-go {
    height: 30px;
    padding: 0 12px;
    border-radius: 7px;
    border: none;
    background: #0d6efd;
    color: #fff;
    font-size: .75rem;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: background .15s, transform .1s;
}
.rz-pg-jump-go:hover  { background: #0a58ca; }
.rz-pg-jump-go:active { transform: scale(.95); }
.rz-pg-jump-cancel {
    height: 30px;
    padding: 0 8px;
    border-radius: 7px;
    border: 1px solid var(--border-color);
    background: transparent;
    color: var(--subtle-text-color);
    font-size: .75rem;
    cursor: pointer;
    font-family: inherit;
    transition: background .15s;
}
.rz-pg-jump-cancel:hover { background: var(--light-bg-color); }
`
    document.head.appendChild(s)
}

// ── Component ─────────────────────────────────────────────────────────────────
export default {
    props: {
        currentPage: { type: Number, required: true },
        totalPages:  { type: Number, required: true },
    },
    emits: ['change-page'],
    delimiters: ['[[', ']]'],
    setup(props, { emit }) {
        const { ref, computed, watch } = Vue

        const inputPage = ref(props.currentPage)
        const isEditing = ref(false)

        watch(() => props.currentPage, v => { inputPage.value = v })

        const visiblePages = computed(() => {
            const total   = props.totalPages
            const current = props.currentPage
            const delta   = 2

            if (total <= 9) return Array.from({ length: total }, (_, i) => i + 1)

            const range = [1]
            const left  = current - delta
            const right = current + delta

            if (left > 2) range.push('...')

            for (let i = Math.max(2, left); i <= Math.min(total - 1, right); i++) {
                range.push(i)
            }

            if (right < total - 1) range.push('...')

            range.push(total)
            return range
        })

        function go(page) {
            if (page < 1 || page > props.totalPages || page === props.currentPage) return
            emit('change-page', page)
        }

        function goToPage() {
            const val = parseInt(inputPage.value)
            if (!isNaN(val) && val >= 1 && val <= props.totalPages) {
                go(val)
            } else {
                inputPage.value = props.currentPage
            }
            isEditing.value = false
        }

        function onEllipsisClick() {
            isEditing.value = !isEditing.value
            if (isEditing.value) inputPage.value = props.currentPage
        }

        return { visiblePages, inputPage, isEditing, go, goToPage, onEllipsisClick }
    },
    directives: {
        focus: {
            mounted(el) { el.focus(); el.select() }
        }
    },
    template: `
<nav v-if="totalPages > 1" class="rz-pagination" aria-label="Pagination">

    <div class="rz-pg-row">

        <!-- Previous -->
        <button class="rz-pg-btn rz-pg-btn--nav"
                :class="{ 'rz-pg-btn--disabled': currentPage === 1 }"
                @click="go(currentPage - 1)"
                :aria-disabled="currentPage === 1"
                aria-label="Previous page">
            <i class="fa-solid fa-chevron-left"></i>
            Prev
        </button>

        <div class="rz-pg-sep"></div>

        <!-- Page numbers -->
        <template v-for="(page, idx) in visiblePages" :key="idx">
            <button v-if="page !== '...'"
                    class="rz-pg-btn"
                    :class="{ 'rz-pg-btn--active': page === currentPage }"
                    @click="go(page)"
                    :aria-current="page === currentPage ? 'page' : undefined">
                [[ page ]]
            </button>
            <button v-else
                    class="rz-pg-btn rz-pg-btn--ellipsis"
                    @click="onEllipsisClick"
                    :title="isEditing ? 'Cancel jump' : 'Jump to page…'"
                    aria-label="Jump to page">
                ···
            </button>
        </template>

        <div class="rz-pg-sep"></div>

        <!-- Next -->
        <button class="rz-pg-btn rz-pg-btn--nav"
                :class="{ 'rz-pg-btn--disabled': currentPage === totalPages }"
                @click="go(currentPage + 1)"
                :aria-disabled="currentPage === totalPages"
                aria-label="Next page">
            Next
            <i class="fa-solid fa-chevron-right"></i>
        </button>
    </div>

    <!-- Jump to page input -->
    <div v-if="isEditing" class="rz-pg-jump">
        <input type="number"
               class="rz-pg-jump-input"
               v-model="inputPage"
               :min="1"
               :max="totalPages"
               placeholder="Page"
               @keyup.enter="goToPage"
               @keyup.escape="isEditing = false"
               v-focus />
        <button class="rz-pg-jump-go"  @click="goToPage">Go</button>
        <button class="rz-pg-jump-cancel" @click="isEditing = false">✕</button>
    </div>

    <!-- Page info -->
    <div v-else class="rz-pg-info" @click="isEditing = true" title="Click to jump to a page">
        Page <strong style="color:var(--text-color);">[[ currentPage ]]</strong>
        of <strong style="color:var(--text-color);">[[ totalPages ]]</strong>
        <i class="fa-solid fa-pen" style="opacity:.5;"></i>
    </div>

</nav>
`
}
