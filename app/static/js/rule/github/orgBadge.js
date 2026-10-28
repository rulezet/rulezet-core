/**
 * orgBadge.js — the organisation badge of Git Sources (setting git.org_badge:
 * label, logo, keywords), fetched once per page and shared by githubFilter.js
 * and githubSelectionTable.js.
 *
 *   const org = await loadOrgBadge()   // { label, logoUrl }
 */
let promise = null;

function logoUrl(logo) {
    if (!logo || typeof logo !== 'string') return '';
    if (/^https:\/\//i.test(logo)) return logo;
    return '/static/' + logo.replace(/^\/+/, '').replace(/^static\//, '');
}

export function loadOrgBadge() {
    if (!promise) {
        promise = fetch('/api/config/settings/git.org_badge')
            .then(r => (r.ok ? r.json() : null))
            .then(d => {
                const v = (d && d.value) || {};
                return { label: v.label || 'Organisation', logoUrl: logoUrl(v.logo) };
            })
            .catch(() => ({ label: 'Organisation', logoUrl: '' }));
    }
    return promise;
}
