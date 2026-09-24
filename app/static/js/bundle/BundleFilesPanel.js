/**
 * BundleFilesPanel.js — "Files & documents" section of the bundle detail page.
 *
 * Lists every non-rule file of the bundle (README.md, notes.txt, *.json…)
 * in one place. Built to stay usable with hundreds of files: text search,
 * per-extension filter chips with counts, and client-side pagination.
 *
 * Props:
 *   files     Array   flat list from flattenFiles() — rule files are ignored
 *
 * Emits:
 *   open(file)  — user clicked a file (parent opens BundleFileViewer)
 *
 * Expose:
 *   focus(file) — clear filters, jump to the page holding that file and flash it
 */

import PaginationComponent from '/static/js/rule/paginationComponent.js'
import { extOf, docIcon, downloadText, formatBytes } from '/static/js/bundle/bundleFileTypes.js'

const { ref, computed, watch, nextTick } = Vue

const PER_PAGE = 12

export default {
    name: 'BundleFilesPanel',
    components: { PaginationComponent },

    props: {
        files:    { type: Array, default: () => [] },
    },

    emits: ['open'],
    expose: ['focus'],

    template: `
    <div class="bfp-root" ref="rootEl">
        <div class="bfp-toolbar">
            <div class="bfp-search">
                <i class="fa-solid fa-magnifying-glass"></i>
                <input type="text" v-model="query" placeholder="Search files by name or folder…">
                <button v-if="query" type="button" class="bfp-search-clear" @click="query = ''" title="Clear">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
        </div>

        <div v-if="extCounts.length > 1" class="bfp-chips">
            <button type="button" class="bfp-chip" :class="{ active: !extFilter }" @click="extFilter = ''">
                All <span class="bfp-chip-count">{{ docs.length }}</span>
            </button>
            <button v-for="e in extCounts" :key="e.ext" type="button" class="bfp-chip"
                    :class="{ active: extFilter === e.ext }" @click="extFilter = extFilter === e.ext ? '' : e.ext">
                <i :class="docIcon('x.' + e.ext).icon" :style="{ color: docIcon('x.' + e.ext).color }"></i>
                .{{ e.ext || '?' }} <span class="bfp-chip-count">{{ e.count }}</span>
            </button>
        </div>

        <div v-if="!filtered.length" class="bfp-empty">
            <i class="fa-regular fa-folder-open"></i> No file matches your search.
        </div>

        <ul v-else class="bfp-list">
            <li v-for="f in pageItems" :key="f.id" class="bfp-item" :data-bfp-id="f.id"
                :class="{ 'bfp-item--flash': flashId === f.id }" @click="$emit('open', f)"
                tabindex="0" @keydown.enter="$emit('open', f)">
                <span class="bfp-item-icon" :style="{ color: docIcon(f.name).color, background: docIcon(f.name).color + '1a' }">
                    <i :class="docIcon(f.name).icon"></i>
                </span>
                <span class="bfp-item-main">
                    <span class="bfp-item-name" :title="f.name">{{ f.name }}</span>
                    <span class="bfp-item-path" :title="f.folder || '/'">
                        <i class="fa-solid fa-folder me-1"></i>{{ f.folder || '/' }}
                    </span>
                </span>
                <span class="bfp-item-size">{{ formatBytes(f.content) }}</span>
                <button type="button" class="bfp-item-btn" title="Open" @click.stop="$emit('open', f)">
                    <i class="fa-solid fa-eye"></i>
                </button>
                <button type="button" class="bfp-item-btn" title="Download" @click.stop="downloadOne(f)">
                    <i class="fa-solid fa-download"></i>
                </button>
            </li>
        </ul>

        <div v-if="totalPages > 1" class="bfp-footer">
            <pagination-component :current-page="page" :total-pages="totalPages" @change-page="p => page = p">
            </pagination-component>
            <span class="bfp-range">{{ rangeLabel }}</span>
        </div>
    </div>
    `,

    setup(props) {
        const query     = ref('')
        const extFilter = ref('')
        const page      = ref(1)

        const docs = computed(() =>
            props.files.filter(f => !f.isRule).sort((a, b) => a.path.localeCompare(b.path))
        )

        const extCounts = computed(() => {
            const m = new Map()
            for (const f of docs.value) {
                const e = extOf(f.name)
                m.set(e, (m.get(e) || 0) + 1)
            }
            return [...m.entries()].map(([ext, count]) => ({ ext, count })).sort((a, b) => b.count - a.count)
        })

        const filtered = computed(() => {
            const q = query.value.trim().toLowerCase()
            return docs.value.filter(f =>
                (!extFilter.value || extOf(f.name) === extFilter.value) &&
                (!q || f.path.toLowerCase().includes(q))
            )
        })

        const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / PER_PAGE)))
        const pageItems  = computed(() => filtered.value.slice((page.value - 1) * PER_PAGE, page.value * PER_PAGE))
        const rangeLabel = computed(() => {
            const start = (page.value - 1) * PER_PAGE + 1
            const end   = Math.min(page.value * PER_PAGE, filtered.value.length)
            return `${start}–${end} of ${filtered.value.length}`
        })

        watch([query, extFilter], () => { page.value = 1 })
        watch(totalPages, (t) => { if (page.value > t) page.value = t })

        const flashId = ref(null)
        const rootEl = ref(null)
        async function focus(file) {
            query.value = ''
            extFilter.value = ''
            await nextTick()                              // let the watchers reset page to 1
            const idx = filtered.value.findIndex(f => f.id === file.id)
            if (idx < 0) return
            page.value = Math.floor(idx / PER_PAGE) + 1
            flashId.value = null
            await nextTick()
            flashId.value = file.id
            rootEl.value?.querySelector(`[data-bfp-id="${CSS.escape(file.id)}"]`)
                ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
            setTimeout(() => { if (flashId.value === file.id) flashId.value = null }, 2300)
        }

        function downloadOne(f) {
            downloadText(f.name, f.content)
        }

        return {
            query, extFilter, page, docs, extCounts, filtered, totalPages, pageItems, rangeLabel,
            docIcon, formatBytes, downloadOne, focus, flashId, rootEl,
        }
    },
}
