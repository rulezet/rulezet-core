# Detection-rule ecosystem research — feeding Workspace from/to real tools

> Purpose: ground the "workspace becomes a real working tool" direction in
> how the actual detection-engineering ecosystem consumes rules today, so
> the Connector idea targets a real, already-expected integration shape
> instead of inventing one from scratch.
>
> Scope: YARA, Sigma, Suricata (priority, per request), Wazuh. Sourced from
> current docs/tooling as of 2026-09-18 (web search + existing knowledge).

## TL;DR

Every one of these ecosystems already has *some* precedent for
"periodically pull rules from an external source" or "push rules into a
running product via API" — Rulezet doesn't need to invent an integration
model, it needs to **speak the protocol each tool already expects**:

| Format | Existing pull/push precedent |
|---|---|
| Suricata | `suricata-update` — register a **source URL**, tool periodically pulls + checksums + reloads. **Closest match to what a Rulezet Connector could offer with the least user-side setup.** |
| Sigma | No native runtime — rules are converted offline/at deploy time by `sigma-cli`/pySigma **backends** into each SIEM's query language, then pushed into that SIEM (some SIEMs take Sigma natively: Logpoint, Sekoia; most don't). |
| Wazuh | REST API supports uploading a custom rule **file** directly (`PUT` to the manager's rule-files endpoint) — a push integration, not a pull-your-own-source mechanism. |
| YARA | No standardized pull protocol. Consumers either watch a git repo of `.yar` files, or accept rules via their own product API (e.g. VirusTotal Livehunt/Retrohunt). |

## Suricata

Suricata (the engine) only ever loads `.rules` files listed in
`suricata.yaml`; getting rules *into* that list is `suricata-update`'s job
(official, OISF-maintained, ships with Suricata).

- **Sources**: `suricata-update` maintains an index of registered "sources"
  (Emerging Threats Open/Pro, community feeds, etc.) plus
  `suricata-update add-source <name> <url>` to register **any** custom URL
  — no need to be listed in the official index. Supports
  `--http-header "Authorization: Bearer …"` for authenticated sources, so
  an API-key-gated feed is already a supported shape, not something we'd
  need to lobby upstream for.
- A registered source is periodically re-pulled (checksum-checked so
  nothing re-downloads/reloads unless it actually changed) and merged
  into the local ruleset; `suricata-update` then calls Suricata's
  `rules-reload` so the engine picks up changes without a restart.
- Full URL/archive format details weren't confirmed by docs search (the
  page covers registration, not the wire format) — worth a scratch
  spike against a real `suricata-update` binary before committing to an
  exact response shape, but the **registration UX is confirmed**: one URL,
  optional bearer header, periodic pull, checksum-gated reload.
- Ecosystem built on top: Security Onion, SELKS, Stamus Networks, Arkime —
  all NSM platforms that assume Suricata-Update-style feeds as normal.

**Why this matters for Rulezet**: this is the lowest-friction integration
imaginable. If a Workspace can expose a `suricata-update`-compatible source
URL (with an API-key header), a user's existing Suricata box needs **zero
custom integration code** — just one `suricata-update add-source` command
pointing at the workspace. This is the strongest "connector" candidate of
the four.

## Sigma

Sigma is deliberately not tied to any runtime — it's a generic YAML
detection format that gets **compiled** into a target's native query
language at conversion time, not interpreted live.

- **pySigma** (Python library, SigmaHQ org) + **sigma-cli** (its CLI) do
  the conversion. `sigma list` shows installed backends/pipelines,
  `sigma convert -t <backend> -p <pipeline> rules/` emits queries for that
  target.
- **Backends exist for**: Splunk, Elasticsearch/OpenSearch (ES|QL/EQL),
  Microsoft Sentinel (KQL), Microsoft 365 Defender, and others — each
  Sigma "backend" is a separate maintained package (some official, some
  community).
- A handful of SIEMs (Logpoint, Sekoia.io) accept Sigma content closer to
  natively; most (Splunk, Sentinel, Elastic, QRadar) need the
  conversion step, then the resulting query has to be manually pasted or
  pushed via that SIEM's own API into a saved search / detection rule.
- **Commercial reference worth knowing**: SOC Prime's **Uncoder AI**
  (successor to the open-source Uncoder.IO) is explicitly a "Detection as
  Code" platform built around this exact conversion-then-push idea at
  scale — translates Sigma into ~48 target languages and has *native
  push* integrations for Microsoft Sentinel, Google SecOps, and Elastic
  Stack, meaning it converts **and deploys** in one step, no manual
  export/import. This is the closest existing commercial product to
  "Rulezet Connector, but for Sigma specifically" — useful as a concrete
  reference point (and competitive context) for how far this direction
  could eventually go.
- **Elastic-specific precedent**: Elastic's own `detection-rules` repo
  (already cloned as scratch reference in `app/rule_from_github/`) ships a
  Python CLI whose `kibana import-rules` command pushes rule files
  straight into a running Kibana instance via Kibana's own Security
  Detection Rules API — i.e. "push detection content from a repo into a
  live security product" is an established, documented pattern, not
  something exotic.

**Why this matters for Rulezet**: Sigma is the format with the *most*
existing "deploy this content into my SIEM" tooling in the wild, but it's
fragmented per-target — there's no single protocol to speak, only many
backend-specific ones. A Rulezet Connector here would most realistically
mean: let the user pick a target backend, run the existing pySigma
conversion server-side, and push the result via that target's own API
(Elastic/Kibana being the best-documented one to start with).

## Wazuh

Wazuh (OSSEC fork) rules are XML, loaded by the manager from
`/var/ossec/etc/rules/` per `ossec.conf`'s ruleset config — already
Rulezet's `wazuh` format (`.xml`).

- **No source/feed-pull mechanism** analogous to suricata-update exists.
  Rule distribution to a Wazuh manager is either manual file placement,
  configuration-management automation (Ansible/Salt/Puppet playbooks that
  template out rule files), or the **Wazuh REST API**.
- The Wazuh manager API exposes a rule-**files** endpoint
  (`PUT` to the manager's `rules/files/<filename>` path family, per
  Wazuh's own API reference) that accepts a raw XML file body
  (`Content-Type: application/octet-stream`) to create/overwrite a custom
  rule file, gated by RBAC (`rules:update`/`rules:delete` on resource type
  `rule:file`). After upload, the manager needs a rules-reload/restart to
  pick it up (Wazuh has clustering/rolling-restart tooling for this at
  scale).
- This is a **push** shape, not a pull-your-own-source one: something on
  the Wazuh side (a script, or eventually Wazuh itself) has to call this
  API with credentials it holds — Rulezet can't "publish a feed" the way
  Suricata does; it would need to actively push to a Wazuh manager's API
  using a token the user configures on the Rulezet side (this is exactly
  the shape the user described for Connector: *"configurer un compte avec
  url pour push de Rulezet vers des outils externes"*).

**Why this matters for Rulezet**: Wazuh is the best-fit format for a
literal "push connector" (URL + credentials, Rulezet calls out) since
that's already how real Wazuh deployments automate rule delivery — we'd
just be doing what an Ansible playbook does today, but from a Workspace's
"Connector" panel instead of a playbook.

## YARA

No standardized rule-distribution protocol exists across YARA consumers —
each product does its own thing:

- Most command-line/scanner tools (Loki, THOR, Fenrir, custom scripts)
  just load `.yar` files from a directory, commonly kept in sync via `git
  pull` on a schedule (cron/systemd timer) rather than any product-native
  pull mechanism.
- **VirusTotal** is the notable exception with an actual API: Livehunt and
  Retrohunt let you create/update a YARA ruleset via VT's REST API
  (a genuine push target, gated by a VT API key) — directly analogous to
  the Wazuh push shape above.
- EDR products that support custom YARA scanning (some CrowdStrike/
  SentinelOne tiers, osquery's yara extension, Velociraptor — which
  Rulezet already integrates with per its `velociraptor` feature) each
  have their own upload/config mechanism, no shared standard.

**Why this matters for Rulezet**: YARA is the format where a Connector
would have to be the most bespoke per-target (there's no
"suricata-update-for-YARA" to imitate) — VirusTotal push and Velociraptor
(already a Rulezet feature) are the two most concrete, already-relevant
targets to start with rather than trying to cover the whole fragmented
YARA-consumer landscape at once.

## Cross-cutting takeaways

1. **"Pull" (Suricata-style) and "push" (Wazuh/VT-style) are genuinely
   different integration shapes**, not two names for the same thing — a
   single generic "Connector" abstraction risks fitting neither well. The
   user's own framing ("configurer un compte avec url pour push de
   Rulezet vers des outils externes") already points at the push shape,
   which fits Wazuh and YARA/VirusTotal better than it fits Suricata
   (where the *tool* should be doing the pulling, not Rulezet doing the
   pushing).
2. **Detection-as-Code is already a named, funded industry direction**
   (SOC Prime Uncoder AI, Splunk's `security_content` repo, Elastic's own
   `detection-rules` CLI+CI) — Rulezet leaning into "Workspace = your
   detection-as-code staging area, Connector = the deploy step" is not a
   novel bet, it's catching up to where serious detection engineering
   teams already expect to operate. That's reassuring (proven demand) and
   a warning (there's real competition, at least for Sigma specifically).
3. **Suricata is the cheapest, highest-confidence win** — registering a
   Workspace as a `suricata-update` source needs no new protocol design,
   just implementing the response shape `suricata-update` already expects.
4. **Sigma is the highest-ceiling but highest-effort** — real value only
   shows up once conversion (pySigma) + push (per-SIEM API) both exist;
   worth sequencing after Suricata, likely starting with one backend
   (Elastic/Kibana has the best-documented push API of the bunch).
5. **Wazuh and YARA are push-shaped and format-specific** — best modeled
   as "Connector targets" (a saved external endpoint + credential a
   Workspace can push to), independent of the Suricata pull-source
   design.

## Sources consulted

- [suricata-update: add-source](https://suricata-update.readthedocs.io/en/latest/add-source.html)
- [suricata-update: update-sources](https://suricata-update.readthedocs.io/en/latest/update-sources.html)
- [OISF/suricata-update on GitHub](https://github.com/OISF/suricata-update)
- [Wazuh API reference — rule file endpoint](https://documentation.wazuh.com/4.3/user-manual/api/reference.html#operation/api.controllers.rule_controller.put_file)
- [Wazuh — Custom rules](https://documentation.wazuh.com/current/user-manual/ruleset/rules/custom.html)
- [elastic/detection-rules CLI.md](https://github.com/elastic/detection-rules/blob/main/CLI.md)
- [SigmaHQ/pySigma](https://github.com/SigmaHQ/pySigma), [Sigma backends](https://sigmahq.io/docs/digging-deeper/backends.html)
- [SOC Prime — Uncoder AI](https://socprime.com/uncoder-ai/)
