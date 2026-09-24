/**
 * BundleHealthPanel.js — "Health" tab of the bundle detail page.
 *
 * Renders GET /bundle/<id>/health: an overall score + verdict, then one card
 * per check (syntax, ID collisions, missing dependencies, TLP/PAP, …) with
 * the offending rules and shortcuts to open / locate them.
 *
 * Props:
 *   bundleId  Number|String  required
 *   active    Boolean        load on first activation (the report can take ~1s)
 *   release   String         version to check instead of the live bundle ('' = live)
 *   csrfToken String         for "Fix it for me" (POST /bundle/<id>/health/fix)
 *
 * Emits:
 *   loaded(health)                 — after each (re)load
 *   show-structure(ruleId)         — "In structure" on an item
 *   show-list({ ruleId, name })    — "In list" on an item
 *   fixed()                        — a fix was applied (parent reloads tree / lists)
 */

import { create_message } from '/static/js/toaster.js'

const { ref, computed, watch, nextTick } = Vue

const LEVELS = {
    error:   { icon: 'fa-solid fa-circle-xmark',          label: 'Blocking' },
    warning: { icon: 'fa-solid fa-triangle-exclamation',  label: 'Review' },
    info:    { icon: 'fa-solid fa-circle-info',           label: 'Info' },
    ok:      { icon: 'fa-solid fa-circle-check',          label: 'OK' },
}
const VERDICTS = {
    ready:    { label: 'Ready to deploy',        icon: 'fa-solid fa-rocket',               cls: 'ok' },
    review:   { label: 'Review recommended',     icon: 'fa-solid fa-magnifying-glass',     cls: 'warning' },
    blocking: { label: 'Blocking issues',        icon: 'fa-solid fa-hand',                 cls: 'error' },
    empty:    { label: 'No rules yet',           icon: 'fa-regular fa-folder-open',        cls: 'info' },
}
const PREVIEW = 6

export default {
    name: 'BundleHealthPanel',

    props: {
        bundleId: { type: [Number, String], required: true },
        active:   { type: Boolean, default: false },
        release:  { type: String,  default: '' },
        csrfToken: { type: String, default: '' },
    },

    emits: ['loaded', 'show-structure', 'show-list', 'fixed'],

    template: `
    <div class="bh-root">
        <div v-if="loading && !health" class="bh-loading">
            <i class="fas fa-spinner fa-spin me-2"></i>Running checks on every rule…
        </div>
        <div v-else-if="error" class="bh-loading">
            <i class="fa-solid fa-circle-exclamation me-2"></i>{{ error }}
        </div>

        <template v-else-if="health">
            <!-- Summary -->
            <div class="bh-summary" :class="['bh-summary--' + verdict.cls, { 'bh-summary--flash': flash }]">
                <div class="bh-score" :style="{ '--bh-pct': (health.score ?? 0) + '%' }">
                    <span v-if="health.score !== null">{{ health.score }}</span>
                    <span v-else>—</span>
                </div>
                <div class="bh-summary-main">
                    <div class="bh-verdict"><i :class="verdict.icon"></i>{{ verdict.label }}
                        <span v-if="release" class="bh-release-tag"><i class="fa-solid fa-snowflake"></i>{{ release }}</span></div>
                    <div class="bh-summary-sub">
                        {{ health.rules }} rule{{ health.rules === 1 ? '' : 's' }} checked ·
                        <span class="bh-cnt bh-cnt--error" v-if="health.counts.error">{{ health.counts.error }} blocking</span>
                        <span class="bh-cnt bh-cnt--warning" v-if="health.counts.warning">{{ health.counts.warning }} to review</span>
                        <span class="bh-cnt bh-cnt--ok">{{ health.counts.ok }} passed</span>
                    </div>
                </div>
                <div class="bh-rerun">
                    <button v-if="canRerun && !release" type="button" class="bd-btn" @click="rerun" :disabled="loading"
                            title="Re-validate every rule now (owner / admin)">
                        <i :class="loading ? 'fas fa-spinner fa-spin' : 'fa-solid fa-rotate'"></i>
                        <span>{{ loading ? 'Checking…' : 'Re-run' }}</span>
                    </button>
                    <span v-if="health.checked_at" class="bh-checked-at">Checked {{ checkedAgo }}</span>
                </div>
            </div>

            <!-- Checks -->
            <div class="bh-checks">
                <div v-for="c in sortedChecks" :key="c.key" class="bh-check" :class="'bh-check--' + c.level">
                    <div class="bh-check-head" @click="c.count && toggle(c.key)" :class="{ 'bh-check-head--clickable': c.count }">
                        <i :class="LEVELS[c.level].icon + ' bh-check-icon'"></i>
                        <div class="bh-check-main">
                            <div class="bh-check-title">
                                {{ c.title }}
                                <span v-if="c.count" class="bh-check-count">{{ c.count }}</span>
                            </div>
                            <div class="bh-check-msg">{{ c.message }}</div>
                            <div v-if="c.fix && c.level !== 'ok'" class="bh-check-fix"><i class="fa-solid fa-wrench"></i>{{ c.fix }}</div>
                        </div>
                        <i v-if="c.count" class="fa-solid bh-chevron" :class="open.has(c.key) ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
                    </div>

                    <ul v-if="c.count && open.has(c.key)" class="bh-items">
                        <li v-for="(it, i) in visibleItems(c)" :key="c.key + i" class="bh-item">
                            <div class="bh-item-main">
                                <span class="bh-item-name" :title="it.name">
                                    <i :class="it.rule_id ? 'fa-solid fa-shield-halved' : 'fa-solid fa-folder'"></i>{{ it.name }}
                                </span>
                                <span class="bh-item-detail">{{ it.detail }}</span>
                            </div>
                            <div v-if="it.fix && !release" class="bh-item-fix">
                                <button type="button" class="am-rule-act am-rule-act--fix"
                                        :class="{ 'am-rule-act--armed': armedFix === c.key + i }"
                                        :disabled="fixing"
                                        :title="it.fix.confirm ? 'Click, then click again to confirm' : 'Apply this fix now'"
                                        @click="applyFix(c, it, c.key + i)">
                                    <i :class="fixing === c.key + i ? 'fas fa-spinner fa-spin' : 'fa-solid fa-wand-magic-sparkles'"></i>
                                    <span>{{ armedFix === c.key + i ? 'Click again to confirm' : it.fix.label }}</span>
                                </button>
                            </div>
                            <div v-if="it.rule_id" class="bh-item-actions">
                                <a v-if="it.can_edit && !release" :href="editUrl(c, it)" class="am-rule-act am-rule-act--edit"
                                   title="Open the bundle editor with this rule selected in the structure — the issue is shown there">
                                    <i class="fa-solid fa-pen"></i><span>Edit in bundle</span>
                                </a>
                                <a :href="'/rule/detail_rule/' + it.rule_id" target="_blank" rel="noopener" class="am-rule-act" title="Open the rule page">
                                    <i class="fa-solid fa-arrow-up-right-from-square"></i><span>Detail</span>
                                </a>
                                <button type="button" class="am-rule-act" @click="$emit('show-list', { ruleId: it.rule_id, name: it.name })" title="Show it in the Rules list">
                                    <i class="fa-solid fa-list"></i><span>In list</span>
                                </button>
                                <button type="button" class="am-rule-act" @click="$emit('show-structure', it.rule_id)" title="Show where it is in the structure">
                                    <i class="fa-solid fa-folder-tree"></i><span>In structure</span>
                                </button>
                            </div>
                        </li>
                        <li v-if="c.items.length > PREVIEW && !showAll.has(c.key)" class="bh-more">
                            <button type="button" class="bd-btn bd-btn--ghost" @click="showAll.add(c.key)">
                                Show all {{ c.items.length }}{{ c.count > c.items.length ? ' (first ' + c.items.length + ' of ' + c.count + ')' : '' }}
                            </button>
                        </li>
                    </ul>
                </div>
            </div>
        </template>
    </div>
    `,

    setup(props, { emit }) {
        const health  = ref(null)
        const loading = ref(false)
        const error   = ref('')
        const open    = ref(new Set())
        const showAll = ref(new Set())
        const canRerun = ref(false)
        const flash    = ref(false)
        const now      = ref(Date.now())
        setInterval(() => { now.value = Date.now() }, 30000)
        const checkedAgo = computed(() => {
            const t = health.value?.checked_at ? Date.parse(health.value.checked_at) : null
            if (!t) return ''
            const s = Math.max(0, Math.round((now.value - t) / 1000))
            return s < 60 ? 'just now' : s < 3600 ? `${Math.round(s / 60)} min ago` : new Date(t).toLocaleString()
        })

        const ORDER = { error: 0, warning: 1, info: 2, ok: 3 }
        const sortedChecks = computed(() =>
            [...(health.value?.checks || [])].sort((a, b) => ORDER[a.level] - ORDER[b.level]))
        const verdict = computed(() => VERDICTS[health.value?.verdict] || VERDICTS.empty)

        async function load(force = false, refresh = false) {
            if (loading.value || (health.value && !force)) return
            loading.value = true
            error.value = ''
            try {
                const qs = props.release ? '?' + new URLSearchParams({ release: props.release })
                                         : (refresh ? '?refresh=1' : '')
                const res = await fetch(`/bundle/${props.bundleId}/health${qs}`)
                const data = await res.json().catch(() => null)
                if (!res.ok || !data?.success) throw new Error(data?.message || `HTTP ${res.status}`)
                health.value = data.health
                canRerun.value = !!data.can_rerun
                now.value = Date.now()
                // open blocking checks by default
                open.value = new Set(data.health.checks.filter(c => c.level === 'error' && c.count).map(c => c.key))
                emit('loaded', data.health)
            } catch (e) {
                error.value = 'Could not run the health checks (' + (e.message || e) + ')'
            } finally {
                loading.value = false
            }
        }

        // Owner/admin: full re-validation, with visible feedback
        async function rerun() {
            const before = health.value?.score
            await load(true, true)
            if (!health.value || error.value) {
                create_message(error.value || 'Health check failed', 'danger-subtle')
                return
            }
            const h = health.value
            const delta = (before !== undefined && before !== null && h.score !== null && h.score !== before)
                ? ` (${h.score > before ? '+' : ''}${h.score - before})` : ''
            create_message(`Health check re-run — score ${h.score ?? '—'}/100${delta} · ${verdict.value.label}`,
                           h.verdict === 'blocking' ? 'warning-subtle' : 'success-subtle')
            flash.value = false
            await nextTick()
            flash.value = true
            setTimeout(() => { flash.value = false }, 1600)
        }

        // Bundle editor, structure tab, with the rule selected where it sits
        function editUrl(c, it) {
            const q = new URLSearchParams({ focus_rule: it.rule_id, rule: it.name || '', check: c.title, issue: it.detail })
            if (c.fix) q.set('fix', c.fix)
            return `/bundle/edit/${props.bundleId}?${q}`
        }

        // "Fix it for me" — two clicks for destructive fixes
        const armedFix = ref(null)
        const fixing   = ref(null)
        let _armT = null
        async function applyFix(c, it, key) {
            if (it.fix.confirm && armedFix.value !== key) {
                armedFix.value = key
                clearTimeout(_armT)
                _armT = setTimeout(() => { armedFix.value = null }, 3500)
                return
            }
            armedFix.value = null
            fixing.value = key
            try {
                const res = await fetch(`/bundle/${props.bundleId}/health/fix`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ fix: it.fix }),
                })
                const data = await res.json().catch(() => ({}))
                create_message(data.message || (res.ok ? 'Fixed' : `Fix failed (HTTP ${res.status})`),
                               data.toast_class || (res.ok ? 'success-subtle' : 'danger-subtle'))
                if (res.ok && data.success) {
                    emit('fixed')
                    const before = health.value?.score
                    await load(true)
                    if (health.value && before != null && health.value.score !== before)
                        create_message(`Health score ${before} → ${health.value.score}`, 'success-subtle')
                    flash.value = false; await nextTick(); flash.value = true
                    setTimeout(() => { flash.value = false }, 1600)
                }
            } catch (e) {
                create_message('Fix failed (' + (e.message || e) + ')', 'danger-subtle')
            } finally {
                fixing.value = null
            }
        }

        function toggle(key) {
            const s = new Set(open.value)
            s.has(key) ? s.delete(key) : s.add(key)
            open.value = s
        }
        function visibleItems(c) {
            return showAll.value.has(c.key) ? c.items : c.items.slice(0, PREVIEW)
        }

        watch(() => props.active, (a) => { if (a) load() }, { immediate: true })
        // switching version → the previous report no longer applies
        watch(() => props.release, () => {
            health.value = null
            if (props.active) load(true)
        })

        return { health, loading, error, open, showAll, sortedChecks, verdict, load, rerun, toggle, visibleItems,
                 canRerun, flash, checkedAgo, editUrl, armedFix, fixing, applyFix, LEVELS, PREVIEW }
    },
}
