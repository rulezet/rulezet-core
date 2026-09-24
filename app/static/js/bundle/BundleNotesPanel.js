/**
 * BundleNotesPanel.js — "Notes" tab: community notes / known issues on a
 * bundle ("⚠ this bundle doesn't work if…"), written in Markdown.
 *
 * Who can do what is decided server-side (/bundle/<id>/notes): anyone who
 * can view the bundle reads; logged-in users write while the bundle is
 * public; authors edit/delete their own notes; owner/admin resolve.
 *
 * Props:  bundleId, csrfToken, isAuthenticated
 * Emits:  loaded({ open, notes })
 */

import SmartEditor from '/static/js/components/smart-editor.js'
import { create_message } from '/static/js/toaster.js'
import { renderSafeMarkdown } from '/static/js/bundle/bundleFileTypes.js'

const { ref, reactive, computed } = Vue

const SEVERITY = {
    critical: { label: 'Critical', icon: 'fa-solid fa-circle-exclamation' },
    warning:  { label: 'Warning',  icon: 'fa-solid fa-triangle-exclamation' },
    info:     { label: 'Info',     icon: 'fa-solid fa-circle-info' },
}

export default {
    name: 'BundleNotesPanel',
    components: { SmartEditor },

    props: {
        bundleId:        { type: [Number, String], required: true },
        csrfToken:       { type: String, default: '' },
        isAuthenticated: { type: Boolean, default: false },
    },

    emits: ['loaded'],

    template: `
    <div class="bn-root">
        <!-- Write -->
        <div v-if="canCreate && !form.open" class="bn-new">
            <button type="button" class="bd-btn bd-btn--primary" @click="openForm()">
                <i class="fa-solid fa-plus"></i><span>Add a note</span>
            </button>
            <span class="bn-hint">Known issue, deployment caveat, false positive… visible to everyone who can see the bundle.</span>
        </div>
        <div v-else-if="!canCreate && loaded && !loadError" class="bn-blocked">
            <i class="fa-solid fa-lock"></i>
            <span v-if="!isAuthenticated">Log in to add a note.</span>
            <span v-else>{{ blockedReason || 'You cannot add notes to this bundle.' }}</span>
        </div>

        <div v-if="form.open" class="bn-form">
            <div class="br-form-row">
                <label class="br-field br-field--grow">
                    <span>Title</span>
                    <input type="text" v-model="form.title" maxlength="200" placeholder="e.g. Suricata rules need the HTTP app-layer enabled">
                </label>
                <label class="br-field">
                    <span>Severity</span>
                    <select v-model="form.severity" class="bn-select">
                        <option value="info">Info</option>
                        <option value="warning">Warning</option>
                        <option value="critical">Critical</option>
                    </select>
                </label>
            </div>
            <div class="br-field">
                <span>Note <em>(Markdown)</em></span>
                <smart-editor :key="form.key" v-model="form.content" mode="markdown" min-height="160px" max-height="420px"
                    placeholder="Explain what doesn't work, in which setup, and any workaround."></smart-editor>
            </div>
            <div class="br-form-actions">
                <button type="button" class="bd-btn bd-btn--ghost" @click="form.open = false">Cancel</button>
                <button type="button" class="bd-btn bd-btn--primary" @click="save" :disabled="busy">
                    <i :class="busy ? 'fas fa-spinner fa-spin' : 'fa-solid fa-paper-plane'"></i>
                    <span>{{ form.id ? 'Save changes' : 'Publish note' }}</span>
                </button>
            </div>
        </div>

        <!-- List -->
        <div v-if="loading && !loaded" class="bh-loading"><i class="fas fa-spinner fa-spin me-2"></i>Loading notes…</div>
        <div v-else-if="loadError && !notes.length" class="bn-blocked">
            <i class="fa-regular fa-note-sticky"></i><span>Notes are not available right now.</span>
        </div>
        <div v-else-if="!notes.length && !form.open" class="br-empty">
            <i class="fa-regular fa-note-sticky"></i>
            <div><strong>No notes yet.</strong><span>Nobody reported a known issue on this bundle.</span></div>
        </div>

        <div class="bn-list">
            <article v-for="n in notes" :key="n.id" class="bn-note" :class="['bn-note--' + n.severity, { 'bn-note--resolved': n.status === 'resolved' }]">
                <header class="bn-head">
                    <i :class="SEVERITY[n.severity].icon + ' bn-sev-icon'"></i>
                    <div class="bn-head-main">
                        <div class="bn-title">{{ n.title }}</div>
                        <div class="bn-meta">
                            <span class="bn-sev">{{ SEVERITY[n.severity].label }}</span>
                            <span v-if="n.status === 'resolved'" class="bn-resolved"><i class="fa-solid fa-check"></i>Resolved<template v-if="n.resolved_by"> by {{ n.resolved_by }}</template></span>
                            <span>{{ n.user_name || 'Deleted user' }} · {{ fmt(n.created_at) }}<template v-if="n.updated_at !== n.created_at"> · edited</template></span>
                        </div>
                    </div>
                    <div class="bn-actions">
                        <button v-if="n.can_resolve" type="button" class="bfv-btn" :title="n.status === 'open' ? 'Mark as resolved' : 'Reopen'" @click="setStatus(n)">
                            <i :class="n.status === 'open' ? 'fa-solid fa-check' : 'fa-solid fa-rotate-left'"></i>
                        </button>
                        <button v-if="n.can_edit" type="button" class="bfv-btn" title="Edit" @click="openForm(n)"><i class="fa-solid fa-pen"></i></button>
                        <button v-if="n.can_delete" type="button" class="bfv-btn bfv-btn--close" :class="{ 'bn-armed': armed === n.id }"
                                :title="armed === n.id ? 'Click again to delete' : 'Delete'" @click="remove(n)"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </header>
                <div class="bfv-md bn-body" v-html="html[n.id] || ''"></div>
            </article>
        </div>
    </div>
    `,

    setup(props, { emit }) {
        const notes = ref([])
        const html = reactive({})
        const loading = ref(false)
        const loaded = ref(false)
        const busy = ref(false)
        const canCreate = ref(false)
        const blockedReason = ref('')
        const armed = ref(null)
        const loadError = ref('')
        const form = reactive({ open: false, id: null, title: '', content: '', severity: 'warning', key: 0 })
        let armT = null

        const fmt = (iso) => window.dayjs ? dayjs(iso).format('MMM D, YYYY HH:mm') : iso
        const json = async (res) => {
            const d = await res.json().catch(() => null)
            if (!res.ok || !d || d.success === false) throw new Error((d && d.message) || `HTTP ${res.status}`)
            return d
        }
        const H = () => ({ 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken })

        async function load() {
            loading.value = true
            try {
                const d = await json(await fetch(`/bundle/${props.bundleId}/notes`))
                loadError.value = ''
                notes.value = d.notes
                canCreate.value = d.can_create
                blockedReason.value = d.create_blocked_reason || ''
                for (const n of d.notes) html[n.id] = await renderSafeMarkdown(n.content)
                loaded.value = true
                emit('loaded', { open: d.open, notes: d.notes })
            } catch (e) {
                // No toast for the list itself — an empty / unavailable list is
                // not an error the user can act on; show it inline instead.
                loadError.value = String(e.message || e)
                loaded.value = true
            } finally {
                loading.value = false
            }
        }

        function openForm(n = null) {
            Object.assign(form, n
                ? { open: true, id: n.id, title: n.title, content: n.content, severity: n.severity }
                : { open: true, id: null, title: '', content: '', severity: 'warning' })
            form.key++
        }

        async function save() {
            busy.value = true
            try {
                const url = form.id ? `/bundle/${props.bundleId}/notes/${form.id}` : `/bundle/${props.bundleId}/notes`
                const d = await json(await fetch(url, {
                    method: form.id ? 'PUT' : 'POST', headers: H(),
                    body: JSON.stringify({ title: form.title, content: form.content, severity: form.severity }),
                }))
                create_message(d.message, 'success-subtle')
                form.open = false
                await load()
            } catch (e) {
                create_message(e.message, 'danger-subtle')
            } finally {
                busy.value = false
            }
        }

        async function setStatus(n) {
            try {
                const d = await json(await fetch(`/bundle/${props.bundleId}/notes/${n.id}/status`, {
                    method: 'POST', headers: H(), body: JSON.stringify({ status: n.status === 'open' ? 'resolved' : 'open' }),
                }))
                create_message(d.message, 'success-subtle')
                await load()
            } catch (e) { create_message(e.message, 'danger-subtle') }
        }

        async function remove(n) {
            if (armed.value !== n.id) {
                armed.value = n.id
                clearTimeout(armT)
                armT = setTimeout(() => { armed.value = null }, 3500)
                return
            }
            armed.value = null
            try {
                const d = await json(await fetch(`/bundle/${props.bundleId}/notes/${n.id}`, { method: 'DELETE', headers: H() }))
                create_message(d.message, 'success-subtle')
                await load()
            } catch (e) { create_message(e.message, 'danger-subtle') }
        }

        load()
        return { notes, html, loading, loaded, loadError, busy, canCreate, blockedReason, armed, form, fmt, openForm, save, setStatus, remove, SEVERITY }
    },
}
