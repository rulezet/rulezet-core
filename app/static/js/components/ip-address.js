/**
 * ip-address.js — an IP address with a magnifier (shown on hover / focus) that
 * opens a window with its whois (RDAP) lookup: country, organisation, network,
 * reverse DNS, abuse contact, registry, links to other tools.
 *
 * Admin pages only (the lookup route, /admin/ip-lookup/<ip>, is admin-only).
 *
 *   Vue:      import IpAddress from '/static/js/components/ip-address.js'
 *             <ip-address :ip="log.ip_address"></ip-address>
 *   Plain HTML (strings built in JS, Jinja): <span class="ipa" data-ip="1.2.3.4">1.2.3.4</span>
 *             then enhanceIpAddresses(rootElement) — idempotent, call it again after a re-render.
 *   Anywhere: openIpLookup('1.2.3.4')
 *
 * CSS: css/components/ip-address.css
 */

const answers = new Map();        // ip → promise of the JSON answer (one lookup per page and address)

function fetchLookup(ip, refresh = false) {
    if (!refresh && answers.has(ip)) return answers.get(ip);
    const p = fetch(`/admin/ip-lookup/${encodeURIComponent(ip)}${refresh ? '?refresh=1' : ''}`,
                    { headers: { Accept: 'application/json' } })
        .then(r => r.json().catch(() => ({ success: false, message: `The lookup failed (${r.status}).` })))
        .catch(() => ({ success: false, message: 'The lookup failed — network error.' }));
    answers.set(ip, p);
    p.then(d => { if (!d.success) answers.delete(ip); });   // never keep an error
    return p;
}

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function flag(code) {
    if (!/^[A-Z]{2}$/.test(code || '')) return '';
    return String.fromCodePoint(...[...code].map(c => 0x1F1E6 + c.charCodeAt(0) - 65));
}

function countryName(code) {
    try { return new Intl.DisplayNames([navigator.language || 'en'], { type: 'region' }).of(code); }
    catch { return code; }
}

function fmtDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return isNaN(d) ? esc(iso) : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

const SCOPE_TEXT = {
    private: 'Private network', loopback: 'Loopback', 'link-local': 'Link-local',
    multicast: 'Multicast', reserved: 'Reserved', public: 'Public',
};

function cell(icon, label, value, { mono = false, wide = false } = {}) {
    if (!value) return '';
    return `<div class="ipa-cell${wide ? ' ipa-cell--wide' : ''}">
        <div class="ipa-cell-label"><i class="fa-solid ${icon}"></i>${esc(label)}</div>
        <div class="ipa-cell-value${mono ? ' ipa-mono' : ''}">${value}</div></div>`;
}

function contactHtml(c) {
    if (!c) return '';
    const bits = [];
    if (c.email) bits.push(`<a href="mailto:${esc(c.email)}">${esc(c.email)}</a>`);
    if (c.phone) bits.push(esc(c.phone));
    return `${esc(c.name || c.handle || '')}${bits.length ? `<div class="ipa-sub">${bits.join(' · ')}</div>` : ''}`;
}

function renderBody(d) {
    if (!d.success) {
        return `<div class="ipa-state ipa-state--error"><i class="fa-solid fa-triangle-exclamation"></i>
                <div>${esc(d.message || 'The lookup failed.')}</div></div>`;
    }
    const links = (d.links || []).map(l =>
        `<a class="ipa-link" href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">
            ${esc(l.label)} <i class="fa-solid fa-arrow-up-right-from-square"></i></a>`).join('');

    if (d.scope !== 'public') {
        return `<div class="ipa-state"><i class="fa-solid fa-house-signal"></i>
                <div><strong>${esc(SCOPE_TEXT[d.scope] || d.scope)} address</strong>
                <div class="ipa-sub">${esc(d.message || '')}</div></div></div>`;
    }

    const net = d.network || {};
    const owner = d.owner || {};
    const place = d.country ? countryName(d.country) : (d.country_name || '');
    const hero = `<div class="ipa-hero">
        <div class="ipa-flag">${d.country ? flag(d.country) : '<i class="fa-solid fa-earth-europe"></i>'}</div>
        <div class="ipa-hero-text">
            <div class="ipa-hero-country">${esc(place || 'Unknown country')}${d.country ? ` <span class="ipa-code">${esc(d.country)}</span>` : ''}</div>
            <div class="ipa-hero-org">${esc(owner.name || net.name || '—')}</div>
        </div>
        ${d.registry ? `<span class="ipa-registry" title="Regional Internet registry">${esc(d.registry)}</span>` : ''}
    </div>`;

    const grid = [
        cell('fa-server', 'Reverse DNS', d.hostname ? esc(d.hostname) : '<span class="ipa-muted">none</span>', { mono: true }),
        cell('fa-network-wired', 'Network', esc(net.name), { mono: true }),
        cell('fa-sitemap', 'CIDR', esc((net.cidrs || []).join(', ')), { mono: true }),
        cell('fa-arrows-left-right', 'Range', esc(net.range), { mono: true }),
        cell('fa-tag', 'Type', esc(net.type)),
        cell('fa-fingerprint', 'Handle', esc(net.handle), { mono: true }),
        cell('fa-calendar-plus', 'Registered', fmtDate(d.registered)),
        cell('fa-calendar-check', 'Last changed', fmtDate(d.updated)),
        cell('fa-building', 'Organisation', contactHtml(owner.name ? owner : null), { wide: true }),
        cell('fa-location-dot', 'Address', esc(owner.address), { wide: true }),
        cell('fa-shield-halved', 'Abuse contact', contactHtml(d.abuse), { wide: true }),
    ].join('');

    const notes = (d.description || []).length
        ? `<details class="ipa-notes"><summary>Registry remarks</summary>${d.description.map(t => `<div>${esc(t)}</div>`).join('')}</details>` : '';

    return `${hero}<div class="ipa-grid">${grid}</div>${notes}
        ${links ? `<div class="ipa-links">${links}</div>` : ''}
        <div class="ipa-source">Source: <a href="${esc(d.source_url)}" target="_blank" rel="noopener noreferrer">${esc(d.registry || 'RDAP')} RDAP</a>
        ${d.cached ? ' · saved answer' : ''}</div>`;
}

let modal = null;
let lastFocus = null;

function ensureModal() {
    if (modal) return modal;
    modal = document.createElement('div');
    modal.className = 'ipa-overlay';
    modal.hidden = true;
    modal.innerHTML = `
      <div class="ipa-modal" role="dialog" aria-modal="true" aria-labelledby="ipa-title">
        <div class="ipa-head">
          <div class="ipa-head-icon"><i class="fa-solid fa-magnifying-glass-location"></i></div>
          <div class="ipa-head-text"><div class="ipa-head-kicker">IP lookup</div>
            <div class="ipa-title ipa-mono" id="ipa-title"></div></div>
          <button type="button" class="ipa-icon-btn" data-act="copy" title="Copy the address"><i class="fa-regular fa-copy"></i></button>
          <button type="button" class="ipa-icon-btn" data-act="refresh" title="Look it up again"><i class="fa-solid fa-rotate"></i></button>
          <button type="button" class="ipa-icon-btn" data-act="close" title="Close (Esc)"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="ipa-body"></div>
      </div>`;
    document.body.appendChild(modal);
    modal.addEventListener('click', e => {
        if (e.target === modal) return closeIpLookup();
        const act = e.target.closest('[data-act]')?.dataset.act;
        const ip = modal.dataset.ip;
        if (act === 'close') closeIpLookup();
        else if (act === 'refresh') load(ip, true);
        else if (act === 'copy') navigator.clipboard?.writeText(ip).then(async () => {
            try { (await import('/static/js/toaster.js')).create_message('Address copied', 'success'); } catch { /* no toast */ }
        });
    });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && modal && !modal.hidden) closeIpLookup(); });
    return modal;
}

function load(ip, refresh = false) {
    const body = modal.querySelector('.ipa-body');
    body.innerHTML = `<div class="ipa-state"><span class="spinner-border spinner-border-sm"></span>
                      <div>Asking the registry…</div></div>`;
    fetchLookup(ip, refresh).then(d => { if (modal.dataset.ip === ip) body.innerHTML = renderBody(d); });
}

export function openIpLookup(ip) {
    if (!ip) return;
    ensureModal();
    lastFocus = document.activeElement;
    modal.dataset.ip = ip;
    modal.querySelector('.ipa-title').textContent = ip;
    modal.hidden = false;
    document.body.classList.add('ipa-open');
    modal.querySelector('[data-act="close"]').focus();
    load(ip);
}

export function closeIpLookup() {
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove('ipa-open');
    lastFocus?.focus?.();
}

const MAGNIFIER = `<button type="button" class="ipa-btn" title="Look up this address (whois)" aria-label="Look up this address">
    <i class="fa-solid fa-magnifying-glass"></i></button>`;

/** Turn every <span class="ipa" data-ip="…"> under root into an address with its magnifier. */
export function enhanceIpAddresses(root = document) {
    root.querySelectorAll('.ipa[data-ip]:not([data-ipa-ready])').forEach(el => {
        el.dataset.ipaReady = '1';
        el.insertAdjacentHTML('beforeend', MAGNIFIER);
        el.querySelector('.ipa-btn').addEventListener('click', e => {
            e.preventDefault(); e.stopPropagation();
            openIpLookup(el.dataset.ip);
        });
    });
}

export default {
    name: 'IpAddress',
    props: { ip: { type: String, default: '' } },
    methods: { open() { openIpLookup(this.ip); } },
    template: `
      <span v-if="ip" class="ipa"><span class="ipa-text">{{ ip }}</span><button type="button" class="ipa-btn"
            title="Look up this address (whois)" aria-label="Look up this address" @click.stop.prevent="open">
          <i class="fa-solid fa-magnifying-glass"></i></button></span>`,
};
