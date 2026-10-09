# Rulezet roadmap — the big features ahead

Everything below is **planned, not built**, unless its status says otherwise.
Order = suggested priority (value for the effort, and what each step unlocks
for the next ones). Details for the larger topics live in their own files.

| # | Feature | Effort | Why it matters | Status |
|---|---|---|---|---|
| 0 | [Code health — full review](#0-code-health--full-review-of-the-codebase) | Large, continuous | A lighter, faster codebase every other feature builds on | Planned |
| 1 | [Sightings](#1-sightings--i-saw-this-rule-fire) | Small | The missing "does this rule work in real life?" signal | Idea |
| 2 | [CVE response kit](#2-cve-response-kit) | Medium | Rules for a critical CVE, in hours, in one place | Idea |
| 3 | [Connectors per format](README.md) — Suricata first | Small → large | Rulezet becomes where tools get their rules | Suricata global feed shipped; per-bundle feed next |
| 4 | [Rulezet Lab](testing_lab.md) | Large | Proof of what each rule detects, a Lab score; replaces the Rule Tester | Idea |
| 5 | [`rulezet-validate` GitHub Action](#5-rulezet-validate-github-action) | Medium | Rulezet inside teams' detection-as-code repos | Idea |
| 6 | [Coverage gap analysis](#6-coverage-gap-analysis--what-dont-i-detect) | Medium → large | From "searching rules" to "knowing what to deploy" | Idea |
| 7 | [Cross-format rule families](#7-cross-format-rule-families) | Medium | One threat, every format; Sigma → SIEM queries | Idea |
| 8 | [Signed releases and verified publishers](#8-signed-releases-and-verified-publishers) | Medium | Trust for automated deployment | Idea |

---

## 0. Code health — full review of the codebase

A foundation running alongside every other item: a complete review of the
code to make it lighter, faster and easier to contribute to.

- **Performance** — find and fix slow pages and endpoints: N+1 queries,
  missing indexes, heavy `to_json()` calls in lists (counts and relations
  loaded per row), work that belongs in background jobs or the cache.
  Measure before / after on the real database.
- **Duplication** — the same logic written several times: near-identical
  endpoints (web routes vs API namespaces), helpers re-implemented per
  feature, tables / badges / dialogs / status logic copied between templates
  and components. Factor them into shared core helpers and components.
- **Size** — split the largest files by responsibility: `rule.py` (~6,700
  lines), `rule_core.py` (~5,800), `job_handlers.py` (~5,400), `db.py`
  (~5,000 lines of models), `bundle.py` (~2,800), the largest templates and
  JS components (`detail_bundle.html` ~2,000, `ruleList.js` ~2,700).
- **Dead code** — remove what is no longer used or is being replaced (the
  Rule Tester once the Lab ships, old templates, unused routes, CSS and JS).
- **Consistency** — one way to do each thing: permissions, pagination,
  toasts, JSON error shapes, activity logs; documented for contributors.
- **Tests** — finish the `tests_new/` restructure (access / CRUD / API /
  robustness per feature) so refactors are safe; run it in CI.

Done feature by feature, each step shipped on its own, never a big-bang
rewrite.

## 1. Sightings — "I saw this rule fire"

MISP's sightings, applied to rules. Anyone using a rule reports, in one click
or through the API:

- **true positive** — it caught something real;
- **false positive** — with the kind of environment (e.g. "Windows domain
  controller", "web proxy");
- **deployed** — "in production here".

Why huge: the strongest quality signal there is, with no agent and no lab.

Uses: quality score, "most deployed" / "noisiest" sorts, a nudge to write a
bundle note (`false-positive:` tags) or an edit proposal when false positives
pile up, rule-page stats ("deployed by 14 teams, 3 FP reports").

Build: a `rule_sighting` table (rule, version, user, type, context, date), a
button on the rule page, `POST /api/rule/<uuid>/sighting`, aggregates on the
rule and bundle pages. It is also the lightweight version of the connectors'
"Learn" level — a sensor agent later posts sightings automatically.

## 2. CVE response kit

When a critical CVE drops, `/cve/CVE-YYYY-NNNN` gathers automatically:

- every rule linked to it, across formats;
- the gaps ("no Sigma rule, no YARA rule yet");
- one-click AI drafts for the missing formats (Rule Generator);
- a ready-made bundle to download / subscribe to (feeds, see connectors);
- an alert when a new rule for it is published (alerts exist).

Most building blocks exist (Vulnerability-Lookup links, alerts, the AI
generator, bundles) — what's missing is the page that assembles them. The use
case where teams need rules *now*; a natural fit with CIRCL's
Vulnerability-Lookup.

## 3. Connectors per format

See [README.md](README.md) and [connectors/](connectors/). Deliver curated
bundles / workspaces to the real tools natively, verify on the tool, learn from
production. First step: a per-bundle Suricata feed
(`/bundle/<uuid>/feed/suricata.rules`) excluding health-check failures.

## 4. Rulezet Lab

See [testing_lab.md](testing_lab.md). Per-format test environments (pcap
replay, malware and clean corpora, attack logs) run every rule, measure
detection / false positives / cost, give a Lab score fed into the quality
score, detect regressions between versions. Supersedes the current Rule
Tester (deprecated; its format drivers are kept as the Lab's execution layer).

## 5. `rulezet-validate` GitHub Action

Teams keeping rules as code add a GitHub Action: on every pull request, their
rules are validated with Rulezet's own parsers and health checks (syntax,
duplicate SIDs / ids, unsatisfied dependencies), with annotations on the
diff. Optional: publish to a bundle / release on merge.

Why huge: Rulezet becomes a daily tool inside the team's repo, not only a
website. Pairs with the parked "pull-back" idea (PR-merged changes on a mirror
repo flowing back into Rulezet as proposals) and the existing GitHub import /
rulesets mirror.

Build: a public validation API (`POST /api/rule/validate` with a batch of
files) + a small Action repository calling it (or running the parsers in a
container).

## 6. Coverage gap analysis — "what don't I detect?"

The user describes their context: sector, threats targeting them (an APT
group, a MISP event, a threat report), their stack (Windows / Linux, web,
cloud…). Rulezet maps it onto ATT&CK and the catalog and shows:

- techniques covered / not covered by existing rules, per format;
- a recommended bundle for their stack;
- AI drafts to fill the gaps.

Builds on the ATT&CK matrix and mappings, MISP integration, bundles, the AI
generator; a workspace could hold the profile.

## 7. Cross-format rule families

Link equivalent rules across formats — this Suricata, Sigma and YARA rule
detect the same threat — into a family, using similarity and linked rules
(both exist). Add Sigma → SIEM query conversion (pySigma backends) so a Sigma
rule shows "also available for Splunk / Elastic / Sentinel". A rule page then
answers "what do I use in *my* tool?".

## 8. Signed releases and verified publishers

Bundle releases signed with the publisher's key; a "verified publisher" badge
(CIRCL, known vendors, trusted contributors); feeds served with their
signature. Required as soon as sensors pull feeds automatically (connectors):
proof that a feed wasn't tampered with, and who stands behind it.
