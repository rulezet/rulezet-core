/**
 * bundleFileTypes.js — one place that knows how a bundle node should look
 * and be edited/rendered, based on whether it's a rule or a custom file
 * (README.md, notes.txt, config.json…) and on its extension.
 *
 * Used by BundleStructureEditor (edit page), BundleFileViewer and
 * BundleFilesPanel (detail page) so the three stay consistent.
 */

import { renderMarkdown, hardenUserHtml } from '/static/js/sanitize.js'

// Markdown -> sanitised + hardened HTML, safe for v-html.
export async function renderSafeMarkdown(text) {
    if (!text) return ''
    return hardenUserHtml(await renderMarkdown(text))
}

export const isRuleNode = (node) =>
    !!node && (node.rule_id != null || String(node.id).startsWith('rule_'))

export function extOf(name) {
    const n = String(name || '')
    const dot = n.lastIndexOf('.')
    return dot > 0 ? n.slice(dot + 1).toLowerCase() : ''
}

export const isMarkdown = (name) => ['md', 'markdown'].includes(extOf(name))

// Custom-file extension -> CodeViewer / SmartEditor language
const EXT_LANG = {
    md: 'markdown', markdown: 'markdown',
    json: 'json',
    yaml: 'yaml', yml: 'yaml',
    toml: 'toml',
    xml: 'xml',
    html: 'html',
    sh: 'bash',
    py: 'python',
    sql: 'sql',
}

export const languageForFile = (name) => EXT_LANG[extOf(name)] || 'text'

// Which SmartEditor mode a custom file opens in.
export function editorModeFor(name) {
    const ext = extOf(name)
    if (ext === 'md' || ext === 'markdown') return { mode: 'markdown', language: 'markdown' }
    if (!ext || ext === 'txt') return { mode: 'text', language: 'text' }
    return { mode: 'code', language: languageForFile(name) }
}

// Custom files are rendered teal/green-ish so they stand out against the
// blue rule files; each extension gets its own glyph + tint.
const DOC_ICONS = {
    md:   { icon: 'fa-brands fa-markdown', color: '#14b8a6', label: 'Markdown' },
    txt:  { icon: 'fa-solid fa-file-lines', color: '#10b981', label: 'Text' },
    json: { icon: 'fa-solid fa-file-code',  color: '#a855f7', label: 'JSON' },
    yaml: { icon: 'fa-solid fa-file-code',  color: '#f97316', label: 'YAML' },
    yml:  { icon: 'fa-solid fa-file-code',  color: '#f97316', label: 'YAML' },
    csv:  { icon: 'fa-solid fa-file-csv',   color: '#22c55e', label: 'CSV' },
}

export function docIcon(name) {
    const ext = extOf(name)
    return DOC_ICONS[ext] || { icon: 'fa-solid fa-file-pen', color: '#14b8a6', label: ext ? ext.toUpperCase() : 'File' }
}

export const RULE_ICON = { icon: 'fa-solid fa-shield-halved', color: '#0d6efd' }

export function downloadText(filename, content) {
    const blob = new Blob([content ?? ''], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || 'file.txt'
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 0)
}

// Fetch a server-generated file (zip/json) and hand it to the browser.
// Returns true on success; on an error response shows its toast.
export async function downloadFromUrl(url, fallbackName) {
    const { create_message } = await import('/static/js/toaster.js')
    try {
        const res = await fetch(url)
        if (!res.ok) {
            const data = await res.json().catch(() => ({}))
            create_message(data.message || 'Download failed', data.toast_class || 'danger-subtle')
            return false
        }
        const blob = await res.blob()
        const m = (res.headers.get('Content-Disposition') || '').match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i)
        const href = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = href
        a.download = m ? decodeURIComponent(m[1]) : fallbackName
        document.body.appendChild(a)
        a.click()
        a.remove()
        setTimeout(() => URL.revokeObjectURL(href), 0)
        return true
    } catch {
        create_message('Download failed', 'danger-subtle')
        return false
    }
}

export function formatBytes(str) {
    const n = new Blob([str ?? '']).size
    if (n < 1024) return n + ' B'
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
    return (n / 1024 / 1024).toFixed(1) + ' MB'
}

/**
 * Flatten the bundle tree (as returned by /bundle/get_bundle_json) into a
 * list of files with their folder path — [{ id, name, path, folder, content,
 * isRule, format, rule_id }]. Folder path excludes the file itself.
 */
export function flattenFiles(nodes, parents = []) {
    const out = []
    for (const n of nodes || []) {
        if (n.type === 'folder') {
            out.push(...flattenFiles(n.children, [...parents, n.name]))
        } else {
            out.push({
                id: String(n.id),
                name: n.name,
                folder: parents.join('/'),
                path: [...parents, n.name].join('/'),
                content: n.content || '',
                // rule content isn't in the light tree — fetched when opened
                lazy: !!n.lazy,
                size: n.size ?? null,
                isRule: isRuleNode(n),
                format: n.format || '',
                rule_id: n.rule_id ?? null,
            })
        }
    }
    return out
}
