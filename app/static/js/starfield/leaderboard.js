// Starfield leaderboards (templates/starfield.html, everyone): one tab per board of the setting
// starfield.leaderboards (stars, endless score, total score, kills…), filtered by ship / difficulty.
// The viewer's own row is marked (logged in: their account; else this browser's anonymous id).
const { createApp, ref, computed, onMounted } = Vue;

const PLAYER_KEY = 'rz-starfield-player';
const SHIP_LABELS = { yara: 'YARA', suricata: 'Suricata', sigma: 'Sigma', zeek: 'Zeek' };
const DIFF_LABELS = { analyst: 'Analyst', hunter: 'Threat hunter', redteam: 'Red team' };

function myPlayerId() {
    try { return localStorage.getItem(PLAYER_KEY) || ''; } catch { return ''; }
}

const fmtTime = (s) => { s = s || 0; const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), r = s % 60; return h ? `${h}h${String(m).padStart(2, '0')}` : `${m}:${String(r).padStart(2, '0')}`; };

createApp({
    delimiters: ['[[', ']]'],
    setup() {
        const loading = ref(true);
        const error = ref('');
        const boards = ref([]);
        const ships = ref([]);
        const difficulties = ref([]);
        const points = ref(null);
        const active = ref('');
        const ship = ref('');
        const difficulty = ref('');

        async function load() {
            loading.value = true;
            error.value = '';
            try {
                const params = new URLSearchParams({ player: myPlayerId() });
                if (ship.value) params.set('ship', ship.value);
                if (difficulty.value) params.set('difficulty', difficulty.value);
                const res = await fetch(`/starfield/leaderboard?${params}`);
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const data = await res.json();
                boards.value = data.boards || [];
                ships.value = data.ships || [];
                difficulties.value = data.difficulties || [];
                points.value = data.points || null;
                if (!boards.value.some(b => b.key === active.value)) active.value = boards.value[0] ? boards.value[0].key : '';
            } catch (e) {
                error.value = 'The leaderboards could not be loaded.';
            } finally {
                loading.value = false;
            }
        }

        const board = computed(() => boards.value.find(b => b.key === active.value) || null);
        const show = (b, value) => (b.key === 'time' ? fmtTime(value) : b.key === 'win_rate' ? `${value} %` : Number(value).toLocaleString());
        const medal = (rank) => ({ 1: 'sfl-gold', 2: 'sfl-silver', 3: 'sfl-bronze' }[rank] || '');

        // the viewer's place on the Overall board, shown on the game's results screens
        function showMyRank() {
            const overall = boards.value.find(b => b.key === 'overall');
            const mine = overall && (overall.rows.find(r => r.me) || overall.me);
            for (const el of document.querySelectorAll('[data-rank]')) {
                if (!mine) { el.hidden = true; continue; }
                el.hidden = false;
                el.innerHTML = '';
                const icon = document.createElement('i');
                icon.className = 'fa-solid fa-crown';
                el.append(icon, ` Overall rank #${mine.rank} of ${overall.players} · ${Number(mine.value).toLocaleString()} pts`);
            }
        }

        onMounted(async () => {
            await load();
            const btn = document.getElementById('sf-btn-leaderboard');
            if (btn) btn.addEventListener('click', () => {
                if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
                document.getElementById('sf-leaderboard').scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
            // a run just recorded: the boards and the player's rank are fresh again
            window.addEventListener('starfield:run-recorded', async () => {
                // the overall board is the one players compare: show it after a run
                active.value = 'overall';
                ship.value = '';
                difficulty.value = '';
                await load();
                showMyRank();
            });
        });
        return { points, loading, error, boards, ships, difficulties, active, ship, difficulty, board, load, show, medal, SHIP_LABELS, DIFF_LABELS };
    },
}).mount('#sf-leaderboard');
