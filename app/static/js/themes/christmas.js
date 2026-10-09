// Christmas themes decorations (css/themes/christmas.css). Present only while
// html[data-theme] is "christmas" or "christmas-night" — added and removed
// live when the theme is switched (theme.js sets the attribute), nothing at
// all for other themes. Both add a snowy landscape band above the footer
// (day or night colours); the night theme also adds discreet stars.
(function () {
    const html = document.documentElement;
    const COLORS = ['red', 'gold', 'green', 'blue', 'pink'];
    const SPACING = 46;          // px between two bulbs (one scallop of the wire)
    const THEMES = ['christmas', 'christmas-night'];
    let mounted = null, resizeTimer = null;     // the theme currently decorated
    let weatherTimer = null;

    function garland(nav) {
        const width = nav.clientWidth;
        const count = Math.max(4, Math.floor(width / SPACING));
        const step = width / count;
        let d = '';
        for (let i = 0; i < count; i++) {
            const x0 = i * step, x1 = x0 + step;
            d += `${i ? '' : `M${x0},2 `}Q${x0 + step / 2},20 ${x1},2 `;
        }
        const el = document.createElement('div');
        el.className = 'xmas-garland';
        el.innerHTML = `<svg class="xmas-garland__wire" viewBox="0 0 ${width} 26" preserveAspectRatio="none"><path d="${d}"/></svg>`;
        for (let i = 0; i < count; i++) {
            const b = document.createElement('span');
            b.className = `xmas-bulb xmas-bulb--${COLORS[i % COLORS.length]}`;
            b.style.left = `${i * step + step / 2}px`;
            b.style.animationDelay = `${((i * 7) % 11) * 0.22}s`;
            el.appendChild(b);
        }
        return el;
    }

    function hat() {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'xmas-hat');
        svg.setAttribute('viewBox', '0 0 64 56');
        svg.setAttribute('aria-hidden', 'true');
        svg.innerHTML =
            '<path d="M8 44 C14 20 30 6 46 8 C54 9 58 16 56 24 L50 22 C44 18 36 24 32 44 Z" fill="#d62828"/>' +
            '<rect x="2" y="40" width="40" height="11" rx="5.5" fill="#fff"/>' +
            '<circle cx="54" cy="26" r="7" fill="#fff"/>';
        return svg;
    }

    function snow() {
        const el = document.createElement('div');
        el.className = 'xmas-snow';
        el.setAttribute('aria-hidden', 'true');
        const n = window.innerWidth < 768 ? 14 : 28;
        for (let i = 0; i < n; i++) {
            const f = document.createElement('span');
            f.className = 'xmas-flake';
            f.textContent = Math.random() < 0.5 ? '❄' : '•';
            f.style.left = `${Math.random() * 100}%`;
            f.style.fontSize = `${8 + Math.random() * 10}px`;
            f.style.opacity = (0.35 + Math.random() * 0.45).toFixed(2);
            const fall = 9 + Math.random() * 10, sway = 2 + Math.random() * 3;
            f.style.animationDuration = `${fall}s, ${sway}s`;
            f.style.animationDelay = `${-Math.random() * fall}s, ${-Math.random() * sway}s`;
            el.appendChild(f);
        }
        return el;
    }

    function stars() {
        const el = document.createElement('div');
        el.className = 'xmas-stars';
        el.setAttribute('aria-hidden', 'true');
        const n = window.innerWidth < 768 ? 18 : 40;
        for (let i = 0; i < n; i++) {
            const st = document.createElement('span');
            st.className = 'xmas-star';
            st.style.left = `${Math.random() * 100}%`;
            st.style.top = `${8 + Math.random() * 90}%`;
            const size = Math.random() < 0.8 ? 1.5 : 2.5;
            st.style.width = st.style.height = `${size}px`;
            st.style.animationDuration = `${3 + Math.random() * 4}s`;
            st.style.animationDelay = `${-Math.random() * 6}s`;
            el.appendChild(st);
        }
        return el;
    }

    // Distant landscape: two rows of snowy hills and fir-tree silhouettes,
    // smaller and paler far away. Seeded so it's the same on every page.
    // Colours of the landscape per theme: snowy day or night.
    const LAND = {
        'christmas': {
            farHills: '#e4ebf3', farTree: '#a9bcae', farSnow: 'rgba(255,255,255,.9)',
            nearHills: '#f3f6fa', nearTree: '#6f8f78', nearSnow: 'rgba(255,255,255,.95)',
            ground: '#ffffff', groundOpacity: '.5', stars: 0,
        },
        'christmas-night': {
            farHills: '#151c2a', farTree: '#141a27', farSnow: 'rgba(220,232,250,.18)',
            nearHills: '#121825', nearTree: '#0e131d', nearSnow: 'rgba(235,242,255,.28)',
            ground: '#e9eef7', groundOpacity: '.06', stars: 18,
        },
    };

    function landscape(theme) {
        const c = LAND[theme] || LAND['christmas-night'];
        let seed = 7;
        const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
        const W = 1440, H = 240;

        const hillY = (base, amp, waves, x) =>
            base - amp * (Math.sin(x / W * Math.PI * waves) * 0.6 + Math.sin(x / W * Math.PI * waves * 2.3 + 1) * 0.4);
        const hills = (base, amp, waves) => {
            let d = `M0,${H} L0,${base}`;
            for (let x = 0; x <= W; x += 40) d += ` L${x},${hillY(base, amp, waves, x).toFixed(1)}`;
            return d + ` L${W},${H} Z`;
        };
        // A small campfire far away on the near hills: flickering flames,
        // a warm glow on the snow, smoke rising and fading (christmas.css).
        const campfire = (x, y) => {
            let g = `<g class="xmas-camp" transform="translate(${x},${y}) scale(1.3)">`;
            g += '<ellipse class="xmas-camp__glow" cx="0" cy="-2" rx="34" ry="12" fill="url(#xmas-camp-glow)"/>';
            for (let i = 0; i < 4; i++) {
                g += `<circle class="xmas-camp__smoke" style="animation-delay:${-i * 1.6}s" cx="0" cy="-12" r="3.5" fill="url(#xmas-camp-smoke)"/>`;
            }
            g += '<rect x="-9" y="-3" width="18" height="3" rx="1.5" fill="#3a2a1f" transform="rotate(14)"/>';
            g += '<rect x="-9" y="-3" width="18" height="3" rx="1.5" fill="#3a2a1f" transform="rotate(-14)"/>';
            g += '<path class="xmas-camp__flame" d="M0,-16 C5,-9 6,-4 0,-2 C-6,-4 -5,-9 0,-16 Z" fill="#ff7a1f"/>';
            g += '<path class="xmas-camp__flame xmas-camp__flame--in" d="M0,-11 C3,-7 3,-4 0,-2.5 C-3,-4 -3,-7 0,-11 Z" fill="#ffd166"/>';
            return g + '</g>';
        };
        const tree = (x, ground, h, color, snow) => {
            const w = h * 0.62;
            let path = '', caps = '';
            for (let t = 0; t < 3; t++) {               // three tiers of branches
                const top = ground - h + t * h * 0.24;
                const bottom = top + h * 0.42;
                const half = w * (0.55 + t * 0.22) / 2;
                path += `M${x},${top} L${x - half},${bottom} L${x + half},${bottom} Z `;
                caps += `M${x},${top} L${x - half * 0.45},${top + h * 0.12} L${x + half * 0.45},${top + h * 0.12} Z `;
            }
            path += `M${x - w * 0.06},${ground - h * 0.1} h${w * 0.12} v${h * 0.12} h${-w * 0.12} Z`;
            return `<path d="${path}" fill="${color}"/><path d="${caps}" fill="${snow}"/>`;
        };

        let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg">`;
        svg += '<defs>' +
            '<radialGradient id="xmas-camp-glow"><stop offset="0" stop-color="#ff9a3c" stop-opacity="1"/><stop offset="1" stop-color="#ff9a3c" stop-opacity="0"/></radialGradient>' +
            '<radialGradient id="xmas-camp-smoke"><stop offset="0" stop-color="#aab4c4" stop-opacity=".9"/><stop offset="1" stop-color="#aab4c4" stop-opacity="0"/></radialGradient>' +
            '</defs>';
        for (let i = 0; i < c.stars; i++) {                                // a few stars in the sky (night)
            const big = rand() < 0.2;
            svg += `<circle class="xmas-sky-star" style="animation-delay:${(-rand() * 5).toFixed(2)}s" ` +
                   `cx="${(rand() * W).toFixed(0)}" cy="${(8 + rand() * 95).toFixed(0)}" r="${big ? 1.4 : 0.8}" fill="#fff"/>`;
        }
        svg += `<path d="${hills(150, 26, 3)}" fill="${c.farHills}"/>`;          // far hills
        for (let i = 0; i < 26; i++) {                                     // far trees
            const x = rand() * W, h = 26 + rand() * 18;
            svg += tree(x, 150 + rand() * 10, h, c.farTree, c.farSnow);
        }
        svg += `<path d="${hills(196, 20, 2)}" fill="${c.nearHills}"/>`;         // near hills
        for (let i = 0; i < 16; i++) {                                     // near trees
            const x = rand() * W, h = 44 + rand() * 30;
            svg += tree(x, 200 + rand() * 12, h, c.nearTree, c.nearSnow);
        }
        const fx = W * 0.71;
        svg += campfire(fx, hillY(196, 20, 2, fx) + 4);
        svg += `<path d="${hills(226, 6, 4)}" fill="${c.ground}" opacity="${c.groundOpacity}"/>`; // snow on the ground
        svg += '</svg>';

        const el = document.createElement('div');
        el.className = 'xmas-land';
        el.setAttribute('aria-hidden', 'true');
        el.innerHTML = svg;
        return el;
    }

    // ── Snow that starts and stops naturally ──────────────────────────
    // Stopping never makes flakes vanish: each one finishes its fall to the
    // bottom of the screen and is then not sent again. Starting sends every
    // flake again from the top, each after its own short delay — the snow
    // builds up progressively. Used by the weather cycle and by the corner
    // switch alike.
    const rangeMs = (min, max) => (min + Math.random() * (max - min)) * 1000;
    const SNOW_OFF_KEY = 'rz-xmas-snow-off';
    const snowOff = () => { try { return localStorage.getItem(SNOW_OFF_KEY) === '1'; } catch { return false; } };

    function stopFalling(snowEl, onDone) {
        let falling = 0;
        Array.from(snowEl.children).forEach((f) => {
            if (f._onFallEnd) f.removeEventListener('animationiteration', f._onFallEnd);
            if (f.classList.contains('xmas-flake--done') || f.classList.contains('xmas-flake--off')) {
                f.classList.add('xmas-flake--done');
                return;
            }
            falling++;
            f._onFallEnd = (e) => {
                if (e.animationName !== 'xmas-fall') return;      // ignore the sway loop
                f.removeEventListener('animationiteration', f._onFallEnd);
                f._onFallEnd = null;
                f.classList.add('xmas-flake--done');
                if (--falling === 0 && onDone) onDone();
            };
            f.addEventListener('animationiteration', f._onFallEnd);
        });
        if (falling === 0 && onDone) onDone();
    }

    function startFalling(snowEl, intensity) {
        const flakes = Array.from(snowEl.children);
        const visible = Math.round(flakes.length * intensity);
        flakes.forEach((f, i) => {
            if (f._onFallEnd) { f.removeEventListener('animationiteration', f._onFallEnd); f._onFallEnd = null; }
            const [fall, sway] = f.style.animationDuration.split(',').map(parseFloat);
            // restart from the top: drop the animation, reflow, put it back with a positive delay
            f.style.animationName = 'none';
            void f.offsetWidth;
            f.style.animationName = '';
            f.style.animationDelay = `${(Math.random() * fall * 0.8).toFixed(2)}s, ${(-Math.random() * sway).toFixed(2)}s`;
            f.classList.toggle('xmas-flake--off', i >= visible);
            f.classList.remove('xmas-flake--done');
        });
    }

    // Weather: snowfalls of varying intensity (40–100% of the flakes), then
    // calm spells. Held while the user turned the snow off.
    function weather(snowEl) {
        const snowfall = () => {
            if (snowOff()) return;
            startFalling(snowEl, 0.4 + Math.random() * 0.6);
            weatherTimer = setTimeout(calm, rangeMs(45, 90));
        };
        const calm = () => {
            stopFalling(snowEl, () => { if (!snowOff()) weatherTimer = setTimeout(snowfall, rangeMs(25, 50)); });
        };
        snowEl._resume = () => { clearTimeout(weatherTimer); snowfall(); };
        snowEl._halt = () => { clearTimeout(weatherTimer); stopFalling(snowEl); };
        if (snowOff()) Array.from(snowEl.children).forEach((f) => f.classList.add('xmas-flake--done'));
        else weatherTimer = setTimeout(calm, rangeMs(45, 90));    // page loads with snow already falling
    }

    // Small switch in a corner to turn the snow off (remembered in this browser).
    function snowSwitch(snowEl) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'xmas-snow-switch';
        const update = () => {
            const off = snowOff();
            btn.classList.toggle('is-off', off);
            btn.title = off ? 'Turn the snow back on' : 'Turn the snow off';
            btn.setAttribute('aria-label', btn.title);
            btn.setAttribute('aria-pressed', String(off));
        };
        btn.innerHTML = '<i class="fa-solid fa-snowflake"></i>';
        btn.addEventListener('click', () => {
            const turnOff = !snowOff();
            try { localStorage.setItem(SNOW_OFF_KEY, turnOff ? '1' : '0'); } catch { /* storage unavailable */ }
            if (turnOff) snowEl._halt(); else snowEl._resume();     // last flakes fall / snow starts from the top
            update();
        });
        update();
        return btn;
    }

    function mount(theme) {
        const nav = document.querySelector('.main-navbar');
        if (nav) nav.appendChild(garland(nav));
        const logo = document.querySelector('.main-navbar .navbar-brand');
        if (logo) { logo.classList.add('xmas-logo'); logo.appendChild(hat()); }
        const snowEl = snow();
        document.body.appendChild(snowEl);
        weather(snowEl);
        document.body.appendChild(snowSwitch(snowEl));
        if (theme === 'christmas-night') document.body.appendChild(stars());
        // Landscape band right above the footer, in the page flow (pushes the footer down).
        const footer = document.querySelector('.rulezet-footer');
        if (footer) footer.parentNode.insertBefore(landscape(theme), footer);
        else document.body.appendChild(landscape(theme));
        mounted = theme;
    }

    function unmount() {
        clearTimeout(weatherTimer);
        document.querySelectorAll('.xmas-garland, .xmas-hat, .xmas-snow, .xmas-snow-switch, .xmas-stars, .xmas-land').forEach((el) => el.remove());
        document.querySelectorAll('.xmas-logo').forEach((el) => el.classList.remove('xmas-logo'));
        mounted = null;
    }

    function sync() {
        const theme = html.getAttribute('data-theme');
        const wanted = THEMES.includes(theme) ? theme : null;
        if (wanted === mounted) return;
        if (mounted) unmount();
        if (wanted) mount(wanted);
    }

    window.addEventListener('resize', () => {
        if (!mounted) return;
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            const nav = document.querySelector('.main-navbar');
            const old = nav && nav.querySelector('.xmas-garland');
            if (old) old.replaceWith(garland(nav));
        }, 200);
    });
    new MutationObserver(sync).observe(html, { attributes: true, attributeFilter: ['data-theme'] });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', sync);
    else sync();
})();
