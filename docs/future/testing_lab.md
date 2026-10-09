# Rulezet Lab — testing every rule against reference data, and scoring it

> Status: **idea**. Builds on what exists: the Rule Tester (one rule against
> one user-supplied input, drivers for Suricata, YARA, Sigma, Zeek, Wazuh, CRS,
> NSE, NOVA, ATR — `app/features/rule_tester/drivers/`), deep validation
> (`rule_format/deep_validate.py`) and the quality score
> (`rule/rule_quality/quality_score_core.py`).

> **The current Rule Tester will be deprecated.** It only tests one rule
> against one input the user brings, by hand, and is already suspended in
> the rule navigation. The Lab replaces it with something far more complete:
> reference corpora, automated campaigns over whole bundles, per-version
> results and a score. Its format drivers are the part worth keeping — they
> become the Lab's execution layer; its pages, tables (`rule_test`,
> `rule_test_result`) and API are to be retired once the Lab ships.

The connectors ([README](README.md)) bring rules to real tools. The Lab is the
step before: **prove what a rule does** in a controlled environment — replay
traffic, scan known malware and known-clean files, run attack logs — and turn
the results into a score everyone can read.

## The idea

For each format, an environment that reproduces where the rule would run, and
two reference corpora:

- **malicious / attack data** — what the rule is supposed to catch;
- **benign data** — what it must *not* catch (false positives).

Every rule (or every rule of a bundle) is run against them by a background
job; the results are stored per rule and per version, shown on the rule page
and summarised as a **Lab score**.

```
 rule v3 ──▶ lab job (format driver, isolated worker)
               ├─ malicious corpus  → matches?  → detection
               ├─ benign corpus     → matches?  → false positives
               └─ timing / profiling            → cost
            ──▶ results per rule + version ──▶ Lab score ──▶ quality score
```

## Per format: environment and reference data

| Format | How to run it in the Lab | Malicious / attack data | Benign data |
|---|---|---|---|
| Suricata | `suricata -r file.pcap` (offline pcap replay), rule profiling | Malware-Traffic-Analysis.net pcaps, Stratosphere IPS (CTU-13), CIC-IDS2017 | Baseline captures of normal traffic (web browsing, updates, DNS…) |
| Zeek | `zeek -r file.pcap` with the script | Same pcaps as Suricata | Same baseline captures |
| YARA | `yara` over a sample directory, scan time per rule | MalwareBazaar (abuse.ch) samples by family, theZoo | Clean OS / software installs (Windows, Linux system binaries, popular apps) |
| Sigma | Converted and run on logs (e.g. Chainsaw / Hayabusa / Zircolite on EVTX) | EVTX-ATTACK-SAMPLES, Security-Datasets (OTRF, ex-Mordor), Splunk attack_data | Normal workstation / server event logs |
| Wazuh | `wazuh-logtest` with sample log lines | Attack log samples per decoder | Normal system logs |
| CRS | ModSecurity / Coraza with `go-ftw` | CRS regression tests, OWASP attack payloads | Normal web application traffic |
| NSE | Nmap against lab targets | Vulnerable containers (e.g. vulhub) | Patched versions of the same services |
| Others (Kunai, NOVA, ATR, Plum…) | Through their Rule Tester driver | To define per format | To define per format |

Attack data can also be **generated**: Atomic Red Team in a sandbox VM
produces the logs / traffic of a known ATT&CK technique — matching rules
mapped to the same technique gives a direct "does it detect T1059.001?" check.

## The score

Per rule and per version, only from data **relevant to the rule** (see
"pitfalls"):

- **Detection** — share of the relevant malicious samples it matches.
- **False positives** — matches on the benign corpus (the most important
  signal: a noisy rule is worse than a narrow one).
- **Cost** — time / CPU per rule (Suricata rule profiling, YARA scan time).
- **Robustness** — loads on the supported engine versions (Suricata 7 / 8…),
  no warnings.

Shown as a Lab badge on the rule (e.g. "Lab: detects 12/12 samples of its
family, 0 false positives on 40 GB of clean data, fast") and added to the
quality score breakdown as a separate, explained component. Re-run
automatically when a rule gets a new version → **regression detection**
("v4 stopped matching 3 samples v3 matched").

## Pitfalls to design around

- **No match ≠ bad rule.** A rule targeting one malware family will match
  nothing in an unrelated corpus. Samples must be labelled (family, CVE,
  ATT&CK technique) and a rule tested only against what it claims to detect —
  through its tags, CVEs and ATT&CK mapping. Otherwise the result is
  "untested", never "0 %".
- **Malware handling.** Samples never leave the Lab and are never served by
  Rulezet: only hashes and results are shown. Isolated workers, no network,
  read-only corpora, clear legal / licensing check per dataset.
- **Cost.** Corpora are large and scans are CPU-heavy: a dedicated Lab worker
  (separate machine or container), opt-in per instance, scheduled campaigns,
  incremental runs (only new / changed rules).
- **Gaming.** A rule written to match the corpus exactly (e.g. a hash) would
  score well — weight false positives and generality, keep part of the corpus
  private.
- **Freshness.** Corpora age; record when and against which corpus version a
  score was computed.

## Steps

1. **Corpora registry** — admin page to declare datasets (path, format, type:
   malicious / benign, labels), stored on the Lab worker.
2. **Lab job** — a `lab_run` background job: a rule or a bundle × a corpus,
   through the existing Rule Tester drivers, results in a new table
   (rule, version, corpus, matches, false positives, timing).
3. **Results on the rule page** — a Lab section next to Tests / AI Analysis;
   on a bundle, a Lab column in the health tab.
4. **Lab score** — computed from the results, added to the quality score
   breakdown, re-run on new versions.
5. **Community corpora** — users submit labelled samples (hash + label, the
   file stays private to the Lab) to grow the corpora.

First format to build it for: **Suricata** (pcap replay is simple, offline
and safe — no malware execution) or **YARA** (the most requested, but needs
the malware-handling safeguards first).
