/**
 * issue-report.js — the "Create issue" window: a Markdown report (rule evaluation, or a Git source's
 * import problems — app/features/rule/issue_report.py) to post as an issue on its repository.
 * Preview / editable Markdown, Copy, Download .md, Open an issue on GitHub / GitLab / Gitea.
 *
 * One per page is enough: any button opens it with
 *     window.dispatchEvent(new CustomEvent('rz:issue-report', { detail: { url: '/rule/42/issue_report' } }))
 * or the helper openIssueReport(url). Several instances on a page: only the first one listens.
 * Its stylesheet (css/components/issue-report.css) is added by the component itself.
 */
import { create_message } from '/static/js/toaster.js';
import { renderMarkdown } from '/static/js/sanitize.js';

const { ref, reactive, onMounted, onUnmounted } = Vue;

if (!document.querySelector('link[data-issue-report-css]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.dataset.issueReportCss = '1';
    link.href = '/static/css/components/issue-report.css' + (new URL(import.meta.url).search || '');
    document.head.appendChild(link);
}

let listening = false;

export function openIssueReport(url) {
    window.dispatchEvent(new CustomEvent('rz:issue-report', { detail: { url } }));
}

const PROVIDER = { github: ['GitHub', 'fa-brands fa-github'], gitlab: ['GitLab', 'fa-brands fa-gitlab'], gitea: ['Gitea / Forgejo', 'fa-solid fa-mug-hot'] };

export default {
    name: 'IssueReport',
    delimiters: ['[[', ']]'],
    setup() {
        const state = reactive({ open: false, loading: false, error: null, data: null, md: '', html: '', tab: 'preview' });
        let owner = false;

        async function open(url) {
            Object.assign(state, { open: true, loading: true, error: null, data: null, md: '', html: '', tab: 'preview' });
            try {
                const res = await fetch(url);
                const data = await res.json().catch(() => ({}));
                if (!res.ok) throw new Error(data.message || 'The report could not be made.');
                state.data = data;
                state.md = data.markdown || '';
                state.html = await renderMarkdown(state.md);
            } catch (e) {
                state.error = e.message;
            } finally {
                state.loading = false;
            }
        }
        const onEvent = (e) => { if (e.detail && e.detail.url) open(e.detail.url); };
        async function showPreview() { state.tab = 'preview'; state.html = await renderMarkdown(state.md); }
        function copy() {
            navigator.clipboard.writeText(state.md).then(() => create_message('Report copied — paste it in the issue.', 'success-subtle'),
                () => create_message('Copy refused by the browser — select the Markdown tab and copy it.', 'warning-subtle'));
        }
        function download() {
            const a = document.createElement('a');
            a.href = URL.createObjectURL(new Blob([state.md], { type: 'text/markdown' }));
            a.download = (state.data && state.data.file_name) || 'rulezet_report.md';
            a.click();
            URL.revokeObjectURL(a.href);
        }
        // The edited text goes in the issue; long reports are cut in the URL (copy the full one first)
        function openIssue() {
            const d = state.data;
            if (!d || !d.repo_url || !d.provider) return;
            const base = d.repo_url.replace(/\/$/, '');
            const max = 6000;
            let body = state.md;
            // Nothing is created: the repository's "new issue" page opens pre-filled, the user posts it
            navigator.clipboard.writeText(state.md).catch(() => {});
            if (body.length > max) {
                body = body.slice(0, max) + '\n\n…_(report cut here — paste the full report from your clipboard)_';
                create_message('The report is long: the page gets the beginning, the full text is in your clipboard.', 'info-subtle');
            } else {
                create_message('New issue page opened, pre-filled (report also in your clipboard). Nothing is posted until you submit it there.', 'info-subtle');
            }
            const q = encodeURIComponent;
            const url = d.provider === 'gitlab'
                ? `${base}/-/issues/new?issue%5Btitle%5D=${q(d.title)}&issue%5Bdescription%5D=${q(body)}`
                : `${base}/issues/new?title=${q(d.title)}&body=${q(body)}`;
            window.open(url, '_blank', 'noopener');
        }

        onMounted(() => {
            if (listening) return;
            listening = owner = true;
            window.addEventListener('rz:issue-report', onEvent);
        });
        onUnmounted(() => { if (owner) { window.removeEventListener('rz:issue-report', onEvent); listening = false; } });

        return { state, showPreview, copy, download, openIssue, PROVIDER };
    },
    template: `
    <teleport to="body">
        <div v-if="state.open" class="irp-modal" @click.self="state.open = false">
            <div class="irp-box" role="dialog" aria-modal="true">
                <div class="irp-head">
                    <div class="irp-title"><i class="fa-solid fa-bug me-2"></i>Create issue</div>
                    <button type="button" class="irp-x" @click="state.open = false" aria-label="Close">×</button>
                </div>
                <div v-if="state.loading" class="irp-body text-center py-5 text-muted">
                    <span class="spinner-border spinner-border-sm me-2"></span>Writing the report…
                </div>
                <div v-else-if="state.error" class="irp-body text-danger">[[ state.error ]]</div>
                <template v-else-if="state.data">
                    <div class="irp-sub">
                        <input class="form-control form-control-sm irp-issue-title" v-model="state.data.title" aria-label="Issue title">
                        <div class="irp-tabs">
                            <button type="button" :class="{ 'is-on': state.tab === 'preview' }" @click="showPreview()"><i class="fa-solid fa-eye"></i>Preview</button>
                            <button type="button" :class="{ 'is-on': state.tab === 'md' }" @click="state.tab = 'md'"><i class="fa-brands fa-markdown"></i>Markdown</button>
                        </div>
                    </div>
                    <div class="irp-body">
                        <div v-if="state.tab === 'preview'" class="irp-preview" v-html="state.html"></div>
                        <textarea v-else class="form-control irp-md" v-model="state.md" spellcheck="false"></textarea>
                    </div>
                    <div class="irp-foot">
                        <span class="irp-hint" v-if="!state.data.provider">
                            <i class="fa-solid fa-circle-info me-1"></i>No GitHub / GitLab / Gitea repository known for it — copy or download the report.
                        </span>
                        <span class="irp-hint" v-else>[[ state.md.length.toLocaleString() ]] characters</span>
                        <div class="irp-actions">
                            <button type="button" class="btn btn-sm btn-light rounded-pill" @click="download()"><i class="fa-solid fa-download me-1"></i>Download .md</button>
                            <button type="button" class="btn btn-sm btn-outline-primary rounded-pill" @click="copy()"><i class="fa-regular fa-copy me-1"></i>Copy</button>
                            <button v-if="state.data.provider" type="button" class="btn btn-sm btn-primary rounded-pill" @click="openIssue()">
                                <i :class="(PROVIDER[state.data.provider] || [])[1]" class="me-1"></i>Go to the new issue page on [[ (PROVIDER[state.data.provider] || [])[0] ]]</button>
                        </div>
                    </div>
                </template>
            </div>
        </div>
    </teleport>`,
};
