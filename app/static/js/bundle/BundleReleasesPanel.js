/**
 * BundleReleasesPanel.js — "Releases" tab of the bundle detail page.
 *
 * Versioned, frozen releases (bundle_release_core): list, publish (with an
 * auto-generated changelog), download the frozen ZIP, compare a release with
 * the live bundle or with another release, per-rule content diff.
 *
 * Props:
 *   bundleId   Number|String  required
 *   csrfToken  String
 *   active     Boolean        (re)load when the tab becomes visible
 *
 * Emits:
 *   loaded({ releases, latest_changes, can_manage })
 *   changed()                 — after publish / delete (parent refreshes history)
 *   view-release(version)     — show the detail page as this release froze it
 *   show-structure(ruleId), show-list({ ruleId, name })
 */

import SmartEditor from '/static/js/components/smart-editor.js'
import DiffViewer  from '/static/js/components/diff-viewer.js'
import { create_message } from '/static/js/toaster.js'
import { renderSafeMarkdown, downloadFromUrl } from '/static/js/bundle/bundleFileTypes.js'

const { ref, computed, watch, reactive } = Vue

export default {
    name: 'BundleReleasesPanel',
    components: { SmartEditor, DiffViewer },

    props: {
        bundleId:  { type: [Number, String], required: true },
        csrfToken: { type: String, default: '' },
        active:    { type: Boolean, default: false },
    },

    emits: ['loaded', 'changed', 'show-structure', 'show-list', 'view-release'],

    template: `
    <div class="br-root">
        <div v-if="loading && !loaded" class="bh-loading"><i class="fas fa-spinner fa-spin me-2"></i>Loading releases…</div>

        <template v-else>
            <!-- Drift since the latest release -->
            <div v-if="latest && drift && drift.total" class="br-drift">
                <i class="fa-solid fa-code-branch"></i>
                <div class="br-drift-main">
                    <strong>{{ drift.total }} change{{ drift.total > 1 ? 's' : '' }} since {{ latest.version }}</strong>
                    <span>{{ driftSummary }}</span>
                </div>
                <button type="button" class="bd-btn" @click="openCompare(latest, 'current')">
                    <i class="fa-solid fa-code-compare"></i><span>See changes</span>
                </button>
                <button v-if="canManage && !formOpen" type="button" class="bd-btn bd-btn--primary" @click="openForm">
                    <i class="fa-solid fa-tag"></i><span>Publish a new release</span>
                </button>
            </div>
            <div v-else-if="latest" class="br-uptodate">
                <i class="fa-solid fa-circle-check"></i>
                The bundle is identical to its latest release <strong>{{ latest.version }}</strong>.
            </div>

            <!-- Publish form -->
            <div v-if="canManage" class="br-new">
                <button v-if="!formOpen && !(latest && drift && drift.total)" type="button" class="bd-btn bd-btn--primary" @click="openForm">
                    <i class="fa-solid fa-tag"></i><span>{{ releases.length ? 'Publish a new release' : 'Publish the first release' }}</span>
                </button>
                <div v-if="formOpen" class="br-form">
                    <div class="br-form-row">
                        <label class="br-field">
                            <span>Version</span>
                            <input type="text" v-model.trim="form.version" placeholder="v1.0.0" maxlength="40">
                        </label>
                        <label class="br-field br-field--grow">
                            <span>Title <em>(optional)</em></span>
                            <input type="text" v-model="form.title" placeholder="e.g. Q3 refresh — new LockBit loaders" maxlength="255">
                        </label>
                    </div>
                    <div class="br-field">
                        <span>Release notes <em>(generated from the changes — edit freely)</em></span>
                        <smart-editor :key="formKey" v-model="form.notes" mode="markdown" min-height="180px" max-height="420px"></smart-editor>
                    </div>
                    <div class="br-form-hint">
                        <i class="fa-solid fa-snowflake"></i>
                        Publishing freezes the exact content of every rule and file. Later edits won't change this release.
                    </div>
                    <div class="br-form-actions">
                        <button type="button" class="bd-btn bd-btn--ghost" @click="formOpen = false">Cancel</button>
                        <button type="button" class="bd-btn bd-btn--primary" @click="publish" :disabled="busy || !form.version">
                            <i :class="busy ? 'fas fa-spinner fa-spin' : 'fa-solid fa-rocket'"></i><span>Publish {{ form.version }}</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- List -->
            <div v-if="!releases.length && !formOpen" class="br-empty">
                <i class="fa-solid fa-tags"></i>
                <div>
                    <strong>No release yet.</strong>
                    <span>A release freezes the bundle so it can be deployed and referenced reliably ("we run Ransomware Pack v1.2").</span>
                </div>
            </div>

            <div class="br-list">
                <div v-for="(r, idx) in releases" :key="r.id" class="br-card" :class="{ 'br-card--latest': idx === 0 }">
                    <div class="br-card-head">
                        <span class="br-version">{{ r.version }}</span>
                        <span v-if="idx === 0" class="br-latest">Latest</span>
                        <span class="br-title">{{ r.title }}</span>
                        <span class="br-meta">
                            <i class="fa-regular fa-calendar"></i>{{ fmtDate(r.created_at) }}
                            <template v-if="r.user_name"> · {{ r.user_name }}</template>
                        </span>
                    </div>
                    <div class="br-stats">
                        <button type="button" class="bd-uuid" :title="'Release UUID — click to copy'" @click="copyUuid(r.uuid)">
                            <i class="fa-solid fa-fingerprint"></i><span>{{ r.uuid }}</span><i class="fa-regular fa-copy"></i>
                        </button>
                        <span><i class="fa-solid fa-shield-halved"></i>{{ r.rule_count }} rules</span>
                        <span><i class="fa-solid fa-file-lines"></i>{{ r.file_count }} files</span>
                        <span v-if="r.health_score !== null" :class="'br-health br-health--' + healthCls(r.health_score)">
                            <i class="fa-solid fa-heart-pulse"></i>health {{ r.health_score }}/100
                        </span>
                    </div>
                    <div v-if="r.notes" class="br-notes" :class="{ 'br-notes--open': openNotes.has(r.id) }">
                        <div class="bfv-md" v-html="notesHtml[r.id] || ''"></div>
                    </div>
                    <div class="br-actions">
                        <button v-if="r.notes" type="button" class="bd-btn bd-btn--ghost" @click="toggleNotes(r)">
                            <i :class="openNotes.has(r.id) ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'"></i>
                            <span>{{ openNotes.has(r.id) ? 'Hide notes' : 'Release notes' }}</span>
                        </button>
                        <button type="button" class="bd-btn" @click="$emit('view-release', r.version)"
                                title="Browse the bundle exactly as it was in this release">
                            <i class="fa-solid fa-eye"></i><span>View this version</span>
                        </button>
                        <button type="button" class="bd-btn bd-btn--primary" @click="download(r)">
                            <i class="fa-solid fa-file-zipper"></i><span>Download {{ r.version }}</span>
                        </button>
                        <button type="button" class="bd-btn" @click="openCompare(r, 'current')">
                            <i class="fa-solid fa-code-compare"></i><span>vs current</span>
                        </button>
                        <button v-if="releases[idx + 1]" type="button" class="bd-btn" @click="openCompare(releases[idx + 1], r.id)">
                            <i class="fa-solid fa-code-compare"></i><span>vs {{ releases[idx + 1].version }}</span>
                        </button>
                        <button v-if="canManage" type="button" class="bd-btn bd-btn--danger ms-auto"
                                :class="{ 'bd-btn--armed': armedDelete === r.id }" @click="remove(r)">
                            <i class="fa-solid fa-trash"></i><span>{{ armedDelete === r.id ? 'Click again to delete' : 'Delete' }}</span>
                        </button>
                    </div>
                </div>
            </div>
        </template>

        <!-- Compare overlay -->
        <teleport to="body">
            <div v-if="compare" class="bfv-backdrop" @mousedown.self="closeCompare">
                <div class="bfv-dialog" role="dialog" aria-modal="true" aria-label="Compare versions">
                    <div class="bfv-header">
                        <div class="bfv-icon" style="color:#0d6efd;background:rgba(13,110,253,.1);"><i class="fa-solid fa-code-compare"></i></div>
                        <div class="bfv-title-wrap">
                            <div class="bfv-title">{{ compare.fromLabel }} → {{ compare.toLabel }}</div>
                            <div class="bfv-meta" v-if="compare.diff">
                                <span>{{ compare.diff.total }} change{{ compare.diff.total === 1 ? '' : 's' }}</span>
                            </div>
                        </div>
                        <div class="bfv-actions">
                            <button v-if="compare.ruleDiff" type="button" class="bfv-locate" @click="compare.ruleDiff = null">
                                <i class="fa-solid fa-arrow-left"></i><span>Back to the list</span>
                            </button>
                            <button type="button" class="bfv-btn bfv-btn--close" title="Close (Esc)" @click="closeCompare">
                                <i class="fa-solid fa-xmark"></i>
                            </button>
                        </div>
                    </div>
                    <div class="bfv-body">
                        <div v-if="!compare.diff" class="bh-loading"><i class="fas fa-spinner fa-spin me-2"></i>Comparing…</div>

                        <template v-else-if="compare.ruleDiff">
                            <div class="br-rulediff-title"><i class="fa-solid fa-shield-halved me-2"></i>{{ compare.ruleDiff.title }}</div>
                            <diff-viewer :key="compare.ruleDiff.key" :initial-left="compare.ruleDiff.old" :initial-right="compare.ruleDiff.new"
                                         :left-label="compare.fromLabel" :right-label="compare.toLabel"></diff-viewer>
                        </template>

                        <template v-else>
                            <div v-if="!compare.diff.total" class="br-uptodate"><i class="fa-solid fa-circle-check"></i>No difference.</div>
                            <div v-for="grp in compareGroups" :key="grp.key" class="br-grp">
                                <div class="br-grp-title" :class="'br-grp-title--' + grp.tone">
                                    <i :class="grp.icon"></i>{{ grp.label }} <span class="bh-check-count">{{ grp.items.length }}</span>
                                </div>
                                <ul class="bh-items br-grp-items">
                                    <li v-for="it in grp.items" :key="grp.key + (it.rule_id || it)" class="bh-item">
                                        <div class="bh-item-main">
                                            <span class="bh-item-name">{{ it.title || it }}</span>
                                            <span v-if="it.format" class="bh-item-detail">{{ it.format }}</span>
                                        </div>
                                        <div v-if="it.rule_id" class="bh-item-actions">
                                            <button v-if="grp.key === 'rules_changed'" type="button" class="am-rule-act" @click="openRuleDiff(it)">
                                                <i class="fa-solid fa-code-compare"></i><span>Diff</span>
                                            </button>
                                            <a :href="'/rule/detail_rule/' + it.rule_id" target="_blank" rel="noopener" class="am-rule-act">
                                                <i class="fa-solid fa-arrow-up-right-from-square"></i><span>Detail</span>
                                            </a>
                                            <button v-if="grp.key !== 'rules_removed' && compare.to === 'current'" type="button" class="am-rule-act"
                                                    @click="closeCompare(); $emit('show-structure', it.rule_id)">
                                                <i class="fa-solid fa-folder-tree"></i><span>In structure</span>
                                            </button>
                                        </div>
                                    </li>
                                </ul>
                            </div>
                            <div v-if="compare.diff.metadata_changed.length" class="br-grp">
                                <div class="br-grp-title br-grp-title--info"><i class="fa-solid fa-pen"></i>Bundle details changed</div>
                                <div class="bh-check-msg" style="padding-left:24px;">{{ compare.diff.metadata_changed.join(', ') }}</div>
                            </div>
                        </template>
                    </div>
                </div>
            </div>
        </teleport>
    </div>
    `,

    setup(props, { emit }) {
        const releases   = ref([])
        const drift      = ref(null)
        const canManage  = ref(false)
        const loading    = ref(false)
        const loaded     = ref(false)
        const busy       = ref(false)
        const formOpen   = ref(false)
        const formKey    = ref(0)
        const form       = reactive({ version: '', title: '', notes: '' })
        const openNotes  = ref(new Set())
        const notesHtml  = reactive({})
        const armedDelete = ref(null)
        const compare    = ref(null)
        let _armTimer = null

        const latest = computed(() => releases.value[0] || null)
        const driftSummary = computed(() => {
            const d = drift.value
            if (!d) return ''
            const parts = []
            const add = (n, s) => { if (n) parts.push(`${n} ${s}`) }
            add(d.rules_changed.length, 'rule(s) updated')
            add(d.rules_added.length, 'added')
            add(d.rules_removed.length, 'removed')
            add(d.files_added.length + d.files_changed.length + d.files_removed.length, 'file change(s)')
            if (d.metadata_changed.length) parts.push('details: ' + d.metadata_changed.join(', '))
            return parts.join(' · ')
        })
        const compareGroups = computed(() => {
            const d = compare.value?.diff
            if (!d) return []
            return [
                { key: 'rules_changed', label: 'Rules updated', icon: 'fa-solid fa-pen-to-square', tone: 'info',    items: d.rules_changed },
                { key: 'rules_added',   label: 'Rules added',   icon: 'fa-solid fa-plus',          tone: 'ok',      items: d.rules_added },
                { key: 'rules_removed', label: 'Rules removed', icon: 'fa-solid fa-minus',         tone: 'error',   items: d.rules_removed },
                { key: 'files_changed', label: 'Files updated', icon: 'fa-solid fa-file-pen',      tone: 'info',    items: d.files_changed },
                { key: 'files_added',   label: 'Files added',   icon: 'fa-solid fa-file-circle-plus', tone: 'ok',   items: d.files_added },
                { key: 'files_removed', label: 'Files removed', icon: 'fa-solid fa-file-circle-minus', tone: 'error', items: d.files_removed },
            ].filter(g => g.items.length)
        })

        const fmtDate = (iso) => window.dayjs ? dayjs(iso).format('MMM D, YYYY HH:mm') : iso
        const healthCls = (s) => s >= 80 ? 'ok' : s >= 50 ? 'warning' : 'error'
        const json = async (res) => {
            const data = await res.json().catch(() => null)
            if (!res.ok || !data || data.success === false) throw new Error((data && data.message) || `HTTP ${res.status}`)
            return data
        }

        async function load() {
            loading.value = true
            try {
                const data = await json(await fetch(`/bundle/${props.bundleId}/releases`))
                releases.value = data.releases
                drift.value = data.latest_changes
                canManage.value = data.can_manage
                loaded.value = true
                emit('loaded', data)
            } catch (e) {
                create_message('Could not load releases (' + e.message + ')', 'danger-subtle')
            } finally {
                loading.value = false
            }
        }

        async function openForm() {
            try {
                const d = await json(await fetch(`/bundle/${props.bundleId}/releases/draft`))
                form.version = d.suggested_version
                form.title = ''
                form.notes = d.notes
                formKey.value++
                formOpen.value = true
            } catch (e) {
                create_message('Could not prepare the release (' + e.message + ')', 'danger-subtle')
            }
        }

        async function publish() {
            busy.value = true
            try {
                const data = await json(await fetch(`/bundle/${props.bundleId}/releases`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ ...form }),
                }))
                create_message(data.message, data.toast_class || 'success-subtle')
                formOpen.value = false
                await load()
                emit('changed')
            } catch (e) {
                create_message(e.message, 'danger-subtle')
            } finally {
                busy.value = false
            }
        }

        async function remove(r) {
            if (armedDelete.value !== r.id) {
                armedDelete.value = r.id
                clearTimeout(_armTimer)
                _armTimer = setTimeout(() => { armedDelete.value = null }, 3500)
                return
            }
            armedDelete.value = null
            try {
                const data = await json(await fetch(`/bundle/${props.bundleId}/releases/${r.id}`, {
                    method: 'DELETE', headers: { 'X-CSRFToken': props.csrfToken },
                }))
                create_message(data.message, data.toast_class || 'success-subtle')
                await load()
                emit('changed')
            } catch (e) {
                create_message(e.message, 'danger-subtle')
            }
        }

        async function toggleNotes(r) {
            const s = new Set(openNotes.value)
            if (s.has(r.id)) s.delete(r.id)
            else {
                s.add(r.id)
                if (!notesHtml[r.id]) notesHtml[r.id] = await renderSafeMarkdown(r.notes)
            }
            openNotes.value = s
        }

        function copyUuid(u) {
            navigator.clipboard.writeText(u)
                .then(() => create_message('Release UUID copied', 'success-subtle'))
                .catch(() => create_message('Could not copy the UUID', 'danger-subtle'))
        }

        function download(r) {
            downloadFromUrl(`/bundle/${props.bundleId}/releases/${r.id}/download`, `bundle_${r.version}.zip`)
        }

        // base = older side (a release), to = release id or 'current'
        async function openCompare(base, to) {
            const toLabel = to === 'current' ? 'current bundle' : (releases.value.find(x => x.id === to)?.version || '?')
            compare.value = { base: base.id, to, fromLabel: base.version, toLabel, diff: null, ruleDiff: null }
            try {
                const d = await json(await fetch(`/bundle/${props.bundleId}/releases/${base.id}/changes?against=${to}`))
                if (compare.value && compare.value.base === base.id) compare.value.diff = d.diff
            } catch (e) {
                create_message('Could not compare (' + e.message + ')', 'danger-subtle')
                compare.value = null
            }
        }
        async function openRuleDiff(it) {
            const c = compare.value
            try {
                const d = await json(await fetch(`/bundle/${props.bundleId}/releases/${c.base}/rule/${it.rule_id}/diff?against=${c.to}`))
                c.ruleDiff = { key: `${c.base}-${c.to}-${it.rule_id}`, title: d.title, old: d.old, new: d.new }
            } catch (e) {
                create_message('Could not load the diff (' + e.message + ')', 'danger-subtle')
            }
        }
        function closeCompare() { compare.value = null }
        document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape' && compare.value) closeCompare() })

        watch(() => props.active, (a) => { if (a) load() })
        load()                                   // header badge needs the latest version right away

        return {
            releases, drift, canManage, loading, loaded, busy, formOpen, formKey, form, openNotes, notesHtml,
            armedDelete, compare, latest, driftSummary, compareGroups,
            fmtDate, healthCls, copyUuid, openForm, publish, remove, toggleNotes, download, openCompare, openRuleDiff, closeCompare,
        }
    },
}
