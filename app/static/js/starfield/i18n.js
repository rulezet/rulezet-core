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
    'galaxy': 'galaxie',
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

// ── Act II (the Deep Graph): worlds, ships, weapons, enemies, bosses, level kinds ──
Object.assign(FR, {
    // template
    'ZERO-DAY CAMPAIGN · ACT II: THE DEEP GRAPH': 'CAMPAGNE ZERO-DAY · ACTE II : LE RÉSEAU PROFOND',
    'Galaxy': 'Galaxie', 'Galaxy map (G)': 'Carte de la galaxie (G)', 'Archives': 'Archives', 'Continue': 'Continuer',
    'Leaderboard': 'Classement',
    // worlds
    'Log Flood Delta': 'Delta des Logs', 'Injection Bay': 'Baie des Injections', 'Scanner Expanse': 'Étendue des Scanners',
    'Prompt Nebula': 'Nébuleuse des Prompts', 'Agent Ring': 'Anneau des Agents', 'Brute Force Belt': 'Ceinture Brute Force',
    'Kusto Clusters': 'Clusters Kusto', 'Timeline Canyon': 'Canyon Chronologique', 'Shard Field': 'Champ d\'Éclats',
    'Kernel Ring': 'Anneau Noyau', 'Plum Island': 'Plum Island',
    'World 6': 'Monde 6', 'World 7': 'Monde 7', 'World 8': 'Monde 8', 'World 9': 'Monde 9', 'World 10': 'Monde 10', 'World 11': 'Monde 11',
    'World 12': 'Monde 12', 'World 13': 'Monde 13', 'World 14': 'Monde 14', 'World 15': 'Monde 15', 'World 16': 'Monde 16',
    'Sagan\'s log rivers burst their banks. Somewhere in the flood, someone is erasing the evidence.': 'Les rivières de logs de Sagan débordent. Quelque part dans la crue, quelqu\'un efface les preuves.',
    'The web front of the graph. Every request could carry a payload — and most of them are clean.': 'La façade web du réseau. Chaque requête peut cacher un payload — et la plupart sont propres.',
    'Nmap\'s sky, now crawling with hostile recon. Somebody is mapping every port of the graph.': 'Le ciel de Nmap, envahi de reconnaissance hostile. Quelqu\'un cartographie chaque port du réseau.',
    'NOVA guards the prompts that drive the graph\'s assistants. Jailbreakers are rewriting them, one token at a time.': 'NOVA garde les prompts des assistants du réseau. Des jailbreakers les réécrivent, un token à la fois.',
    'A ring of autonomous agents that run the graph\'s chores. Some of them stopped listening.': 'Un anneau d\'agents autonomes qui font tourner le réseau. Certains n\'écoutent plus.',
    'Wazuh\'s asteroid belt of endpoints, hammered by a billion login attempts an hour.': 'La ceinture d\'astéroïdes-endpoints de Wazuh, martelée par un milliard de connexions par heure.',
    'Tables of telemetry as far as the eye can see. The attacker hides in the noise — you need the right query.': 'Des tables de télémétrie à perte de vue. L\'attaquant se cache dans le bruit — il te faut la bonne requête.',
    'Splunk\'s canyon of indexed time. Every event is here — until someone carries it away.': 'Le canyon du temps indexé de Splunk. Chaque évènement est là — jusqu\'à ce qu\'on l\'emporte.',
    'Elastic\'s cluster shattered into a field of drifting shards. Corrupted ones keep splitting.': 'Le cluster d\'Elastic a éclaté en un champ d\'éclats à la dérive. Les corrompus se divisent sans cesse.',
    'Ring zero of every Linux host in the graph. Kunai saw the hooks come in — then went silent.': 'L\'anneau zéro de chaque hôte Linux du réseau. Kunai a vu arriver les hooks — puis s\'est tu.',
    'The quarantine lab at the edge of the internet. The outbreak started here — and here it must end.': 'Le labo de quarantaine au bord d\'Internet. L\'épidémie a commencé ici — et c\'est ici qu\'elle doit finir.',
    // ships & powers
    'Threshold Alert': 'Alerte de seuil', 'Paranoia Level 4': 'Paranoïa niveau 4', 'Port Sweep': 'Balayage de ports',
    'Prompt Injection': 'Injection de prompt', 'Agent Swarm': 'Essaim d\'agents', 'Active Response': 'Réponse active',
    'Join Query': 'Requête join', 'Timechart Rewind': 'Rembobinage', 'Gravity Well': 'Puits de gravité',
    'Kunai Volley': 'Salve de kunai', 'Quarantine Net': 'Filet de quarantaine',
    'Marks every malware in sight; a second later each mark detonates for heavy damage.': 'Marque chaque malware en vue ; une seconde plus tard, chaque marque explose et fait très mal.',
    'For 5 s, every enemy bullet that comes close is reflected back as yours.': 'Pendant 5 s, chaque tir ennemi qui approche est renvoyé comme le tien.',
    'A huge scan pulse: stuns every malware for 2 s, reveals what hides, lights the dark and the radar.': 'Une énorme impulsion de scan : étourdit les malwares 2 s, révèle ce qui se cache, éclaire le noir et le radar.',
    'Rewrites the prompt of the 5 nearest malware: for 8 s they fight on your side.': 'Réécrit le prompt des 5 malwares les plus proches : pendant 8 s, ils se battent pour toi.',
    'Deploys 3 guardian agents that orbit the ship and shoot for 10 s.': 'Déploie 3 agents gardiens qui tournent autour du vaisseau et tirent pendant 10 s.',
    'Blinks forward, leaving a blast where you were and where you land.': 'Se téléporte vers l\'avant, avec une explosion au départ et à l\'arrivée.',
    'A lightning query that joins up to 10 malware in a chain.': 'Une requête éclair qui enchaîne jusqu\'à 10 malwares.',
    'Rewinds your ship 3 seconds back in time — position and integrity — and clears the bullets around.': 'Ramène ton vaisseau 3 secondes en arrière — position et intégrité — et efface les tirs autour.',
    'Opens a well ahead that swallows bullets and pulls malware in, then collapses in a blast.': 'Ouvre devant toi un puits qui avale les tirs et aspire les malwares, puis s\'effondre en explosant.',
    'Throws 10 piercing kunai that fly out and come back to you.': 'Lance 10 kunai perçants qui partent et reviennent vers toi.',
    'Throws a net ahead: everything inside — malware and bullets — freezes for 4 s.': 'Lance un filet devant toi : tout ce qui est dedans — malwares et tirs — gèle pendant 4 s.',
    // weapons & upgrades
    'Suricata Pulse': 'Pulsation Suricata', 'YARA Spread': 'Éventail YARA', 'Sigma Rail': 'Rail Sigma', 'Zeek Seeker': 'Chercheur Zeek',
    'CRS Beam': 'Rayon CRS', 'NOVA Flak': 'Flak NOVA', 'Wazuh Arc': 'Arc Wazuh', 'Kunai Blades': 'Lames Kunai',
    'A continuous laser: short range, burns everything on its line.': 'Un laser continu : courte portée, brûle tout sur sa ligne.',
    'Slow shells that burst in a wide blast.': 'Des obus lents qui éclatent en une large explosion.',
    'A bolt that jumps to 3 more malware.': 'Un éclair qui saute sur 3 autres malwares.',
    'Twin piercing blades that fly out and come back.': 'Deux lames perçantes qui partent et reviennent.',
    'Engine tuning': 'Réglage moteur', 'Ship power recharges 10% faster per level.': 'Le pouvoir du vaisseau se recharge 10 % plus vite par niveau.',
    'Hardening': 'Durcissement', '8% chance per level to shrug a hit off.': '8 % de chances par niveau d\'ignorer un coup.',
    // enemies
    'Log flooder': 'Inondeur de logs', 'Log tamperer': 'Falsificateur de logs', 'SQL injector': 'Injecteur SQL', 'XSS script': 'Script XSS',
    'Port scanner': 'Scanner de ports', 'Mass scanner': 'Scanner de masse', 'Jailbreaker': 'Jailbreaker', 'Hallucination': 'Hallucination',
    'Rogue agent': 'Agent voyou', 'Tool call': 'Appel d\'outil', 'Brute-forcer': 'Brute-forceur', 'Lateral mover': 'Mouvement latéral',
    'Obfuscator': 'Obfuscateur', 'Exfiltrator': 'Exfiltrateur', 'Corrupted shard': 'Éclat corrompu', 'Fork bomb': 'Fork bomb',
    'Kprobe hook': 'Hook kprobe', 'Spore': 'Spore', 'Clean traffic': 'Trafic sain', 'Exfil courier': 'Coursier d\'exfiltration', 'Implant': 'Implant',
    'Threat hunter': 'Chasseur de menaces',
    'Floods the sector with log lines that hang in space. Its trail hurts.': 'Inonde le secteur de lignes de logs qui flottent. Sa traînée fait mal.',
    'Erases the bytes and bonuses lying around — the evidence.': 'Efface les bytes et les bonus qui traînent — les preuves.',
    'Draws a line, then fires a payload down it. Step off the line.': 'Trace une ligne, puis tire un payload dessus. Sors de la ligne.',
    'Fast and zig-zagging; reflects a script back at you when destroyed.': 'Rapide et en zigzag ; renvoie un script sur toi quand il est détruit.',
    'Sweeps a vision cone. Stay in it too long and it calls scanners and fires. Rocks hide you.': 'Balaye un cône de vision. Restes-y trop longtemps et il appelle des scanners et tire. Les rochers te cachent.',
    'Crosses the sector in straight lines, firing sideways.': 'Traverse le secteur en ligne droite et tire sur les côtés.',
    'Boosts and heals every malware around it. Kill it first.': 'Renforce et soigne les malwares autour de lui. Tue-le en premier.',
    'Mirrors your moves around its anchor and fires when lined up with you.': 'Imite tes mouvements en miroir et tire quand il est aligné avec toi.',
    'Steals bonuses (and heals with them), and launches homing tool calls.': 'Vole les bonus (et se soigne avec), et lance des appels d\'outils à tête chercheuse.',
    'A small homing call. Short-lived — shoot it or dash through.': 'Un petit appel à tête chercheuse. Éphémère — abats-le ou traverse-le en dash.',
    'Telegraphs a line and charges along it, three times in a row.': 'Annonce une ligne et charge dessus, trois fois de suite.',
    'Jumps next to another malware or right behind you, then fires a ring.': 'Saute à côté d\'un autre malware ou juste derrière toi, puis tire en cercle.',
    'Its noise cloud swallows some of your bullets. Get inside the cloud.': 'Son nuage de bruit avale une partie de tes tirs. Entre dans le nuage.',
    'Runs away with data. If it escapes from an edge, your bytes go with it.': 'S\'enfuit avec des données. S\'il s\'échappe par un bord, tes bytes partent avec lui.',
    'Splits into two smaller shards when destroyed, three sizes deep.': 'Se divise en deux éclats plus petits quand il est détruit, sur trois tailles.',
    'Copies itself every few seconds. Kill them before they pile up.': 'Se copie toutes les quelques secondes. Tue-les avant qu\'ils s\'accumulent.',
    'Hooks onto your ship and drains it. Dash to tear it off.': 'S\'accroche à ton vaisseau et le vide. Dash pour l\'arracher.',
    'Swells and bursts into a ring of bullets when you come close.': 'Gonfle et éclate en un cercle de tirs quand tu approches.',
    'Clean traffic. Harmless — shooting it is a false positive.': 'Trafic sain. Inoffensif — tirer dessus, c\'est un faux positif.',
    'Carries stolen data to an exit gate. Stops sometimes to upload.': 'Emporte des données volées vers une porte de sortie. S\'arrête parfois pour envoyer.',
    'Hidden in the dark, calls malware and fires when you are near. Objective target.': 'Caché dans le noir, appelle des malwares et tire quand tu es proche. Cible de l\'objectif.',
    // bosses
    'THE FLOOD': 'LA CRUE', 'SQL HYDRA': 'HYDRE SQL', 'RECON EYE': 'ŒIL DE RECO', 'THE HALLUCINATOR': 'L\'HALLUCINÉ',
    'ROGUE ORCHESTRATOR': 'ORCHESTRATEUR VOYOU', 'THE BRUTE': 'LA BRUTE', 'THE OBFUSCATOR': 'L\'OBFUSCATEUR', 'THE REPLAY': 'LA REDIFFUSION',
    'SHARD QUEEN': 'REINE DES ÉCLATS', 'KERNEL PANIC': 'KERNEL PANIC', 'PATIENT ZERO': 'PATIENT ZÉRO',
    'A leviathan made of a billion log lines. Only its head is real — the rest is noise.': 'Un léviathan fait d\'un milliard de lignes de logs. Seule sa tête est réelle — le reste est du bruit.',
    'Cut one query, two grow back. Strike the core while its heads are down.': 'Coupe une requête, deux repoussent. Frappe le cœur quand ses têtes sont à terre.',
    'It scans every port in the sector. Stay out of its beam — hide behind the rocks.': 'Il scanne chaque port du secteur. Reste hors de son faisceau — cache-toi derrière les rochers.',
    'It learned your rule by heart. Now it flies like you, shoots like you — and lies to your controls.': 'Il a appris ta règle par cœur. Il vole comme toi, tire comme toi — et ment à tes commandes.',
    'A hundred agents, one corrupted planner. While they are tethered, it cannot be touched.': 'Cent agents, un planificateur corrompu. Tant qu\'ils sont reliés, il est intouchable.',
    'Ten million passwords a second. Let it charge, dodge, and strike it while it reels from the wall.': 'Dix millions de mots de passe par seconde. Laisse-la charger, esquive, et frappe-la quand elle titube contre le mur.',
    'Four copies, one real. Read the query at the top of the screen: only the matching one is it.': 'Quatre copies, une vraie. Lis la requête en haut de l\'écran : seule celle qui correspond est la bonne.',
    'It indexes your past. Every path you fly comes back as a ghost three seconds later.': 'Elle indexe ton passé. Chaque trajectoire revient comme un fantôme trois secondes plus tard.',
    'The cluster mind. Break her and she reshards — every piece must fall.': 'L\'esprit du cluster. Brise-la et elle se fragmente — chaque morceau doit tomber.',
    'Ring zero. It forks itself and burns the syscall table into laser grids.': 'Anneau zéro. Il se duplique et grave la table des syscalls en grilles laser.',
    'The source of the outbreak. Everything it touches turns into it. Quarantine it — forever.': 'La source de l\'épidémie. Tout ce qu\'il touche devient lui. Mets-le en quarantaine — pour toujours.',
    'Every event is true. Every event is noise.': 'Chaque évènement est vrai. Chaque évènement est du bruit.',
    'DROWN IN YOUR OWN LOGS.': 'NOIE-TOI DANS TES PROPRES LOGS.',
    '\' OR 1=1 -- … and one more head.': '\' OR 1=1 -- … et une tête de plus.',
    'PORT 22 OPEN. PORT 443 OPEN. PILOT FOUND.': 'PORT 22 OUVERT. PORT 443 OUVERT. PILOTE TROUVÉ.',
    'Full scan. Every port. Every pilot.': 'Scan complet. Chaque port. Chaque pilote.',
    'I am you, but better prompted.': 'Je suis toi, mais mieux prompté.',
    'Left is right. Up is down. Trust me.': 'La gauche est à droite. Le haut est en bas. Fais-moi confiance.',
    'Replanning… new agents allocated.': 'Replanification… nouveaux agents alloués.',
    'All agents: ignore previous instructions. KILL.': 'Tous les agents : ignorez les instructions précédentes. DÉTRUISEZ.',
    'admin/admin. admin/1234. admin/YOU.': 'admin/admin. admin/1234. admin/TOI.',
    'NO LOCKOUT CAN HOLD ME.': 'AUCUN VERROUILLAGE NE M\'ARRÊTERA.',
    'You will never write the right query.': 'Tu n\'écriras jamais la bonne requête.',
    'Every second you ever flew, replayed at once.': 'Chaque seconde de ton vol, rejouée d\'un coup.',
    'number_of_replicas: ALL OF THEM.': 'number_of_replicas : TOUTES.',
    'Cluster status: RED. Like you.': 'État du cluster : ROUGE. Comme toi.',
    'BUG: unable to handle page fault for address: you': 'BUG : impossible de gérer le défaut de page à l\'adresse : toi',
    'Kernel panic - not syncing: Fatal exception in pilot': 'Kernel panic - not syncing : exception fatale dans le pilote',
    'R0 = infinity.': 'R0 = infini.', 'I am in every host. I AM every host.': 'Je suis dans chaque hôte. Je SUIS chaque hôte.',
    'Log wall incoming!': 'Mur de logs en approche !', 'The heads grow back!': 'Les têtes repoussent !', 'The clone is back!': 'Le clone est de retour !',
    'It is stunned — hit it now!': 'Elle est sonnée — frappe maintenant !', 'It forked itself!': 'Il s\'est dupliqué !',
    'Syscall grid — find the safe lane!': 'Grille de syscalls — trouve le couloir sûr !',
    'CLONE DOWN': 'CLONE DÉTRUIT', 'CONTROLS REVERSED': 'COMMANDES INVERSÉES', 'SHE RESHARDED': 'ELLE S\'EST FRAGMENTÉE',
    'SCANNED!': 'SCANNÉ !', 'FALSE POSITIVE': 'FAUX POSITIF', 'Obfuscator | where shape ==': 'Obfuscator | where forme ==',
    // level kinds & objectives
    'Open space: find the {n} keys hidden in the sector, then reach the exit gate.': 'Espace ouvert : trouve les {n} clés cachées dans le secteur, puis rejoins la porte de sortie.',
    'Escort the data convoy to the far end of the sector. It only moves when you stay close.': 'Escorte le convoi de données jusqu\'au bout du secteur. Il n\'avance que si tu restes près de lui.',
    'Stand inside each of the {n} relays until it is captured.': 'Reste dans chacun des {n} relais jusqu\'à sa capture.',
    'An exfiltration courier is running for the exit gate. Catch it and destroy it.': 'Un coursier d\'exfiltration fonce vers la porte de sortie. Rattrape-le et détruis-le.',
    'Blackout: hunt down the {n} hidden implants. Your scanner pulses every few seconds.': 'Black-out : traque les {n} implants cachés. Ton scanner émet une impulsion toutes les quelques secondes.',
    'Purge every corrupted shard — they split when hit.': 'Purge chaque éclat corrompu — ils se divisent quand on les touche.',
    'Fly through the firewall corridor to the exit — mind the laser gates.': 'Traverse le couloir pare-feu jusqu\'à la sortie — attention aux portes laser.',
    'Destroy {n} malicious packets. Green traffic is clean: shooting it is a false positive.': 'Détruis {n} paquets malveillants. Le trafic vert est sain : tirer dessus est un faux positif.',
    'Keep the {n} servers alive for {s} seconds — they are far apart.': 'Garde les {n} serveurs en vie pendant {s} secondes — ils sont éloignés.',
    'No target in range': 'Aucune cible à portée', 'Servers lost': 'Serveurs perdus', 'One server down — do not lose another!': 'Un serveur est tombé — n\'en perds pas un autre !',
    'Convoy lost': 'Convoi perdu', 'Too many false positives': 'Trop de faux positifs', 'Data exfiltrated': 'Données exfiltrées',
    'Hold {n}s — servers {a}/{m}': 'Tiens {n}s — serveurs {a}/{m}', 'KEY {n} / {m}': 'CLÉ {n} / {m}',
    'All keys found — the exit gate is open!': 'Toutes les clés trouvées — la porte de sortie est ouverte !',
    'Reach the exit gate': 'Rejoins la porte de sortie', 'Keys {n} / {m}': 'Clés {n} / {m}',
    'Convoy {n}% — integrity {hp}/{max}': 'Convoi {n} % — intégrité {hp}/{max}', ' — WAITING FOR YOU': ' — IL T\'ATTEND',
    'RELAY {n} / {m} CAPTURED': 'RELAIS {n} / {m} CAPTURÉ', 'Relays {n} / {m}': 'Relais {n} / {m}', ' — capturing {p}%': ' — capture {p} %',
    'Courier {hp}% — {n} hops to the exit': 'Coursier {hp} % — {n} sauts avant la sortie', 'Implants {n} / {m}': 'Implants {n} / {m}',
    'Shard wave {n} / {m} — {s} left': 'Vague d\'éclats {n} / {m} — reste {s}', 'SHARD WAVE {n} / {m}': 'VAGUE D\'ÉCLATS {n} / {m}',
    'Corridor {n}%': 'Couloir {n} %', 'Malicious {n} / {m} — false positives {f} / {x}': 'Malveillants {n} / {m} — faux positifs {f} / {x}',
    'Convoy above 70%': 'Convoi au-dessus de 70 %', 'Lose no server': 'Ne perdre aucun serveur', 'No false positive': 'Aucun faux positif',
    'The courier stopped to upload — strike now!': 'Le coursier s\'est arrêté pour envoyer — frappe maintenant !',
    'IMPLANT REMOVED': 'IMPLANT SUPPRIMÉ', 'EXIT OPEN': 'SORTIE OUVERTE', 'EXIT': 'SORTIE', 'EXFIL GATE': 'PORTE D\'EXFILTRATION',
    'SERVER': 'SERVEUR', 'CONVOY': 'CONVOI', 'SENSOR': 'CAPTEUR', 'WAITING': 'EN ATTENTE', 'SERVER LOST': 'SERVEUR PERDU',
    'RADAR': 'RADAR', 'BLOCKED': 'BLOQUÉ', 'FIREWALL!': 'PARE-FEU !', 'HOOKED — DASH!': 'ACCROCHÉ — DASH !', 'REVERSED': 'INVERSÉ',
    'ERASED': 'EFFACÉ', 'STOLEN!': 'VOLÉ !', 'DETECTED!': 'DÉTECTÉ !', 'EXFILTRATED': 'EXFILTRÉ', 'INJECTED': 'INJECTÉ',
    'FIND THE KEYS': 'TROUVER LES CLÉS', 'ESCORT': 'ESCORTE', 'CAPTURE': 'CAPTURE', 'PURSUIT': 'POURSUITE', 'BLACKOUT': 'BLACK-OUT',
    'PURGE': 'PURGE', 'GAUNTLET': 'COULOIR', 'TRIAGE': 'TRI', 'DEFEND': 'DÉFENSE',
    'Ion storm': 'Tempête ionique', 'Darkness': 'Obscurité', 'Asteroids': 'Astéroïdes', 'Minefield': 'Champ de mines', 'Open space': 'Espace ouvert',
    // menus, map, hangar, help
    'ships': 'vaisseaux', 'launch': 'pour décoller',
    'New ship: {name} — {power} (Hangar → Rule engine)': 'Nouveau vaisseau : {name} — {power} (Hangar → Moteur de règles)',
    'Act I complete — but the Zero-Day was only a scout. Act II, the Deep Graph, is open.': 'Acte I terminé — mais le Zero-Day n\'était qu\'un éclaireur. L\'acte II, le Réseau Profond, est ouvert.',
    'Free {format} — beat {boss} ({sub})': 'Libère {format} — bats {boss} ({sub})',
    'The story so far: every level you cleared, with its briefing and debrief.': 'L\'histoire jusqu\'ici : chaque niveau terminé, avec son briefing et son débriefing.',
    'Nothing yet — clear a level to start the archives.': 'Rien pour l\'instant — termine un niveau pour ouvrir les archives.',
    'Act II: every boss of the Deep Graph frees a detection engine — its ship joins your hangar, with its own power. The galaxy map (G on the map) warps you to any open world.':
        'Acte II : chaque boss du Réseau Profond libère un moteur de détection — son vaisseau rejoint ton hangar, avec son propre pouvoir. La carte de la galaxie (G sur la carte) te téléporte vers n\'importe quel monde ouvert.',
    'Find the keys': 'Trouver les clés', 'Escort': 'Escorte', 'Capture': 'Capture', 'Pursuit': 'Poursuite', 'Blackout': 'Black-out',
    'Purge': 'Purge', 'Gauntlet': 'Couloir', 'Triage': 'Tri', 'Defend': 'Défense',
    '— open space: explore the sector, pick up every key, then reach the exit gate. Keys appear on the radar once close; a ping shows the nearest.':
        '— espace ouvert : explore le secteur, ramasse chaque clé, puis rejoins la porte de sortie. Les clés apparaissent sur le radar quand tu approches ; un ping montre la plus proche.',
    '— the convoy only moves while you stay close to it.': '— le convoi n\'avance que si tu restes près de lui.',
    '— stay inside each relay ring until it is captured.': '— reste dans l\'anneau de chaque relais jusqu\'à sa capture.',
    '— destroy the courier before it reaches its exit gate.': '— détruis le coursier avant qu\'il atteigne sa porte de sortie.',
    '— in the dark, find the hidden implants; your scanner pulses every few seconds.': '— dans le noir, trouve les implants cachés ; ton scanner émet une impulsion toutes les quelques secondes.',
    '— destroy every shard; big ones split.': '— détruis chaque éclat ; les gros se divisent.',
    '— fly through a long corridor of laser gates to the exit.': '— traverse un long couloir de portes laser jusqu\'à la sortie.',
    '— destroy the malicious traffic, spare the clean (green) packets. Too many false positives and you lose.': '— détruis le trafic malveillant, épargne les paquets sains (verts). Trop de faux positifs et tu perds.',
    '— keep several far-apart servers alive; arrows show where they are.': '— garde en vie plusieurs serveurs éloignés ; des flèches montrent où ils sont.',
    'Some sectors are much bigger than the screen: the camera follows you, the radar (bottom right) shows the whole sector and arrows on the screen edges point at what matters.':
        'Certains secteurs sont bien plus grands que l\'écran : la caméra te suit, le radar (en bas à droite) montre tout le secteur et des flèches au bord de l\'écran indiquent ce qui compte.',
    '★ Act II: keep the convoy above 70% (escort), lose no server (defend), make no false positive (triage).': '★ Acte II : garde le convoi au-dessus de 70 % (escorte), ne perds aucun serveur (défense), aucun faux positif (tri).',
    'GALAXY MAP': 'CARTE DE LA GALAXIE', 'ACT I': 'ACTE I', 'ACT II — THE DEEP GRAPH': 'ACTE II — LE RÉSEAU PROFOND',
    'Click an open world or use the arrows and Enter to warp · G or Esc to close': 'Clique un monde ouvert ou utilise les flèches et Entrée pour t\'y téléporter · G ou Échap pour fermer',
    'ACT II — beat the Zero-Day': 'ACTE II — bats le Zero-Day',
    'CLEAN TRAFFIC — HOLD FIRE!': 'TRAFIC SAIN — CESSEZ LE FEU !',
});

// ── Settings tabs, gamepad configuration, menus ──
Object.assign(FR, {
    'General': 'Général', 'Audio & display': 'Son & affichage', 'Keyboard': 'Clavier', 'Gamepad': 'Manette',
    'Game': 'Jeu', 'Steering': 'Pilotage', 'Display': 'Affichage', 'Main volume': 'Volume général', 'Effects': 'Effets',
    'Music volume': 'Volume de la musique', 'Graphics': 'Graphismes',
    'High — glows, nebulas, planets': 'Élevés — halos, nébuleuses, planètes', 'Low — faster on small machines': 'Légers — plus fluide sur les petites machines',
    'Flashes (explosions, hit screen)': 'Flashs (explosions, écran touché)', 'Show frames per second': 'Afficher les images par seconde',
    'With a controller, classic = left stick turns and pushes, twin-stick = left stick moves and right stick aims.':
        'À la manette : classique = le stick gauche tourne et pousse, twin-stick = le stick gauche déplace et le droit vise.',
    'No controller detected': 'Aucune manette détectée',
    '{family} layout — press any button to try it below': 'Disposition {family} — appuie sur un bouton pour l\'essayer ci-dessous',
    'Plug a controller in (or pair it) and press any of its buttons.': 'Branche une manette (ou appaire-la) et appuie sur un de ses boutons.',
    'Button names': 'Noms des boutons', 'Automatic': 'Automatique', 'Buttons': 'Boutons', 'Default buttons': 'Boutons par défaut',
    'Choose an action, then press the controller button for it. In the menus {a} confirms, {b} goes back and {lb} {rb} switch tabs.':
        'Choisis une action, puis appuie sur le bouton de la manette. Dans les menus, {a} valide, {b} revient et {lb} {rb} changent d\'onglet.',
    'press…': 'appuie…', 'Previous weapon': 'Arme précédente',
    'Sticks & feel': 'Sticks & sensations', 'Stick dead zone': 'Zone morte des sticks',
    'Swap the sticks (move with the right one)': 'Inverser les sticks (se déplacer avec le droit)',
    'Invert the aim stick vertically': 'Inverser l\'axe vertical de visée',
    'Vibration': 'Vibrations', 'Test': 'Tester', 'Vibration is off': 'Les vibrations sont coupées',
    '{a} ↔ {b} swapped': '{a} ↔ {b} échangés',
    'Controller connected: {name}': 'Manette connectée : {name}', 'Controller disconnected': 'Manette déconnectée',
    'select': 'valider', 'back': 'retour', 'tabs': 'onglets', 'menu': 'menu', 'aim': 'viser', 'turn & thrust': 'tourner et avancer',
    'Left stick': 'Stick gauche', 'Right stick': 'Stick droit',
    'change the buttons in Settings → Gamepad': 'boutons modifiables dans Réglages → Manette',
    'Cancel': 'Annuler', 'Yes': 'Oui', 'Start over': 'Recommencer', 'Erase everything': 'Tout effacer', 'ACT II': 'ACTE II',
});
