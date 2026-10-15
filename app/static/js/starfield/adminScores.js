// Starfield admin panel (templates/starfield.html, admins only — the
// /starfield/admin/* routes check it again): every player, and every run of
// one player in detail.
const { createApp, ref, computed, onMounted } = Vue;

const SHIPS = { yara: 'YARA', suricata: 'Suricata', sigma: 'Sigma', zeek: 'Zeek' };
const DIFFS = { analyst: 'Analyst', hunter: 'Threat hunter', redteam: 'Red team' };
const WEAPONS = { pulse: 'Suricata Pulse', spread: 'YARA Spread', rail: 'Sigma Rail', seeker: 'Zeek Seeker' };
const PLAYER_COLS = [
    { key: 'name', label: 'Player' },
    { key: 'runs', label: 'Runs', cls: 'text-center' },
    { key: 'win_rate', label: 'Won', cls: 'text-center' },
    { key: 'levels_cleared', label: 'Levels', cls: 'text-center' },
    { key: 'stars', label: 'Stars', cls: 'text-center' },
    { key: 'best_endless', label: 'Best endless', cls: 'text-center' },
    { key: 'kills', label: 'Kills', cls: 'text-center' },
    { key: 'favorite_ship', label: 'Ship' },
    { key: 'difficulty', label: 'Difficulty' },
    { key: 'last_played', label: 'Last played' },
];

const fmt = (n) => (n == null ? '—' : Number(n).toLocaleString());
const fmtTime = (s) => { s = s || 0; const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), r = s % 60; return h ? `${h}h${String(m).padStart(2, '0')}` : `${m}:${String(r).padStart(2, '0')}`; };
const when = (iso) => (iso ? new Date(iso).toLocaleString() : '');
function ago(iso) {
    if (!iso) return '—';
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return 'just now';
    if (s < 3600) return `${Math.floor(s / 60)} min ago`;
    if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
    return `${Math.floor(s / 86400)} d ago`;
}

createApp({
    delimiters: ['[[', ']]'],
    setup() {
        const loading = ref(true);
        const players = ref([]);
        const runsTotal = ref(0);
        const topEndless = ref([]);
        const q = ref('');
        const hideAnon = ref(false);
        const sortKey = ref('last_played');
        const sortDir = ref('desc');
        const selected = ref(null);
        const runs = ref([]);
        const runsLoading = ref(false);
        const openRun = ref(null);

        async function load() {
            loading.value = true;
            try {
                const data = await fetch('/starfield/admin/players').then(r => r.json());
                players.value = data.players || [];
                runsTotal.value = data.runs || 0;
                topEndless.value = data.top_endless || [];
                if (selected.value) {
                    const fresh = players.value.find(p => p.key === selected.value.key);
                    if (fresh) openPlayer(fresh);
                }
            } finally {
                loading.value = false;
            }
        }

        function sortBy(key) {
            if (sortKey.value === key) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
            else { sortKey.value = key; sortDir.value = key === 'name' ? 'asc' : 'desc'; }
        }

        const sortValue = (p, key) => (key === 'best_endless' ? (p.best_endless ? p.best_endless.score : -1) : p[key] ?? '');
        const sortedPlayers = computed(() => {
            const needle = q.value.trim().toLowerCase();
            const list = players.value.filter(p => (!hideAnon.value || p.user_id)
                && (!needle || (p.name || '').toLowerCase().includes(needle) || (p.player_id || '').includes(needle)));
            const dir = sortDir.value === 'asc' ? 1 : -1;
            return [...list].sort((a, b) => {
                const va = sortValue(a, sortKey.value), vb = sortValue(b, sortKey.value);
                return (va > vb ? 1 : va < vb ? -1 : 0) * dir;
            });
        });

        async function openPlayer(p) {
            selected.value = p;
            openRun.value = null;
            runsLoading.value = true;
            try {
                const data = await fetch('/starfield/admin/runs?player=' + encodeURIComponent(p.key)).then(r => r.json());
                runs.value = data.success ? data.runs : [];
            } finally {
                runsLoading.value = false;
            }
        }

        // Best run per campaign level of the selected player.
        const bestByLevel = computed(() => {
            const out = {};
            for (const r of runs.value) {
                if (r.mode !== 'level') continue;
                const k = `${r.world}-${r.level_index}`;
                const cur = out[k];
                const better = !cur || (r.won && !cur.won) || (r.won === cur.won && (r.stars > cur.stars || (r.stars === cur.stars && r.score > cur.score)));
                if (better) out[k] = { ...r, tries: (cur ? cur.tries : 0) + 1 };
                else cur.tries += 1;
            }
            return out;
        });
        const best = (w, i) => bestByLevel.value[`${w}-${i}`];
        function cellClass(w, i) {
            const b = best(w, i);
            if (!b) return 'sfa-cell--none';
            return b.won ? `sfa-cell--won sfa-cell--s${b.stars}` : 'sfa-cell--lost';
        }
        function cellTitle(w, i) {
            const b = best(w, i);
            if (!b) return 'Never played';
            return `${b.level_name} — ${b.won ? 'won' : 'not cleared yet'}, best ${fmt(b.score)} (${b.tries} tr${b.tries > 1 ? 'ies' : 'y'})`;
        }

        const sortedCounts = (counts) => Object.fromEntries(Object.entries(counts || {}).sort((a, b) => b[1] - a[1]));

        onMounted(load);

        return {
            SHIPS, DIFFS, WEAPONS, PLAYER_COLS, loading, players, runsTotal, topEndless, q, hideAnon, sortKey, sortDir,
            selected, runs, runsLoading, openRun, sortedPlayers, load, sortBy, openPlayer, best, cellClass, cellTitle,
            sortedCounts, fmt, fmtTime, when, ago,
        };
    },
}).mount('#sf-admin');
