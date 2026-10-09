import { create_message } from '/static/js/toaster.js';

// "Rule formats" page (templates/rule/formats.html): live search over the
// format cards (matches the data-search text of each card).
(function () {
    const input = document.getElementById('fmt-search-input');
    const cols  = document.querySelectorAll('#fmt-grid .fmt-col');
    const empty = document.getElementById('fmt-empty');
    if (!input) return;

    input.addEventListener('input', () => {
        const q = input.value.trim().toLowerCase();
        let shown = 0;
        cols.forEach(col => {
            const match = !q || col.dataset.search.includes(q);
            col.classList.toggle('d-none', !match);
            if (match) shown++;
        });
        empty.classList.toggle('d-none', shown > 0);
    });
})();

// Cards | Graph switch. The graph is Pivograph (app/modules/pivograph, built
// into static/pivograph by `manage.py pivograph`) in an iframe: loaded on
// first use, then handed the document from /rule/formats/graph.json with
// its postMessage protocol (pivograph:ready → pivograph:load). The view is
// kept in the URL (?view=graph) so it can be shared and survives a reload.
(function () {
    const buttons = document.querySelectorAll('.fmt-view-btn');
    const grid    = document.getElementById('fmt-grid');
    const search  = document.getElementById('fmt-search-wrap');
    const empty   = document.getElementById('fmt-empty');
    const graph   = document.getElementById('fmt-graph-view');
    const frame   = document.getElementById('fmt-graph-frame');
    if (!buttons.length) return;

    let graphData = null;
    window.addEventListener('message', async (event) => {
        if (!frame || event.source !== frame.contentWindow) return;
        const msg = event.data || {};
        if (msg.type === 'pivograph:ready') {
            try {
                graphData = graphData || await (await fetch(frame.dataset.graph)).json();
                frame.contentWindow.postMessage(
                    { type: 'pivograph:load', data: graphData, name: 'rulezet-formats.json' },
                    window.location.origin);
            } catch {
                create_message('Could not load the formats graph', 'danger');
            }
        } else if (msg.type === 'pivograph:error') {
            create_message(`Graph error: ${msg.message}`, 'danger');
        }
    });

    function show(view) {
        const isGraph = view === 'graph';
        buttons.forEach(b => {
            const on = b.dataset.view === view;
            b.classList.toggle('active', on);
            b.setAttribute('aria-selected', on);
        });
        const wasHidden = grid.classList.contains('d-none');
        grid.classList.toggle('d-none', isGraph);
        if (!isGraph && wasHidden) {
            // Replay the cards reveal: drop the animation, force a reflow, put it back.
            grid.classList.add('fmt-replay');
            void grid.offsetWidth;
            grid.classList.remove('fmt-replay');
        }
        search.classList.toggle('d-none', isGraph);
        if (isGraph) empty.classList.add('d-none');
        graph.classList.toggle('d-none', !isGraph);
        if (isGraph && frame && !frame.src) frame.src = frame.dataset.src;
        const url = new URL(window.location);
        if (isGraph) url.searchParams.set('view', 'graph'); else url.searchParams.delete('view');
        history.replaceState(null, '', url);
    }

    buttons.forEach(b => b.addEventListener('click', () => show(b.dataset.view)));
    if (new URLSearchParams(window.location.search).get('view') === 'graph') show('graph');
})();
