/**
 * main.js — Night Shift, the hidden investigation game (/nightshift).
 * Screens: title → desk (investigate, pin evidence, write the rule, test,
 * deploy) → case closed (score). The case and every result come from the
 * server (app/features/nightshift/); this file only shows them.
 */
import { call } from './api.js';
import { initialLang, saveLang, text } from './i18n.js';
import { startRain } from './rain.js';

const { createApp, ref, reactive, computed } = Vue;

const TABS = [
    { key: 'mail', icon: 'fa-solid fa-envelope' },
    { key: 'files', icon: 'fa-solid fa-folder-open' },
    { key: 'logs', icon: 'fa-solid fa-list' },
];
const MINUTES_PER_ACTION = 1;   // the shift clock moves with what the player does, not with real time

createApp({
    delimiters: ['[[', ']]'],
    setup() {
        const lang = ref(initialLang());
        const screen = ref('title');
        const busy = ref(false);
        const error = ref('');
        const caseData = ref(null);
        const run = ref({ evidence: [], hints: [], hints_used: 0, tests: 0, failed_deploys: 0 });
        const tool = ref('mail');
        const file = ref(null);
        const logQuery = ref('');
        const logHost = ref('');
        const blanks = reactive({ a: '', b: '', condition: '' });
        const result = ref(null);
        const reaction = ref('');
        const introStep = ref(0);
        const minutes = ref(21 * 60);
        const playerName = window.NS_PLAYER_NAME || '';

        const t = (key) => text(lang.value, key);
        const tr = (value) => (value && typeof value === 'object') ? (value[lang.value] || value.en) : value;

        const clock = computed(() => {
            const m = minutes.value % (24 * 60);
            return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
        });
        // The mug empties over the night: full at 21:00, empty at 06:00.
        const coffee = computed(() => {
            const elapsed = (minutes.value - 21 * 60 + 24 * 60) % (24 * 60);
            return Math.max(5, 100 - Math.round(elapsed / (9 * 60) * 100));
        });
        const tick = (n = MINUTES_PER_ACTION) => { minutes.value += n; };

        const introLines = computed(() => caseData.value ? tr(caseData.value.rulezy.intro) : []);
        const rulezySay = computed(() => reaction.value ? [reaction.value] : introLines.value.slice(0, introStep.value + 1));
        const say = (key) => { reaction.value = tr(caseData.value.rulezy.lines[key]) || ''; };

        const logHosts = computed(() => caseData.value ? [...new Set(caseData.value.tools.logs.map(l => l.host))].sort() : []);
        const filteredLogs = computed(() => {
            if (!caseData.value) return [];
            const q = logQuery.value.trim().toLowerCase();
            return caseData.value.tools.logs
                .filter(l => !logHost.value || l.host === logHost.value)
                .filter(l => !q || `${l.host} ${l.source} ${l.text}`.toLowerCase().includes(q))
                .slice().sort((a, b) => a.time.localeCompare(b.time));
        });

        const isPinned = (key) => run.value.evidence.includes(key);
        const requiredPinned = computed(() => caseData.value
            ? caseData.value.evidence.required.filter(isPinned).length : 0);
        const ruleReady = computed(() => blanks.a.trim() && blanks.b.trim() && blanks.condition);
        const details = computed(() => run.value.score_details || {});
        const closingLine = computed(() => caseData.value
            ? tr(caseData.value.rulezy.lines[details.value.variants_caught ? 'closed' : 'closed_missed_variant']) : '');

        function evidenceLabel(key) {
            const c = caseData.value;
            if (key.startsWith('line:')) {
                const [, sample, index] = key.split(':');
                const f = c.tools.files.find(x => x.sample === sample);
                return f ? `${f.name} · ${f.lines[+index].trim()}` : key;
            }
            const mail = c.tools.mail.find(m => m.key === key);
            if (mail) return `✉ ${mail.subject}`;
            const f = c.tools.files.find(x => x.key === key);
            if (f) return `🗎 ${f.name}`;
            const log = c.tools.logs.find(l => l.key === key);
            return log ? `${log.time} ${log.host} · ${log.text.slice(0, 70)}${log.text.length > 70 ? '…' : ''}` : key;
        }

        async function guarded(fn) {
            if (busy.value) return;
            busy.value = true;
            error.value = '';
            try {
                await fn();
            } catch (e) {
                error.value = e.message && !e.message.startsWith('HTTP') ? e.message : t('network');
            } finally {
                busy.value = false;
            }
        }

        function startCase(caseId) {
            return guarded(async () => {
                const data = await call('start', { case: caseId });
                caseData.value = data.case;
                run.value = data.run;
                const [h, m] = data.case.time.split(':').map(Number);
                minutes.value = h * 60 + m + data.run.evidence.length + data.run.tests;
                Object.assign(blanks, { a: '', b: '', condition: '' });
                result.value = null;
                reaction.value = '';
                introStep.value = data.run.evidence.length ? introLines.value.length - 1 : 0;
                tool.value = 'mail';
                file.value = null;
                screen.value = data.run.closed ? 'closed' : 'desk';
            });
        }

        function pin(key) {
            return guarded(async () => {
                const first = !run.value.evidence.length;
                const data = await call('pin', { run: run.value.uuid, key });
                run.value = data.run;
                tick();
                if (first) say('pin_first');
                else if (key.startsWith('log:dns-printer') && isPinned(key)) say('printer');
            });
        }

        function openFile(name) {
            const f = caseData.value.tools.files.find(x => x.name === name);
            if (f) { file.value = f; tool.value = 'files'; }
        }

        function askHint() {
            return guarded(async () => {
                const data = await call('hint', { run: run.value.uuid });
                run.value = data.run;
                reaction.value = '';
                tick(5);
            });
        }

        function check(deploy) {
            if (!ruleReady.value) { error.value = t('blank_needed'); return; }
            return guarded(async () => {
                const data = await call(deploy ? 'deploy' : 'test', { run: run.value.uuid, blanks: { ...blanks } });
                run.value = data.run;
                result.value = data.outcome === 'need_evidence' ? null : data;
                tick(deploy ? 5 : 2);
                say(data.outcome === 'closed' ? 'ok' : data.outcome);
                if (data.outcome === 'closed') screen.value = 'closed';
            });
        }

        function toggleLang() {
            lang.value = lang.value === 'en' ? 'fr' : 'en';
            saveLang(lang.value);
            if (reaction.value) reaction.value = '';
        }

        return {
            lang, screen, busy, error, caseData, run, tool, tabs: TABS, file, logQuery, logHost, logHosts,
            filteredLogs, blanks, result, introStep, introLines, rulezySay, clock, coffee, playerName,
            requiredPinned, ruleReady, details, closingLine,
            t, tr, isPinned, evidenceLabel, startCase, pin, openFile, askHint, check, toggleLang,
        };
    },
    mounted() {
        startRain(document.getElementById('ns-rain'));
    },
}).mount('#ns-app');
