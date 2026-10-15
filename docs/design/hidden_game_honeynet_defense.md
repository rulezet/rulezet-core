# Honeynet Defense

> Status: **design** — nothing built yet. Third hidden game of Rulezet (after Starfield and The Analyst — see
> `hidden_game_the_analyst.md`).

A tower defense on a company network seen from above. Attacks walk the network's paths — phishing in, lateral
movement across, exfiltration out — and the player defends it with **probes** that are Rulezet's real formats:
YARA on endpoints, Suricata on network links, Sigma on log collectors, Zeek as an observer. Every attack carries
**real MITRE ATT&CK techniques** (from Rulezet's own ATT&CK table), and the right probe has to be in the right
place. Rulezy is the SOC manager on the radio.

---

## 1. Goals

- **Rulezet as game mechanics**: the probe types are the rule formats; enemies are ATT&CK techniques; the strength
  of a probe against a technique comes from **the real Rulezet catalog** (how many rules of that format cover that
  technique on this instance).
- **Different from Starfield and The Analyst**: strategy and placement, not action or reading; short rounds
  (5–10 min); highly replayable.
- **Learn the kill chain without noticing**: initial access → execution → lateral movement → exfiltration, and
  which data source sees which step.
- **Stay hidden**: same rules as the other hidden games.
- **Trustworthy leaderboard**: the round is replayed server-side from the player's actions.

## 2. Access — keeping it hidden

- Secret URL **`/honeynet`** — linked from nowhere, not in the sitemap or the chatbot routes, JS folder excluded
  from the import map (`static_versions.HIDDEN_DIRS`).
- **The trail**:
  1. In The Analyst, case 5 ("Lateral"), one of the hosts in the logs is called `HONEYNET-GW` and its DNS log
     contains a single query to `honeynet.<instance host>/honeynet`.
  2. On the ATT&CK matrix page, clicking the same empty cell of the matrix five times in a row makes Rulezy pop
     up for a second with *"Want to defend it for real?"* → the link appears once, then is gone.
  3. In Starfield, the honeypot levels' description gains a line for players who finished one:
     *"Some honeypots are a whole network."*
- Progress for logged-in players server-side; anonymous players in the browser, scores grouped by a browser id.

## 3. Setting and art direction

- **Top-down network map, neon on dark**: the company network drawn as a glowing circuit board — buildings are
  zones (Office, Datacenter, DMZ, Cloud), hosts are chips, links are traces where packets flow as light pulses.
- Attacks are small glitched sprites coloured by tactic (initial access red, execution orange, lateral movement
  purple, exfiltration cyan…) — the same colours as the ATT&CK matrix heatmap (`AttackMatrix` component).
- Probes are stylised devices with the format's identity (YARA magnifier, Suricata meerkat, Sigma Σ, Zeek eye).
- Day/night cycle per wave; a "breach" flashes the zone red.
- Sound: low ambient hum, packet blips, a siren when a crown jewel is hit. Muted by default.
- FR and EN, browser language by default.

## 4. Core loop

```
Plan (place / upgrade probes) ─▶ Wave (attacks walk the network) ─▶ Debrief (what got through, and why) ─▶ Plan …
```

### The network

- A graph: **nodes** (workstations, servers, domain controller, mail gateway, file server, database, cloud bucket)
  and **links** (LAN, VPN, internet uplink).
- **Entry points**: internet (mail, web, VPN). **Crown jewels**: the database, the domain controller, the
  customer data bucket — the round is lost when the "data exfiltrated" gauge fills up.
- Attacks follow paths on the graph; each step of an attack is one ATT&CK technique and happens **on a node or a
  link** (e.g. `T1566.001 Spearphishing Attachment` on the mail gateway, `T1021.002 SMB/Windows Admin Shares` on a
  LAN link, `T1048 Exfiltration Over Alternative Protocol` on the uplink).

### Probes (towers)

| Probe | Placed on | Sees | Typical techniques |
|-------|-----------|------|--------------------|
| **YARA** scanner | endpoints, file servers, mail gateway | files and memory | malicious documents, loaders, implants |
| **Suricata** IDS | network links | packets, protocols | C2 beacons, exploits, exfiltration |
| **Sigma** collector | any node (log source) | logs and events | PowerShell, service creation, log clearing, logons |
| **Zeek** sensor | links / segments | network metadata | anomalies, lateral movement, DNS tunnelling |

- A probe **detects** techniques it is good at, in its range; a detected step is stopped (the attack is
  "contained") or slowed, depending on the probe's level.
- **Coverage, not damage**: each probe has a detection chance per technique — that's the core tuning knob.
- **Upgrades**: rule packs (better coverage), faster response, wider range; and **Response** actions (isolate a
  host, block a domain) on cooldown.
- **Budget**: "analyst hours" earned per wave and per technique contained; false-positive noise (probes
  overlapping too much on the same node) costs hours — over-instrumenting has a price.

### The Rulezet catalog as game data

- A probe's detection chance against a technique is derived from the **real number of rules of that format
  mapped to that technique** in Rulezet (`RuleAttackAssociation` × `Rule.format`), with a curve and a floor/ceiling
  so the game stays balanced on any instance:
  `chance = clamp(base + k · log(1 + rules_count), floor, ceiling)`.
- The debrief shows it: *"Your Sigma collector caught T1059.001 PowerShell — 1,284 Sigma rules on this instance
  cover it."* with a link-free mention (the game never links out, to stay hidden).
- **Community intel bonus**: once per round, the player can "import a bundle" — a random real public bundle of the
  instance whose techniques get a temporary coverage boost. The bundle name is shown.
- Balance values (base, k, floor, ceiling, costs) live in `app/config/honeynet.balance.json` — editable in Admin →
  Configuration like any setting.

## 5. Rulezy — SOC manager on the radio

- Briefs each mission ("A finance user just opened an invoice. Here we go.").
- Calls out what's happening during waves ("Lateral movement towards the DC — Zeek on that segment would see it.").
- **Debrief coach**: after each wave, explains the one breach that hurt most and which probe would have caught it,
  with the ATT&CK technique name and tactic.
- Hints cost nothing but appear only after a failed wave (no hand-holding for good players).
- Same voice as everywhere: dry, tired, loyal. Uses the existing poses + a "headset" pose.

## 6. Campaign — "Glasshouse, Part II"

Continues The Analyst's story: after the night shift, the Glasshouse group comes back, this time against the whole
company — and the SOC has a budget to build its detection. Six missions, each a network map, plus endless mode.

| # | Mission | Network | New threat | New probe / mechanic |
|---|---------|---------|-----------|----------------------|
| 1 | **First Contact** | small office (8 nodes) | phishing → macro → PowerShell | YARA, Sigma; tutorial |
| 2 | **Beacon** | office + DMZ | C2 beaconing, DNS | Suricata on links |
| 3 | **Sideways** | office + datacenter | lateral movement (SMB, RDP, remote services) | Zeek, response: isolate host |
| 4 | **Living off the Land** | full company | LOLBins, scheduled tasks — files are clean, only logs show it | Sigma upgrades; YARA useless here (a lesson) |
| 5 | **Exfil** | company + cloud | staging, compression, exfiltration over alternative protocols | uplink defense, data gauge pressure |
| 6 | **Glasshouse** | the whole network, two entry points | a full intrusion set mixing every tactic, waves adapt to the player's blind spots | everything; the boss wave targets the weakest-covered tactic |

- **Stars per mission** (1–3): survived / no crown jewel touched / under budget.
- **Endless mode — "Red Team Night"**: procedurally built networks, waves drawn from real ATT&CK techniques (any
  of the instance's techniques that have at least one rule mapped), difficulty rising every 5 waves. This mode
  feeds the main leaderboard.
- **Daily network**: one seeded endless map per day, same for everyone — a fair daily ranking.

## 7. Scoring and anti-cheat

- The client sends the **action log** of the round (probe placements, upgrades, response actions, each with its
  wave/tick) and the seed — never a score.
- The server **replays the round deterministically** (same seed, same simulation code — the simulation core is
  written once in plain JS and run server-side with a small Node or a Python port; see open questions) and
  computes the score.
- Score: techniques contained × their tactic weight, crown jewels intact, budget left, waves survived (endless),
  minus noise penalties.

## 8. Leaderboard (visible to players)

On the hidden page:
- **Campaign**: total stars and score per player.
- **Endless**: best wave and score; filter by week / all time.
- **Daily network**: today's ranking, with the player's build shown as a mini-map (where they put which probe).
- Per player: favourite probe, tactics most often contained, the technique that breaches them most ("Your
  nemesis: T1021.002 SMB/Windows Admin Shares").
- Logged-in players by username, anonymous as "Anonymous defender #c3d4", opt-out to appear anonymous.
- **Admin view**: same panel as Starfield — every player, every round, the action log replayable as a timeline.

## 9. Two new badges (secret)

| Key | Name | Unlock | Description (shown) |
|-----|------|--------|---------------------|
| `honeynet_keeper` | **Honeynet Keeper** | Finish mission 1 | *"You drew the map before they did. Every link has eyes now."* |
| `full_coverage` | **Full Coverage** | Finish mission 6 with 3 stars, no crown jewel touched | *"Every tactic, every path, every hour of the night. Nothing reached the jewels."* |

Same mechanism as the other secret badges: `'secret': True` in `badges.py`, not in the public catalog, shown on a
profile once unlocked, teased in "Hidden badges" on How to earn points. Icons: `fa-network-wired` (teal) and
`fa-shield-halved` (gold).

**Cross-game nod** (optional, not a badge): a profile with all six hidden badges (Starfield ×2, The Analyst ×2,
Honeynet ×2) shows a tiny Rulezy in the badge section, asleep on a server rack.

## 10. Technical architecture

Follows `docs/refactor/00_conventions.md`.

```
app/features/honeynet/
    honeynet.py              # routes: page, round start (seed), round submit (action log), leaderboard, admin
    honeynet_core.py         # replay + scoring, ATT&CK coverage from the catalog, progress
    missions/*.json          # the 6 campaign maps and their waves
app/core/db_class/honeynet.py
    HoneynetRound            # user_id / player_id, mission or endless/daily, seed, action log, replayed score, stars
    HoneynetProgress         # campaign progress per player
app/config/honeynet.balance.json   # coverage curve, costs, budgets — admin-editable setting
app/templates/honeynet/honeynet.html
app/static/js/honeynet/            # excluded from the import map (HIDDEN_DIRS)
app/static/css/honeynet/
```

- **ATT&CK data**: `AttackTechnique` (858 techniques on this instance) for names/tactics; coverage counts from
  `RuleAttackAssociation` joined with `Rule.format`, computed once per hour and cached (not per request).
- **Rendering**: a single canvas for the map (no library); HTML for the build menu, debrief and leaderboard.
- **Determinism**: integer simulation with a seeded RNG, so the server replay matches the client exactly.
- **Tests**: replay determinism (client log → same score), coverage curve bounds, mission validation (each
  mission winnable with a reference build), access tests, and the "nothing outside `/honeynet` mentions it" check.

## 11. Milestones

1. **Vertical slice** — mission 1: map, two probes (YARA, Sigma), three waves, debrief, local score.
2. **Catalog-driven coverage** — real ATT&CK data and rule counts, balance config, Suricata + Zeek.
3. **Server replay + leaderboard** — action log, deterministic replay, ranking, admin panel.
4. **Campaign** — missions 2–6, Rulezy radio lines, story link with The Analyst, badges.
5. **Endless + daily network**, polish, FR translation, the trails from the other games.

## 12. Open questions

- Server replay: port the simulation to Python, or run the JS simulation server-side (Node via a subprocess)?
- Should the instance's catalog really change difficulty (a small instance = weak probes), or only flavour text?
- Mission maps: hand-made only, or a map editor for admins later?
- Order of development between The Analyst and Honeynet Defense — Honeynet's story continues The Analyst's.
