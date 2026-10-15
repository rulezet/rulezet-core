// Git tokens & hosts (templates/rule/url_github/git_settings.html, backend
// features/rule/rule_from_github/git_settings): admins and Git Managers set
// the GitHub token / host and the other git hosts and their tokens.
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

        onMounted(load);
        return { loading, cfg, editing, draft, saving, testing, test, edit, cancel, save, testGithub };
    },
}).mount('#main-container');
