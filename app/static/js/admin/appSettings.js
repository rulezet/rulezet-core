// Admin Configuration page (templates/admin/app_settings.html, backend
// features/admin/app_settings): edit the admin-editable settings as JSON,
// browse every value written in the code and the data files.
import { create_message } from '/static/js/toaster.js';
import CodeViewer from '/static/js/components/code-viewer.js';
import SmartEditor from '/static/js/components/smart-editor.js';
import DiffViewer from '/static/js/components/diff-viewer.js';

const { createApp, ref, reactive, computed, onMounted, nextTick } = Vue;

const csrf = () => document.getElementById('csrf_token')?.value || '';

async function postJson(url, body) {
    const res = await fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
        body: JSON.stringify(body || {}),
    });
    return res.json();
}

const STATUS_FILTERS = [
    { key: 'all', label: 'All' },
    { key: 'editable', label: 'Editable' },
    { key: 'readonly', label: 'Read-only' },
];
const TABS = ['settings', 'code', 'files'];
const CATEGORY_ICONS = {
    'AI': 'fa-solid fa-robot',
    'Accounts': 'fa-solid fa-user-astronaut',
    'Bundles': 'fa-solid fa-boxes-stacked',
    'Community': 'fa-solid fa-people-group',
    'Formats': 'fa-solid fa-file-shield',
    'Gamification': 'fa-solid fa-trophy',
    'Git sources': 'fa-brands fa-git-alt',
    'Notifications': 'fa-solid fa-bell',
    'Rulesets mirror': 'fa-solid fa-code-branch',
    'Tags': 'fa-solid fa-tags',
};

const pretty = (v) => JSON.stringify(v, null, 2);
const ACTION_LABELS = { saved: 'Saved', reset: 'Reset to the file', merged: 'Merge kept', restored: 'Restored' };
const formatDate = (iso) => (iso ? new Date(iso).toLocaleString() : '');

createApp({
    delimiters: ['[[', ']]'],
    components: { CodeViewer, SmartEditor, DiffViewer },
    setup() {
        const params = new URLSearchParams(location.search);
        const tab = ref(TABS.includes(params.get('tab')) ? params.get('tab') : 'settings');
        const loading = ref(true);
        const settings = ref([]);
        const constants = ref([]);
        const dataFiles = ref([]);
        const drafts = reactive({});
        const modes = reactive({});
        const history = reactive({});
        const openVersion = reactive({});
        const q = ref((params.get('q') || '').slice(0, 100));   // ?q= from a link (e.g. Workflows → Templates)
        const category = ref(null);
        const modifiedOnly = ref(false);
        const statusFilter = ref('all');
        const openRow = ref(null);
        const openFile = ref(null);
        const fileLoading = ref(false);

        async function load() {
            loading.value = true;
            try {
                const data = await fetch('/admin/configuration/data').then(r => r.json());
                settings.value = data.settings;
                constants.value = data.constants;
                dataFiles.value = data.data_files;
                for (const s of data.settings) drafts[s.key] = { text: pretty(s.value), busy: false, error: null };
            } finally {
                loading.value = false;
            }
        }

        function setTab(t) {
            tab.value = t;
            q.value = '';
            const url = new URL(location);
            if (t === 'settings') url.searchParams.delete('tab'); else url.searchParams.set('tab', t);
            history.replaceState(null, '', url);
        }

        function openSettings(changedOnly) {
            modifiedOnly.value = changedOnly;
            category.value = null;
            setTab('settings');
        }

        // ── Settings ──
        const categories = computed(() => [...new Set(settings.value.map(s => s.category))].sort());
        const modifiedCount = computed(() => settings.value.filter(s => s.overridden).length);
        const categoryIcon = (cat) => CATEGORY_ICONS[cat] || 'fa-solid fa-sliders';

        const matches = (...fields) => {
            const needle = q.value.trim().toLowerCase();
            return !needle || fields.some(f => (f || '').toLowerCase().includes(needle));
        };

        const visibleSettings = (cat) => settings.value.filter(s =>
            (!cat || s.category === cat)
            && (!modifiedOnly.value || s.overridden)
            && matches(s.label, s.key, s.description, s.category));

        const itemCount = (v) => (Array.isArray(v) ? v.length : (v && typeof v === 'object' ? Object.keys(v).length : 1));

        const mode = (s) => modes[s.key] || 'view';
        function setMode(s, m) {
            if (m === 'edit' && mode(s) !== 'edit') drafts[s.key].text = pretty(s.value);
            if (m === 'history') loadHistory(s);
            modes[s.key] = m;
        }

        async function loadHistory(s) {
            history[s.key] = null;
            const data = await fetch('/admin/configuration/' + s.key + '/history').then(r => r.json());
            history[s.key] = data.success ? data.history : [];
        }

        // Reload one setting's state (value, merge flag…) after a change.
        async function refreshSetting(s) {
            const data = await fetch('/admin/configuration/data').then(r => r.json());
            const fresh = data.settings.find(x => x.key === s.key);
            if (fresh) Object.assign(s, fresh);
            drafts[s.key] = { text: pretty(s.value), busy: false, error: null };
            if (mode(s) === 'history') loadHistory(s);
        }

        async function acceptMerge(s) {
            drafts[s.key].busy = true;
            const data = await postJson('/admin/configuration/' + s.key + '/accept_merge');
            if (!data.success) { drafts[s.key].busy = false; return create_message(data.message, 'danger-subtle'); }
            await refreshSetting(s);
            create_message(`${s.label} — merge kept`, 'success-subtle');
        }

        async function restoreVersion(s, h) {
            drafts[s.key].busy = true;
            const data = await postJson('/admin/configuration/' + s.key + '/restore/' + h.id);
            if (!data.success) { drafts[s.key].busy = false; return create_message(data.message, 'danger-subtle'); }
            await refreshSetting(s);
            create_message(`${s.label} — version of ${formatDate(h.created_at)} restored`, 'success-subtle');
        }

        function parseDraft(s) {
            try { return { ok: true, value: JSON.parse(drafts[s.key].text) }; }
            catch (e) { return { ok: false, error: 'Invalid JSON — ' + e.message }; }
        }
        const draftError = (s) => drafts[s.key].error || (parseDraft(s).ok ? null : parseDraft(s).error);
        function isDirty(s) {
            const parsed = parseDraft(s);
            return !parsed.ok || pretty(parsed.value) !== pretty(s.value);
        }

        function cancelEdit(s) {
            drafts[s.key] = { text: pretty(s.value), busy: false, error: null };
            modes[s.key] = 'view';
        }

        async function saveSetting(s) {
            const parsed = parseDraft(s);
            if (!parsed.ok) return;
            drafts[s.key].busy = true;
            drafts[s.key].error = null;
            try {
                const data = await postJson('/admin/configuration/' + s.key, { value: parsed.value });
                if (!data.success) {
                    drafts[s.key].error = data.message;
                    return;
                }
                modes[s.key] = 'view';
                await refreshSetting(s);
                create_message(`${s.label} — saved`, 'success-subtle');
            } finally {
                drafts[s.key].busy = false;
            }
        }

        async function resetSetting(s) {
            drafts[s.key].busy = true;
            try {
                const data = await postJson('/admin/configuration/' + s.key + '/reset');
                if (!data.success) return create_message(data.message, 'danger-subtle');
                if (mode(s) !== 'history') modes[s.key] = 'view';
                await refreshSetting(s);
                create_message(`${s.label} — back to the file value`, 'success-subtle');
            } finally {
                if (drafts[s.key]) drafts[s.key].busy = false;
            }
        }

        // ── Values in the code ──
        const statusOf = (c) => (c.setting_key ? 'editable' : 'readonly');
        const statusCount = (key) => constants.value.filter(c => key === 'all' || statusOf(c) === key).length;
        const filteredConstants = computed(() => constants.value.filter(c =>
            (statusFilter.value === 'all' || statusOf(c) === statusFilter.value)
            && matches(c.name, c.file, c.setting_key)));

        function toggleRow(c) {
            const id = c.file + c.name;
            openRow.value = openRow.value === id ? null : id;
        }

        async function goToSetting(key) {
            const s = settings.value.find(x => x.key === key);
            modifiedOnly.value = false;
            category.value = s ? s.category : null;
            setTab('settings');
            await nextTick();
            document.getElementById('setting-' + key)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        // ── Data files ──
        async function viewFile(f) {
            fileLoading.value = true;
            try {
                const data = await fetch('/admin/configuration/data_file?file=' + encodeURIComponent(f.file)).then(r => r.json());
                if (!data.success) return create_message(data.message, 'danger-subtle');
                openFile.value = { file: data.file, content: data.content };
            } finally {
                fileLoading.value = false;
            }
        }

        onMounted(load);

        return {
            STATUS_FILTERS, ACTION_LABELS, formatDate, history, openVersion, acceptMerge, restoreVersion, tab, loading, settings, constants, dataFiles, drafts, q, category, modifiedOnly, statusFilter,
            openRow, openFile, fileLoading, categories, modifiedCount, categoryIcon, visibleSettings, itemCount, pretty,
            mode, setMode, draftError, isDirty, cancelEdit, saveSetting, resetSetting, statusCount, filteredConstants,
            setTab, openSettings, toggleRow, goToSetting, viewFile,
        };
    },
}).mount('#main-container');
