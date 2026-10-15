/**
 * report.js — sends each finished run to the server (/starfield/run) so
 * admins can follow who plays and how well. Fire-and-forget: the game never
 * waits for it, and a failure (offline, rate limit) changes nothing.
 *
 * player id: a random id kept in this browser, which groups the runs of an
 * anonymous player (logged-in players are grouped by account server-side).
 */
const PLAYER_KEY = 'rz-starfield-player';

function playerId() {
    try {
        let id = localStorage.getItem(PLAYER_KEY);
        if (!id) {
            id = (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`).slice(0, 36);
            localStorage.setItem(PLAYER_KEY, id);
        }
        return id;
    } catch {
        return 'session-' + Math.random().toString(16).slice(2, 14);
    }
}

export function reportRun(run) {
    try {
        fetch('/starfield/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById('csrf_token')?.value || '' },
            body: JSON.stringify({ player: playerId(), ...run }),
            keepalive: true,
        }).catch(() => {});
    } catch { /* never break the game */ }
}
