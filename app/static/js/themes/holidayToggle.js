// Home page "Holiday theme" switch (seasonal, end of year). Switches to the
// Christmas theme — "christmas-night" when the user is on a dark theme,
// "christmas" otherwise — and back to the theme they had before, saved in
// localStorage. Uses theme.js (applyTheme, _saveThemeToDb, _DARK_THEMES),
// so the choice is stored on the account like one made in the settings.
// The home page is re-rendered by its Vue app after this script runs, so the
// click is caught by delegation on the document, and the initial label comes
// from the server (the user's saved theme).
(function () {
    if (typeof applyTheme !== 'function') return;
    const PREV_KEY = 'rz-pre-holiday-theme';

    const currentPref = () => localStorage.getItem('theme-pref') || 'system';
    const isHoliday = () => currentPref().startsWith('christmas');

    function refresh(btn) {
        const label = btn.querySelector('[data-holiday-label]');
        if (label) label.textContent = isHoliday() ? 'Back to your theme' : 'Holiday theme';
    }

    document.addEventListener('click', (event) => {
        const btn = event.target.closest('#holidayToggle');
        if (!btn) return;
        let next;
        if (isHoliday()) {
            next = localStorage.getItem(PREV_KEY) || 'system';
        } else {
            const pref = currentPref();
            localStorage.setItem(PREV_KEY, pref);
            const resolved = localStorage.getItem('theme') || 'light';
            next = _DARK_THEMES.indexOf(resolved) !== -1 ? 'christmas-night' : 'christmas';
        }
        applyTheme(next);
        if (typeof updateThemeIcon === 'function') updateThemeIcon(next);
        if (typeof _saveThemeToDb === 'function') _saveThemeToDb(next);
        refresh(btn);
    });
})();
