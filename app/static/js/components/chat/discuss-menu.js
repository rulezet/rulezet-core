/**
 * discuss-menu.js — fills the "Discuss" dropdown (macros/discuss.html) with the channels about this object,
 * the first time it is opened. One listener for the whole page, whatever the number of buttons.
 */
if (!window.__rzDiscussMenu) {
    window.__rzDiscussMenu = true
    const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
    // One request per object on the page (a detail page has one): the button shows how many channels are about it,
    // so a public channel is seen without opening the menu. The count is a data attribute (CSS draws it) — the page's
    // Vue never re-renders it away. The menu reuses the same answer.
    const cache = new Map()
    const about = box => {
        const k = `${box.dataset.kind}/${box.dataset.key}`
        if (!cache.has(k)) cache.set(k, fetch(`/messages/api/about/${encodeURIComponent(box.dataset.kind)}/${encodeURIComponent(box.dataset.key)}`)
            .then(r => r.ok ? r.json() : { channels: [] }).catch(() => ({ channels: [] })))
        return cache.get(k)
    }
    function badge() {
        document.querySelectorAll('.discuss-menu').forEach(async box => {
            if (box.dataset.counted) return
            box.dataset.counted = '1'
            const { channels = [] } = await about(box)
            const btn = box.querySelector('.discuss-menu__btn')
            if (!btn || !channels.length) return
            const pub = channels.filter(c => !c.is_private).length
            btn.setAttribute('data-count', channels.length)
            btn.title = `${channels.length} channel${channels.length > 1 ? 's' : ''} about it` +
                (pub ? ` — ${pub} public: anyone signed in can join and read ${pub > 1 ? 'them' : 'it'}` : '') +
                '. Click to see, join or start one.'
            if (pub) btn.classList.add('has-public')
        })
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(badge, 300))
    else setTimeout(badge, 300)
    window.addEventListener('load', () => setTimeout(badge, 600))      // buttons rendered later by the page's Vue

    document.addEventListener('show.bs.dropdown', async e => {
        const box = e.target.closest && e.target.closest('.discuss-menu')
        if (!box || box.dataset.loaded) return
        box.dataset.loaded = '1'
        const slot = box.querySelector('.discuss-menu__slot')
        try {
            const { channels = [] } = await about(box)
            slot.outerHTML = channels.length
                ? `<li><h6 class="dropdown-header discuss-menu__head">Channels about it</h6></li>` + channels.map(c =>
                    `<li class="discuss-menu__chan"><a class="dropdown-item" href="/messages/c/${esc(c.uuid)}">
                        <span class="discuss-menu__icon">${c.avatar ? `<img src="${esc(c.avatar)}" alt="">` : `<i class="fa-solid ${c.is_private ? 'fa-lock' : 'fa-hashtag'}"></i>`}</span>
                        <span class="discuss-menu__name">${esc(c.name)}<small>${c.is_private ? 'Private' : 'Public — anyone can join'}</small></span>
                        <span class="discuss-menu__count"><i class="fa-solid fa-user-group"></i>${c.member_count}</span></a>
                        ${c.is_member ? '<span class="discuss-menu__in">Joined</span>' : `<button type="button" class="discuss-menu__join" data-uuid="${esc(c.uuid)}">Join</button>`}</li>`).join('')
                : `<li><span class="discuss-menu__note">No channel about it yet.</span></li>`
        } catch {
            slot.outerHTML = `<li><span class="discuss-menu__note">Couldn't load the channels.</span></li>`
        }
    })
    // "Join" a public channel from the menu: you're in, then it opens
    document.addEventListener('click', async e => {
        const btn = e.target.closest && e.target.closest('.discuss-menu__join')
        if (!btn) return
        e.preventDefault(); e.stopPropagation()
        btn.disabled = true
        const res = await fetch(`/messages/api/channels/${encodeURIComponent(btn.dataset.uuid)}/join`, {
            method: 'POST', headers: { 'X-CSRFToken': document.getElementById('csrf_token')?.value || '', 'Content-Type': 'application/json' },
        }).catch(() => null)
        if (res && res.ok) location.href = `/messages/c/${encodeURIComponent(btn.dataset.uuid)}`
        else btn.disabled = false
    })
}
