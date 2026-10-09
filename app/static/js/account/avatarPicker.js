// Profile picture on /account/edit: "Upload a picture", or build one —
// "Rulezy" (a pose) or "Icon" (Font Awesome), on a background, with an
// optional outline — rendered server-side by account_core.render_built_avatar
// when the form is saved. This script switches the tabs, sets the hidden
// avatar_mode field and updates the previews; the upload tab keeps its own
// preview script in edit_user.html.
// Loaded as a module so it runs after the page's Vue app is mounted on
// #edit-app (which re-renders the form and would drop earlier listeners).
//
// Nothing is chosen for the user: opening a builder tab keeps the current
// picture; avatar_mode only becomes "rulezy"/"icon" once a pose/icon is
// picked, and going back to the upload tab restores the current picture.
(function () {
    const mode     = document.getElementById('avatarMode');
    const tabs     = document.querySelectorAll('[data-avatar-mode]');
    const uploadPane  = document.querySelector('[data-avatar-pane="upload"]');
    const builderPane = document.querySelector('[data-avatar-pane="builder"]');
    const preview  = document.getElementById('builderPreview');
    const wrapper  = document.getElementById('avatarWrapper');
    if (!mode || !tabs.length || !builderPane) return;
    const original = wrapper ? wrapper.innerHTML : '';     // the current picture
    let tab = 'upload';

    const checked = (name) => document.querySelector(`input[name="${name}"]:checked`);
    const choiceName = (kind) => (kind === 'rulezy' ? 'rulezy_pose' : 'avatar_icon');

    function showEmpty(text) {
        const img = preview.querySelector('img');
        img.classList.add('d-none');
        preview.classList.add('avp-preview--empty');
        let span = preview.querySelector('[data-empty-text]');
        if (!span) { span = document.createElement('span'); span.dataset.emptyText = ''; preview.appendChild(span); }
        span.textContent = text;
    }

    function render() {
        const kind = tab;
        const choice = checked(choiceName(kind));
        if (!choice) {                                       // nothing picked in this builder yet
            showEmpty(kind === 'rulezy' ? 'Pick a pose' : 'Pick an icon');
            if (mode.value !== 'upload') { mode.value = 'upload'; if (wrapper) wrapper.innerHTML = original; }
            return;
        }
        let bg = checked('avatar_bg');
        if (!bg) { bg = document.querySelector('input[name="avatar_bg"]'); if (!bg) return; bg.checked = true; }
        const border = checked('avatar_border')?.value || 'none';
        // Rendered by the server exactly as it will be saved (cached per combination).
        const src = `/account/avatar_preview.png?kind=${kind}&choice=${encodeURIComponent(choice.value)}` +
                    `&bg=${encodeURIComponent(bg.value)}&border=${encodeURIComponent(border)}`;
        const img = preview.querySelector('img');
        img.src = src;
        img.classList.remove('d-none');
        preview.classList.remove('avp-preview--empty');
        preview.querySelector('[data-empty-text]')?.remove();
        mode.value = kind;
        document.getElementById('removeAvatarFlag').value = '0';
        const input = document.getElementById('avatarInput');
        if (input) input.value = '';
        if (wrapper) {
            wrapper.innerHTML = `<img src="${src}" class="rounded-circle" alt="" style="width:72px;height:72px;object-fit:cover;">`;
        }
    }

    function setTab(next) {
        tab = next;
        tabs.forEach((t) => {
            const on = t.dataset.avatarMode === next;
            t.classList.toggle('active', on);
            t.setAttribute('aria-selected', on);
        });
        uploadPane?.classList.toggle('d-none', next !== 'upload');
        builderPane.classList.toggle('d-none', next === 'upload');
        builderPane.querySelectorAll('[data-builder-kind]').forEach((el) => el.classList.toggle('d-none', el.dataset.builderKind !== next));
        if (next === 'upload') {
            // Leaving the builder cancels its choice: back to the current picture.
            if (mode.value !== 'upload') { mode.value = 'upload'; if (wrapper) wrapper.innerHTML = original; }
        } else {
            render();
        }
    }
    // The upload tab's own preview script calls this when a file is chosen.
    window.setAvatarMode = (next) => { if (next === 'upload') { mode.value = 'upload'; setTab('upload'); } };

    tabs.forEach((t) => t.addEventListener('click', () => setTab(t.dataset.avatarMode)));
    builderPane.querySelectorAll('input[type="radio"]').forEach((input) => input.addEventListener('change', render));

    // Icon search
    const search = document.getElementById('avatarIconSearch');
    if (search) {
        search.addEventListener('input', () => {
            const q = search.value.trim().toLowerCase();
            builderPane.querySelectorAll('[data-icon-name]').forEach((el) => {
                el.classList.toggle('d-none', !!q && !el.dataset.iconName.includes(q));
            });
        });
        search.addEventListener('keydown', (e) => { if (e.key === 'Enter') e.preventDefault(); });
    }
})();
