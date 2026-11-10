# Deep Rulezet ↔ MISP integration

Goal: connect Rulezet to MISP as much as possible — everything Rulezet knows
about a rule or a bundle can go to MISP, and the detection rules living in MISP
can come back into Rulezet.

Plan in 4 steps:

1. **Complete mapping** — update every Rulezet → MISP converter, cover every format, export the whole context (scopes, tests, reviews, comments, files…).
2. **Two-way sync** — better push (update instead of re-create) + **receive**: import the rules found in MISP.
3. **Rulezet misp-modules** — expansion / enrichment / import / export on the MISP side.
4. **Other integrations** — ideas to go further.

---

## 0. Current state (November 2026)

| Piece | Where | Note |
|---|---|---|
| MISP servers (CRUD, Fernet-encrypted key, test, history) | `app/features/misp/misp.py`, `misp_connector_core.py`, `db_class/misp.py` | admin only |
| Push (job `misp_push`) | `job_handlers.py` `handle_misp_push`, `trigger_push()` | `add_event()` only → **every push creates a new event** (no update, not idempotent) |
| Rule → MISP | `app/features/misp/rule/misp_object.py` | event = `rulezet-metadata` + one content object per format + `vulnerability` attributes + tags |
| Bundle → MISP | `app/features/misp/bundle/misp_object.py` | event = `rulezet-bundle` + for each rule (metadata + content) + tags + vulnerabilities |
| Custom templates | `app/features/misp/object_templates/` | `rulezet-metadata`, `rulezet-bundle`, `splunk-rule`, `elastic-detection-rule`, `kql-analytics-rule`, `kunai-rule` |
| API | rule `misp_object`, bundle download `part=misp` | |
| MISP → STIX | `misp_core.convert_misp_to_stix` | |
| Taxonomies / galaxies | submodules `misp-taxonomies`, `misp-galaxy`, job `update_misp_data` | Rulezet tags = MISP tags (uuid + colour) |

### Format coverage (`formats.catalog.json`)

| Format | MISP object | Status |
|---|---|---|
| yara | `yara` (official) | OK — add `comment`, `version`, `context` |
| sigma | `sigma` (official) | OK — add `context`, `reference`, `comment` |
| suricata | `suricata` (official) | OK — `ref` = source; add `version`, `comment` |
| wazuh | `wazuh-rule` | check against the official template |
| nse | `nse` | **bug**: `misp_object.uuid = rule.uuid` → collision when the same rule is pushed in several events; remove it |
| crs | `owasp-crs-rule` | to check |
| nova | `nova`? | check that a template exists, otherwise a custom one |
| splunk / elastic / kql / kunai | custom templates (PR MISP/misp-objects#529) | follow the upstream merge, then switch to the official templates |
| **zeek** | — | **missing** → falls back to an invalid generic object |
| **sagan** | — | **missing** (close to Snort/Suricata → `suricata`-like or a `sagan-rule` template) |
| **atr** | — | **missing** |
| **plum** | — | **missing** |
| no format | — | generic fallback |

The current fallback `MISPObject(name=fmt, ignore_warning=True)` produces an
object whose name matches no known template: MISP handles it badly / shows it as
raw data. → Replace it with one generic **`detection-rule`** template (Rulezet
custom, to propose upstream): `rule-content`, `format`, `rule-name`,
`language`, `reference`.

---

## 1. Step 1 — Complete mapping

### 1.1 Principles

- **One source of truth**: a `FORMAT → builder` registry (dict) instead of the
  `if/elif` chain; the registry also lists the template used, so the coverage
  can be shown on `/misp/how-it-works`.
- **Configurable mapping**: object name / meta-category / `to_ids` per format go
  in `app/config/misp.format_objects.json` (project rule: no tables in code).
  What stays in code: the building logic.
- **Stable UUIDs**: objects derived deterministically
  (`uuid5(rule.uuid, "misp:<object>")`) → a re-push updates instead of
  duplicating (prerequisite for step 2).
- **Export levels** (option of the push and of the endpoint):
  `minimal` (rule + metadata, as today) · `standard` (+ scopes, ATT&CK,
  vulnerabilities, relations) · `full` (+ tests, reviews, comments, history,
  files). Default = setting `misp.export_level`.
- **Respect access rights**: never export a deleted rule (`_active()`), a
  private bundle unless owner/admin, hidden / moderated comments, or users'
  e-mails / personal data (only username + profile link).
- **Distribution / sharing group**: set per MISP server (field on `MispServer`),
  plus TLP → distribution (the rule's `tlp:*` tag → MISP distribution level,
  table in a setting).

### 1.2 Rule — what we want to export

| Rulezet data | Model | MISP target |
|---|---|---|
| Content + title | `Rule` | format object (§0) |
| Metadata (version, license, author, source, dates, votes, github-path, extra-metadata, references) | `Rule` | `rulezet-metadata` (exists) — **add**: `rulezet-url` (link to the rule), `status` (validated / invalid), `download-count`, `favorite-count`, `owner`, `parent/original` |
| CVE / GHSA | `rule.cve_id` | `vulnerability` attributes + `related-to` reference (exists) — add the link to the **CVE kit** `/vulnerability/<id>` |
| ATT&CK | `get_techniques_for_rule` | today `attack-id` as text → **add real galaxy clusters** `mitre-attack-pattern` on the event and on the object |
| Tags | `Tag` | event tags (exists) + **attribute-level tags** on the content (so `to_ids` and TLP follow the rule) |
| **Scopes** | `RuleScope` | new template `rulezet-rule-scope` (product, platform, log source, environment…) or `scope` attributes in `rulezet-metadata` |
| **Tests** (unit / samples) | `RuleTest`, `RuleTestResult`, `SampleTestRun`, `RuleSampleResult` | new template `rulezet-rule-test`: date, engine + version, verdict, matched / unmatched samples, **sample hashes** (`sha256` attributes linked with `detects`) — never the samples themselves |
| **Reviews / evaluations** | `RuleReview`, `RuleVote` | template `rulezet-review` (score, reviewer, date, verdict) + MISP **opinion** (analyst data, see §1.4) |
| **Comments** | `UnifiedComment` | MISP **analyst notes** (MISP ≥ 2.5) on the rule object; fallback: `comment` attribute |
| Rule relations | `RuleRelation`, `RuleSimilarity` | object references (`derived-from`, `similar-to`, `duplicate-of`) when the other rule is in the same event, otherwise a `link` attribute to Rulezet |
| History / proposals | `RuleUpdateHistory`, `RuleEditProposal` | `full` only: `last-modif` attribute + number of versions + link to the history; no full diff |
| Validation | `InvalidRuleModel`, validators | `validation-status` attribute + message; `to_ids=False` when the rule is invalid |

### 1.3 Bundle — what we want to export

Today: `rulezet-bundle` object + rules + tags + vulnerabilities. To add:

| Data | Model | MISP target |
|---|---|---|
| Structure (folders) | `BundleNode` | `structure` attribute (JSON) in `rulezet-bundle` + a `path` attribute in each rule's metadata |
| **External / custom files** (README, scripts, docs) | `BundleNode` file nodes | `file` object (filename, size, sha256, `attachment` with the content when under the `misp.max_attachment_size` setting), `included-in` reference to the bundle |
| README | bundle | MISP **event report** (markdown) — rendered directly in MISP |
| **Notes** | `BundleNote`, `BundleNoteTag` | analyst notes (or event reports when long) |
| **Comments** | `CommentBundle`, `UnifiedComment` | analyst notes on the bundle object |
| **Evaluations / votes** | `BundleVote`, `is_verified` | MISP opinion + existing attributes |
| **Releases** | `BundleRelease` | one push per release possible (`release=v1.2`): frozen event, `info = "<bundle> v1.2"`, tag `rulezet:release="v1.2"` |
| History | `BundleHistory` | `full`: summarised timeline as an event report |
| Forks / merge requests | `BundleForkRule`, `BundleMergeRequest` | `forked-from` attribute (uuid + link); `derived-from` reference between events when the parent is already in MISP |
| ATT&CK coverage | kit_core | galaxy clusters on the event + "coverage" event report (formats, gaps) |
| Bundle rules | `BundleRuleAssociation` | same export as §1.2 at the chosen level |

### 1.4 MISP analyst data (notes / opinions / relationships)

MISP 2.5 has **analyst data**: `Note`, `Opinion` (score 0-100 + comment),
`Relationship`, attachable to any event / object / attribute. It is the natural
mapping for:
- Rulezet comments → `Note`;
- reviews / votes → `Opinion` (score = vote ratio or review score);
- rule ↔ rule relations → `Relationship`.

Fallback for MISP < 2.5: `comment` / `text` attributes. Detect the version in
`test_server_connection` (store `misp_version` on `MispServer`).

### 1.5 New templates to create (`object_templates/`)

| Template | Role |
|---|---|
| `detection-rule` | generic (zeek, sagan, atr, plum, fallback) |
| `zeek-script` / `sagan-rule` / `atr-rule` / `plum-rule` | if we want a dedicated object (to propose upstream to misp-objects) |
| `rulezet-rule-scope` | scopes |
| `rulezet-rule-test` | test results |
| `rulezet-review` | if opinions can't be used |
| `rulezet-metadata` / `rulezet-bundle` | **bump `version`** + new fields |

Each custom template → PR on MISP/misp-objects (like #529) so other MISP
instances know them natively.

### 1.6 Step 1 checklist

- [ ] Format → builder registry + `misp.format_objects` setting
- [ ] zeek / sagan / atr / plum builders + `detection-rule` template
- [ ] Remove `uuid = rule.uuid` from the NSE builder; deterministic UUIDs everywhere
- [ ] Silent `except Exception: return None` in `content_convert_to_misp_object` → log the error
- [ ] Rule: scopes, tests, reviews, comments, relations, ATT&CK galaxy, Rulezet link
- [ ] Bundle: files, README → event report, notes, comments, releases, forks, structure
- [ ] `minimal / standard / full` levels (push, rule API, bundle API `part=misp`)
- [ ] TLP → distribution mapping + sharing group per server
- [ ] `/misp/how-it-works` page: coverage table generated from the registry
- [ ] Tests `tests_new/misp/`: one test per format (object valid against its template via pymisp), full rule, full bundle, no leak (private / deleted / hidden comment)

---

## 2. Step 2 — Two-way sync

### 2.1 Better push

- **Idempotence**: new table `misp_sync_link` (`server_id`, `local_type`
  rule|bundle|release, `local_uuid`, `misp_event_uuid`, `misp_object_uuid`,
  `last_pushed_at`, `last_pushed_hash`). When a link exists → `update_event`
  (or `update_object`) instead of `add_event`.
- Hash of the exported content → re-push only when it changed.
- **Auto push** (optional, per server): when a followed rule / bundle changes,
  a debounced `misp_push` job. Per-server setting: "follow bundles X, Y" /
  "every rule with a tag / format".
- **Publish**: per-server option (publish after the push, or leave as draft).
- Deleted in Rulezet → option: remove / set `to_ids=False` on the MISP side.

### 2.2 Receive — MISP → Rulezet

Goal: rules that live in MISP (`yara`, `sigma`, `snort` attributes,
`yara`/`sigma`/`suricata`/… objects, and our own `rulezet-*` objects) arrive in
Rulezet.

**How they are fetched**
- **Pull** (job `misp_pull`, scheduled through the task scheduler): `search(controller='attributes', type_attribute=[yara, sigma, snort, …], timestamp=<last_pull>, tags=…, org=…)` + `search(controller='objects', object_name=[...])`. Per-server filters: tags, orgs, event ids, published only, `to_ids` only.
- **Push from MISP** (later): endpoint `POST /api/misp/receive` (API key) called by a **MISP workflow** or an export misp-module (§3) → real-time reception.
- **MISP ZMQ / Kafka** (advanced option): listen to `misp_json_attribute` and filter the rule types.

**MISP → Rulezet conversion** (`misp/import_core.py`, the inverse of §1)
- `rulezet-metadata` object present → **faithful rebuild** (original uuid, version, license, ATT&CK, CVE, tags); if the uuid already exists in Rulezet → it is a **round trip**: an edit proposal rather than an overwrite.
- Native object / attribute without metadata → format inferred from the type (`yara`→yara, `sigma`→sigma, `snort`→suricata/snort, …), title = parsed rule name, author = MISP org, source = link to the MISP event, event / attribute tags → Rulezet tags (through the already loaded taxonomies), ATT&CK galaxies → techniques, event `vulnerability` attributes → CVEs.
- **Validation**: goes through the format parser like any creation; invalid ones go to `InvalidRuleModel` (like the GitHub import) with the MISP link.
- **Dedup**: MISP attribute uuid stored (`original_uuid` / `misp_sync_link`) + the existing similarity check for content duplicates.
- **Ownership**: rules created under a "bot" user of the MISP server (configurable), or the admin who started the pull.
- **Soft / hard modes** like connectors: soft = skip existing ones, hard = update / edit proposal.
- **Auto bundle**: option "one bundle per MISP event" (name = `event.info`, README = event reports).
- Activity log `misp.pull`, history in the server timeline, job visible in `/jobs`.

### 2.3 UI

- Server page: **Push** / **Receive** tabs (filters, frequency, mode, last run, counters).
- On a rule / bundle: "synced with MISP X (event link)" badge, re-push button, state (up to date / changed since).
- Pull preview (dry run: N new, M updated, K invalid) before importing.

### 2.4 Step 2 checklist

- [ ] `misp_sync_link` table + migration
- [ ] Idempotent push (update) + hash
- [ ] Auto push (per-server subscriptions) + optional publish
- [ ] `misp_pull` job + filters + scheduling
- [ ] MISP → Rulezet converter (with the `rulezet-metadata` round trip)
- [ ] Dry run + Receive UI
- [ ] `POST /api/misp/receive` endpoint
- [ ] Tests: round trip rule → MISP → identical rule; dedup; invalid rules

---

## 3. Step 3 — Rulezet misp-modules

Separate repo (`rulezet/misp-modules-rulezet`) or a PR straight to
MISP/misp-modules. Each module calls the public Rulezet API (instance URL + API
key in the module config) — works with rulezet.org or a private instance.

| Type | Module | What it does |
|---|---|---|
| **expansion** | `rulezet_cve` | on a `vulnerability` attribute → the Rulezet rules detecting that CVE (reuses `search_rules_by_cve`, **do not change this endpoint**) → adds the rule objects to the event |
| expansion | `rulezet_attack` | on an ATT&CK galaxy / `T…` attribute → rules covering the technique (ATT&CK kit) |
| expansion | `rulezet_hash` / `rulezet_ioc` | on a hash / domain / IP → rules containing that IOC (full-text search on the content) |
| expansion | `rulezet_rule_lookup` | on a `yara`/`sigma`/`snort` attribute → is the rule in Rulezet? link, votes, reviews, tests, newer version |
| expansion | `rulezet_validate` | validates an event's rule with the Rulezet validator (+ YARA-X / yaraQA) and puts the result in a comment |
| **hover** | `rulezet_hover` | hovering a CVE / T-id / rule → number of rules, formats, link |
| **import** | `rulezet_import` | imports a Rulezet rule or bundle (uuid / URL) into an event |
| **export** | `rulezet_export` | exports an event → creates / proposes the rules in Rulezet (same path as receive §2.2) |
| **action** (MISP 2.5 workflows) | `rulezet_push_on_publish` | when an event is published → sends its rules to Rulezet |

On the Rulezet side:
- stable dedicated endpoints (`/api/misp/…`) returning MISP JSON ready to merge;
- an API key with a limited scope (read / propose only) for the modules;
- suitable rate limits (expansions can be called in bulk — mind the allowlist in progress).

---

## 4. Other integration ideas

1. **Rulezet MISP feed**: rulezet.org publishes a **native MISP feed** (manifest.json + one event per bundle / per format / per CVE kit) → any MISP adds it in one click under *Feeds*. The biggest reach for the least code, no API key needed.
2. **Rulezet in MISP's default feed list** (`defaults/feed-metadata/default-feeds.json`) once the feed is stable.
3. **"Rulezet" galaxy**: one cluster per verified bundle (or known ruleset) in misp-galaxy → analysts tag an event "detected by bundle X".
4. **`rulezet` taxonomy**: `rulezet:status=validated|tested|community`, `rulezet:quality=…`, `rulezet:format=…` → pushed on attributes to filter the IDS export.
5. **Targeted IDS export**: MISP already exports `yara`/`snort` through `/events/nids`; make sure our objects go through with the right `to_ids` so Rulezet rules land directly in the Suricata sensors / YARA scanners fed by MISP.
6. **Sightings**: when a rule matches (rule tester, feedback from a connector / Velociraptor / sensor), send a MISP **sighting** on the rule's attribute; the other way, read MISP sightings to show "seen in production N times" on the rule (false positives = sighting type 1).
7. **MISP proposals ↔ edit proposals**: a *proposal* on a rule attribute in MISP → a `RuleEditProposal` in Rulezet, and the other way round.
8. **Event reports**: auto-generated markdown report (CVE kit / ATT&CK kit) in the event — "here are all the detections available for this CVE".
9. **Pivotick / pivograph**: the MISP graph (event ↔ objects ↔ rules ↔ CVE ↔ ATT&CK) is already displayable; extend it to received events.
10. **Test an event's IOCs**: a button in Rulezet "test these rules against the samples / hashes of MISP event X" (rule tester + MISP malware-sample attachments).
11. **Rules generated from an event**: the AI Generator reads a MISP event (IOCs, ATT&CK, reports) and proposes YARA / Sigma / Suricata rules → pushed as drafts in Rulezet, then sent back to the event.
12. **Event coverage**: for a MISP event, which techniques / CVEs have rules in Rulezet and which are **gaps** (kit_core) — as an expansion module or an event report.
13. **Sync the custom taxonomies / galaxies** of the connected MISP instance into Rulezet (today only the public repos are loaded).
14. **SSO / identity**: log into Rulezet through MISP (OIDC when MISP is the source) for communities already living in MISP — and the MISP org as the Rulezet organisation.
15. **MISP communities** (CIRCL, sector-based): one connector per community with a dedicated sharing group, private bundles shared only within that group.
16. **MISP 2.5 workflows**: ready-made blueprints ("on publish → send to Rulezet", "new vulnerability attribute → enrich with Rulezet").

---

## Suggested order

1. Step 1 (mapping) — prerequisite for everything else, and stable UUIDs.
2. MISP feed (idea 1) — little code once the mapping is done, big impact.
3. Step 2: idempotent push, then receive.
4. misp-modules: `rulezet_cve` and `rulezet_rule_lookup` first.
5. Sightings, analyst data, workflows.
