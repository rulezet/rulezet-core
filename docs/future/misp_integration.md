# Intégration profonde Rulezet ↔ MISP

Objectif : brancher Rulezet sur MISP au maximum — tout ce que Rulezet sait d'une
rule ou d'un bundle doit pouvoir partir dans MISP, et ce que MISP contient comme
règles de détection doit pouvoir revenir dans Rulezet.

Plan en 4 étapes :

1. **Mapping complet** — remettre à jour tous les convertisseurs Rulezet → MISP, couvrir tous les formats, exporter tout le contexte (scopes, tests, reviews, commentaires, fichiers…).
2. **Sync bidirectionnelle** — push amélioré (update au lieu de recréer) + **receive** : importer les rules présentes dans MISP.
3. **misp-modules Rulezet** — expansion / enrichment / import / export côté MISP.
4. **Autres intégrations** — idées pour aller plus loin.

---

## 0. État actuel (novembre 2026)

| Élément | Où | Remarque |
|---|---|---|
| Serveurs MISP (CRUD, clé chiffrée Fernet, test, historique) | `app/features/misp/misp.py`, `misp_connector_core.py`, `db_class/misp.py` | admin only |
| Push (job `misp_push`) | `job_handlers.py:5608`, `trigger_push()` | `add_event()` uniquement → **chaque push crée un nouvel event** (pas d'update, pas d'idempotence) |
| Rule → MISP | `app/features/misp/rule/misp_object.py` | event = `rulezet-metadata` + objet de contenu par format + attributs `vulnerability` + tags |
| Bundle → MISP | `app/features/misp/bundle/misp_object.py` | event = `rulezet-bundle` + pour chaque rule (metadata + contenu) + tags + vulnérabilités |
| Templates custom | `app/features/misp/object_templates/` | `rulezet-metadata`, `rulezet-bundle`, `splunk-rule`, `elastic-detection-rule`, `kql-analytics-rule`, `kunai-rule` |
| API | `GET` rule `misp_object`, bundle download `part=misp` | |
| MISP → STIX | `misp_core.convert_misp_to_stix` | |
| Taxonomies / galaxies | submodules `misp-taxonomies`, `misp-galaxy`, job `update_misp_data` | tags Rulezet = tags MISP (uuid + colour) |

### Couverture des formats (`formats.catalog.json`)

| Format | Objet MISP | Statut |
|---|---|---|
| yara | `yara` (officiel) | OK — ajouter `comment`, `version`, `context` |
| sigma | `sigma` (officiel) | OK — ajouter `context`, `reference`, `comment` |
| suricata | `suricata` (officiel) | OK — `ref` = source ; ajouter `version`, `comment` |
| wazuh | `wazuh-rule` | à vérifier contre le template officiel |
| nse | `nse` | **bug** : `misp_object.uuid = rule.uuid` → collision si la même rule est poussée dans plusieurs events / avec la metadata ; à retirer |
| crs | `owasp-crs-rule` | à vérifier |
| nova | `nova`? | vérifier qu'un template existe, sinon template custom |
| splunk / elastic / kql / kunai | templates custom (PR MISP/misp-objects#529) | suivre le merge upstream, puis passer sur les templates officiels |
| **zeek** | — | **manquant** → fallback générique invalide |
| **sagan** | — | **manquant** (proche Snort/Suricata → `suricata`-like ou template `sagan-rule`) |
| **atr** | — | **manquant** |
| **plum** | — | **manquant** |
| no format | — | fallback générique |

Le fallback actuel `MISPObject(name=fmt, ignore_warning=True)` produit un objet
dont le nom n'est pas un template connu : MISP l'accepte mal / l'affiche en vrac.
→ Remplacer par un template unique **`detection-rule`** générique (custom
Rulezet, à proposer upstream) : `rule-content`, `format`, `rule-name`,
`language`, `reference`.

---

## 1. Étape 1 — Mapping complet

### 1.1 Principes

- **Une seule source de vérité** : un registre `FORMAT → builder` (dict) au lieu
  de la chaîne `if/elif` ; le registre liste aussi le template utilisé, pour
  pouvoir afficher la couverture sur `/misp/how-it-works`.
- **Mapping configurable** : le nom d'objet / meta-category / `to_ids` par
  format va dans `app/config/misp.format_objects.json` (règle du projet : pas de
  tables dans le code). Ce qui reste en code : la logique de construction.
- **UUID stables** : objets dérivés de façon déterministe
  (`uuid5(rule.uuid, "misp:<objet>")`) → un re-push met à jour au lieu de
  dupliquer (pré-requis de l'étape 2).
- **Niveaux d'export** (option du push et du endpoint) :
  `minimal` (rule + metadata, comme aujourd'hui) · `standard` (+ scopes, ATT&CK,
  vulnérabilités, relations) · `full` (+ tests, reviews, commentaires, historique,
  fichiers). Défaut = setting `misp.export_level`.
- **Respect des droits** : on n'exporte jamais une rule supprimée (`_active()`),
  ni un bundle privé sans être owner/admin, ni des commentaires masqués /
  modérés, ni les e-mails / données perso des users (seulement username +
  lien profil).
- **Distribution / sharing group** : réglable par serveur MISP (champ sur
  `MispServer`), plus TLP → distribution (tag `tlp:*` de la rule → niveau de
  distribution MISP, table dans un setting).

### 1.2 Rule — ce qu'on veut exporter

| Donnée Rulezet | Modèle | Cible MISP |
|---|---|---|
| Contenu + titre | `Rule` | objet du format (§0) |
| Metadata (version, licence, auteur, source, dates, votes, github-path, extra-metadata, références) | `Rule` | `rulezet-metadata` (existe) — **ajouter** : `rulezet-url` (lien vers la rule), `status` (validée / invalide), `download-count`, `favorite-count`, `owner`, `parent/original` |
| CVE / GHSA | `rule.cve_id` | attributs `vulnerability` + référence `related-to` (existe) — ajouter le lien vers le **CVE kit** `/vulnerability/<id>` |
| ATT&CK | `get_techniques_for_rule` | aujourd'hui `attack-id` texte → **ajouter les galaxy clusters** `mitre-attack-pattern` sur l'event et sur l'objet (vrais clusters, pas que des tags) |
| Tags | `Tag` | tags event (existe) + **tags au niveau attribut** du contenu (pour que `to_ids` et TLP suivent la rule) |
| **Scopes** | `RuleScope` | nouveau template `rulezet-rule-scope` (produit, plateforme, log source, environnement…) ou attributs `scope` dans `rulezet-metadata` |
| **Tests** (unitaires / samples) | `RuleTest`, `RuleTestResult`, `SampleTestRun`, `RuleSampleResult` | nouveau template `rulezet-rule-test` : date, moteur + version, verdict, nb samples matchés / non matchés, **hash des samples** (`sha256` → attributs `sha256` liés `detects`) — jamais les samples eux-mêmes |
| **Reviews / évaluations** | `RuleReview`, `RuleVote` | template `rulezet-review` (score, reviewer, date, verdict) + **opinion** MISP (analyst data, voir §1.4) |
| **Commentaires** | `UnifiedComment` | **analyst notes** MISP (MISP ≥ 2.5) sur l'objet de la rule ; fallback : attribut `comment` |
| Relations entre rules | `RuleRelation`, `RuleSimilarity` | références d'objets (`derived-from`, `similar-to`, `duplicate-of`) quand l'autre rule est dans le même event, sinon attribut `link` vers Rulezet |
| Historique / propositions | `RuleUpdateHistory`, `RuleEditProposal` | `full` uniquement : attribut `last-modif` + nb de versions + lien vers l'historique ; pas de diff complet |
| Validation | `InvalidRuleModel`, validateurs | attribut `validation-status` + message ; `to_ids=False` si la rule est invalide |

### 1.3 Bundle — ce qu'on veut exporter

Aujourd'hui : objet `rulezet-bundle` + rules + tags + vulnérabilités. À ajouter :

| Donnée | Modèle | Cible MISP |
|---|---|---|
| Structure (dossiers) | `BundleNode` | attribut `structure` (JSON) dans `rulezet-bundle` + pour chaque rule l'attribut `path` dans son metadata |
| **Fichiers externes / custom** (README, scripts, docs) | `BundleNode` type fichier | objet `file` (filename, size, sha256, `attachment` avec le contenu si < seuil setting `misp.max_attachment_size`), référence `included-in` vers le bundle |
| README | bundle | `report` MISP (event report markdown) — rendu direct dans MISP |
| **Notes** | `BundleNote`, `BundleNoteTag` | analyst notes (ou event reports si longues) |
| **Commentaires** | `CommentBundle`, `UnifiedComment` | analyst notes sur l'objet bundle |
| **Évaluations / votes** | `BundleVote`, `is_verified` | opinion MISP + attributs existants |
| **Releases** | `BundleRelease` | un push par release possible (`release=v1.2`) : event figé, `info = "<bundle> v1.2"`, tag `rulezet:release="v1.2"` |
| Historique | `BundleHistory` | `full` : timeline résumée en event report |
| Forks / merge requests | `BundleForkRule`, `BundleMergeRequest` | attribut `forked-from` (uuid + lien) ; référence `derived-from` entre events si le parent est déjà dans MISP |
| Couverture ATT&CK | kit_core | galaxy clusters sur l'event + event report « coverage » (formats, gaps) |
| Rules du bundle | `BundleRuleAssociation` | même export que §1.2 au niveau choisi |

### 1.4 Analyst data MISP (notes / opinions / relationships)

MISP 2.5 a les **analyst data** : `Note`, `Opinion` (score 0-100 + commentaire),
`Relationship`, attachables à n'importe quel event / objet / attribut. C'est le
mapping naturel pour :
- commentaires Rulezet → `Note` ;
- reviews / votes → `Opinion` (score = vote ratio ou note de review) ;
- relations rule ↔ rule → `Relationship`.

Fallback pour MISP < 2.5 : attributs `comment` / `text`. Détection de la version
au `test_server_connection` (stocker `misp_version` sur `MispServer`).

### 1.5 Nouveaux templates à créer (`object_templates/`)

| Template | Rôle |
|---|---|
| `detection-rule` | générique (zeek, sagan, atr, plum, fallback) |
| `zeek-script` / `sagan-rule` / `atr-rule` / `plum-rule` | si on veut un objet dédié (à proposer upstream misp-objects) |
| `rulezet-rule-scope` | scopes |
| `rulezet-rule-test` | résultats de tests |
| `rulezet-review` | si on ne peut pas utiliser les opinions |
| `rulezet-metadata` / `rulezet-bundle` | **bump `version`** + nouveaux champs |

Chaque template custom → PR sur MISP/misp-objects (comme #529) pour que les
autres instances MISP les connaissent nativement.

### 1.6 Checklist étape 1

- [ ] Registre format → builder + setting `misp.format_objects`
- [ ] Builders zeek / sagan / atr / plum + template `detection-rule`
- [ ] Retirer `uuid = rule.uuid` du builder NSE ; UUID déterministes partout
- [ ] `except Exception: return None` silencieux dans `content_convert_to_misp_object` → logger l'erreur
- [ ] Rule : scopes, tests, reviews, commentaires, relations, galaxy ATT&CK, lien Rulezet
- [ ] Bundle : fichiers, README → event report, notes, commentaires, releases, forks, structure
- [ ] Niveaux `minimal / standard / full` (push, API rule, API bundle `part=misp`)
- [ ] Mapping TLP → distribution + sharing group par serveur
- [ ] Page `/misp/how-it-works` : tableau de couverture généré depuis le registre
- [ ] Tests `tests_new/misp/` : un test par format (objet valide contre son template via pymisp), rule complète, bundle complet, pas de fuite (privé / supprimé / commentaire masqué)

---

## 2. Étape 2 — Sync bidirectionnelle

### 2.1 Push amélioré

- **Idempotence** : nouvelle table `misp_sync_link` (`server_id`, `local_type`
  rule|bundle|release, `local_uuid`, `misp_event_uuid`, `misp_object_uuid`,
  `last_pushed_at`, `last_pushed_hash`). Si un lien existe → `update_event`
  (ou `update_object`) au lieu de `add_event`.
- Hash du contenu exporté → on ne re-pousse que si ça a changé.
- **Push auto** (optionnel, par serveur) : quand une rule / un bundle suivi
  change, job `misp_push` en différé (debounce). Réglage par serveur : « suivre
  les bundles X, Y » / « toutes les rules d'un tag / format ».
- **Publish** : option par serveur (`publish` après push ou laisser en draft).
- Supprimer côté Rulezet → option : retirer / marquer `to_ids=False` côté MISP.

### 2.2 Receive — MISP → Rulezet

But : les rules qui vivent dans MISP (attributs `yara`, `sigma`, `snort`,
objets `yara`/`sigma`/`suricata`/…, et nos propres objets `rulezet-*`)
arrivent dans Rulezet.

**Mode de récupération**
- **Pull** (job `misp_pull`, planifié via task scheduler) : `search(controller='attributes', type_attribute=[yara, sigma, snort, …], timestamp=<last_pull>, tags=…, org=…)` + `search(controller='objects', object_name=[...])`. Filtres par serveur : tags, orgs, eventid, `published only`, `to_ids only`.
- **Push depuis MISP** (plus tard) : endpoint `POST /api/misp/receive` (API key) appelé par un **workflow MISP** ou un misp-module d'export (§3) → réception en temps réel.
- **ZMQ / Kafka** de MISP (option avancée) : écouter `misp_json_attribute` et filtrer les types de rules.

**Conversion MISP → Rulezet** (`misp/import_core.py`, inverse du §1)
- Objet `rulezet-metadata` présent → on **reconstruit fidèlement** (uuid d'origine, version, licence, ATT&CK, CVE, tags) ; si l'uuid existe déjà dans Rulezet → c'est un **aller-retour** : proposition de modification plutôt qu'écrasement.
- Objet / attribut natif sans metadata → format déduit du type (`yara`→yara, `sigma`→sigma, `snort`→suricata/snort, …), titre = nom de règle parsé, auteur = org MISP, source = lien vers l'event MISP, tags de l'event / attribut → tags Rulezet (via taxonomies déjà chargées), galaxies ATT&CK → techniques, attributs `vulnerability` de l'event → CVE.
- **Validation** : passe par le parser du format comme toute création ; les invalides vont dans `InvalidRuleModel` (comme l'import GitHub) avec le lien MISP.
- **Dédup** : uuid MISP de l'attribut stocké (`original_uuid` / `misp_sync_link`) + similarité existante pour les doublons de contenu.
- **Propriété** : rules créées au nom d'un user « bot » du serveur MISP (configurable), ou de l'admin qui a lancé le pull.
- **Modes soft / hard** comme les connectors : soft = skip existantes, hard = update / proposition d'édition.
- **Bundle auto** : option « un bundle par event MISP » (nom = `event.info`, README = event reports).
- Activity log `misp.pull`, historique dans la timeline du serveur, job visible dans `/jobs`.

### 2.3 UI

- Fiche serveur : onglets **Push** / **Receive** (filtres, fréquence, mode, dernier run, compteurs).
- Sur une rule / un bundle : badge « synchronisé avec MISP X (event lien) », bouton re-push, état (à jour / modifié depuis).
- Prévisualisation du pull (dry-run : N nouvelles, M mises à jour, K invalides) avant import.

### 2.4 Checklist étape 2

- [ ] Table `misp_sync_link` + migration
- [ ] Push update / idempotent + hash
- [ ] Push auto (abonnements par serveur) + publish optionnel
- [ ] Job `misp_pull` + filtres + planification
- [ ] Convertisseur MISP → Rulezet (avec aller-retour `rulezet-metadata`)
- [ ] Dry-run + UI Receive
- [ ] Endpoint `POST /api/misp/receive`
- [ ] Tests : aller-retour rule → MISP → rule identique ; dédup ; invalides

---

## 3. Étape 3 — misp-modules Rulezet

Repo à part (`rulezet/misp-modules-rulezet` ou PR directe sur
MISP/misp-modules). Chaque module appelle l'API publique Rulezet
(URL instance + API key en config du module) — fonctionne avec rulezet.org ou
une instance privée.

| Type | Module | Ce qu'il fait |
|---|---|---|
| **expansion** | `rulezet_cve` | sur un attribut `vulnerability` → rules Rulezet qui détectent ce CVE (réutilise `search_rules_by_cve`, **ne pas changer ce endpoint**) → ajoute les objets rules dans l'event |
| expansion | `rulezet_attack` | sur un galaxy / attribut ATT&CK `T…` → rules couvrant la technique (kit ATT&CK) |
| expansion | `rulezet_hash` / `rulezet_ioc` | sur un hash / domaine / IP → rules qui contiennent cet IOC (recherche plein texte du contenu) |
| expansion | `rulezet_rule_lookup` | sur un attribut `yara`/`sigma`/`snort` → la rule existe-t-elle dans Rulezet ? lien, votes, reviews, tests, version plus récente |
| expansion | `rulezet_validate` | valide une rule de l'event avec le validateur Rulezet (+ YARA-X / yaraQA) et met le résultat en commentaire |
| **hover** | `rulezet_hover` | survol d'un CVE / T-id / rule → nb de rules, formats, lien |
| **import** | `rulezet_import` | importe une rule ou un bundle Rulezet (uuid / URL) dans un event |
| **export** | `rulezet_export` | export d'un event → crée / propose les rules dans Rulezet (même chemin que le receive §2.2) |
| **action** (workflows MISP 2.5) | `rulezet_push_on_publish` | à la publication d'un event → envoie ses rules à Rulezet |

Côté Rulezet, prévoir :
- endpoints dédiés stables (`/api/misp/…`) qui renvoient directement du MISP JSON prêt à fusionner ;
- une clé API à scope limité (lecture / proposition seulement) pour les modules ;
- rate limit adapté (les expansions peuvent être appelées en masse — attention à l'allowlist en cours).

---

## 4. Autres idées d'intégration

1. **Feed MISP Rulezet** : rulezet.org publie un **feed MISP natif** (manifest.json + un event par bundle / par format / par CVE kit) → n'importe quel MISP l'ajoute en un clic dans *Feeds*. Le plus gros levier de diffusion, et sans clé API.
2. **Rulezet dans le catalogue de feeds par défaut de MISP** (`defaults/feed-metadata/default-feeds.json`) une fois le feed stable.
3. **Galaxy « Rulezet »** : un cluster par bundle vérifié (ou par ruleset connu) dans misp-galaxy → les analystes taguent un event « détecté par le bundle X ».
4. **Taxonomie `rulezet`** : `rulezet:status=validated|tested|community`, `rulezet:quality=…`, `rulezet:format=…` → poussée sur les attributs pour filtrer l'export IDS.
5. **Export IDS ciblé** : MISP exporte déjà `yara`/`snort` via `/events/nids` ; s'assurer que nos objets passent avec le bon `to_ids` pour que les rules Rulezet arrivent directement dans les sondes Suricata / scanners YARA branchés sur MISP.
6. **Sightings** : quand une rule matche (rule-tester, retour d'un connecteur / Velociraptor / sonde), envoyer un **sighting** MISP sur l'attribut de la rule ; en sens inverse, lire les sightings MISP pour afficher « vue en prod N fois » sur la rule (faux positifs = sighting type 1).
7. **Proposals MISP ↔ propositions d'édition** : une *proposal* sur un attribut rule dans MISP → `RuleEditProposal` dans Rulezet, et inversement.
8. **Event reports** : génération auto d'un rapport markdown (CVE kit / ATT&CK kit) dans l'event — « voici toutes les détections dispo pour ce CVE ».
9. **Pivotick / pivograph** : le graphe MISP (event ↔ objets ↔ rules ↔ CVE ↔ ATT&CK) déjà affichable, l'étendre aux events reçus.
10. **Tester les IOC d'un event** : bouton dans Rulezet « tester ces rules contre les samples / hashes de l'event MISP X » (rule-tester + attachments MISP malware-sample).
11. **Génération de rules depuis un event** : l'IA Generator lit un event MISP (IOC, ATT&CK, rapports) et propose des rules YARA / Sigma / Suricata → poussées en draft dans Rulezet puis renvoyées dans l'event.
12. **Couverture d'un event** : pour un event MISP, quelles techniques / CVE ont des rules dans Rulezet et lesquelles sont des **gaps** (kit_core) — sous forme de module d'expansion ou d'event report.
13. **Sync des taxonomies / galaxies custom** de l'instance MISP connectée vers Rulezet (aujourd'hui on ne charge que les dépôts publics).
14. **SSO / identité** : login Rulezet via MISP (OIDC si MISP en est la source) pour les communautés qui vivent déjà dans MISP — et l'org MISP comme organisation Rulezet.
15. **Communautés MISP** (CIRCL, sectoriels) : un connecteur par communauté avec sharing group dédié, bundles privés partagés seulement dans ce groupe.
16. **Workflows MISP 2.5** : blueprints prêts à l'emploi (« à la publication → envoyer à Rulezet », « nouvel attribut vulnerability → enrichir avec Rulezet »).

---

## Ordre proposé

1. Étape 1 (mapping) — prérequis de tout le reste, et UUID stables.
2. Feed MISP (idée 1) — peu de code une fois le mapping fait, gros impact.
3. Étape 2 push idempotent, puis receive.
4. misp-modules : `rulezet_cve` et `rulezet_rule_lookup` d'abord.
5. Sightings, analyst data, workflows.
