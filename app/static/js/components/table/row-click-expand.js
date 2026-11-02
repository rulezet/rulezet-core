/**
 * row-click-expand.js — in every table whose rows open (rule list, bundle list, data tables, proposals, git
 * sources…), clicking anywhere on a row opens / closes it, like its chevron button (.dt-action-btn--expand).
 * Links, buttons, checkboxes, menus, inputs and selecting text keep working as before. One listener for the
 * whole page (loaded by base.html), whatever the number of tables or rows.
 */
if (!window.__rzRowClickExpand) {
    window.__rzRowClickExpand = true
    const INTERACTIVE = 'a, button, input, select, textarea, label, summary, details, [role="button"], [role="menu"], ' +
        '[data-bs-toggle], .dropdown-menu, [contenteditable="true"], .dt-td--checkbox, .dt-td--drag, [data-no-row-toggle]'
    document.addEventListener('click', e => {
        if (e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return
        const row = e.target.closest && e.target.closest('tr.dt-row')
        if (!row || e.target.closest(INTERACTIVE)) return
        if (String(window.getSelection && window.getSelection()).trim()) return     // selecting text, not toggling
        const btn = row.querySelector('.dt-action-btn--expand')
        if (btn && !btn.disabled) btn.click()
    })
}
