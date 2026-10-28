/**
 * home.js — motion of the home page:
 *   [data-reveal]          fades in once when it scrolls into view ([data-reveal-stagger]: its
 *                          children one after the other)
 *   [data-count]           the key figures count up when they appear
 *   [data-rulezy]          Rulezy floats, changes pose and says something new every few seconds
 *   [data-typing]          the search box types example searches in its placeholder, a caret
 *                          blinking after them; stops for good as soon as the visitor focuses it
 *                          (click: next tip); stops while the tab is hidden
 * The page is rendered by Vue after load, so elements are picked up as they appear.
 * prefers-reduced-motion: no motion at all, everything is shown as is.
 */
(function () {
    const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const root = document.documentElement;
    const canObserve = 'IntersectionObserver' in window;
    if (!reduce && canObserve) root.classList.add('rv-ready');

    // ── reveal + count-up ──────────────────────────────────────────────────────
    const io = canObserve ? new IntersectionObserver((entries) => {
        for (const e of entries) {
            if (!e.isIntersecting) continue;
            e.target.classList.add('is-in');
            e.target.querySelectorAll('[data-count]').forEach(countUp);
            io.unobserve(e.target);
        }
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 }) : null;

    function countUp(el) {
        const target = parseInt(el.getAttribute('data-count'), 10);
        if (!Number.isFinite(target) || reduce) return;
        const fmt = new Intl.NumberFormat('en-US');
        const start = performance.now();
        const dur = 1400;
        const tick = (now) => {
            const p = Math.min(1, (now - start) / dur);
            const eased = 1 - Math.pow(1 - p, 3);
            el.textContent = fmt.format(Math.round(target * eased));
            if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    }

    function watch() {
        document.querySelectorAll('[data-reveal]:not([data-rv])').forEach((el) => {
            el.setAttribute('data-rv', '');
            if (el.hasAttribute('data-reveal-stagger')) Array.from(el.children).forEach((c, i) => c.style.setProperty('--i', i));
            if (io && !reduce) io.observe(el); else el.classList.add('is-in');
        });
        document.querySelectorAll('[data-rulezy]:not([data-rz])').forEach(rulezy);
    }

    // ── Rulezy ─────────────────────────────────────────────────────────────────
    function rulezy(el) {
        el.setAttribute('data-rz', '');
        let poses = [];
        try { poses = JSON.parse(el.getAttribute('data-rulezy')) || []; } catch { poses = []; }
        const img = el.querySelector('[data-rulezy-img]');
        const bubble = el.querySelector('[data-rulezy-text]');
        if (!poses.length || !img || !bubble) return;
        poses.forEach((p) => { const pre = new Image(); pre.src = p.img; });   // no flicker on change
        let index = 0;
        let timer = null;
        let typing = null;

        function type(text) {
            clearInterval(typing);
            if (reduce) { bubble.textContent = text; return; }
            let n = 0;
            bubble.textContent = '';
            typing = setInterval(() => {
                n += 1;
                bubble.textContent = text.slice(0, n);
                if (n >= text.length) clearInterval(typing);
            }, 24);
        }
        function show(i) {
            index = (i + poses.length) % poses.length;
            const pose = poses[index];
            el.classList.add('is-switching');
            setTimeout(() => {
                img.src = pose.img;
                el.classList.remove('is-switching');
                type(pose.text);
            }, reduce ? 0 : 220);
        }
        function schedule() {
            clearTimeout(timer);
            if (reduce || document.hidden) return;
            timer = setTimeout(() => { show(index + 1); schedule(); }, 5200);
        }
        el.addEventListener('click', () => { show(index + 1); schedule(); });
        el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); show(index + 1); schedule(); } });
        document.addEventListener('visibilitychange', schedule);
        // let the logo build first, then Rulezy starts talking
        setTimeout(() => { el.classList.add('is-awake'); type(poses[0].text); schedule(); }, reduce ? 0 : 1800);
    }

    // ── Search box: example searches typed in the placeholder ─────────────────
    function typing(input) {
        let phrases = [];
        try { phrases = JSON.parse(input.getAttribute('data-typing')) || []; } catch { phrases = []; }
        if (!phrases.length || reduce) return;
        const original = input.placeholder;
        let phrase = 0, chars = 0, deleting = false, caret = true, timer = null, blink = null, stopped = false;
        const show = () => { input.placeholder = 'Search ' + phrases[phrase].slice(0, chars) + (caret ? '|' : ''); };
        function step() {
            if (stopped) return;
            const text = phrases[phrase];
            if (!deleting && chars < text.length) { chars += 1; show(); timer = setTimeout(step, 55 + Math.random() * 70); return; }
            if (!deleting) { deleting = true; timer = setTimeout(step, 1800); return; }          // read it
            if (chars > 0) { chars -= 1; show(); timer = setTimeout(step, 28); return; }
            deleting = false;
            phrase = (phrase + 1) % phrases.length;
            timer = setTimeout(step, 450);
        }
        blink = setInterval(() => { caret = !caret; if (!stopped) show(); }, 530);
        function stop() {
            stopped = true;
            clearTimeout(timer);
            clearInterval(blink);
            input.placeholder = original;
        }
        input.addEventListener('focus', stop, { once: true });
        input.addEventListener('input', stop, { once: true });
        setTimeout(step, 1200);                                    // after the hero has risen in
    }

    function start() {
        watch();
        document.querySelectorAll('input[data-typing]').forEach(typing);
        // the hero figures are on screen from the start: count once the strip has risen in
        setTimeout(() => document.querySelectorAll('.hv2-stats [data-count]').forEach(countUp), reduce ? 0 : 900);
        new MutationObserver(watch).observe(document.body, { childList: true, subtree: true });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
})();
