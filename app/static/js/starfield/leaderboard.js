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

        onMounted(load);
        return { loading, error, boards, ships, difficulties, active, ship, difficulty, board, load, show, medal, SHIP_LABELS, DIFF_LABELS };
    },
}).mount('#sf-leaderboard');
