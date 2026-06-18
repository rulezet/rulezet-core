/**
 * timeline.js — Vertical event timeline with day grouping.
 *
 * Props:
 *   items        Array   Required. Each item: { uuid, title, description, level,
 *                        category, action, created_at, actor_name, meta }
 *   loading      Boolean Show skeleton rows
 *   group-by-day Boolean Group items under sticky day headers (default: true)
 *   max-desc     Number  Max chars shown in description before truncation (default: 180)
 *
 * Events:
 *   select(item)  — item clicked (for detail panels, modals, etc.)
 *
 * Usage:
 *   import Timeline from '/static/js/components/timeline.js'
 *   <timeline :items="logs" :loading="fetching" @select="openDetail"></timeline>
 */

const { computed, ref } = Vue

// ── Helpers ───────────────────────────────────────────────────────────────────

const LEVEL_CONFIG = {
    info:    { color: 'tl-dot--info',    icon: 'fa-circle-info'  },
    success: { color: 'tl-dot--success', icon: 'fa-circle-check' },
    warning: { color: 'tl-dot--warning', icon: 'fa-triangle-exclamation' },
    error:   { color: 'tl-dot--error',   icon: 'fa-circle-xmark' },
}

const CATEGORY_ICONS = {
    user:     'fa-user',
    system:   'fa-gear',
    security: 'fa-shield-halved',
    admin:    'fa-crown',
    api:      'fa-code',
    database: 'fa-database',
    connectors: 'fa-plug',
}

function levelConfig(level) {
    return LEVEL_CONFIG[level] || LEVEL_CONFIG.info
}

function categoryIcon(cat) {
    return CATEGORY_ICONS[cat] || 'fa-circle'
}

function initials(name) {
    if (!name) return '?'
    const parts = name.trim().split(/\s+/)
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function formatRelative(iso) {
    if (!iso) return '—'
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
    if (diff < 5)    return 'just now'
    if (diff < 60)   return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

function formatFull(iso) {
    if (!iso) return ''
    return new Date(iso).toLocaleString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
    })
}

function dayKey(iso) {
    if (!iso) return 'Unknown'
    const d = new Date(iso)
    const today     = new Date(); today.setHours(0,0,0,0)
    const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1)
    const itemDay   = new Date(d); itemDay.setHours(0,0,0,0)

    if (itemDay.getTime() === today.getTime()) return 'Today'
    if (itemDay.getTime() === yesterday.getTime()) return 'Yesterday'
    return d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })
}

function truncate(str, max) {
    if (!str || str.length <= max) return str
    return str.slice(0, max) + '…'
}

// ── Component ─────────────────────────────────────────────────────────────────

export default {
    name: 'Timeline',

    props: {
        items:      { type: Array,   default: () => [] },
        loading:    { type: Boolean, default: false },
        groupByDay: { type: Boolean, default: true },
        maxDesc:    { type: Number,  default: 180 },
    },

    emits: ['select'],

    setup(props, { emit }) {
        const expanded = ref(new Set())

        function toggle_expand(uuid) {
            if (expanded.value.has(uuid)) {
                expanded.value.delete(uuid)
            } else {
                expanded.value.add(uuid)
            }
            expanded.value = new Set(expanded.value)
        }

        const grouped = computed(() => {
            if (!props.groupByDay) {
                return [{ day: null, items: props.items }]
            }
            const map = new Map()
            for (const item of props.items) {
                const key = dayKey(item.created_at)
                if (!map.has(key)) map.set(key, [])
                map.get(key).push(item)
            }
            return Array.from(map.entries()).map(([day, items]) => ({ day, items }))
        })

        return {
            grouped, expanded, toggle_expand,
            levelConfig, categoryIcon, initials,
            formatRelative, formatFull, truncate,
        }
    },

    template: `
<div class="tl">

    <!-- Skeleton -->
    <template v-if="loading">
        <div class="tl-skeleton" v-for="i in 5" :key="i">
            <div class="tl-skeleton-dot"></div>
            <div class="tl-skeleton-body">
                <div class="tl-skeleton-title"></div>
                <div class="tl-skeleton-meta"></div>
            </div>
        </div>
    </template>

    <!-- Empty -->
    <div v-else-if="!items.length" class="tl-empty">
        <i class="fas fa-scroll"></i>
        <span>No events</span>
    </div>

    <!-- Groups -->
    <template v-else>
        <div v-for="group in grouped" :key="group.day" class="tl-group">
            <div v-if="group.day" class="tl-day-header">
                <span>{{ group.day }}</span>
            </div>

            <div class="tl-items">
                <div
                    v-for="item in group.items"
                    :key="item.uuid"
                    class="tl-item"
                    @click="$emit('select', item)">

                    <!-- Dot -->
                    <div :class="['tl-dot', levelConfig(item.level).color]">
                        <i :class="'fas ' + levelConfig(item.level).icon"></i>
                    </div>

                    <!-- Line -->
                    <div class="tl-line"></div>

                    <!-- Content -->
                    <div class="tl-content">
                        <div class="tl-header">
                            <span class="tl-title">{{ item.title }}</span>
                            <div class="tl-badges">
                                <span class="tl-cat-badge">
                                    <i :class="'fas ' + categoryIcon(item.category)"></i>
                                    {{ item.category }}
                                </span>
                                <span :class="['tl-level-badge', 'tl-level-badge--' + item.level]">
                                    {{ item.level }}
                                </span>
                            </div>
                        </div>

                        <div class="tl-meta">
                            <span v-if="item.actor_name" class="tl-actor">
                                <span class="tl-actor-avatar">{{ initials(item.actor_name) }}</span>
                                {{ item.actor_name }}
                            </span>
                            <span v-else class="tl-actor tl-actor--system">
                                <i class="fas fa-gear"></i> System
                            </span>
                            <span class="tl-sep">·</span>
                            <span class="tl-time" :title="formatFull(item.created_at)">
                                {{ formatRelative(item.created_at) }}
                            </span>
                            <span v-if="item.action" class="tl-sep">·</span>
                            <span v-if="item.action" class="tl-action">{{ item.action }}</span>
                        </div>

                        <!-- Description (collapsible) -->
                        <template v-if="item.description">
                            <div
                                v-if="!expanded.has(item.uuid)"
                                class="tl-desc">
                                {{ truncate(item.description, maxDesc) }}
                                <button
                                    v-if="item.description.length > maxDesc"
                                    class="tl-expand-btn"
                                    @click.stop="toggle_expand(item.uuid)">
                                    more
                                </button>
                            </div>
                            <div v-else class="tl-desc">
                                {{ item.description }}
                                <button class="tl-expand-btn" @click.stop="toggle_expand(item.uuid)">less</button>
                            </div>
                        </template>
                    </div>
                </div>
            </div>
        </div>
    </template>

</div>
    `,
}
