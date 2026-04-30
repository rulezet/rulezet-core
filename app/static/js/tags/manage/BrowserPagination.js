/**
 * BrowserPagination — compact pagination used in browser tabs.
 */
const BrowserPagination = {
    props: {
        current: { type: Number, required: true },
        total: { type: Number, required: true },
    },
    emits: ['change'],
    template: `
        <nav v-if="total > 1" class="d-flex justify-content-center mt-3">
            <ul class="pagination pagination-sm mb-0">
                <li class="page-item" :class="{ disabled: current <= 1 }">
                    <button class="page-link" @click="$emit('change', current - 1)">
                        <i class="fas fa-chevron-left"></i>
                    </button>
                </li>
                <li
                    v-for="p in visiblePages" :key="p"
                    class="page-item" :class="{ active: p === current, disabled: p === '…' }"
                >
                    <button class="page-link" @click="p !== '…' && $emit('change', p)">{{ p }}</button>
                </li>
                <li class="page-item" :class="{ disabled: current >= total }">
                    <button class="page-link" @click="$emit('change', current + 1)">
                        <i class="fas fa-chevron-right"></i>
                    </button>
                </li>
            </ul>
        </nav>
    `,
    computed: {
        visiblePages() {
            const pages = [];
            const { current, total } = this;
            if (total <= 7) {
                for (let i = 1; i <= total; i++) pages.push(i);
            } else {
                pages.push(1);
                if (current > 3) pages.push('…');
                for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) pages.push(i);
                if (current < total - 2) pages.push('…');
                pages.push(total);
            }
            return pages;
        }
    }
};

export default BrowserPagination;