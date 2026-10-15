// Collapsible section cards (h-card) — which ones are closed is remembered
// per page type in this browser (a viewer convenience: localStorage, ignored
// when unavailable).
//
//   const { collapsed, toggle } = useCollapsedCards('cve-kit', { charts: true }, onOpen)
//   defaults: cards closed until the viewer opens them; onOpen(card) runs when
//   one is opened (e.g. to load its data only then).
//   <div class="h-card__header" @click="toggle('rules')"> … <div class="h-card__body" v-show="!collapsed.rules">
const { reactive } = Vue;

export function useCollapsedCards(pageKey, defaults = {}, onOpen = null) {
    const storageKey = `rulezet.collapsed.${pageKey}`;
    let saved = {};
    try { saved = JSON.parse(localStorage.getItem(storageKey) || '{}') || {}; } catch { saved = {}; }
    const collapsed = reactive({ ...defaults, ...saved });

    function toggle(card) {
        collapsed[card] = !collapsed[card];
        if (!collapsed[card] && onOpen) onOpen(card);
        try { localStorage.setItem(storageKey, JSON.stringify(collapsed)); } catch { /* storage unavailable */ }
    }

    return { collapsed, toggle };
}
