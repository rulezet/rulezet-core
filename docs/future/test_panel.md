# Testing rules on samples — one system for every format

> Status: **in progress**. The execution part is its own project,
> [rulezet-tester](https://github.com/rulezet/rulezet-tester) (submodule `app/modules/rulezet-tester`):
> contract, YARA driver, bubblewrap sandbox, sample store, HTTP API, CLI — its
> [design](https://github.com/rulezet/rulezet-tester/blob/main/docs/design.md) is the reference.
> This page keeps the Rulezet view. Joins three plans that were written separately:
> the editor's test panel ([rulezet_editor.md](./rulezet_editor.md) step 8,
> [yara_editor.md](./yara_editor.md) §3.5), the **Lab** ([testing_lab.md](./testing_lab.md):
> reference corpora, score) and the "Test on samples" step of the YARA editor's Create job
> (`app/features/editor/editor_jobs.py`, today `skipped`).
> First format: **YARA**. The design must not change when Suricata, Sigma, Zeek… come next.

## 1. What we want

A **Test** button in the editor. It opens a test view (panel or page); it can be switched on by
default so it runs on Create. One click and, **live**, sample after sample:

- does the rule fire on the **malicious** samples it claims to detect (family, campaign, CVE,
  ATT&CK technique)?
- does it stay silent on the **benign** samples (false positives)?
- how long does it take (cost)?

Grouped by set: *False positives 0 / 250 · Emotet 12 / 15 · Campaign X 3 / 8*. A click on a hit
shows what matched and jumps to that part of the rule in the editor.

## 2. The key idea: the same system for every format, only the "driver" changes

Whatever the format, testing is always the same sentence:

> **run a rule on a sample, in a safe place, and say whether it fired and where.**

What changes per format is only *what a sample is* and *what runs the rule*:

| Format | A sample is | The engine | "Where" in a hit |
|---|---|---|---|
| YARA | a file (bytes) | yara-python / yara-x | string id + offset in the file |
| Suricata | a pcap | `suricata -r` | packet number / flow, alert sid |
| Zeek | a pcap | `zeek -r` + the script | notice / log line |
| Sigma | log events (EVTX, JSON) | converted query (Chainsaw / Zircolite…) | event number + matched fields |
| Wazuh | log lines | `wazuh-logtest` | line number, decoder, rule id |
| CRS | HTTP requests | ModSecurity / Coraza | request number, matched variable |
| NSE | a target (container) | nmap | host / port |

So we build **one pipeline** with **one plug per format** (the driver), the same way the editor
has one core with one *language pack* per format. Rulezet already has these drivers for one rule
× one input (`app/features/rule_tester/drivers/`: YARA, Suricata, Sigma, Zeek, Wazuh, CRS, NSE,
NOVA, ATR): they become the execution layer.

## 3. Who does what — three projects

> Decided: the runner is **rulezet-tester**, a separate project, so the editor, Rulezet, a CI
> pipeline or a MISP module can all use it without importing each other. rulezet-editor mounts
> its HTTP API on `/editor-api/test` and shows the Test panel; Rulezet only adds persistence
> (sets and results in the database, a shared run registry, its job worker, permissions).


```
┌──────────────────── rulezet-editor (submodule, generic) ────────────────────┐
│  Test panel UI (same for every format)                                      │
│  pack.test = { sample kind, how to show a hit, how to map a hit to the rule}│
│  host.startTest() / host.testState()    ── no execution, no samples here ── │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ HTTP (same protocol for every format)
┌──────────────────────────────────▼──────────────────────────────────────────┐
│  Rulezet — the Lab (app/features/lab/)                                      │
│  sample sets & labels (metadata only: hash, family, campaign, type, TLP)    │
│  which sets are relevant to this rule · test jobs · results · score         │
│  ── never reads a sample's bytes ──                                         │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ job queue (rule text + sample ids)
┌──────────────────────────────────▼──────────────────────────────────────────┐
│  Lab runner — isolated worker (separate machine or sandbox)                 │
│  holds the samples · one driver per format · no network · limits            │
│  returns verdicts + hits, never bytes                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Piece | Knows | Never |
|---|---|---|
| **rulezet-editor** | how to *show* a test for a format | runs a rule, touches a sample |
| **Rulezet Lab** | samples' metadata, labels, which sets to use, jobs, results, score | reads sample bytes, runs an engine |
| **rulezet-tester** (runner) | sample bytes, engines, sandbox, run states, outcomes | decides who may test, stores in a database |

This is exactly the editor's rule — *a pack never calls a server, an adapter never parses a
rule* — extended to testing. Each piece can change without the others:

- a new format = a pack `test` profile (editor) + a driver (runner) + sample sets (admin);
- moving the runner to another machine changes nothing in the editor or the Lab pages;
- outside Rulezet, the editor can talk to any backend that speaks the same protocol (standalone
  server with a local folder of samples, a SOC's own lab…).

## 4. The common contract

### 4.1 Results (same shape for every format)

```json
{
  "run": "uuid", "status": "running", "rule_version": 3,
  "sets": [
    { "id": 1, "name": "Goodware — Linux binaries", "kind": "benign", "total": 250, "done": 120, "hits": 0 },
    { "id": 7, "name": "Emotet (2025)", "kind": "malicious", "family": "emotet", "total": 15, "done": 15, "hits": 12 }
  ],
  "samples": [
    {
      "id": 4211, "set": 7, "label": "emotet loader", "sha256": "…", "size": 284672,
      "expected": "match",
      "verdict": "match",
      "time_ms": 14,
      "hits": [
        { "rule": "Emotet_Loader", "item": "$api", "where": { "kind": "offset", "offset": 51200, "length": 18 } }
      ]
    }
  ]
}
```

- `expected` comes from the labels: `match` on a malicious set relevant to the rule, `no_match` on
  a benign set, `unknown` otherwise.
- `verdict` is one closed list for every format: `pending`, `match`, `no_match`, `timeout`,
  `error`, `skipped`.
- The **outcome** is derived, never stored by the driver: `match` + `expected: match` = detected;
  `match` + `no_match` = **false positive**; `no_match` + `match` = missed.
- Only `where` depends on the format (`offset`, `packet`, `event`, `line`, `request`…). The pack
  tells the editor how to display it and how to map `item` back to the rule (YARA: `$api` → its
  line in `strings:`; Suricata: the `content` keyword; Sigma: the selection field).

### 4.2 Driver (runner side, Python)

Extends today's `BaseTesterDriver`, so the existing drivers keep working:

```python
class LabDriver(BaseTesterDriver):
    sample_kind = 'file'            # file | pcap | events | log_lines | http | target

    def prepare(self, rule_text) -> Prepared | Error:    # compile once (YARA: yara.compile)
    def run(self, prepared, sample_path, limits) -> Verdict:   # one sample, normalised hits
```

`prepare` once per run, `run` once per sample: compiling a YARA rule 500 times would be slow.

### 4.3 Language pack (editor side, JS)

```js
test: {
  sampleKind: 'file',
  hitLabel(hit)  { return `${hit.item} at 0x${hit.where.offset.toString(16)}`; },
  locate(model, hit) { /* range of $api in the rule, for "go to" */ },
}
```

No `test` field → no Test button for that format, as for every other pack feature.

### 4.4 Host adapter (editor → Rulezet)

```
POST /editor-api/test              { format, rules: [{ name, text }], sets?: [ids] }   -> 202 { run }
GET  /editor-api/test/<run>                                                            -> results (4.1)
GET  /editor-api/test/sets?format=                                                     -> sets the user may use
```

Same polling as the Create job today. Server-sent events can replace polling later without
changing the result shape.

## 5. Which samples for which rule (relevance)

Testing a ransomware rule on a phishing-kit set says nothing. As in the Lab plan: **no match is
not a failure unless the sample was expected to match**.

- Every sample set has labels: `kind` (malicious / benign / synthetic), family, campaign / actor
  (MISP galaxies), CVE, ATT&CK techniques, file type / platform.
- A rule is matched to sets through its own data: tags (`malware:`…), CVEs, ATT&CK mapping, YARA
  `meta` (family, `malware_family`…). The user can add or remove sets in the test view.
- **Benign sets always run** (false positives concern every rule).
- Malicious sets with no link to the rule: run only if the user asks; their results are shown as
  "extra matches", never counted as missed.

## 6. Security — non-negotiable

YARA never *executes* a sample, but the risks are real: storing and leaking live malware, hostile
input for the engine (a crafted file or rule hitting a parser bug), and denial of service with a
slow rule over hundreds of files. The same rules apply to every format (a pcap or an EVTX is
hostile input too).

**Isolation**

- The web application never opens a sample. Only the runner does.
- Runner on a **separate machine or VM** as soon as real malware is stored; until then (synthetic
  and benign sets only) a sandbox on the same host is acceptable.
- Every run in a throw-away sandbox (nsjail, bubblewrap or a container): **no network**, read-only
  root, samples mounted `ro,noexec,nosuid,nodev`, non-root user, no capabilities, seccomp, cgroup
  limits (CPU, memory, pids), killed at the time limit.
- The rule is compiled **inside** the sandbox, not in Flask.

**Rule limits** (checked before queueing, again in the runner)

- size cap (512 KB, like `/api/rule/public/validate`), max rules per run, no `include` (YARA),
  no `lua` / file output (Suricata), no external lookups;
- per-sample timeout (YARA `timeout=` 2–5 s) and per-run timeout; a rule that times out on several
  samples stops the run ("too slow").

**Samples**

- Stored on the runner only, outside any web root, named by sha256, no extension.
- **Never downloadable** from Rulezet. Results carry hashes, offsets and a few bytes of context at
  most. If a download is ever offered: admins, password-protected zip (`infected`), logged.
- Added by admins only (or later: users submit a hash + label, an admin fetches the file).
  Hash checked, duplicates refused, source / licence / TLP recorded.
- Excluded from Rulezet's backups (separate encrypted backup if needed); the folder excluded from
  the host antivirus on purpose — documented.

**Access**

- Logged-in users only; rate limit per user, max concurrent runs, a queue; TLP of a set decides
  who may see its labels.
- Every run in the activity log (`rule.test`), and results kept with the rule version tested.

## 7. YARA first — how it looks

1. **Test** button in the editor toolbar (and Ctrl+T); the panel opens under or beside the editor.
2. Sets proposed from the rule (§5), benign sets always ticked; **Run**.
3. Each sample row turns live: ⏳ → ✅ detected · ⚪ no match · ⚠ false positive · ⏱ timeout.
   Counters per set at the top.
4. Click a hit → matched strings with offsets; click a string → the editor jumps to it.
5. "Test on Create" switch (setting `app/config/lab.test_on_create.json`, default on): the
   Create job's "Test on samples" step runs the same test; false positives are a **warning**,
   not a blocker (decision to confirm, §9).
6. Later: result kept with the rule version → badge "tested on N samples, 0 FP" and the Lab
   score in the quality score.

First corpora, in this order (no risk first):

| Set | Content |
|---|---|
| Synthetic | small crafted files per test case (EICAR, strings in UTF-16, PE headers…) |
| Benign | Linux system binaries, open-source installers, clean Office / PDF documents (licences checked) |
| Malicious | by family / campaign: MalwareBazaar (abuse.ch), CIRCL / MISP internal — once the isolated runner exists |

## 8. Steps

| Step | Content | Where |
|---|---|---|
| 1 | Data model: `SampleSet`, `Sample` (metadata only), `LabRun`, `LabResult`; admin page for sets (no download) | Rulezet `features/lab/` |
| 2 | Runner + sandbox + YARA `LabDriver`; protocol job → results; synthetic and benign sets | runner (in Rulezet repo first, own repo when it moves to its own machine) |
| 3 | Generic Test panel + `pack.test` + host methods; YARA profile — **done** | rulezet-editor |
| 4 | Wire into Rulezet: `/editor-api/test*`, the Create job step, "test on Create" setting — **done** (runs in the database, setting `editor.test_on_create`) | Rulezet `features/editor/` |
| 5 | Relevance from tags / CVE / ATT&CK; malicious sets on the isolated machine | Lab |
| 6 | Results per version, badge — **done** (Samples tab of the rule page); Lab score, regressions ("v4 misses 3 samples v3 caught") still to do | Lab |
| 7 | Second format: Suricata (pcap) — only a driver, a pack profile and sets; no core change | all three |

Step 7 is the test of this design: if Suricata needs a change outside its driver, its pack
profile and its sets, the contract (§4) is wrong and must be fixed then.

## 9. Decisions to take

- Runner: same server in a sandbox for the synthetic / benign phase, then a separate machine
  before any real malware? (recommended)
- Who feeds the malicious sets: admins by hand, or an import from MalwareBazaar by tag / family?
- On Create: false positives = warning only, or block above a threshold? → warning by default,
  blocking with `block_on_false_positives` (setting `editor.test_on_create`).
- Results public on the rule page (hashes and counts only), or visible to the author and admins
  first? → public (Samples tab): hashes, labels, offsets and a few bytes per hit only.
- The Rule Tester pages (one rule × one input) retire when the Lab ships (already planned in
  testing_lab.md); its drivers stay.
