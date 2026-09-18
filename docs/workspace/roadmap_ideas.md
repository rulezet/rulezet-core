# Workspace roadmap — brainstormed ideas

> Status: **brainstorm, nothing decided or built yet.** This is a running
> list so ideas discussed in conversation don't get lost. Builds on
> [`current_state.md`](current_state.md) and
> [`connector_research.md`](connector_research.md) — read those first for
> the "why" behind each idea below.

## Guiding goal

Turn Workspace from "a folder you file finished rules into" into the
natural starting point of the workflow: **draft → test → push → publish**,
all without leaving a workspace. That's what "devient vraiment utile" /
"très utilisé" means here — not more features for their own sake, but
removing the reasons someone currently skips using a workspace at all.

## Ideas, roughly in suggested sequence

### 1. Connector — Suricata source (pull), do this first

Highest impact for the lowest implementation cost. `suricata-update`
already knows how to subscribe to an external **source URL** (optionally
with an auth header) and periodically pull + checksum + trigger a reload —
see `connector_research.md`. A Workspace could expose one such source URL
(scoped to that workspace's current rules), so a user's real Suricata
install syncs itself with zero custom integration code on their end —
just one `suricata-update add-source` command.

- Rulezet is the one being *pulled from* here — passive, low operational
  risk (no outbound credentials to manage on our side for this one).
- Natural fit for the existing Connector concept, but the *pull* shape is
  the opposite direction of what's described in idea #2 below — don't
  conflate the two under one generic mechanism.

### 2. Connector — push targets (Wazuh, YARA/VirusTotal, Velociraptor)

Matches what was explicitly asked for: *"configurer un compte avec url
pour push de Rulezet vers des outils externes."* A Connector panel where a
user registers an external endpoint + credential (their Wazuh manager API
token, a VirusTotal API key, a Velociraptor endpoint — Velociraptor is
already a Rulezet feature), and Rulezet calls out to push the workspace's
current rules whenever they change, or on a manual "Push now."

- Wazuh: `PUT` a rule XML file to the manager's rule-files API endpoint.
- YARA: push to VirusTotal Livehunt/Retrohunt via their ruleset API.
- Each target is genuinely different (different auth shape, different
  payload) — expect one small adapter per target, not one generic pusher.
- Needs a per-connector activity log (last push: success/failure, when) —
  a silently-failing push destroys trust fast. Same pattern already used
  for Rulesets/GitHub mirror configs (`RuleMirrorConfig.last_error`/
  `last_tested_at` + its History panel) — reuse that shape here instead of
  inventing a new one.

### 3. Draft Rules as the actual entry point

Write and iterate on rule content **inside** the workspace, before it
exists as a published `Rule` row at all. This is what makes idea #1/#2
valuable *before* publishing, not just after: test a draft against your
own real Suricata/Wazuh via the connector, iterate, and only then promote
it to a real Rulezet rule. Closes the loop: **draft → test → push →
publish**, all in one place.

### 4. Sigma connector — one backend first (Elastic/Kibana)

Sigma has no runtime of its own — it's compiled per-target (pySigma
backends) then pushed via that target's own API. Don't try to support
every SIEM at once; the fragmentation is real (see
`connector_research.md`). Elastic's `detection-rules` CLI already proves
the "push into Kibana via its Security Detections API" pattern is
well-documented — start there, add more backends later only if there's
real demand for a specific one.

### 5. Publish Checklist

A go/no-go checklist a draft has to clear before promotion to a real
published rule: references present, license set, ATT&CK tags present,
at least one connector test/push attempted. Keeps the "draft" tier from
becoming a dumping ground of never-finished rules.

### 6. Test History

A log of every Rule Tester run against a workspace's drafts — lets you see
detection quality improve across iterations before publishing, instead of
only ever seeing the final pass/fail.

### 7. Activity Feed

A workspace-scoped timeline (added rule X, edited draft Y, doc updated) —
useful solo too, not just for eventual collaboration, to retrace your own
steps in a workspace that's been alive for months.

## Open question, not yet answered

Workspace today is **single-owner, no collaboration model** at all (see
`current_state.md`). None of the ideas above require solving that first,
but if "très utilisé" eventually means *team* usage rather than deeper
solo usage, a members/roles table is a prerequisite that touches the data
model directly — worth deciding deliberately rather than backing into it
accidentally while building connectors.
