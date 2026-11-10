/**
 * pendingUpdateParts.js — small pieces shared by the two Pending git updates
 * pages (list + compare). CSS: css/rule/github/pending_updates.css (pu-*).
 *
 *   <pu-git-line :item="entry" />     provider icon + repo / file link + branch
 *   <pu-status :item="entry" />       Update found / Failed / Accepted / Rejected
 *   <pu-diffstat :added="n" :removed="m" />  +n −m and a 5-block bar
 *
 * `item` = RuleUpdateHistory.to_json(): rule_source, rule_branch,
 * rule_github_path, rule_git_provider, success, message, new_content / has_new_content.
 */
import { gitProviderIcon, gitProviderLabel, repoTreeUrl, repoBlobUrl } from '/static/js/components/git-links.js'

/** 'ready' | 'failed' | 'accepted' | 'rejected' for one update entry. */
export function updateState(item) {
    if (!item) return 'failed'
    if (item.message === 'accepted') return 'accepted'
    if (item.message === 'rejected') return 'rejected'
    const hasContent = 'has_new_content' in item ? item.has_new_content : !!item.new_content
    return item.success && hasContent ? 'ready' : 'failed'
}

function isUrl(s) { return /^https?:\/\//i.test(s || '') }

export const PuGitLine = {
    name: 'PuGitLine',
    delimiters: ['[[', ']]'],
    props: { item: { type: Object, required: true } },
    computed: {
        src()      { return isUrl(this.item.rule_source) ? this.item.rule_source : null },
        provider() { return this.item.rule_git_provider || null },
        icon()     { return gitProviderIcon(this.src, this.provider) },
        label()    { return gitProviderLabel(this.src, this.provider) },
        repoName() { return (this.src || '').replace(/^https?:\/\/[^/]+\//, '').replace(/\.git$/, '') },
        repoUrl()  { return repoTreeUrl(this.src, this.item.rule_branch, this.provider) },
        fileUrl()  { return this.item.rule_github_path ? repoBlobUrl(this.src, this.item.rule_branch, this.item.rule_github_path, this.provider) : null },
    },
    template: `
<div v-if="src" class="pu-git-line">
    <i :class="icon" :title="label"></i>
    <a :href="repoUrl" target="_blank" rel="noreferrer" :title="src">[[ repoName ]]</a>
    <span v-if="item.rule_branch" class="pu-branch"><i class="fa-solid fa-code-branch"></i>[[ item.rule_branch ]]</span>
    <a v-if="fileUrl" :href="fileUrl" target="_blank" rel="noreferrer" :title="item.rule_github_path">
        <i class="fa-regular fa-file-code me-1"></i>[[ item.rule_github_path ]]
    </a>
</div>
<div v-else-if="item.rule_source" class="pu-git-line"><i class="fa-solid fa-file-import"></i><span>[[ item.rule_source ]]</span></div>`,
}

const STATES = {
    ready:    { cls: 'pu-status--ready',    icon: 'fa-circle-check',  text: 'Update found' },
    failed:   { cls: 'pu-status--failed',   icon: 'fa-circle-xmark',  text: 'Failed' },
    accepted: { cls: 'pu-status--accepted', icon: 'fa-check-double',  text: 'Accepted' },
    rejected: { cls: 'pu-status--rejected', icon: 'fa-ban',           text: 'Rejected' },
}

export const PuStatus = {
    name: 'PuStatus',
    delimiters: ['[[', ']]'],
    props: { item: { type: Object, required: true } },
    computed: { s() { return STATES[updateState(this.item)] } },
    template: `<span class="pu-status" :class="s.cls"><i class="fa-solid" :class="s.icon"></i>[[ s.text ]]</span>`,
}

export const PuDiffstat = {
    name: 'PuDiffstat',
    delimiters: ['[[', ']]'],
    props: { added: { type: Number, default: 0 }, removed: { type: Number, default: 0 } },
    computed: {
        blocks() {
            const total = this.added + this.removed
            if (!total) return ['', '', '', '', '']
            const add = Math.round((this.added / total) * 5)
            return Array.from({ length: 5 }, (_, i) => (i < add ? 'add' : 'del'))
        },
    },
    template: `
<span class="pu-diffstat" :title="added + ' line(s) added, ' + removed + ' removed'">
    <span class="pu-diffstat__add">+[[ added ]]</span>
    <span class="pu-diffstat__del">−[[ removed ]]</span>
    <span class="pu-diffstat__bar"><span v-for="(b, i) in blocks" :key="i" :class="b"></span></span>
</span>`,
}
