// Links into a git repository on any host — GitHub, GitLab, Gitea / Forgejo,
// Bitbucket or a plain git server. Each host spells "this branch" and "this
// file" differently in its web UI; everything that builds such a link goes
// through here.

const PUBLIC_HOSTS = {
    'github.com': 'github',
    'gitlab.com': 'gitlab',
    'framagit.org': 'gitlab',
    'salsa.debian.org': 'gitlab',
    'codeberg.org': 'gitea',
    'gitea.com': 'gitea',
    'bitbucket.org': 'bitbucket',
}

export const PROVIDER_LABELS = {
    github: 'GitHub', gitlab: 'GitLab', gitea: 'Gitea', bitbucket: 'Bitbucket', generic: 'Git',
}

export const PROVIDER_ICONS = {
    github: 'fa-brands fa-github', gitlab: 'fa-brands fa-gitlab', gitea: 'fa-solid fa-mug-hot',
    bitbucket: 'fa-brands fa-bitbucket', generic: 'fa-brands fa-git-alt',
}

function hostOf(url) {
    try { return new URL(url).hostname.toLowerCase() } catch { return '' }
}

// provider: pass the server-side value (git_provider.detect_provider) when
// known — a self-hosted GitLab on "git.corp.lan" can't be guessed from its name.
export function gitProvider(url, provider) {
    if (provider) return provider
    const host = hostOf(url)
    if (PUBLIC_HOSTS[host]) return PUBLIC_HOSTS[host]
    if (host.includes('gitlab')) return 'gitlab'
    if (host.includes('gitea') || host.includes('forgejo')) return 'gitea'
    if (host.includes('github')) return 'github'
    return 'generic'
}

export function gitProviderLabel(url, provider) {
    return PROVIDER_LABELS[gitProvider(url, provider)]
}

export function gitProviderIcon(url, provider) {
    return PROVIDER_ICONS[gitProvider(url, provider)]
}

function cleanBase(url) {
    return (url || '').replace(/\/+$/, '').replace(/\.git$/, '')
}

function encodePath(path) {
    return path.split('/').map(encodeURIComponent).join('/')
}

// Web page of a branch (or the repo itself when no branch).
export function repoTreeUrl(url, branch, provider) {
    const base = cleanBase(url)
    if (!branch) return base
    const b = encodePath(branch)
    switch (gitProvider(url, provider)) {
        case 'gitlab':    return `${base}/-/tree/${b}`
        case 'gitea':     return `${base}/src/branch/${b}`
        case 'bitbucket': return `${base}/src/${b}`
        default:          return `${base}/tree/${b}`
    }
}

// Commit history of a branch (or of the default branch).
export function repoCommitsUrl(url, branch, provider) {
    const base = cleanBase(url)
    const b = branch ? encodePath(branch) : ''
    switch (gitProvider(url, provider)) {
        case 'gitlab':    return b ? `${base}/-/commits/${b}` : `${base}/-/commits`
        case 'gitea':     return b ? `${base}/commits/branch/${b}` : `${base}/commits`
        case 'bitbucket': return b ? `${base}/commits/branch/${b}` : `${base}/commits`
        default:          return b ? `${base}/commits/${b}` : `${base}/commits`
    }
}

// Web page of one file. Without a branch: the default branch (HEAD).
export function repoBlobUrl(url, branch, path, provider) {
    const base = cleanBase(url)
    const p = encodePath((path || '').replace(/^\/+/, ''))
    const kind = gitProvider(url, provider)
    const b = branch ? encodePath(branch) : 'HEAD'
    switch (kind) {
        case 'gitlab':    return `${base}/-/blob/${b}/${p}`
        case 'gitea':     return branch ? `${base}/src/branch/${b}/${p}` : base
        case 'bitbucket': return `${base}/src/${b}/${p}`
        default:          return `${base}/blob/${b}/${p}`
    }
}
