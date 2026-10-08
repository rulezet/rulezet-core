/**
 * BundleAIAnalysisPanel.js — "AI Analysis" tab of the bundle detail page.
 *
 * A long narrative review of the whole bundle written by the local model
 * (BundleAnalysisAgent, run as an 'ai_bundle_analysis' background job).
 * Launching / following a run / moderating: admins + AI Managers only —
 * enforced server-side, `canManage` only decides what is shown. Public
 * reports are readable by anyone who can view the bundle.
 *
 * Props:  bundleId, csrfToken, active (lazy: nothing is fetched before the
 *         tab is first opened), canManage
 * Emits:  loaded({ count, latest })
 */

import { create_message } from '/static/js/toaster.js'
import { renderSafeMarkdown } from '/static/js/bundle/bundleFileTypes.js'
import { MASCOT_ENABLED } from '/static/js/components/mascot.js'
import AIThinkingSteps from '/static/js/components/ai-thinking-steps.js'

const { ref, computed, watch, onUnmounted } = Vue

const RULEZY = '/static/images/rulezy/'
const TERMINAL = new Set(['done', 'failed', 'cancelled'])

const VERDICT = {
    ready:               { icon: 'fa-solid fa-circle-check',         cls: 'bai-verdict--ready' },
    usable_with_caveats: { icon: 'fa-solid fa-circle-half-stroke',   cls: 'bai-verdict--caveats' },
    needs_work:          { icon: 'fa-solid fa-screwdriver-wrench',   cls: 'bai-verdict--work' },
    not_recommended:     { icon: 'fa-solid fa-circle-xmark',         cls: 'bai-verdict--no' },
}

// "## Title\nbody…" → [{ id, title, body }] — each section is rendered on its
// own so the report gets a real table of contents (ids we control, not ids
// inside sanitised HTML).
function splitSections(md) {
    const out = []
    let current = { title: null, lines: [] }
    for (const line of String(md || '').split('\n')) {
        const m = /^##\s+(.+?)\s*#*\s*$/.exec(line)
        if (m) {
            if (current.title || current.lines.join('').trim()) out.push(current)
            current = { title: m[1], lines: [] }
        } else {
            current.lines.push(line)
        }
    }
    if (current.title || current.lines.join('').trim()) out.push(current)
    return out.map((s, i) => ({ id: 'bai-sec-' + i, title: s.title, body: s.lines.join('\n').trim() }))
}

export default {
    name: 'BundleAIAnalysisPanel',
    components: { 'ai-thinking-steps': AIThinkingSteps },
    props: {
        bundleId:  { type: [Number, String], required: true },
        csrfToken: { type: String, default: '' },
        active:    { type: Boolean, default: false },
        canManage: { type: Boolean, default: false },
    },
    emits: ['loaded'],
    setup(props, { emit }) {
        const mascot   = MASCOT_ENABLED
        const loaded   = ref(false)
        const loading  = ref(false)
        const history  = ref([])
        const selected = ref(null)
        const sections = ref([])
        const rendering = ref(false)
        const copied   = ref(false)

        // ── Launch card ──
        const featureEnabled = ref(true)
        const models         = ref([])
        const selectedModel  = ref('')
        const makePublic     = ref(true)
        const launching      = ref(false)

        // ── Running job → thinking steps ──
        const job     = ref(null)       // { uuid, status, steps, error }
        let pollTimer = null
        const running = computed(() => !!job.value && !TERMINAL.has(job.value.status))
        const steps   = computed(() => {
            if (!job.value) return []
            const s = [...(job.value.steps || [])]
            if (job.value.status === 'pending' && !s.length)
                s.push({ stage: 'reading', text: 'Queued — waiting for the AI worker to pick it up…' })
            return s
        })

        const latest = computed(() => history.value[0] || null)
        const verdictMeta = (v) => VERDICT[v] || VERDICT.usable_with_caveats

        async function fetchList() {
            loading.value = true
            try {
                const res = await fetch(`/bundle/${props.bundleId}/ai_analysis/list`)
                const data = await res.json()
                history.value = data.items || []
                if (!selected.value || !history.value.some(h => h.id === selected.value.id))
                    selected.value = history.value[0] || null
                emit('loaded', { count: history.value.length, latest: history.value[0] || null })
            } catch {
                create_message('Could not load the AI analyses', 'danger-subtle')
            } finally {
                loading.value = false
                loaded.value = true
            }
        }

        async function fetchModels() {
            if (!props.canManage) return
            try {
                const res = await fetch('/bundle/ai_analysis/models')
                if (!res.ok) return
                const data = await res.json()
                featureEnabled.value = data.enabled
                models.value = data.models || []
                selectedModel.value = (data.default_model && models.value.includes(data.default_model))
                    ? data.default_model : (models.value[0] || '')
            } catch { /* launch card shows the "no models" hint */ }
        }

        async function pollJob(uuid) {
            try {
                const q = uuid ? `?job=${encodeURIComponent(uuid)}` : ''
                const res = await fetch(`/bundle/${props.bundleId}/ai_analysis/job${q}`)
                const data = await res.json()
                if (!data.job) { if (!uuid) job.value = null; return }
                job.value = data.job
                if (TERMINAL.has(data.job.status)) {
                    stopPolling()
                    if (data.job.status === 'done') {
                        await fetchList()
                        selected.value = history.value[0] || null
                        create_message('The bundle analysis is ready', 'success-subtle')
                    }
                }
            } catch { /* keep polling */ }
        }
        function startPolling(uuid) {
            stopPolling()
            pollJob(uuid)
            pollTimer = setInterval(() => pollJob(uuid), 2500)
        }
        function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

        async function launch() {
            launching.value = true
            try {
                const res = await fetch(`/bundle/${props.bundleId}/ai_analysis`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ model: selectedModel.value, default_public: makePublic.value }),
                })
                const data = await res.json()
                if (!res.ok || !data.success) {
                    create_message(data.message || 'Could not start the analysis', 'danger-subtle')
                    return
                }
                if (data.already_running) create_message('An analysis of this bundle is already running — following it.', 'info-subtle')
                job.value = { uuid: data.job_uuid, status: 'pending', steps: [] }
                startPolling(data.job_uuid)
            } catch (e) {
                create_message('Network error: ' + e, 'danger-subtle')
            } finally {
                launching.value = false
            }
        }

        // First activation: load everything, and resume following a run
        // that was started earlier (page reload, another tab…).
        watch(() => props.active, async (on) => {
            if (!on || loaded.value) return
            await Promise.all([fetchList(), fetchModels()])
            if (props.canManage) {
                await pollJob(null)
                if (running.value) startPolling(job.value.uuid)
            }
        }, { immediate: true })
        onUnmounted(stopPolling)

        // Render the selected report section by section.
        watch(selected, async (entry) => {
            if (!entry || !entry.content) { sections.value = []; return }
            rendering.value = true
            const parts = splitSections(entry.content)
            const html = await Promise.all(parts.map(p => renderSafeMarkdown(p.body)))
            if (selected.value !== entry) return
            sections.value = parts.map((p, i) => ({ ...p, html: html[i] }))
            rendering.value = false
        })

        function scrollTo(id) {
            document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }

        function copyReport() {
            if (!selected.value) return
            navigator.clipboard?.writeText(selected.value.content || '')
            copied.value = true
            setTimeout(() => { copied.value = false }, 1800)
        }
        const downloadUrl = (entry, kind) => `/bundle/${props.bundleId}/ai_analysis/${entry.id}/download/${kind}`

        async function toggleVisibility(entry) {
            const res = await fetch(`/bundle/${props.bundleId}/ai_analysis/${entry.id}/visibility`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                body: JSON.stringify({ is_public: !entry.is_public }),
            })
            const data = await res.json()
            if (data.success) {
                entry.is_public = data.analysis.is_public
                create_message(entry.is_public ? 'Analysis is now public' : 'Analysis is now private', 'success-subtle')
            } else create_message(data.message || 'Failed to update visibility', 'danger-subtle')
        }

        async function remove(entry) {
            if (!confirm('Delete this AI analysis? This cannot be undone.')) return
            const res = await fetch(`/bundle/${props.bundleId}/ai_analysis/${entry.id}`, {
                method: 'DELETE', headers: { 'X-CSRFToken': props.csrfToken },
            })
            const data = await res.json()
            if (data.success) {
                if (selected.value?.id === entry.id) selected.value = null
                await fetchList()
                create_message('Analysis deleted', 'success-subtle')
            } else create_message(data.message || 'Failed to delete', 'danger-subtle')
        }

        const fmtDate = (iso) => iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : ''
        const wordCount = (md) => String(md || '').split(/\s+/).filter(Boolean).length

        return {
            mascot, RULEZY, loaded, loading, history, selected, latest, sections, rendering, copied,
            featureEnabled, models, selectedModel, makePublic, launching, launch,
            job, running, steps, verdictMeta, scrollTo, copyReport, downloadUrl,
            toggleVisibility, remove, fmtDate, wordCount,
        }
    },
    template: `
<div class="bai">
    <div v-if="!loaded" class="text-center py-5" style="color:var(--subtle-text-color);">
        <div class="spinner-border text-primary mb-2" role="status"></div>
        <div class="small">Loading AI analyses…</div>
    </div>

    <template v-else>
        <!-- ── Launch (admins / AI Managers) ── -->
        <div v-if="canManage && !running" class="bai-launch">
            <div class="bai-launch__who">
                <img v-if="mascot" :src="RULEZY + 'analyseRule.png'" alt="Rulezy" class="bai-launch__avatar">
                <div v-else class="rulezy-icon-fallback" style="width:48px;height:48px;font-size:1.2rem;"><i class="fa-solid fa-robot"></i></div>
                <div>
                    <div class="bai-launch__title">{{ history.length ? 'Run a fresh review' : 'Let Rulezy review this bundle' }}</div>
                    <div class="bai-launch__sub">I read every rule, the structure, the documents, the health checks, ATT&amp;CK coverage and community notes, then write a detailed review for the people who will deploy it. Takes a few minutes; you can leave the page.</div>
                </div>
            </div>
            <div v-if="!featureEnabled" class="bai-hint"><i class="fa-solid fa-circle-info me-1"></i>Bundle Analysis is disabled instance-wide (AI admin → Bundle Analysis).</div>
            <div v-else-if="!models.length" class="bai-hint"><i class="fa-solid fa-circle-info me-1"></i>No model available — is Ollama running and reachable?</div>
            <div v-else class="bai-launch__controls">
                <select class="form-select form-select-sm" v-model="selectedModel" title="Model">
                    <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
                </select>
                <label class="form-check form-switch mb-0 small">
                    <input class="form-check-input" type="checkbox" v-model="makePublic">
                    <span class="form-check-label">Public immediately</span>
                </label>
                <button class="btn btn-sm btn-primary rounded-pill px-3" :disabled="launching || !selectedModel" @click="launch">
                    <i class="fa-solid me-1" :class="launching ? 'fa-spinner fa-spin' : 'fa-wand-magic-sparkles'"></i>
                    {{ launching ? 'Starting…' : (history.length ? 'Analyze again' : 'Analyze this bundle') }}
                </button>
            </div>
        </div>

        <!-- ── Run in progress / just failed ── -->
        <div v-if="job && (running || job.status === 'failed')" class="bai-run">
            <div class="bai-run__head">
                <span class="bai-run__title"><i class="fa-solid fa-brain me-1"></i>{{ running ? 'Rulezy is reviewing this bundle' : 'The analysis failed' }}</span>
                <a :href="'/jobs/detail/' + job.uuid" class="small ms-auto" target="_blank">Job details →</a>
            </div>
            <ai-thinking-steps :steps="steps" :active="running"></ai-thinking-steps>
            <div v-if="!running && job.error" class="bai-hint mt-2"><i class="fa-solid fa-triangle-exclamation me-1"></i>{{ job.error }}</div>
        </div>

        <!-- ── Empty ── -->
        <div v-if="!history.length && !running" class="bai-empty">
            <div v-if="mascot" class="rulezy-say rulezy-say--below align-self-center mb-2" tabindex="0">
                <img :src="RULEZY + 'reflexion.png'" alt="Rulezy" class="rulezy-say__avatar">
                <div class="rulezy-say__bubble">I haven't reviewed this bundle yet — an admin or AI Manager just has to ask me.</div>
            </div>
            <i v-else class="fa-solid fa-robot mb-2" style="font-size:2rem;color:#0d6efd;"></i>
            <p class="mb-0 fst-italic">"No review of this bundle yet."</p>
        </div>

        <!-- ── Report ── -->
        <div v-if="selected" class="bai-report">
            <div class="bai-report__bar">
                <div class="d-flex align-items-center gap-2 min-w0">
                    <div v-if="mascot" class="rulezy-say" tabindex="0">
                        <img :src="RULEZY + 'analyseRule.png'" alt="Rulezy" class="rulezy-say__avatar" style="width:34px;height:34px;">
                        <div class="rulezy-say__bubble">I reviewed this bundle with <code>{{ selected.model || 'unknown model' }}</code> — every rule, its structure, health, coverage and notes — and wrote down what I'd tell a team about to deploy it.</div>
                    </div>
                    <span class="bai-report__stamp">
                        {{ fmtDate(selected.created_at) }}<span v-if="selected.username"> · for {{ selected.username }}</span>
                        · {{ wordCount(selected.content).toLocaleString() }} words
                    </span>
                    <span v-if="!selected.is_public" class="bai-pill bai-pill--private">Private</span>
                    <span v-if="selected !== latest" class="bai-pill">Older version</span>
                </div>
                <div class="d-flex gap-2 flex-wrap">
                    <button class="btn btn-sm btn-outline-secondary rounded-pill px-3" @click="copyReport">
                        <i class="fa-solid" :class="copied ? 'fa-check' : 'fa-copy'"></i> {{ copied ? 'Copied' : 'Copy' }}
                    </button>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary rounded-pill px-3 dropdown-toggle" data-bs-toggle="dropdown">
                            <i class="fa-solid fa-download me-1"></i>Download
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end shadow border-0 rounded-3" style="background:var(--card-bg-color);">
                            <li><a class="dropdown-item small" :href="downloadUrl(selected, 'markdown')" style="color:var(--text-color);"><i class="fa-solid fa-file-lines me-2 opacity-50"></i>Markdown (.md)</a></li>
                            <li><a class="dropdown-item small" :href="downloadUrl(selected, 'pdf')" style="color:var(--text-color);"><i class="fa-solid fa-file-pdf me-2 opacity-50"></i>PDF</a></li>
                        </ul>
                    </div>
                    <template v-if="canManage">
                        <button class="btn btn-sm btn-outline-secondary rounded-pill px-3" @click="toggleVisibility(selected)">
                            <i class="fa-solid" :class="selected.is_public ? 'fa-eye-slash' : 'fa-eye'"></i>
                            {{ selected.is_public ? 'Make private' : 'Make public' }}
                        </button>
                        <button class="btn btn-sm btn-outline-danger rounded-pill px-3" @click="remove(selected)" title="Delete"><i class="fa-solid fa-trash"></i></button>
                    </template>
                </div>
            </div>

            <!-- At a glance -->
            <div v-if="selected.meta" class="bai-glance">
                <div class="bai-glance__top">
                    <span class="bai-verdict" :class="verdictMeta(selected.meta.verdict).cls">
                        <i :class="verdictMeta(selected.meta.verdict).icon"></i>{{ selected.meta.verdict_label }}
                    </span>
                    <p class="bai-headline">{{ selected.meta.headline }}</p>
                </div>
                <p v-if="selected.meta.audience" class="bai-audience"><i class="fa-solid fa-users me-1"></i>{{ selected.meta.audience }}</p>
                <div v-if="selected.meta.snapshot" class="bai-snapshot">
                    <span><i class="fa-solid fa-shield-halved"></i>{{ selected.meta.snapshot.rule_count }} rules analysed</span>
                    <span v-if="selected.meta.snapshot.health_score !== null && selected.meta.snapshot.health_score !== undefined"><i class="fa-solid fa-heart-pulse"></i>Health {{ selected.meta.snapshot.health_score }}/100</span>
                    <span v-if="selected.meta.snapshot.total_tactics"><i class="fa-solid fa-crosshairs"></i>{{ selected.meta.snapshot.covered_tactics }}/{{ selected.meta.snapshot.total_tactics }} tactics</span>
                    <span><i class="fa-solid fa-note-sticky"></i>{{ selected.meta.snapshot.open_notes }} open note{{ selected.meta.snapshot.open_notes === 1 ? '' : 's' }}</span>
                    <span><i class="fa-solid fa-tags"></i>{{ selected.meta.snapshot.releases ? selected.meta.snapshot.releases + ' release(s)' : 'no release' }}</span>
                </div>
                <div class="bai-cols">
                    <div v-if="selected.meta.strengths && selected.meta.strengths.length" class="bai-col bai-col--good">
                        <div class="bai-col__title"><i class="fa-solid fa-thumbs-up"></i>Strengths</div>
                        <ul><li v-for="(s, i) in selected.meta.strengths" :key="i">{{ s }}</li></ul>
                    </div>
                    <div v-if="selected.meta.risks && selected.meta.risks.length" class="bai-col bai-col--risk">
                        <div class="bai-col__title"><i class="fa-solid fa-triangle-exclamation"></i>Risks</div>
                        <ul><li v-for="(s, i) in selected.meta.risks" :key="i">{{ s }}</li></ul>
                    </div>
                    <div v-if="selected.meta.next_steps && selected.meta.next_steps.length" class="bai-col bai-col--next">
                        <div class="bai-col__title"><i class="fa-solid fa-list-check"></i>Next steps</div>
                        <ul><li v-for="(s, i) in selected.meta.next_steps" :key="i">{{ s }}</li></ul>
                    </div>
                </div>
            </div>

            <!-- Full report -->
            <div class="bai-body">
                <nav v-if="sections.filter(s => s.title).length > 1" class="bai-toc">
                    <div class="bai-toc__title">Contents</div>
                    <a v-for="s in sections.filter(s => s.title)" :key="s.id" href="#" @click.prevent="scrollTo(s.id)">{{ s.title }}</a>
                </nav>
                <div class="bai-sections">
                    <div v-if="rendering" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary"></div></div>
                    <section v-for="s in sections" :key="s.id" :id="s.id" class="bai-section">
                        <h3 v-if="s.title" class="bai-section__title">{{ s.title }}</h3>
                        <div class="bai-md" v-html="s.html"></div>
                    </section>
                </div>
            </div>
        </div>

        <!-- ── History ── -->
        <div v-if="history.length > 1" class="bai-history">
            <div class="bai-history__title"><i class="fa-solid fa-clock-rotate-left me-1"></i>Previous reviews ({{ history.length }})</div>
            <button v-for="h in history" :key="h.id" type="button" class="bai-history__item"
                    :class="{ active: selected && selected.id === h.id }" @click="selected = h">
                <span v-if="h.meta" class="bai-dot" :class="verdictMeta(h.meta.verdict).cls"></span>
                <span class="bai-history__main">
                    <strong>{{ h.meta ? h.meta.verdict_label : 'Review' }}</strong>
                    <span>{{ fmtDate(h.created_at) }} · <code>{{ h.model || '?' }}</code><span v-if="h.username"> · {{ h.username }}</span></span>
                </span>
                <span v-if="!h.is_public" class="bai-pill bai-pill--private">Private</span>
            </button>
        </div>
    </template>
</div>
    `,
}
