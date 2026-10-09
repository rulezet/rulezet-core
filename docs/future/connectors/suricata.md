# Suricata connector

> Status: **level 0 shipped** — a public feed of every Suricata rule exists
> (`/rule/feed/suricata.rules`). Levels 1–4 below are ideas.

## How the format is used in real life

Suricata is a network IDS/IPS engine: it inspects the traffic seen by a
sensor and matches it against **rules**. A rule is one line of text:

```
alert http any any -> any any (msg:"Example"; content:"evil"; http.uri; sid:1000001; rev:1;)
```

- `sid` — the rule's unique identifier. Two rules with the same `sid` conflict:
  the sensor keeps only one (this is what the bundle health check *Identifier
  collisions* reports).
- `rev` — the rule's revision.

On a sensor, rules are managed like this:

1. **`suricata-update`** downloads rules from several **sources** (ET Open,
   vendor feeds, custom URLs serving a `.rules` file or an archive).
2. It merges them into one file, `/var/lib/suricata/rules/suricata.rules`,
   applying the local `enable.conf` / `disable.conf` / `modify.conf`.
3. Suricata reloads the rules without restarting:
   `suricatasc -c reload-rules` (or `kill -USR2`).
4. Alerts are written to `eve.json`, each with the `sid` of the rule that fired.

`suricata-update` usually runs from cron a few times a day.

## What Rulezet already offers for it

- **Global feed** — `GET /rule/feed/suricata.rules`: every active Suricata
  rule as one plain-text file, public, cached one hour
  (`rule.py: suricata_feed`, `rule_core.py: get_suricata_feed_text`).
  Usable today:

  ```
  suricata-update add-source rulezet https://rulezet.org/rule/feed/suricata.rules
  suricata-update && suricatasc -c reload-rules
  ```

- **Validation** — the Suricata format parser, and deep validation
  (`rule_format/deep_validate.py`) that runs the rules through a real Suricata.
- **Bundle health checks** — SID collisions, flowbits dependencies satisfied
  inside the bundle, rules that don't parse (`bundle_health_core.py`).
- **Bundles and releases** — curated, versioned sets of rules.

Limits of the global feed: all-or-nothing (no curation), no quality filter
(duplicate SIDs or SIDs colliding with ET Open can get rules rejected by the
sensor), public rules only, no versioning.

## Connector levels

### 1. Deliver — a feed per bundle (small)

- `GET /bundle/<uuid>/feed/suricata.rules` and a pinned one per release
  (`/bundle/<uuid>/releases/<version>/feed/suricata.rules`).
- Only the bundle's Suricata rules, **minus those failing the health checks**
  (duplicate SID, unparsable), with a header listing what was excluded and why.
- Private bundles through an API key — `suricata-update` sends a header per
  source: `suricata-update add-source my-bundle <url> --http-header "X-API-KEY: …"`.
- `ETag` / `Last-Modified` so unchanged feeds aren't re-downloaded.
- A "Use with Suricata" box on the bundle page with the exact commands.

Value: a team deploys exactly the set it curated, validated, versioned.

### 2. Deliver — a workspace as a deployment profile (medium)

- A workspace describes a fleet of sensors: chosen bundles / releases /
  single rules, a list of disabled SIDs, its own feed URL and API key.
- Shows what is in production (which release, since when) and notifies when a
  deployed rule gets a new version, is deprecated or is deleted.

### 3. Verify — a sensor agent (larger)

- A small agent on the sensor (Python script + systemd timer):
  1. fetches the workspace feed,
  2. validates it with `suricata -T` against the sensor's own Suricata version
     before reloading,
  3. reloads, then reports to Rulezet which SIDs loaded and which were
     rejected (with Suricata's error).
- Rulezet shows per workspace: loaded / rejected rules, Suricata versions in
  the fleet, last sync.
- Same pattern as the existing Velociraptor connector. Note: today's
  "connectors" in Rulezet are instance-to-instance federation, not sensors.

### 4. Learn — production feedback (most valuable, most sensitive)

- The agent sends **counters per SID** extracted from `eve.json`: number of
  alerts over a period, optionally "marked false positive" by the analyst.
- Rulezet uses them to: feed the rule quality score, flag noisy rules,
  suggest a bundle note (`false-positive:` tags), start an edit proposal.
- Privacy: only aggregate counters per SID — never IPs, hostnames or payloads;
  opt-in per workspace; documented.

## Value added

- From "a website with rules" to "the place my sensors get their rules from".
- Curation and health checks actually protect production (no silently
  dropped rules because of SID collisions).
- The community learns which rules are useful or noisy in the real world.

## Risks and open questions

- **SID ranges**: Rulezet rules may collide with ET Open / vendor SIDs —
  detect collisions against well-known ranges, or reserve a range?
- **Suricata versions**: keywords differ between 6.x / 7.x / 8.x — validate per
  target version (deep validation could take a version).
- **Load**: many sensors polling — caching, ETag, rate limits per API key.
- **Private rules**: API-key scoping (read-only, one workspace), rotation.
- **Agent trust**: what an agent may write to Rulezet must be strictly limited
  to its workspace's reports.

## First step to build

Level 1, the per-bundle feed:

- `app/features/bundle/bundle.py` — route `/<uuid>/feed/suricata.rules`
  (+ release variant), API-key access for private bundles.
- `app/features/bundle/bundle_core.py` — build the feed from the bundle's
  Suricata rules, excluding the ones flagged by `bundle_health_core`
  (collisions, parse errors).
- Bundle page — a "Use with Suricata" box with the `suricata-update` commands.
- Reuse `get_suricata_feed_text()`'s output shape.
