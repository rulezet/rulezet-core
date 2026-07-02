// ─────────────────────────────────────────────────────────────────────────────
//  attackGraph.js — Global ATT&CK coverage graph (Tactic → Technique → Sub-technique).
//  Renders the /attack/heatmap_data payload with Pivotick.
//  Call initAttackGraph(containerId, coverage) only when the graph view is shown —
//  it lazy-loads pivotick.iife.js on first call, it is not bundled on the page.
// ─────────────────────────────────────────────────────────────────────────────

const _TACTIC_ORDER = [
    'reconnaissance', 'resource-development', 'initial-access', 'execution',
    'persistence', 'privilege-escalation', 'defense-evasion', 'credential-access',
    'discovery', 'lateral-movement', 'collection', 'command-and-control',
    'exfiltration', 'impact',
]

// One distinct hue per tactic so its technique/sub-technique cluster reads as a group.
const _PALETTE_LIGHT = [
    '#0ea5e9', '#14b8a6', '#22c55e', '#84cc16', '#eab308', '#f97316', '#ef4444',
    '#ec4899', '#a855f7', '#6366f1', '#3b82f6', '#06b6d4', '#f43f5e', '#7c3aed',
]
const _PALETTE_DARK = [
    '#38bdf8', '#2dd4bf', '#4ade80', '#a3e635', '#facc15', '#fb923c', '#f87171',
    '#f472b6', '#c084fc', '#818cf8', '#60a5fa', '#22d3ee', '#fb7185', '#a78bfa',
]

const _instances = new Map()
let _themeObserver = null

function _isDark() {
    return document.documentElement.classList.contains('dark-mode')
}

function _tacticColor(tacticKey) {
    const idx = Math.max(0, _TACTIC_ORDER.indexOf(tacticKey))
    return (_isDark() ? _PALETTE_DARK : _PALETTE_LIGHT)[idx % _PALETTE_LIGHT.length]
}

function _clamp(n, min, max) {
    return Math.max(min, Math.min(max, n))
}

function _showSpinner(container, message) {
    container.innerHTML =
        `<div style="display:flex;align-items:center;justify-content:center;height:100%;gap:.75rem;
                     color:var(--subtle-text-color,#6c757d);font-size:.875rem;">
            <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
            <span>${message}</span>
        </div>`
}

// ─────────────────────────────────────────────────────────────────────────────
//  Public: buildAttackGraphData
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Turn the /attack/heatmap_data payload into a Pivotick { nodes, edges } graph.
 *
 * Hierarchy:
 *   Tactic (hexagon, hub) ──covers──► Technique (circle)
 *   Technique ──has──────────────────► Sub-technique (small circle)
 */
export function buildAttackGraphData(coverage) {
    const nodes = [], edges = []
    const seen = new Set()
    function addNode(n) { if (!seen.has(n.id)) { seen.add(n.id); nodes.push(n) } }

    const tactics = (coverage?.tactics || []).filter(t => t.covered)

    // technique id -> { count, color, tacticKeys: [], rules, parentAdded }
    const techMap = new Map()

    for (const tactic of tactics) {
        const color = _tacticColor(tactic.key)
        const tacticId = `tactic_${tactic.key}`
        addNode({
            id: tacticId,
            data: {
                label: tactic.label,
                sublabel: `${tactic.rule_count} rule${tactic.rule_count === 1 ? '' : 's'}`,
                type: 'tactic',
                raw: tactic,
            },
            style: {
                shape: 'hexagon',
                color,
                size: _clamp(30 + Math.round(Math.sqrt(tactic.rule_count) * 3), 30, 56),
                iconClass: 'fa-solid fa-crosshairs',
            },
        })

        for (const tech of (tactic.techniques || [])) {
            if (!tech.count) continue
            if (!techMap.has(tech.id)) {
                techMap.set(tech.id, { count: 0, color, tacticKeys: [], tacticIds: [], rules: tech.rules || [] })
            }
            const entry = techMap.get(tech.id)
            entry.count = Math.max(entry.count, tech.count)
            entry.tacticKeys.push(tactic.key)
            entry.tacticIds.push(tacticId)
        }
    }

    // Technique + sub-technique nodes, sized by how many rules cover them.
    for (const [id, entry] of techMap) {
        const isSub = id.includes('.')
        addNode({
            id,
            data: {
                label: id,
                sublabel: `${entry.count} rule${entry.count === 1 ? '' : 's'}`,
                type: isSub ? 'subtechnique' : 'technique',
                raw: entry,
            },
            style: {
                shape: 'circle',
                color: entry.color,
                size: isSub
                    ? _clamp(7 + Math.round(Math.sqrt(entry.count) * 2.5), 7, 20)
                    : _clamp(10 + Math.round(Math.sqrt(entry.count) * 4), 10, 30),
            },
        })

        if (isSub) {
            // Prefer hanging off the parent technique for a clean 3-tier layout;
            // fall back to the tactic hub if the parent technique itself has 0 rules.
            const parentId = id.split('.')[0]
            if (techMap.has(parentId)) {
                edges.push({ from: parentId, to: id, data: { label: 'sub-technique' } })
            } else {
                edges.push({ from: entry.tacticIds[0], to: id, data: { label: 'covers' } })
            }
        } else {
            entry.tacticIds.forEach(tacticId => {
                edges.push({ from: tacticId, to: id, data: { label: 'covers' } })
            })
        }
    }

    return { nodes, edges }
}

function _nodeProperties(node) {
    const d = node.getData()
    const raw = d?.raw ?? {}
    const props = []
    if (d?.type === 'tactic') {
        props.push({ name: 'Tactic', value: raw.label || '' })
        props.push({ name: 'Techniques covered', value: String(raw.technique_count ?? 0) })
        props.push({ name: 'Rules', value: String(raw.rule_count ?? 0) })
    } else {
        props.push({ name: 'Technique', value: d?.label || '' })
        props.push({ name: 'Rules', value: String(raw.count ?? 0) })
        for (const r of (raw.rules || []).slice(0, 10)) {
            props.push({ name: 'Rule', value: r.name || r.uuid || '' })
        }
    }
    return props.filter(p => p.value !== '')
}

// ─────────────────────────────────────────────────────────────────────────────
//  Public: initAttackGraph
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Render the global ATT&CK graph inside `containerId`.
 * Must be called when the container is visible (view/tab shown) — lazily
 * injects pivotick.iife.js on first use so it never loads on page mount.
 *
 * @param {string} containerId  DOM id of the target div
 * @param {object} coverage     The /attack/heatmap_data payload
 */
export function initAttackGraph(containerId, coverage) {
    const container = document.getElementById(containerId)
    if (!container) return

    const prev = _instances.get(containerId)
    if (prev?.destroy) { try { prev.destroy() } catch {} }
    _instances.delete(containerId)

    if (_themeObserver) { _themeObserver.disconnect(); _themeObserver = null }

    if (typeof window.Pivotick !== 'function') {
        _showSpinner(container, 'Loading graph engine…')

        if (!document.querySelector('script[data-pivotick]')) {
            const s = document.createElement('script')
            s.src = '/static/js/pivotick.iife.js'
            s.dataset.pivotick = '1'
            document.head.appendChild(s)
        }

        let attempts = 0
        const poll = setInterval(() => {
            attempts++
            if (typeof window.Pivotick === 'function') {
                clearInterval(poll)
                initAttackGraph(containerId, coverage)
            } else if (attempts > 50) {
                clearInterval(poll)
                container.innerHTML = '<p style="padding:2rem;text-align:center;color:#888">Could not load the graph engine.</p>'
            }
        }, 200)
        return
    }

    _showSpinner(container, 'Building coverage graph…')

    setTimeout(() => {
        const parsed = buildAttackGraphData(coverage)

        if (!parsed.nodes.length) {
            container.innerHTML = '<p style="padding:2rem;text-align:center;color:#888">No ATT&CK coverage to graph yet.</p>'
            return
        }

        container.innerHTML = ''

        const instance = new window.Pivotick(container, parsed, {
            isDirected: true,
            layout: { type: 'force' },
            simulation: {
                useWorker: false,
                warmupTicks: parsed.nodes.length > 200 ? 0 : 'auto',
            },
            render: {
                defaultEdgeStyle: { markerEnd: 'arrow' },
                nodeHeaderMap: {
                    title:    (node) => node.getData()?.label    ?? '',
                    subtitle: (node) => node.getData()?.sublabel ?? '',
                },
            },
            UI: {
                mode: 'full',
                sidebar: { collapsed: 'auto' },
                mainHeader: {
                    nodeHeaderMap: {
                        title:    (node) => node.getData()?.label    ?? String(node.id),
                        subtitle: (node) => node.getData()?.sublabel ?? node.getData()?.type ?? '',
                    },
                },
                propertiesPanel: {
                    nodePropertiesMap: (node) => _nodeProperties(node),
                },
                tooltip: {
                    nodeHeaderMap: {
                        title:    (node) => node.getData()?.label    ?? '',
                        subtitle: (node) => node.getData()?.sublabel ?? '',
                    },
                },
            },
            callbacks: {
                onNodeClick: (_evt, node) => {
                    const d = node.getData()
                    if (d?.type === 'tactic') {
                        const ids = (d.raw?.techniques || []).filter(t => t.count > 0).map(t => t.id).join(',')
                        if (ids) window.location.href = `/rule/rules_list?attacks=${ids}`
                    } else if (d?.type === 'technique' || d?.type === 'subtechnique') {
                        window.location.href = `/rule/rules_list?attacks=${node.id}`
                    }
                },
            },
        })

        _instances.set(containerId, instance)

        _themeObserver = new MutationObserver(() => {
            _themeObserver.disconnect()
            _themeObserver = null
            initAttackGraph(containerId, coverage)
        })
        _themeObserver.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['class'],
        })
    }, 0)
}

export function destroyAttackGraph(containerId) {
    const prev = _instances.get(containerId)
    if (prev?.destroy) { try { prev.destroy() } catch {} }
    _instances.delete(containerId)
}
