/**
 * workflowNotebook.js — under a workflow's launch history: its markdown notes (why it exists,
 * what to do when it fails, what happened on one launch), attached files and activity feed.
 * Admin page only (routes under /admin/tasks/workflows/<uuid>/…, see workflow_notes.py).
 *
 * Props:  workflowUuid, csrfToken, runs ([{uuid, started_at, status}] — to tie a note to a launch),
 *         readOnly + apiBase — the shared read-only page (/workflow/shared/<key>): no edit, no upload, no delete
 * Exposed: newNote(runUuid?) — the history table opens the editor on a launch with it.
 * Emits:  'changed' — a note was saved / deleted (the history refreshes its note counts).
 */
import { create_message } from '/static/js/toaster.js';
import { renderMarkdown } from '/static/js/sanitize.js';

const { ref, reactive, computed, onMounted, watch } = Vue;

export default {
    name: 'WorkflowNotebook',
    delimiters: ['[[', ']]'],
    props: {
        workflowUuid: { type: String, required: true },
        csrfToken: { type: String, default: '' },
        readOnly: { type: Boolean, default: false },
        apiBase: { type: String, default: '' },
        runs: { type: Array, default: () => [] },
    },
    emits: ['changed'],
    setup(props, { emit, expose }) {
        const tab = ref('notes');
        const notes = ref([]);
        const files = ref([]);
        const activity = ref([]);
        const maxMb = ref(10);
        const loading = ref(true);
        const rendered = reactive({});          // note uuid → sanitized HTML
        const open = reactive({});              // note uuid → expanded
        const editor = reactive({ show: false, uuid: null, title: '', content: '', pinned: false, run_uuid: '', preview: false, html: '' });
        const saving = ref(false);
        const uploading = ref(false);
        const dragOver = ref(false);
        const fileInput = ref(null);
        const runFilter = ref('');

        const base = computed(() => props.apiBase || `/admin/tasks/workflows/${encodeURIComponent(props.workflowUuid)}`);
        const shownNotes = computed(() => runFilter.value ? notes.value.filter(n => n.run_uuid === runFilter.value) : notes.value);

        async function load() {
            loading.value = true;
            try {
                const res = await fetch(`${base.value}/notebook`);
                if (!res.ok) return;
                const data = await res.json();
                notes.value = data.notes; files.value = data.files; activity.value = data.activity; maxMb.value = data.max_file_mb;
                for (const n of notes.value) {
                    rendered[n.uuid] = await renderMarkdown(n.content);
                    if (n.pinned && open[n.uuid] === undefined) open[n.uuid] = true;
                }
            } finally {
                loading.value = false;
            }
        }

        function newNote(runUuid) {
            Object.assign(editor, { show: true, uuid: null, title: '', content: '', pinned: false, run_uuid: runUuid || '', preview: false, html: '' });
            if (runUuid) {
                const r = props.runs.find(x => x.uuid === runUuid);
                editor.title = r ? `Launch of ${r.started_at} (${r.status})` : 'About a launch';
            }
            tab.value = 'notes';
        }
        function editNote(n) {
            Object.assign(editor, { show: true, uuid: n.uuid, title: n.title, content: n.content, pinned: n.pinned, run_uuid: n.run_uuid || '', preview: false, html: '' });
        }
        async function togglePreview() {
            editor.preview = !editor.preview;
            if (editor.preview) editor.html = await renderMarkdown(editor.content);
        }

        async function saveNote() {
            saving.value = true;
            try {
                const url = editor.uuid ? `${base.value}/notes/${editor.uuid}` : `${base.value}/notes`;
                const res = await fetch(url, {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                    body: JSON.stringify({ title: editor.title, content: editor.content, pinned: editor.pinned, run_uuid: editor.run_uuid || null }),
                });
                const data = await res.json();
                create_message(data.message, data.toast_class);
                if (res.ok) {
                    editor.show = false;
                    open[data.note.uuid] = true;
                    await load();
                    emit('changed');
                }
            } finally {
                saving.value = false;
            }
        }

        async function remove(kind, item) {
            const label = kind === 'notes' ? `the note "${item.title}"` : `the file "${item.filename}"`;
            if (!window.confirm(`Delete ${label}?`)) return;
            const res = await fetch(`${base.value}/${kind}/${item.uuid}`, { method: 'DELETE', headers: { 'X-CSRFToken': props.csrfToken } });
            const data = await res.json();
            create_message(data.message, data.toast_class);
            if (res.ok) { await load(); if (kind === 'notes') emit('changed'); }
        }

        async function togglePin(n) {
            const res = await fetch(`${base.value}/notes/${n.uuid}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': props.csrfToken },
                body: JSON.stringify({ title: n.title, content: n.content, pinned: !n.pinned, run_uuid: n.run_uuid }),
            });
            if (res.ok) await load();
        }

        async function upload(fileList) {
            const list = [...(fileList || [])];
            if (!list.length) return;
            uploading.value = true;
            try {
                for (const f of list) {
                    if (f.size > maxMb.value * 1024 * 1024) { create_message(`${f.name}: more than ${maxMb.value} MB.`, 'danger-subtle'); continue; }
                    const body = new FormData();
                    body.append('file', f);
                    const res = await fetch(`${base.value}/files`, { method: 'POST', headers: { 'X-CSRFToken': props.csrfToken }, body });
                    const data = await res.json();
                    create_message(res.ok ? `${f.name} attached.` : data.message, data.toast_class);
                }
                await load();
            } finally {
                uploading.value = false;
                if (fileInput.value) fileInput.value.value = '';
            }
        }
        function onDrop(e) { dragOver.value = false; upload(e.dataTransfer.files); }

        function size(b) {
            if (b < 1024) return `${b} B`;
            if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
            return `${(b / 1024 / 1024).toFixed(1)} MB`;
        }
        function fileIcon(name) {
            const ext = (name.split('.').pop() || '').toLowerCase();
            if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return 'fa-file-image';
            if (['json', 'yml', 'yaml', 'py', 'sh', 'yar', 'yara', 'rules', 'xml'].includes(ext)) return 'fa-file-code';
            if (['md', 'txt', 'log'].includes(ext)) return 'fa-file-lines';
            if (ext === 'pdf') return 'fa-file-pdf';
            if (['csv', 'xlsx', 'xls'].includes(ext)) return 'fa-file-csv';
            if (['zip', 'gz', 'tar', '7z'].includes(ext)) return 'fa-file-zipper';
            return 'fa-file';
        }

        expose({ newNote, reload: load });
        onMounted(load);
        watch(() => props.workflowUuid, load);

        return { tab, notes, files, activity, maxMb, loading, rendered, open, editor, saving, uploading, dragOver, fileInput,
                 runFilter, shownNotes, base, newNote, editNote, togglePreview, saveNote, remove, togglePin, upload, onDrop, size, fileIcon };
    },
    template: `
    <div class="card border-0 shadow-sm rounded-3 mt-4 wnb">
        <div class="card-body p-3 p-md-4">
            <div class="wnb-head">
                <div class="d-flex align-items-center gap-2">
                    <div class="wnb-bar"></div>
                    <span class="wnb-title"><i class="fa-solid fa-book me-1"></i>Notebook</span>
                </div>
                <div class="wnb-tabs" role="tablist">
                    <button type="button" :class="{ 'is-on': tab === 'notes' }" @click="tab = 'notes'"><i class="fa-solid fa-note-sticky"></i>Notes <span>[[ notes.length ]]</span></button>
                    <button type="button" :class="{ 'is-on': tab === 'files' }" @click="tab = 'files'"><i class="fa-solid fa-paperclip"></i>Files <span>[[ files.length ]]</span></button>
                    <button type="button" :class="{ 'is-on': tab === 'activity' }" @click="tab = 'activity'"><i class="fa-solid fa-wave-square"></i>Activity</button>
                </div>
            </div>

            <div v-if="loading" class="text-muted small py-3"><span class="spinner-border spinner-border-sm me-2"></span>Loading…</div>

            <!-- Notes -->
            <template v-else-if="tab === 'notes'">
                <div class="wnb-toolbar">
                    <select v-if="notes.some(n => n.run_uuid)" class="form-select form-select-sm wnb-select" v-model="runFilter">
                        <option value="">Every note</option>
                        <option v-for="r in runs.filter(r => notes.some(n => n.run_uuid === r.uuid))" :key="r.uuid" :value="r.uuid">Launch of [[ r.started_at ]]</option>
                    </select>
                    <button v-if="!editor.show && !readOnly" type="button" class="btn btn-sm btn-primary rounded-pill ms-auto" @click="newNote()">
                        <i class="fa-solid fa-plus me-1"></i>New note
                    </button>
                </div>

                <div v-if="editor.show && !readOnly" class="wnb-editor">
                    <input class="form-control wnb-input" v-model="editor.title" maxlength="200" placeholder="Title — e.g. Why this workflow exists, What to do when it fails">
                    <div class="wnb-editor-row">
                        <select class="form-select form-select-sm wnb-select" v-model="editor.run_uuid">
                            <option value="">About the whole workflow</option>
                            <option v-for="r in runs" :key="r.uuid" :value="r.uuid">About the launch of [[ r.started_at ]] ([[ r.status ]])</option>
                        </select>
                        <label class="wnb-check"><input type="checkbox" v-model="editor.pinned"> <i class="fa-solid fa-thumbtack"></i> Pinned on top</label>
                        <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill ms-auto" @click="togglePreview()">
                            <i :class="editor.preview ? 'fa-solid fa-pen' : 'fa-solid fa-eye'" class="me-1"></i>[[ editor.preview ? 'Write' : 'Preview' ]]
                        </button>
                    </div>
                    <textarea v-if="!editor.preview" class="form-control wnb-textarea" v-model="editor.content" rows="9"
                              placeholder="Markdown: **bold**, lists, links, \`code\`, tables…"></textarea>
                    <div v-else class="wnb-md wnb-preview" v-html="editor.html || '<em>Nothing to preview.</em>'"></div>
                    <div class="d-flex gap-2 justify-content-end mt-2">
                        <button type="button" class="btn btn-sm btn-light rounded-pill" @click="editor.show = false">Cancel</button>
                        <button type="button" class="btn btn-sm btn-primary rounded-pill" :disabled="saving || !editor.title.trim()" @click="saveNote()">
                            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>Save
                        </button>
                    </div>
                </div>

                <div v-if="!shownNotes.length && !editor.show" class="wnb-empty">
                    <i class="fa-solid fa-note-sticky"></i>
                    <div v-if="readOnly">No note.</div><div v-else>No note yet. Write what this workflow is for, what to check when it fails, or what happened on a launch.</div>
                </div>
                <div v-for="n in shownNotes" :key="n.uuid" class="wnb-note" :class="{ 'is-pinned': n.pinned }">
                    <div class="wnb-note-head" @click="open[n.uuid] = !open[n.uuid]">
                        <i class="fa-solid fa-chevron-right wnb-caret" :class="{ 'is-open': open[n.uuid] }"></i>
                        <i v-if="n.pinned" class="fa-solid fa-thumbtack wnb-pin"></i>
                        <span class="wnb-note-title">[[ n.title ]]</span>
                        <span v-if="n.run_uuid" class="wnb-chip"><i class="fa-solid fa-rocket"></i>Launch [[ n.run_started_at ]]</span>
                        <span class="wnb-meta">[[ n.author || '—' ]] · [[ n.updated_at ]]</span>
                        <span v-if="!readOnly" class="wnb-actions" @click.stop>
                            <button type="button" :title="n.pinned ? 'Unpin' : 'Pin on top'" @click="togglePin(n)"><i class="fa-solid fa-thumbtack"></i></button>
                            <button type="button" title="Edit" @click="editNote(n)"><i class="fa-solid fa-pen"></i></button>
                            <button type="button" title="Delete" class="is-danger" @click="remove('notes', n)"><i class="fa-solid fa-trash"></i></button>
                        </span>
                    </div>
                    <div v-if="open[n.uuid]" class="wnb-md" v-html="rendered[n.uuid] || '<em>Empty note.</em>'"></div>
                </div>
            </template>

            <!-- Files -->
            <template v-else-if="tab === 'files'">
                <label v-if="!readOnly" class="wnb-drop" :class="{ 'is-over': dragOver, 'is-busy': uploading }"
                       @dragover.prevent="dragOver = true" @dragleave.prevent="dragOver = false" @drop.prevent="onDrop">
                    <input ref="fileInput" type="file" multiple hidden @change="upload($event.target.files)">
                    <i :class="uploading ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-cloud-arrow-up'"></i>
                    <span><strong>Drop files here</strong> or click to choose — runbook, exported config, screenshot… ([[ maxMb ]] MB max each)</span>
                </label>
                <div v-if="!files.length" class="wnb-empty"><i class="fa-solid fa-paperclip"></i><div>No file attached.</div></div>
                <div v-for="f in files" :key="f.uuid" class="wnb-file">
                    <i class="fa-solid wnb-file-icon" :class="fileIcon(f.filename)"></i>
                    <div class="wnb-file-body">
                        <a :href="base + '/files/' + f.uuid" class="wnb-file-name">[[ f.filename ]]</a>
                        <div class="wnb-meta">[[ size(f.size) ]] · [[ f.uploader || '—' ]] · [[ f.created_at ]]</div>
                    </div>
                    <span class="wnb-actions">
                        <a :href="base + '/files/' + f.uuid" title="Download"><i class="fa-solid fa-download"></i></a>
                        <button v-if="!readOnly" type="button" title="Delete" class="is-danger" @click="remove('files', f)"><i class="fa-solid fa-trash"></i></button>
                    </span>
                </div>
            </template>

            <!-- Activity -->
            <template v-else>
                <div v-if="!activity.length" class="wnb-empty"><i class="fa-solid fa-wave-square"></i><div>Nothing recorded yet.</div></div>
                <ol class="wnb-feed">
                    <li v-for="(a, i) in activity" :key="i">
                        <span class="wnb-feed-dot"><i :class="a.icon || 'fa-solid fa-circle'"></i></span>
                        <div>
                            <div class="wnb-feed-text">[[ a.description || a.title || a.action ]]</div>
                            <div class="wnb-meta">[[ a.user || 'Rulezet' ]] · [[ a.created_at ]] · <code>[[ a.action ]]</code></div>
                        </div>
                    </li>
                </ol>
            </template>
        </div>
    </div>`,
};
