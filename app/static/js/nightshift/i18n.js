/**
 * i18n.js — interface text of Night Shift, EN and FR. The story text lives in
 * each case (app/features/nightshift/cases/*.json), already in both languages.
 */
const TEXT = {
    en: {
        kicker: 'a Rulezet detour', tagline: 'One analyst. One night. Every alert is yours.',
        analyst: 'Analyst on duty', anonymous: 'Anonymous analyst', badge_in: 'Badge in',
        clock: 'Shift clock', language: 'Language', coffee: 'Coffee',
        mail: 'Mailbox', files: 'Files', logs: 'Logs',
        pin: 'Pin to the evidence board', unpin: 'Click to unpin', from: 'From', to: 'To', bytes: 'bytes',
        strings_hint: 'Click a line to pin it as evidence.', pick_file: 'Pick a file on the left.',
        search_logs: 'Search the logs…', host: 'Host', all_hosts: 'All hosts', no_logs: 'Nothing matches.',
        next: 'Next', hint: 'Hint', board: 'Evidence board', key_evidence: 'key evidence',
        board_empty: 'Nothing pinned yet. Click a mail, a file, a line or a log entry.',
        your_rule: 'Your rule', test: 'Test', deploy: 'Deploy', tests_run: 'Tests', failed_deploys: 'Failed deploys',
        sample: 'Sample', expected: 'Should', rule_said: 'Your rule', malicious: 'match', benign: 'stay silent',
        match: 'matched', silent: 'silent',
        case_closed: 'Case closed', hidden_variant: 'Hidden variant', caught: 'caught', missed: 'got through',
        s_closed: 'Case closed', s_quality: 'Rule quality', s_investigation: 'Investigation', bonus_clues: 'bonus clues',
        s_speed: 'Speed', s_hints: 'Hints', s_failed: 'Failed deploys', total: 'Total',
        next_case_soon: '22:15 — the next alert is on its way. (More of the night soon.)', replay: 'Replay this case',
        blank_needed: 'Fill both strings and pick a condition.', network: 'The SOC lost its connection. Try again.',
    },
    fr: {
        kicker: 'un détour Rulezet', tagline: 'Un analyste. Une nuit. Toutes les alertes sont pour toi.',
        analyst: 'Analyste de garde', anonymous: 'Analyste anonyme', badge_in: 'Badger',
        clock: 'Horloge de garde', language: 'Langue', coffee: 'Café',
        mail: 'Messagerie', files: 'Fichiers', logs: 'Journaux',
        pin: 'Épingler au tableau des preuves', unpin: 'Cliquer pour retirer', from: 'De', to: 'À', bytes: 'octets',
        strings_hint: 'Clique sur une ligne pour l\'épingler comme preuve.', pick_file: 'Choisis un fichier à gauche.',
        search_logs: 'Chercher dans les journaux…', host: 'Machine', all_hosts: 'Toutes les machines', no_logs: 'Aucun résultat.',
        next: 'Suite', hint: 'Indice', board: 'Tableau des preuves', key_evidence: 'preuves clés',
        board_empty: 'Rien d\'épinglé. Clique sur un mail, un fichier, une ligne ou une entrée de journal.',
        your_rule: 'Ta règle', test: 'Tester', deploy: 'Déployer', tests_run: 'Tests', failed_deploys: 'Déploiements ratés',
        sample: 'Échantillon', expected: 'Doit', rule_said: 'Ta règle', malicious: 'déclencher', benign: 'rester muette',
        match: 'déclenchée', silent: 'muette',
        case_closed: 'Affaire classée', hidden_variant: 'Variante cachée', caught: 'attrapée', missed: 'passée',
        s_closed: 'Affaire classée', s_quality: 'Qualité de la règle', s_investigation: 'Enquête', bonus_clues: 'indices bonus',
        s_speed: 'Rapidité', s_hints: 'Indices', s_failed: 'Déploiements ratés', total: 'Total',
        next_case_soon: '22:15 — la prochaine alerte arrive. (La suite de la nuit bientôt.)', replay: 'Rejouer ce cas',
        blank_needed: 'Remplis les deux chaînes et choisis une condition.', network: 'Le SOC a perdu la connexion. Réessaie.',
    },
};

const LANG_KEY = 'rz-nightshift-lang';

export function initialLang() {
    try {
        const saved = localStorage.getItem(LANG_KEY);
        if (saved === 'en' || saved === 'fr') return saved;
    } catch { /* private mode */ }
    return (navigator.language || 'en').toLowerCase().startsWith('fr') ? 'fr' : 'en';
}

export function saveLang(lang) {
    try { localStorage.setItem(LANG_KEY, lang); } catch { /* private mode */ }
}

export function text(lang, key) {
    return (TEXT[lang] && TEXT[lang][key]) || TEXT.en[key] || key;
}
