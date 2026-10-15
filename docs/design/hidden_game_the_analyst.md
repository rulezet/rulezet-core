# The Analyst — Night Shift

> Status: **design** — nothing built yet. Second hidden game of Rulezet, after Starfield.

A narrative investigation game. You are the only analyst on the night shift of a SOC. Alerts come in, you dig
through logs, processes and files, and you close each case by **writing a real detection rule** (YARA or Sigma,
simplified) that Rulezet's own rule tester runs against real samples: it must catch the threat and stay silent on
everything else. Rulezy is your night-shift partner.

---

## 1. Goals

- **The most "Rulezet" game possible**: the win condition is a working detection rule, checked by the real engines
  (`app/features/rule_tester/drivers/yara_driver.py`, `sigma_driver.py`).
- **A story worth following**: one investigation that spans the whole night, with recurring characters, a twist
  and an ending.
- **Learn without noticing**: a player who never wrote a rule finishes the first case; a detection engineer finds
  the late cases tricky (false positives, evasion, encoding).
- **Stay hidden**: no link anywhere, nothing in the page source of other pages (see Starfield: the import map
  excludes hidden folders).
- **Scores that can be trusted**: everything that counts is computed server-side.

## 2. Access — keeping it hidden

- Secret URL **`/nightshift`** — linked from nowhere, not in the sitemap, not in the chatbot routes, its JS folder
  excluded from the import map (`static_versions.HIDDEN_DIRS`).
- **The way in is a trail, not a link**:
  1. Beating Starfield's final boss shows, among the victory lines, a "corrupted" log line:
     `[02:13:07] nightshift: analyst wanted — /nightshift`.
  2. The **Anomaly Detected** badge description gains a second sentence for players who own it (shown on their
     own profile only): *"The night shift is still hiring."*
  3. Typing `nightshift` in the chatbot makes Rulezy answer *"Shh. Not here."* — and nothing else.
- Logged-in players save their progress server-side; anonymous players play too (progress in the browser, scores
  grouped by a browser id, as in Starfield).

## 3. Setting and art direction

- **Neo-noir, pixel art**: a SOC room at night, rain on the windows, a city skyline, three monitors, a coffee mug
  that slowly empties, a wall clock that advances with each case (21:00 → 06:00).
- Palette: deep blues and purples, amber screen glow, red for alerts. Pixel art at 2x/3x scale on a canvas for the
  room, regular HTML for the "screens" (readable text, selectable, accessible).
- Sound: rain, keyboard clicks, a low synth; a ping for new alerts. Muted by default, one click to enable.
- Two languages, FR and EN, defaulting to the browser's language (same approach as Starfield's `i18n.js`).

## 4. Rulezy — the night-shift partner

Rulezy lives in the corner of the main screen (existing poses in `static/images/rulezy/`; a few new night poses
would be welcome: with a coffee, sleepy, alarmed).

- **Narrator**: introduces each case, reacts to what you find ("That process has no business talking to the
  internet.").
- **Hint system** (costs score): 3 levels per case — a nudge ("look at the parent process"), a direction
  ("the C2 domain is in the DNS log"), then the answer to one step. Each hint used is recorded.
- **Rule coach**: after a test run, Rulezy explains the result in plain words — "Your rule fired on
  `notepad.exe` — that's a false positive. Your string is too generic."
- **Personality**: dry humour, tired, loyal — the same voice as the badge congratulation lines. Never cheesy.
- **Story role**: Rulezy notices things the player missed; in the last act, Rulezy is the one who spots that the
  attacker is reading the SOC's own alerts (see the twist).
- Optional later: Rulezy's lines written by the AI module (`app/features/ai`) when an instance has it enabled —
  but every line must exist as static text first, the game can't depend on an LLM.

## 5. Core loop of a case

```
Alert arrives ─▶ Investigate ─▶ Collect evidence ─▶ Write the rule ─▶ Test it ─▶ Deploy
                    ▲                                     │
                    └──────── wrong / noisy rule ◀────────┘
```

1. **Alert**: a ticket appears (severity, host, short description). The clock ticks.
2. **Investigate** — tools on the analyst's desktop, each a window:
   - **Log viewer**: Windows events, proxy, DNS, authentication logs — searchable, filterable by host and time.
   - **Process tree**: parent/child processes with command lines.
   - **File browser**: suspicious files with hex view, strings, hashes.
   - **Mailbox**: phishing emails, internal messages from colleagues (story).
   - **Threat intel notes**: a notebook where the player pins evidence (clicking a log line or a string pins it).
3. **Evidence board**: pinned items; a case can only be closed once the key evidence is pinned
   (prevents guessing the rule without investigating).
4. **Write the rule**: a guided editor —
   - Case 1–2: **fill the blanks** (`strings: $a = "____"`, `condition: ____`).
   - Case 3–4: **building blocks** (drag strings/conditions from the evidence board).
   - Case 5+: **free editor** (YARA or Sigma, syntax highlighting via the existing `SmartEditor`).
5. **Test**: the rule runs server-side against the case's **test corpus**: malicious samples (must match) and
   benign samples (must not). Result: true/false positives/negatives, shown sample by sample.
6. **Deploy**: when the rule catches every malicious sample with no false positive, the case closes; the score is
   computed; the story advances.

## 6. Scoring (server-side)

Per case:

| Component | Points |
|-----------|--------|
| Case closed | 1,000 |
| Rule quality | up to 1,000 — 0 false positive, 0 false negative, plus a bonus for a rule that also catches the **hidden variants** (samples not shown during the investigation, revealed after deploy) |
| Investigation | up to 500 — key evidence pinned, side clues found |
| Speed | up to 500 — in-game time, not real time (no pressure on slow readers) |
| Hints | −150 per hint |
| Failed deploys | −50 per deploy with a false positive (a "pager storm" at 3 a.m.) |

- **Stars per case** (1–3): closed / zero false positive / hidden variants caught.
- The rule itself is stored with the result — the leaderboard can show "best rule" per case.
- Every test run is executed and scored on the server; the client never sends a score.

## 7. Scenario — "Operation Glasshouse"

One night, eight cases, one antagonist group, one twist. Each case teaches one detection idea.

**Prologue — 21:00, Shift handover.** The day analyst, *Mara*, leaves in a hurry: "Quiet night. The new
EDR is noisy, ignore the printer." Rulezy boots up on the third monitor. Tutorial: read an alert, pin evidence.

| # | Time | Case | What the player learns | Rule |
|---|------|------|------------------------|------|
| 1 | 21:30 | **The Invoice** — a phishing mail with a macro document. | Strings in a file, a basic YARA rule. | YARA, fill the blanks |
| 2 | 22:15 | **Night Owl** — `powershell.exe -enc …` spawned by Word. | Parent/child process, Sigma on process creation. | Sigma, fill the blanks |
| 3 | 23:00 | **The Printer** — the "noisy" printer beacons to a strange domain every 60 s. Mara said to ignore it. | Beaconing in DNS logs; false positives (other printers are legit). | Sigma, building blocks |
| 4 | 00:20 | **Glasshouse** — a loader with XOR-encoded strings; the group's name appears for the first time. | Hex strings, wildcards, `xor` modifier. | YARA, building blocks |
| 5 | 01:30 | **Lateral** — admin shares and remote services across 4 hosts. | Correlating hosts and time; tuning a Sigma rule against an admin tool used legitimately. | Sigma, free |
| 6 | 02:45 | **Quiet Hours** — logs go silent on one server: someone cleared them. | Detecting the absence/clearing of logs; Rulezy notices the timestamps match Mara's badge-out. | Sigma, free |
| 7 | 04:00 | **Mirror** — the attacker's tool checks the SOC's own alert queue before acting. **Twist**: the "noisy printer" from case 3 is the implant; Mara's account was used, not Mara — her credentials were phished in case 1's campaign, which the player has just shut down. | Detecting an attacker who reads your detections; writing a rule the attacker can't see coming (unusual field). | YARA + Sigma |
| 8 | 05:30 | **Dawn** — final confrontation: the group launches the payload at shift change. One rule, no hints, the real-time clock is running. | Everything together; hidden variants matter. | Free, one shot per sample set |

**Epilogue — 06:00.** Mara comes back; the player's rules are "promoted to production" (a fake Rulezet page
showing the player's 8 rules as a bundle — a wink to the real platform). Rulezy, finally, falls asleep.

**Optional endings**: perfect night (all 3 stars) unlocks a short extra scene — Rulezy's log shows it was awake
the whole time, watching the printer since before the shift.

**Characters**:
- **You** — the analyst. Never shown, never named (the player's username appears on the badge-in screen).
- **Rulezy** — partner, narrator, coach.
- **Mara** — the day analyst; suspected, then cleared.
- **Glasshouse** — the antagonist group; never seen, only their tools, comments in code and one taunting message
  in case 7.
- **The CISO** — one phone call in case 6 ("Is it bad? Don't answer that.").

## 8. Case data

Each case is **one JSON file** in `app/features/nightshift/cases/<n>_<slug>.json` (game content, not
configuration — not in `app/config/`), fully fictional:

```json
{
  "id": "1-invoice",
  "title": {"en": "The Invoice", "fr": "La facture"},
  "time": "21:30",
  "alert": {...},
  "rulezy": {"intro": {...}, "hints": [{...}, {...}, {...}], "lines": {...}},
  "tools": {
    "logs": [{"host": "WS-042", "source": "sysmon", "event": {...}}],
    "processes": [...],
    "files": [{"name": "invoice_0923.docm", "strings": [...], "hex": "...", "sha256": "..."}],
    "mail": [...]
  },
  "evidence": {"required": ["file:invoice_0923.docm", "string:AutoOpen"], "bonus": [...]},
  "rule": {"format": "yara", "mode": "blanks", "template": "rule invoice { strings: $a = \"____\" condition: ____ }"},
  "corpus": {
    "malicious": [{"type": "string", "value": "..."}],
    "benign": [{"type": "string", "value": "..."}],
    "hidden_variants": [...]
  }
}
```

- Samples are **synthetic** (no real malware in the repository): strings and structures that look like the real
  thing for a YARA/Sigma rule, but are harmless text.
- A validation script checks each case: the reference rule catches all malicious samples and hidden variants and
  no benign one — runs in the test suite, so a broken case can't ship.

## 9. Leaderboard (visible to players)

On the game's own page (hidden like the rest), reachable from the main menu:

- **Global**: total score over the 8 cases, best night first; ties broken by fewer hints, then earlier date.
- **Per case**: best score, fastest close, and the **best rule** (shortest rule with 3 stars) — shown read-only
  in a `CodeViewer`, a nice way to learn from others.
- Logged-in players appear with their username; anonymous players as "Anonymous analyst #a1b2".
- Player opt-out: a toggle to appear as anonymous even when logged in.
- **Admin view**: same panel as Starfield (every player, every case, every rule attempt, hints used, failed
  deploys) — reuse `app/features/starfield` patterns.

Scores are trustworthy here: the client sends rules and evidence, the server tests and scores.

## 10. Two new badges (secret, like Starfield's)

| Key | Name | Unlock | Description (shown) |
|-----|------|--------|---------------------|
| `night_shift` | **Night Shift** | Close the first case | *"Someone has to watch the logs at 3 a.m. You took the chair."* |
| `glasshouse_broken` | **Glasshouse Broken** | Finish the night with 3 stars on every case | *"They read every alert you raised. They never saw your last rule coming."* |

Both use the existing secret-badge mechanism (`'secret': True` in `app/features/account/badges.py`): not in the
public catalog, shown on a profile only once unlocked, teased in "Hidden badges" on How to earn points.
Icons: `fa-mug-hot` (purple) and `fa-glasses` / `fa-house-crack` (gold). A night-shift Rulezy pose would fit both.

## 11. Technical architecture

Follows `docs/refactor/00_conventions.md`.

```
app/features/nightshift/
    nightshift.py            # routes: page, start/resume, test rule, deploy, leaderboard, admin
    nightshift_core.py       # case loading, evidence check, scoring, progress
    cases/*.json             # the 8 cases + prologue/epilogue text
app/core/db_class/nightshift.py
    NightshiftProgress       # user_id / player_id, current case, per-case state (pinned evidence, hints used)
    NightshiftAttempt        # one row per rule test/deploy: case, rule text, TP/FP/FN, score — admin + best rule
app/templates/nightshift/nightshift.html
app/static/js/nightshift/    # excluded from the import map (HIDDEN_DIRS)
app/static/css/nightshift/
```

- **Rule testing** reuses the rule tester drivers directly (`get_driver('yara')`, `get_driver('sigma')`), run in
  the request with a time limit — samples are small. Rules are size-limited (e.g. 4 KB) and rate-limited per
  player.
- **No real malware**, no file upload, no network access from rules: the corpus is fixed text per case.
- **Sound and pixel art**: canvas for the room, HTML windows for the tools (accessible, copyable text).
- **Save**: logged-in → `NightshiftProgress` row; anonymous → `localStorage`, migrated to the account if the player
  logs in later.
- **Tests**: case validation (reference rules), scoring unit tests, access tests (admin routes), and a check that
  no page outside `/nightshift` mentions it.

## 12. Milestones

1. **Vertical slice** — case 1 only: room, Rulezy intro, log viewer + file browser, fill-the-blanks YARA, test,
   deploy, score. Validates the loop and the engine integration.
2. **Act 1** — cases 1–3, evidence board, hints, Sigma, progress saving.
3. **Act 2** — cases 4–6, building-blocks editor, hidden variants, leaderboard.
4. **Act 3** — cases 7–8, the twist, the epilogue, free editor, badges, admin panel.
5. **Polish** — art, sound, FR translation, trail from Starfield.

## 13. Open questions

- Formats: YARA + Sigma only, or a Suricata case too (network-flavoured case 3)?
- Should a finished night be replayable with a different seed (shuffled samples, renamed hosts) for the
  leaderboard, or one fixed night?
- Art: drawn by hand / sourced (CC0 pixel packs), or generated?
- Rulezy night poses: new images needed — who draws them?
- Real-time element: only in case 8, or an optional "hard mode" for the whole night?
