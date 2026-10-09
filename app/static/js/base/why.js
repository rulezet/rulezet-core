// "Why Rulezet" page (templates/why.html): sections fade in as they scroll
// into view, the figures count up once, and the table of contents
// highlights the section being read. Without JS (or with
// reduced motion) everything is simply shown as rendered by the server.
(function () {
    // Table of contents: highlight the section in view (works with reduced motion too).
    const tocLinks = document.querySelectorAll('.why-toc a[href^="#"]');
    if (tocLinks.length && 'IntersectionObserver' in window) {
        const byId = {};
        tocLinks.forEach((a) => { byId[a.getAttribute('href').slice(1)] = a; });
        const spy = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                tocLinks.forEach((a) => a.classList.remove('is-active'));
                byId[entry.target.id]?.classList.add('is-active');
            });
        }, { rootMargin: '-30% 0px -60% 0px' });
        Object.keys(byId).forEach((id) => { const el = document.getElementById(id); if (el) spy.observe(el); });
    }

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce || !('IntersectionObserver' in window)) return;
    document.documentElement.classList.add('js-why');

    const reveal = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('is-visible');
            reveal.unobserve(entry.target);
        });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    document.querySelectorAll('.why-reveal').forEach((el) => reveal.observe(el));

    const fmt = new Intl.NumberFormat('en-US');
    document.querySelectorAll('.why-stat__num[data-count]').forEach((el) => {
        const target = parseInt(el.dataset.count, 10) || 0;
        const start = performance.now(), duration = 1200;
        const tick = (now) => {
            const t = Math.min((now - start) / duration, 1);
            el.textContent = fmt.format(Math.round(target * (1 - Math.pow(1 - t, 3))));
            if (t < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    });
})();
