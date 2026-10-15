/**
 * api.js — the game's calls to the server. Every call carries the player id
 * (a random id kept in this browser, as in Starfield); the server decides
 * everything that counts — evidence, hints, rule results, score.
 */
const PLAYER_KEY = 'rz-nightshift-player';

export function playerId() {
    try {
        let id = localStorage.getItem(PLAYER_KEY);
        if (!id) {
            id = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2, 14)}`;
            localStorage.setItem(PLAYER_KEY, id);
        }
        return id;
    } catch {
        return `session-${Math.random().toString(16).slice(2, 14)}`;
    }
}

export async function call(path, body = {}) {
    const res = await fetch(`/nightshift/case/${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById('csrf_token')?.value || '' },
        body: JSON.stringify({ player: playerId(), ...body }),
    });
    let data = {};
    try { data = await res.json(); } catch { /* not JSON */ }
    if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);
    return data;
}
