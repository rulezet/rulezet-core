const { computed } = Vue

export default {
    name: 'Pagination',

    props: {
        currentPage:  { type: Number, required: true },
        totalPages:   { type: Number, required: true },
        maxVisible:   { type: Number, default: 7 },
    },

    emits: ['change-page'],

    template: `
        <nav v-if="totalPages > 1" class="pag-wrapper" aria-label="Pagination">

            <!-- Prev -->
            <button
                class="pag-btn"
                :class="{ 'pag-btn--disabled': currentPage <= 1 }"
                :disabled="currentPage <= 1"
                @click="go(currentPage - 1)"
                aria-label="Previous page">
                <i class="fas fa-chevron-left" style="font-size:.65rem;"></i>
            </button>

            <!-- Page buttons -->
            <template v-for="item in pages" :key="item.key">
                <span v-if="item.ellipsis" class="pag-ellipsis">…</span>
                <button
                    v-else
                    class="pag-btn"
                    :class="{ 'pag-btn--active': item.page === currentPage }"
                    :aria-current="item.page === currentPage ? 'page' : undefined"
                    @click="go(item.page)">
                    {{ item.page }}
                </button>
            </template>

            <!-- Next -->
            <button
                class="pag-btn"
                :class="{ 'pag-btn--disabled': currentPage >= totalPages }"
                :disabled="currentPage >= totalPages"
                @click="go(currentPage + 1)"
                aria-label="Next page">
                <i class="fas fa-chevron-right" style="font-size:.65rem;"></i>
            </button>

        </nav>
    `,

    setup(props, { emit }) {
        const pages = computed(() => {
            const total = props.totalPages
            const cur   = props.currentPage
            const max   = props.maxVisible

            if (total <= max) {
                return Array.from({ length: total }, (_, i) => ({ page: i + 1, key: i + 1 }))
            }

            const half  = Math.floor((max - 2) / 2)
            const items = []

            const showLeadingEllipsis  = cur > half + 2
            const showTrailingEllipsis = cur < total - half - 1

            items.push({ page: 1, key: 1 })

            if (showLeadingEllipsis) {
                items.push({ ellipsis: true, key: 'el-start' })
            }

            const rangeStart = showLeadingEllipsis
                ? (showTrailingEllipsis ? cur - half : total - (max - 3))
                : 2
            const rangeEnd = showTrailingEllipsis
                ? (showLeadingEllipsis ? cur + half : max - 2)
                : total - 1

            for (let p = rangeStart; p <= rangeEnd; p++) {
                if (p > 1 && p < total) {
                    items.push({ page: p, key: p })
                }
            }

            if (showTrailingEllipsis) {
                items.push({ ellipsis: true, key: 'el-end' })
            }

            items.push({ page: total, key: total })

            return items
        })

        function go(page) {
            if (page < 1 || page > props.totalPages || page === props.currentPage) return
            emit('change-page', page)
        }

        return { pages, go }
    }
}
