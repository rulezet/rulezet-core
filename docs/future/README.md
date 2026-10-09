# The future of Rulezet — connecting rules to real use

Rulezet today is where detection rules are **shared, reviewed and curated**:
formats, validation, bundles, health checks, proposals, AI analysis. The next
step is to make Rulezet useful **where the rules actually run** — the sensor,
the SIEM, the scanner, the EDR — and to bring what happens there back into
Rulezet.

**→ The full roadmap of big features is in [ROADMAP.md](ROADMAP.md).**

This folder collects that direction: one file per rule format, describing how
a Rulezet **connector** could link the format's real tooling to Rulezet and
what value it adds. Nothing here is built yet unless its status says so.

## The idea in one picture

```
            curate                      deploy                     run
 Rulezet  ─────────▶  bundle / workspace  ─────────▶  tool (Suricata, SIEM…)
    ▲                (a feed, an API, a push)                     │
    │                                                             │
    └──────────────  feedback: loaded / rejected, alert counts ◀──┘
```

1. **Deliver** — a curated, validated set of rules (a bundle, a release, a
   workspace) reaches the tool in the form it natively consumes, without
   copy-paste: a feed URL, an API push, a package.
2. **Verify** — what was deployed is checked by the tool itself (does it load?
   is the syntax valid for *this* version?) and reported back.
3. **Learn** — anonymous, aggregate signals from production (how often a rule
   fires, false positives reported) flow back to improve quality scores,
   notes and proposals — the community loop Rulezet is built for.

## The Lab — testing before deploying

Before a rule reaches a real tool, prove what it does: for each format, a
controlled environment (pcap replay, malware and clean-file corpora, attack
logs) runs every rule, measures detection, false positives and cost, and
turns it into a **Lab score**. See [testing_lab.md](testing_lab.md).
The Lab supersedes the current Rule Tester, which will be deprecated.

## Principles

- **Native first.** Use what each tool already supports (a `suricata-update`
  source, a Sigma backend, a Wazuh API…) before writing an agent.
- **Curated, not everything.** Deliver bundles / releases / workspaces, never
  "all rules of a format" by default — and exclude rules failing their health
  checks.
- **Pull over push** when possible: the tool fetches with an API key; Rulezet
  never needs credentials to the user's infrastructure.
- **Privacy by design** for feedback: counters per rule only (never IPs,
  hostnames, payloads), opt-in, documented.
- **Same building blocks everywhere**: API keys (`X-API-KEY`), background jobs,
  activity log, notifications, health checks, releases.

## Status per format

| Format | Tool(s) where rules run | Connector idea | Status | File |
|---|---|---|---|---|
| Suricata | Suricata IDS/IPS, `suricata-update` | Per-bundle / workspace feed → deployment profile → sensor agent → alert feedback | Global feed exists (`/rule/feed/suricata.rules`); rest is an idea | [suricata.md](connectors/suricata.md) |
| Sagan | Sagan log engine | Same feed model as Suricata (shares the `.rules` grammar) | Idea | — |
| YARA | yara CLI, ClamAV, Velociraptor, MISP, scanners (THOR, Loki…) | Compiled / per-bundle rule pack, Velociraptor push | Velociraptor connector exists (admin) | — |
| Sigma | SIEMs through pySigma backends (Splunk, Elastic, Sentinel…) | Convert a bundle to the target backend and push / export | Idea | — |
| Zeek | Zeek, `zkg` packages | Bundle published as a Zeek package | Idea | — |
| Wazuh | Wazuh manager | Push rules / decoders through the Wazuh API, reload | Idea | — |
| Splunk | Splunk saved searches | Export / push as saved searches (app package) | Idea | — |
| KQL | Microsoft Sentinel / Defender | Analytics rules through the Sentinel API / ARM templates | Idea | — |
| Elastic | Kibana detection engine | Detection rules through the Kibana API (ndjson) | Idea | — |
| CRS | ModSecurity / Coraza WAF | Rule set package for the WAF | Idea | — |
| NSE | Nmap | Script pack for nmap | Idea | — |
| Kunai, NOVA, Plum, ATR | Their own engines | To study | Idea | — |

To add a format: copy [`connectors/_template.md`](connectors/_template.md) to
`connectors/<format>.md`, fill it in, and add its line to the table above.
