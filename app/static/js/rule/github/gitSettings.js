// Git tokens & hosts (templates/rule/url_github/git_settings.html, backend
// features/rule/rule_from_github/git_settings): admins and Git Managers set
// the GitHub token / host and the other git hosts and their tokens, and pull
// or clear the cache of cloned repositories.
import { create_message } from '/static/js/toaster.js';

const { createApp, ref, onMounted } = Vue;

const csrf = () => document.getElementById('csrf_token')?.value || '';

createApp({
    delimiters: ['[[', ']]'],
    setup() {
        const loading = ref(true);
        const cfg = ref(null);
        const editing = ref(null);
        const draft = ref('');
        const saving = ref(false);
        const testing = ref(false);
        const test = ref(null);

        async function load() {
            cfg.value = await fetch('/rule/github/settings/data').then(r => r.json());
            loading.value = false;
        }

        function edit(key, current = '') {
            editing.value = key;
            draft.value = current;   // secrets start empty: they are never sent back
        }
        function cancel() { editing.value = null; draft.value = ''; }

        async function save(key) {
            saving.value = true;
            try {
                const res = await fetch('/rule/github/settings/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf(), Accept: 'application/json' },
                    body: JSON.stringify({ key, value: draft.value }),
                });
                const data = await res.json().catch(() => ({ success: false, message: `HTTP ${res.status}` }));
                create_message(data.message, data.success ? 'success-subtle' : 'danger-subtle');
                if (data.success) {
                    cancel();
                    test.value = null;
                    await load();
                    if (key === 'GITHUB_TOKEN') testGithub();
                }
            } finally {
                saving.value = false;
            }
        }

        async function testGithub() {
            testing.value = true;
            try {
                const res = await fetch('/rule/github/settings/test_github_token', {
                    method: 'POST', headers: { 'X-CSRFToken': csrf(), Accept: 'application/json' },
                });
                test.value = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
            } finally {
                testing.value = false;
            }
        }

        // ── Clone cache ──
        const cache = ref(null);
        const clearing = ref(false);
        const confirmClear = ref(false);
        let confirmTimer = null;

        async function loadCache() {
            cache.value = await fetch('/rule/github/settings/cache').then(r => r.json()).catch(() => null);
        }

        function formatSize(bytes) {
            const units = ['B', 'KB', 'MB', 'GB'];
            let i = 0;
            while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
            return `${bytes.toFixed(i ? 1 : 0)} ${units[i]}`;
        }

        // Two clicks instead of a confirm() dialog: the first arms the button for 4 s.
        async function clearCache() {
            if (!confirmClear.value) {
                confirmClear.value = true;
                clearTimeout(confirmTimer);
                confirmTimer = setTimeout(() => { confirmClear.value = false; }, 4000);
                return;
            }
            confirmClear.value = false;
            clearing.value = true;
            try {
                const res = await fetch('/rule/github/settings/cache/clear', {
                    method: 'POST', headers: { 'X-CSRFToken': csrf(), Accept: 'application/json' },
                });
                const data = await res.json().catch(() => ({ success: false, message: `HTTP ${res.status}` }));
                create_message(data.message, data.success ? 'success-subtle' : 'danger-subtle');
                await loadCache();
            } finally {
                clearing.value = false;
            }
        }

        const pulling = ref(false);
        const pullJob = ref(null);
        async function pullAll() {
            pulling.value = true;
            try {
                const res = await fetch('/rule/github/settings/cache/pull', {
                    method: 'POST', headers: { 'X-CSRFToken': csrf(), Accept: 'application/json' },
                });
                const data = await res.json().catch(() => ({ success: false, message: `HTTP ${res.status}` }));
                create_message(data.message, data.success ? 'success-subtle' : 'danger-subtle');
                if (data.job_uuid) pullJob.value = data.job_uuid;
            } finally {
                pulling.value = false;
            }
        }

        onMounted(() => { load(); loadCache(); });
        return {
            loading, cfg, editing, draft, saving, testing, test, edit, cancel, save, testGithub,
            cache, clearing, confirmClear, clearCache, formatSize, pulling, pullJob, pullAll,
        };
    },
}).mount('#main-container');
