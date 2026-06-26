/**
 * constants.js — shared fetch helper and constants for Rulezet frontend modules.
 */

export const TOAST = {
    SUCCESS: 'success',
    WARNING: 'warning',
    ERROR:   'danger',
    INFO:    'info',
}

/**
 * Authenticated JSON fetch.
 * Automatically attaches the CSRF token from the hidden #csrf_token input.
 */
export async function apiFetch(url, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.getElementById('csrf_token')?.value ?? '',
        },
    }
    if (body !== null) options.body = JSON.stringify(body)
    return fetch(url, options)
}
