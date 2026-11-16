# AI Tag Suggestions (6th AI integration)

Proposes MISP taxonomy / galaxy tags on the **rule edit** page and the **bundle edit** page (Tags tab). Not on the rule create page (on purpose).

**Who:** admins, AI Operators (`ai.use`) and AI Managers (`ai.manage`) — not plain users — and only while the agent is enabled. A Tag manager (`rule.tag_any`) who is also an AI Operator gets it on the tags-only restricted edit of any rule (the card sits outside the disabled fieldsets). One check, `tag_suggest_core.can_use(user)`, used by the four routes and by the Jinja global `can_suggest_tags()` that shows the card. Bundle routes also require the bundle's owner or an admin (like the edit page). The admin page `/ai/admin/tag-suggest` is under the AI blueprint's own guard (admin or `ai.manage`).

## Why two steps

The `tag` table holds ~76k tags in ~365 families (taxonomies + galaxies). Most families have nothing to do with a detection rule (firearms 6k, culture collections 6.6k, satellites 2k, drugs…), and the whole set fits no model context. So:

1. **Trie (no AI, ~1–2 ms).** `app/features/ai/tag_suggest_core.py` builds an in-memory token trie from the tags of the families listed in the setting `ai.tag_suggest` (≈70 detection-relevant ones: tool, threat-actor, malpedia, ransomware, rat, botnet, MITRE ATT&CK galaxies, ms-caro-malware, maec, kill-chain, file-type…) plus every tag already used on ≥ `include_used_min_rules` rules. Each tag gives its terms: the value of its name (`misp-galaxy:tool="Mimikatz"` → `mimikatz`), its galaxy `synonyms`, its ATT&CK id. The rule's title / description / content are tokenized and walked through the trie (phrases up to 6 tokens). Score per tag = Σ field weight (title ×2) × phrase length / √(tags sharing the term), each phrase counted once per field. Tags already on the rule are excluded. The trie is rebuilt when the tag table (count, max `updated_at`) or the setting changes, checked at most every 60 s per worker; the first build takes <1 s.
2. **AI pick.** `app/features/ai/agents/tag_suggest_agent.py` (`TagSuggestAgent`, key `tag_suggest`) gets the top 25 candidates + the gist of the rule (2,500 chars of content) and returns `{"suggestions": [{id, confidence, reason}]}`. Ids outside the candidate list are dropped: the model can't invent a tag. Runs through `AIAgent.run()`, so the enable switch, rate limit, budget, provider choice and `AIExecutionLog` work as for the other agents.

Nothing is applied by itself: the user clicks a tag or **Add all**, then saves the rule.

## Wiring

| Piece | Where |
|---|---|
| Settings | `app/config/ai.tag_suggest.json` (sources, families, stopwords, limits, `simulate_ai`) and `app/config/ai.tag_suggest_formats.json` (context per format) → Admin → Configuration |
| Trie + simulation | `app/features/ai/tag_suggest_core.py` |
| Agent | `app/features/ai/agents/tag_suggest_agent.py` |
| Shared logic | `tag_suggest_core.py`: `candidates()`, `ai_available()`, `bundle_text()` (name + description + its rules' titles and tag names), `ai_pick()` (agent + history row) |
| Routes | `POST /rule/suggest_tags`, `POST /rule/ai_suggest_tags` (`rule.py`); `POST /bundle/suggest_tags`, `POST /bundle/ai_suggest_tags` (`bundle.py`, + bundle owner or admin) |
| UI | `static/js/ai/TagSuggest.js` + `css/ai/tag_suggest.css` — one component, `kind="rule"` (reads the form) or `kind="bundle"` (`target-id`), on `rule/edit_rule.html` and `bundle/edit_bundle.html`. Rulezy shows a pose per state (idle / scanning / thinking / found / empty / error) when the mascot is on (`mascot.js`), a blue gradient icon otherwise. AI picks are cards (tag chip, confidence, reason); other matches are chips in the global `.tag-split` style; "Add all" on both |
| Admin page | `/ai/admin/tag-suggest`: enable, model, limits (`agentConfigCard`), tag sources switches, trie KPIs and families, context per format, history of AI calls (`AIGeneration`, agent_key `tag_suggest`); CSS `css/ai/admin_tag_suggest.css` |
| Default config row | `insert_default_ai_agent_configs()` (`init_db.py`), created by `manage.py update` (`--seed-defaults`) |
| Navs / overview / docs | `macros/ai_admin_nav.html`, `sidebar.html` AI menu, `ai/admin_overview.html`, `ai/models_security.html`, `ai/ai_how_it_works.html` (#tag-suggest) |

Request body for both routes: `{title, description, content, format, rule_id?, exclude_ids: [tag ids already selected]}`. The form fields are read from the enclosing `<form>` (`title`, `description`, `to_string`, `format`), so suggestions work before the rule is saved.

Marking tags are excluded through `exclude_prefixes` (tlp, pap, …): they are on every rule by default and would top every bundle.

## Tag sources

Setting `ai.tag_suggest` → `sources`: `taxonomy`, `galaxy` (limited to `families`), `imported` (Tag.source `Imported`, tags that came with imported rules) and `custom` (everything else: `Manual`, `Connector`…). Imported and custom tags must be used on ≥ `include_used_min_rules` rules (0 = all). Defaults: taxonomy, galaxy, imported on; custom off. Switchable on the admin page (`POST /ai/admin/tag-suggest/sources`, admin or `ai.manage`, saved through `set_setting` with its history, logged `ai.tag_suggest_sources`); at least one source must stay on.

## Context per format (generic tags)

Setting `ai.tag_suggest_formats`, one entry per Rulezet format (yara, sigma, suricata, sagan, zeek, splunk, elastic, kql, wazuh, crs, nse, kunai, atr, plum, nova):

- `context`: what a rule of the format detects. It goes into the prompt (`FORMAT CONTEXT`).
- `tags`: generic tags every rule of the format gets (e.g. Network Traffic data source + `rsit:intrusion-attempts="ids-alert"` for Suricata).
- `signals`: `{label, pattern, tags}`, a case-insensitive regex on title + description + content that adds generic tags. Examples: YARA `uint16(0) == 0x5A4D` → `file-type:type="peexe"` + Win32; Sigma `category: process_creation` → Process data source; Suricata `classtype:trojan-activity` → `rsit:malicious-code="c2-server"` + `kill-chain:Command and Control`.

Generic tags are looked up by exact name, whatever their family (chosen on purpose), but still active, not excluded and of an enabled source. They score 1.0 (format) / 1.6 (signal), are flagged `generic: true`, and always reach the model besides the top 25 NAME candidates (`for_model()`). The model is told to keep a GENERIC tag only when the rule clearly supports it. In the UI they carry a "Generic" badge. A bundle uses the context of the format most of its rules have. The admin page lists each format with its context and any tag name not found.

## Simulation mode (dev)

`simulate_ai: true` in the setting skips the model call: `simulate_ai_picks()` keeps NAME candidates scoring ≥ 35 % of the best one, then the generic tags a signal found (not the per-format ones), one tag per set of matched words (galaxy / taxonomy before a plain twin), confidence from the score ratio, reason `[simulated] The rule mentions …`. The answer has the same shape as the real model's and the UI shows the model as `simulated`. Useful when the local Ollama runs on CPU (a 7B model there needs over a minute even for a tiny prompt). Never on production.

## Next

- Tune the family list from what users accept (log accepted suggestions?).
