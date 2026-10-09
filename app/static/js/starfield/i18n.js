/**
 * i18n.js — English / French. The game is written in English; tr() looks the
 * English string up in FR and fills {placeholders}. Data tables (worlds,
 * enemies, bosses…) are translated once at start-up by localizeData(), the
 * static HTML of the template by localizeDom(). Switching language reloads
 * the page, so nothing has to be re-translated on the fly.
 */

let lang = 'en';

export function setLang(l) { lang = l === 'fr' ? 'fr' : 'en'; document.documentElement.lang = lang; }
export const getLang = () => lang;
export const defaultLang = () => ((navigator.language || '').toLowerCase().startsWith('fr') ? 'fr' : 'en');

/** Translate an English string; {name} placeholders are filled from params */
export function tr(str, params) {
    let s = str;
    if (lang === 'fr' && typeof str === 'string' && Object.prototype.hasOwnProperty.call(FR, str)) s = FR[str];
    if (params) s = s.replace(/\{(\w+)\}/g, (m, k) => (k in params ? params[k] : m));
    return s;
}

/** Translate the display fields of the data tables, in place */
export function localizeData(tables) {
    if (lang !== 'fr') return;
    const FIELDS = ['name', 'desc', 'intro', 'story', 'sub', 'label'];
    const walk = obj => {
        if (!obj || typeof obj !== 'object') return;
        for (const f of FIELDS) if (typeof obj[f] === 'string') obj[f] = tr(obj[f]);
        if (obj.special) walk(obj.special);
    };
    for (const t of tables) Object.values(t).forEach(walk);
}

/** Translate the text and tooltips of the template's static HTML */
export function localizeDom(root) {
    if (lang !== 'fr') return;
    const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (tw.nextNode()) nodes.push(tw.currentNode);
    for (const n of nodes) {
        const key = n.data.replace(/\s+/g, ' ').trim();
        if (key && FR[key]) n.data = n.data.replace(n.data.trim(), FR[key]);
    }
    root.querySelectorAll('[title], [aria-label]').forEach(el => {
        ['title', 'aria-label'].forEach(a => { const v = el.getAttribute(a); if (v && FR[v]) el.setAttribute(a, FR[v]); });
    });
}

const FR = {
    // ── Template ──
    'a Rulezet detour': 'un détour par Rulezet',
    'ZERO-DAY CAMPAIGN': 'CAMPAGNE ZERO-DAY',
    'Continue campaign': 'Continuer la campagne',
    'New campaign': 'Nouvelle campagne',
    'Threat hunt': 'Chasse aux menaces',
    '(endless)': '(sans fin)',
    'Hangar': 'Hangar',
    'How to play': 'Comment jouer',
    'Settings': 'Réglages',
    'Choose your clearance': 'Choisis ton niveau',
    'You can change it later in the settings. A new campaign resets the map, not the hangar.':
        'Tu pourras le changer dans les réglages. Une nouvelle campagne remet la carte à zéro, pas le hangar.',
    'Back': 'Retour',
    'Deploy': 'Déployer',
    'travel': 'voyager',
    'deploy': 'déployer',
    'hangar': 'hangar',
    'menu · 10 stars in a world open its secret honeypot': 'menu · 10 étoiles dans un monde ouvrent son honeypot secret',
    'Paused': 'Pause',
    'Resume': 'Reprendre',
    'Settings & keys': 'Réglages et touches',
    'Restart': 'Recommencer',
    'Abandon': 'Abandonner',
    'Level cleared': 'Niveau terminé',
    'Next level': 'Niveau suivant',
    'Retry': 'Réessayer',
    'Map': 'Carte',
    'Hunt over': 'Chasse terminée',
    'Hunt again': 'Rejouer',
    'Menu': 'Menu',
    'bytes': 'bytes',
    'Upgrades': 'Améliorations',
    'Weapons': 'Armes',
    'Rule engine': 'Vaisseaux',
    'Controls': 'Commandes',
    'Bestiary': 'Bestiaire',
    'Objectives & stars': 'Objectifs et étoiles',
    'Reset all progress': 'Effacer toute la progression',
    'Sound on / off': 'Son on / off',
    'Fullscreen': 'Plein écran',
    'Stars in this world': 'Étoiles dans ce monde',
    'Bytes to spend in the hangar': 'Bytes à dépenser au hangar',
    'Dash (Shift)': 'Dash',

    // ── Title / map / intro ──
    'stars': 'étoiles',
    'bosses': 'boss',
    'best hunt': 'meilleure chasse',
    'Start a new campaign? Map progress and stars are reset; bytes, upgrades and weapons are kept.':
        'Lancer une nouvelle campagne ? La carte et les étoiles repartent de zéro ; les bytes, améliorations et armes sont gardés.',
    'WAVES': 'VAGUES', 'SURVIVE': 'SURVIE', 'CUT THE C2': 'COUPER LE C2', 'PROTECT': 'PROTÉGER', 'BOSS': 'BOSS', 'BONUS': 'BONUS',
    'Best score {n}': 'Meilleur score {n}',
    'Not cleared yet': 'Pas encore terminé',
    'BOSS FIGHT': 'COMBAT DE BOSS',
    'LEVEL {n}': 'NIVEAU {n}',
    'SECRET': 'SECRET',
    'ENDLESS': 'SANS FIN',
    'Waves never stop. A boss every 5 waves. How long does your rule hold?':
        'Les vagues ne s\'arrêtent jamais. Un boss toutes les 5 vagues. Combien de temps ta règle va tenir ?',
    'LOCKED': 'VERROUILLÉ',

    // ── Results ──
    '{name} defeated': '{name} vaincu',
    'Rule disabled': 'Règle désactivée',
    'Sensor lost': 'Capteur perdu',
    'Score': 'Score', 'Wave': 'Vague', 'Bytes': 'Bytes', 'Kills': 'Éliminés', 'Best combo': 'Meilleur combo',
    'Time': 'Temps', 'Hits taken': 'Coups reçus', 'Date': 'Date',
    'New weapon: {name} — key {key}': 'Nouvelle arme : {name} — touche {key}',
    '{sub} unlocked: {name}': '{sub} débloqué : {name}',
    'Secret honeypot found on this world\'s map!': 'Honeypot secret trouvé sur la carte de ce monde !',
    'Campaign complete — the graph is quiet. Try Red team, or the endless hunt.':
        'Campagne terminée — le réseau est calme. Essaie le mode Red team, ou la chasse sans fin.',
    'Half of the bytes collected were kept: +{n}': 'La moitié des bytes ramassés est gardée : +{n}',
    'Complete the level': 'Terminer le niveau',
    'Take {n} hits or fewer': 'Prendre {n} coups maximum',
    'Take no hit at all': 'Ne prendre aucun coup',
    'Sensor above 70%': 'Capteur au-dessus de 70 %',
    'Collect {n} bytes': 'Ramasser {n} bytes',
    'Finish under {n}s': 'Finir en moins de {n} s',

    // ── Controls hint / HUD ──
    'move': 'bouger', 'mouse aims': 'la souris vise', 'click fires': 'clic pour tirer', 'dash': 'dash', 'bomb': 'bombe',
    'ship power': 'pouvoir', 'turn': 'tourner', 'thrust': 'avancer', 'brake': 'freiner', 'fire': 'tirer',
    'weapons': 'armes', 'pause': 'pause', 'mute': 'son',
    'change controls and keys in Settings': 'commandes et touches modifiables dans les Réglages',
    'COMBO x{n}': 'COMBO x{n}',
    'RAPID': 'RAPIDE', 'SHIELD': 'BOUCLIER', 'OVERCLOCK': 'OVERCLOCK', 'ENCRYPTED': 'CHIFFRÉ',
    ' — SHIELDED': ' — PROTÉGÉ',

    // ── Hangar ──
    'Maxed': 'Max',
    'Unlocked': 'Débloquée',
    'Defeat {boss} ({sub}) to unlock': 'Bats {boss} ({sub}) pour la débloquer',
    'Recharges in {n} s.': 'Se recharge en {n} s.',
    'Equipped': 'Équipé',
    'Click to equip': 'Clique pour l\'équiper',

    // ── Bestiary ──
    'Crawls towards you and splits into two wormlets when destroyed.': 'Rampe vers toi et se coupe en deux petits vers quand il est détruit.',
    'Keeps its distance and sprays five-way bursts.': 'Reste à distance et tire en éventail dans cinq directions.',
    'Looks exactly like a heal pickup — until you get close. Then it charges.': 'Ressemble à un cœur bonus… jusqu\'à ce que tu t\'approches. Là, il fonce sur toi.',
    'Throws hooks: if one lands, you are dragged towards it.': 'Lance des hameçons : si l\'un te touche, tu es tiré vers lui.',
    'Swarms in numbers. Fragile alone, deadly together.': 'Arrive en essaim. Fragile seul, dangereux en groupe.',
    'Avoids you and eats the bytes you collected while it lives.': 'T\'évite et mange tes bytes tant qu\'il est en vie.',
    'Shielded at the front (shoot its back or use the Sigma Rail). Its touch encrypts your weapon.':
        'Protégé devant (tire dans son dos ou utilise le Sigma Rail). S\'il te touche, il chiffre ton arme.',
    'Arms when you come near and blows up after a short fuse.': 'S\'arme quand tu t\'approches et explose peu après.',
    'Nearly invisible. Shows itself only when lining up a sniper shot.': 'Presque invisible. Il ne se montre que pour viser un tir de sniper.',
    'An elite operator: strafes, dodges your shots and fires precise bursts.': 'Un pirate d\'élite : il esquive tes tirs et tire des rafales précises.',
    'Rushes you and detonates — keep moving.': 'Fonce sur toi et explose — ne reste pas immobile.',
    'A static C2 node that keeps producing bots. Take it down first.': 'Un nœud C2 immobile qui fabrique des bots sans arrêt. Détruis-le en premier.',
    'Burrows, pops up next to you with a ring of bullets, then hides again. Hit it while surfaced.':
        'Se cache, surgit à côté de toi avec un cercle de balles, puis disparaît. Frappe-le quand il est sorti.',
    'A command-and-control beacon calling reinforcements. Objective target.': 'Une balise de commande qui appelle des renforts. C\'est ta cible.',

    // ── Help: controls ──
    'You are a detection rule deployed into the graph. Five worlds of malware stand between you and the zero-day.':
        'Tu es une règle de détection envoyée dans le réseau. Cinq mondes remplis de malwares te séparent du zero-day.',
    'Classic controls (default — keyboard only)': 'Commandes classiques (par défaut — clavier seul)',
    'Turn': 'Tourner',
    'Thrust forward (the ship keeps its momentum)': 'Avancer (le vaisseau garde son élan)',
    'Brake': 'Freiner',
    'Fire straight ahead (hold)': 'Tirer droit devant (maintenir)',
    'Twin-stick controls (Settings → Controls)': 'Commandes twin-stick (Réglages → Commandes)',
    'Move in that direction': 'Aller dans cette direction',
    'Mouse': 'Souris',
    'Aim — click or {key} to fire, right-click to dash': 'Viser — clic ou {key} pour tirer, clic droit pour le dash',
    'Both': 'Dans les deux cas',
    'Dash — a quick burst, invulnerable while dashing': 'Dash — une accélération éclair, invincible pendant le dash',
    'Quarantine bomb — clears every bullet on screen and hurts everything': 'Bombe de quarantaine — efface toutes les balles et blesse tout le monde',
    'Ship power — each ship (Hangar → Rule engine) has its own, recharging on its own: YARA Signature Sweep, Suricata IPS Drop, Sigma Correlation, Zeek Deep Inspection':
        'Pouvoir du vaisseau — chaque vaisseau (Hangar → Vaisseaux) a le sien, qui se recharge tout seul : YARA Balayage de signature, Suricata Blocage IPS, Sigma Corrélation, Zeek Inspection profonde',
    'Switch weapon': 'Changer d\'arme',
    'Pause': 'Pause',
    'Every key can be changed in Settings → Keys.': 'Toutes les touches se changent dans Réglages → Touches.',
    'Gamepad': 'Manette',
    'Left stick turn/thrust (classic) or move (twin) · right stick aim · RT fire · A dash · B bomb · Y ship power · LB/RB weapons':
        'Stick gauche tourner/avancer (classique) ou bouger (twin) · stick droit viser · RT tirer · A dash · B bombe · Y pouvoir · LB/RB armes',
    'Progress': 'Progression',
    'Bytes dropped by malware are spent in the hangar. Each world boss unlocks a new weapon and the next world. Get 10 stars in a world to reveal its secret honeypot. Kill fast to build a combo (up to x8).':
        'Les bytes lâchés par les malwares se dépensent au hangar. Chaque boss débloque une nouvelle arme et le monde suivant. Gagne 10 étoiles dans un monde pour révéler son honeypot secret. Élimine vite pour faire monter le combo (jusqu\'à x8).',

    // ── Help: objectives ──
    'Objectives': 'Objectifs',
    'Waves': 'Vagues', '— clear every wave.': '— élimine toutes les vagues.',
    'Survive': 'Survie', '— hold out until the timer runs out.': '— tiens bon jusqu\'à la fin du chrono.',
    'Cut the C2': 'Couper le C2', '— destroy every beacon; they keep calling reinforcements.': '— détruis toutes les balises ; elles appellent des renforts.',
    'Protect': 'Protéger', '— keep the network sensor alive until the scan completes. Malware goes for it too.':
        '— garde le capteur réseau en vie jusqu\'à la fin du scan. Les malwares l\'attaquent aussi.',
    'Boss': 'Boss', '— three phases each. Watch the dashed lines and red sectors: they are attacks about to land.':
        '— trois phases chacun. Surveille les lignes pointillées et les zones rouges : ce sont des attaques qui arrivent.',
    'Honeypot': 'Honeypot', '(secret) — 45 seconds, triple bytes.': '(secret) — 45 secondes, bytes x3.',
    'Stars': 'Étoiles',
    '★ Complete the level.': '★ Termine le niveau.',
    '★ Take 2 hits or fewer (3 against a boss).': '★ Prends 2 coups maximum (3 contre un boss).',
    '★ Beat the par time — or take no hit (survive), keep the sensor above 70% (protect), collect enough bytes (honeypot).':
        '★ Bats le temps de référence — ou ne prends aucun coup (survie), garde le capteur au-dessus de 70 % (protéger), ramasse assez de bytes (honeypot).',
    'Pickups': 'Bonus',
    '+1 integrity ·': '+1 cœur ·', 'rapid fire ·': 'tir rapide ·', 'shield (absorbs a hit) ·': 'bouclier (encaisse un coup) ·',
    'overclock (double damage) ·': 'overclock (dégâts doublés) ·', '+1 bomb': '+1 bombe',
    'Beware: a heart that wobbles a little too much might be a trojan.': 'Attention : un cœur qui tremble un peu trop pourrait être un trojan.',

    // ── Settings ──
    'Sound': 'Son', 'Music': 'Musique', 'Screen shake': 'Tremblement de l\'écran',
    'Classic — arrows only (turn & thrust)': 'Classique — flèches seules (tourner et avancer)',
    'Twin-stick — WASD move, mouse aims': 'Twin-stick — clavier pour bouger, souris pour viser',
    'Auto-aim when the mouse isn\'t used': 'Visée auto quand la souris n\'est pas utilisée',
    'Audio engine:': 'Moteur audio :', '(muted)': '(coupé)', 'Test sound': 'Tester le son',
    'Difficulty': 'Difficulté', 'Language': 'Langue',
    'Keys': 'Touches', 'Default keys': 'Touches par défaut',
    'Click a key, then press the new one. {esc} cancels, {back} clears it.': 'Clique sur une touche, puis appuie sur la nouvelle. {esc} annule, {back} l\'efface.',
    '{key} is kept for the weapons': '{key} est réservée aux armes',
    'You should hear two beeps. Nothing? Check the tab / system volume.': 'Tu devrais entendre deux bips. Rien ? Vérifie le volume de l\'onglet ou de l\'ordinateur.',
    'This browser has no Web Audio.': 'Ce navigateur n\'a pas Web Audio.',
    'The browser keeps audio {state} — click the page once more.': 'Le navigateur garde l\'audio en « {state} » — clique encore une fois sur la page.',
    'Erase every star, byte, upgrade and score? This cannot be undone.': 'Effacer toutes les étoiles, bytes, améliorations et scores ? Impossible d\'annuler.',
    'Thrust / move up': 'Avancer / haut', 'Brake / move down': 'Freiner / bas', 'Turn / move left': 'Tourner / gauche',
    'Turn / move right': 'Tourner / droite', 'Fire': 'Tirer', 'Dash': 'Dash', 'Quarantine bomb': 'Bombe de quarantaine',
    'Ship power': 'Pouvoir du vaisseau', 'Next weapon': 'Arme suivante',

    // ── In game (canvas) ──
    'QUARANTINE': 'QUARANTAINE', 'HEARTS RESTORED': 'CŒURS RESTAURÉS', 'WAVE {n}': 'VAGUE {n}', 'WAVE {n} / {m}': 'VAGUE {n} / {m}',
    'WAVE {n} — {name}': 'VAGUE {n} — {name}', 'Wave {n} / {m}': 'Vague {n} / {m}', 'Wave {n}': 'Vague {n}',
    'Incoming swarm!': 'Un essaim arrive !',
    'Scan {n}% — sensor {hp}/{max}': 'Scan {n} % — capteur {hp}/{max}',
    'Survive — {n}s': 'Survie — {n} s', 'Honeypot — {n}s — {b} bytes': 'Honeypot — {n} s — {b} bytes',
    'C2 beacons — {n} / {m} down': 'Balises C2 — {n} / {m} détruites',
    '{name} NEUTRALIZED': '{name} NEUTRALISÉ',
    'ENCRYPTED!': 'CHIFFRÉ !', 'HOOKED!': 'HAMEÇONNÉ !', '-{n} byte': '-{n} byte',
    'WARNING': 'ATTENTION', 'PHASE 2': 'PHASE 2', 'FINAL PHASE': 'PHASE FINALE', 'CORE EXPOSED': 'NOYAU EXPOSÉ',
    'Nodes respawned — the botnet heals itself.': 'Les nœuds sont revenus — le botnet se soigne.',
    'Encrypting sector…': 'Chiffrement de la zone…',
    'Such a nice link. Click it. CLICK IT.': 'Quel joli lien. Clique dessus. CLIQUE !',
    'Every inbox. Every user. Mine.': 'Toutes les boîtes mail. Tous les utilisateurs. À moi.',
    'Reroute. Reinfect. Rebuild.': 'Rediriger. Réinfecter. Reconstruire.',
    'You cannot patch ten thousand hosts.': 'Tu ne peux pas patcher dix mille machines.',
    'Your files are encrypted. Pay to continue.': 'Tes fichiers sont chiffrés. Paie pour continuer.',
    'The price just doubled.': 'Le prix vient de doubler.',
    'We have been here since before your first log line.': 'On est là depuis avant ta première ligne de log.',
    'Which one of us is real?': 'Lequel d\'entre nous est le vrai ?',
    'Patch Tuesday is six days away.': 'Le Patch Tuesday, c\'est dans six jours.',
    'You wrote a rule for me. Let us see if it holds.': 'Tu as écrit une règle pour moi. Voyons si elle tient.',

    // ── Data: weapons, upgrades, pickups ──
    'Fast single shots.': 'Tirs simples et rapides.',
    'Five-way fan, short range.': 'Éventail de cinq tirs, courte portée.',
    'Slow, heavy, pierces everything.': 'Lent, puissant, traverse tout.',
    'Twin homing missiles.': 'Deux missiles à tête chercheuse.',
    'Signature depth': 'Profondeur de signature', '+15% damage per level.': '+15 % de dégâts par niveau.',
    'Parser speed': 'Vitesse du parseur', 'Fire 8% faster per level.': 'Tire 8 % plus vite par niveau.',
    'Integrity': 'Intégrité', '+1 max shield cell per level.': '+1 cœur maximum par niveau.',
    'Thrusters': 'Réacteurs', '+6% speed per level.': '+6 % de vitesse par niveau.',
    'Hot patch': 'Patch à chaud', 'Dash recharges 12% faster per level.': 'Le dash se recharge 12 % plus vite par niveau.',
    'Quarantine bombs': 'Bombes de quarantaine', '+1 bomb capacity per level.': '+1 bombe maximum par niveau.',
    'Collector': 'Collecteur', 'Pick bytes up from further away.': 'Ramasse les bytes de plus loin.',
    '+1 INTEGRITY': '+1 CŒUR', 'RAPID FIRE': 'TIR RAPIDE', '+1 BOMB': '+1 BOMBE', 'OVERCLOCK x2': 'OVERCLOCK x2',

    // ── Data: ships ──
    'Signature Sweep': 'Balayage de signature', 'A ring of 24 piercing shots in every direction.': 'Une couronne de 24 tirs perçants dans toutes les directions.',
    'IPS Drop': 'Blocage IPS', 'For 5 s, a field around the ship drops every enemy bullet and burns what touches it.':
        'Pendant 5 s, un champ autour du vaisseau détruit les balles ennemies et brûle ce qui le touche.',
    'Correlation': 'Corrélation', 'For 6 s, malware and their bullets move at half speed.': 'Pendant 6 s, les malwares et leurs balles vont deux fois moins vite.',
    'Deep Inspection': 'Inspection profonde', 'Launches a swarm of 10 homing probes.': 'Lance un essaim de 10 sondes à tête chercheuse.',

    // ── Data: enemies ──
    'Worm': 'Ver', 'Wormlet': 'Petit ver', 'Spammer': 'Spammeur', 'Trojan': 'Trojan', 'Phisher': 'Phisher', 'Bot': 'Bot',
    'C2 node': 'Nœud C2', 'Cryptominer': 'Cryptomineur', 'Locker': 'Locker', 'Logic bomb': 'Bombe logique', 'Keylogger': 'Keylogger',
    'Rootkit': 'Rootkit', 'APT operator': 'Opérateur APT', 'Wiper': 'Wiper', 'C2 beacon': 'Balise C2', 'Decoy': 'Leurre',

    // ── Data: bosses ──
    'PHISH KING': 'ROI DU PHISHING', 'BOTNET HIVE': 'RUCHE BOTNET', 'THE LOCKER': 'LE LOCKER', 'APT GHOST': 'FANTÔME APT', 'ZERO-DAY': 'ZERO-DAY',
    'A lure so convincing the whole shallows took the bait. It hides its hooks behind gifts.':
        'Un appât si convaincant que tout le récif a mordu. Il cache ses hameçons derrière des cadeaux.',
    'Ten thousand infected hosts, one brain. Take the C2 nodes down to reach the core.':
        'Dix mille machines infectées, un seul cerveau. Détruis les nœuds C2 pour atteindre le noyau.',
    'It encrypts everything it touches. Watch the arena: what turns red is lost.':
        'Il chiffre tout ce qu\'il touche. Surveille l\'arène : ce qui devient rouge est perdu.',
    'Patient, invisible, everywhere. Only one of them is real.': 'Patient, invisible, partout. Un seul d\'entre eux est le vrai.',
    'No signature. No patch. No name — until you write the rule that catches it.':
        'Pas de signature. Pas de patch. Pas de nom — jusqu\'à ce que tu écrives la règle qui l\'attrape.',

    // ── Data: worlds ──
    'Phishing Shallows': 'Récif du Phishing', 'Botnet Nebula': 'Nébuleuse Botnet', 'Ransomware Rift': 'Faille Ransomware',
    'APT Deep': 'Abysses APT', 'Zero-Day Core': 'Noyau Zero-Day',
    'World 1': 'Monde 1', 'World 2': 'Monde 2', 'World 3': 'Monde 3', 'World 4': 'Monde 4', 'World 5': 'Monde 5',
    'Inboxes flooded, links everywhere. Every gift could be a trojan.': 'Boîtes mail inondées, des liens partout. Chaque cadeau peut être un trojan.',
    'A cloud of zombie hosts beams orders from command-and-control nodes.': 'Un nuage de machines zombies reçoit ses ordres de nœuds de commande.',
    'Files locked, backups wiped, a countdown on every screen.': 'Fichiers verrouillés, sauvegardes effacées, un compte à rebours sur chaque écran.',
    'Quiet. Too quiet. Someone has been inside for months.': 'Calme. Trop calme. Quelqu\'un est caché ici depuis des mois.',
    'The source. Every exploit chain in the graph leads here.': 'La source. Toutes les attaques du réseau mènent ici.',

    // ── Data: levels, difficulties ──
    'Boss fight.': 'Combat de boss.',
    'Bonus level — bait the malware, collect every byte you can in 45 seconds.': 'Niveau bonus — attire les malwares et ramasse un max de bytes en 45 secondes.',
    'Initial access': 'Accès initial', 'Clear every wave of malware.': 'Élimine toutes les vagues de malwares.',
    'Hold the line': 'Tenir la ligne', 'Survive {n} seconds of continuous infection.': 'Survis {n} secondes à une infection continue.',
    'Guard the sensor': 'Garder le capteur', 'Keep the network sensor alive until the scan completes.': 'Garde le capteur réseau en vie jusqu\'à la fin du scan.',
    'Destroy the command-and-control beacons — they keep calling reinforcements.': 'Détruis les balises de commande — elles appellent des renforts.',
    'Analyst': 'Analyste', 'Relaxed — tougher you, softer malware.': 'Tranquille — tu es plus solide, les malwares plus faibles.',
    'The intended experience.': 'L\'expérience prévue.',
    'Red team': 'Red team', 'Everything hits harder. Bytes x1.5.': 'Tout fait plus mal. Bytes x1,5.',
};
