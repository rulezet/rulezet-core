# Suricata Rework + Sagan Format — Design Plan

> Status: **proposed, not started.** Written in response to
> [rulezet/rulezet-core#61](https://github.com/rulezet/rulezet-core/issues/61)
> (reported by @regit / Eric Leblond, Stamus Networks), which the maintainer
> already acknowledged and committed to fixing in a comment on that issue.
> Every number and code reference below was verified directly against this
> dev instance's own database and the current codebase, not just copied from
> the issue.

## Context

@regit validated 33,496 rulezet-only Suricata-tagged rules (rules not also
present in Emerging Threats Open) with `suricata-language-server` and found
**7,207 fail real Suricata parsing (≈21.5%)**. The breakdown:

| Count | Root cause |
|------:|------------|
| 6,686 | `protocol "any"` used — not a valid Suricata protocol |
| 412   | `unknown rule keyword 'parse_src_ip'` |
| 44    | Duplicate `sid`+`rev` / SID collisions across authors |
| 22    | `protocol "syslog"` used — not a valid Suricata protocol |
| 29    | sticky-buffer keyword (`http_uri`, etc.) used with no preceding `content:` |
| 3     | references a file (`fileextraction-chksum.list`) not part of the ruleset |
| 2     | `dst-ip` keyword — that's Snort, not Suricata |
| 2     | fake `altemplate` protocol (Suricata's own dev/test rules) |
| 2     | non-existent decode event |
| ~5    | misc (bad quoting, undefined variable, `isdataat` out of range, …) |

**~7,120 of the 7,207 failures (99%) are actually [Sagan](https://github.com/quadrantsec/sagan-rules)
rules mistagged as Suricata** — Sagan and Suricata share the same
Snort-descended header/option grammar and the same `.rules` file extension,
but Sagan targets log lines, not packets: it allows protocol keywords
Suricata doesn't (`any`, `syslog`) and has its own option vocabulary
(`program:`, `meta_content:`, `parse_src_ip:`, `parse_dst_ip:`, `parse_port`,
`bro-intel:`, `after:`, `normalize`, `flexbits:`).

**Confirmed independently on this instance's own database** (not just
rulezet.org's): 86,231 active rules tagged `format='suricata'`, of which
**7,119 match the same Sagan fingerprint** (`alert any`/`alert syslog` header,
or a `program:` option) — a near-exact match to the issue's 7,120, so the
same root cause and the same fix apply here directly.

### Root cause, precisely

`SuricataRule.validate()` (`app/features/rule/rule_format/available_format/suricata_format.py`)
only calls `suricataparser.parse_rules()` — a **grammar-only** Python parser.
It happily accepts `alert any $EXTERNAL_NET any -> $HOME_NET any (...)` as a
structurally well-formed rule, because it has no notion of which protocol
names or option keywords are actually real in Suricata — that knowledge only
lives inside the real Suricata engine (or `suricata-language-server`, which
wraps it). Nothing in this codebase currently shells out to either.

`SuricataRule` also has **no `detect()` method at all**. `detect()` is not
part of the `RuleType` ABC — it's a duck-typed convention (`hasattr(ri,
'detect')`) two import pipelines already use to disambiguate formats that
share a file extension, exactly the situation Sigma/ATR/Splunk are already
in for `.yml`/`.yaml` (see `sigma_format.py`'s `detect()` and its docstring):

- `main_format.py`'s `extract_rule_from_repo()` (direct repo import)
- `rule_from_github/import_rule/session_class.py`'s worker (interactive
  GitHub-import wizard)

Both do: if more than one registered format's `get_rule_files()` claims a
given filename, call every candidate's `detect()` on a content sample and
pick the first that returns `True`, else fall back to the first candidate
arbitrarily. Since Suricata is currently the **only** format claiming
`.rule`/`.rules`, every such file is unconditionally Suricata today — there
is nothing to disambiguate against yet. Adding Sagan without giving **both**
formats a correct, mutually-exclusive `detect()` would just make the
tie-break a coin flip instead of fixing anything.

## 1. Add `sagan` as a first-class format

New `app/features/rule/rule_format/available_format/sagan_format.py`, a
`RuleType` subclass — auto-discovered by `load_all_rule_formats()`'s
`pkgutil` scan, no registry file to edit (same as every other format,
confirmed via `rule_type_abstract.py`'s `load_all_rule_formats()`).

- `format` → `"sagan"`, `get_class()` → `"SaganRule"`.
- **`validate(content)`**: reuse `suricataparser.parse_rules()` for grammar
  (Sagan's header/option shape is compatible with it) — Sagan doesn't need a
  keyword *allowlist* the way Suricata will (§2), since nothing currently
  rejects unknown option names at the grammar level; only the **protocol**
  needs checking, and Sagan's accepted set is Suricata's normal protocols
  **plus** `any` and `syslog` (a superset, not a swap — some real Sagan
  rules do use `tcp`/`udp` too).
- **`detect(content)`**: mirror image of Suricata's new one (§2) — return
  `True` when the sample shows Sagan-specific evidence: protocol token
  `any`/`syslog` right after the action keyword, or any option name in the
  Sagan-only set above. Modeled on `sigma_format.py`'s `detect()`.
- **`parse_metadata()`**: same `msg`/`sid`/`rev` extraction shape as
  Suricata's — literally the same regexes, since Sagan's `msg:`/`sid:`/
  `rev:` syntax is identical. Worth factoring the shared bit into one small
  helper both formats import (e.g. `_snort_family_common.py` with
  `extract_msg_sid_rev(content)`) rather than copy-pasting it, since the two
  formats will otherwise drift out of sync silently.
- **`get_rule_files()` / `extract_rules_from_file()` / `get_rule_files_update()`
  / `find_rule_in_repo()`**: same approach as `SuricataRule`'s (same
  extensions, same `suricataparser`-based extraction — it parses Sagan's
  grammar fine, it just doesn't validate it semantically).
- **Corpus identifier (SID uniqueness)**: add `'sagan': 'Sagan SID'` to
  `_CORPUS_IDENTIFIER_LABEL` and a `'sagan'` branch to
  `_extract_corpus_identifier()` in `rule_core.py` — same `\bsid\s*:\s*(\d+)`
  regex as Suricata's. This gives Sagan its own SID-collision protection
  (`check_identifier_uniqueness()`), scoped separately from Suricata's SID
  space by construction (the uniqueness check filters `Rule.format == fmt`).
  **This must ship before §3's reclassification job runs** — see the
  ordering note there.
- `init_db.py`: seed `{"name": "sagan", "can_be_execute": False}` into the
  `formats` list, same convention as the existing `suricata`/`kunai` entries.
- Skip for this first pass (matching the precedent already set when Kunai
  was added): a `rule_tester` driver and `documentation_signals()`. Neither
  is needed to fix the mistagging problem; both can follow later once
  Sagan's real-world shape on this instance is confirmed.

## 2. Give Suricata a real `detect()` + tighten `validate()`

- **`detect(content)`** (new): the inverse of Sagan's — return `False`
  (i.e. "not Suricata") when the sample shows Sagan-only evidence (protocol
  `any`/`syslog`, or a Sagan-only keyword). This is what makes the
  `len(candidates) > 1` disambiguation in both import pipelines (§ Context)
  actually pick correctly once two formats claim `.rules`.
- **Tighten `validate()` itself** — `detect()` only ever runs when a file's
  extension is ambiguous between two *registered* formats. A rule submitted
  directly (paste form, private API) or re-validated during a GitHub sync
  check goes straight through `validate()` and never calls `detect()` at
  all, so the real fix has to live in `validate()`, not just in the
  disambiguator. After `suricataparser`'s grammar parse succeeds, add:
  - **Protocol allowlist**: reject when the header's protocol token isn't
    one of Suricata's real values (`tcp`, `udp`, `icmp`, `icmpv4`, `icmpv6`,
    `ip`, `ip4`, `ip6`, plus the app-layer protocols — `http`, `http2`,
    `tls`, `ssl`, `dns`, `ftp`, `ssh`, `smtp`, `imap`, `smb`, `dcerpc`,
    `modbus`, `dnp3`, `enip`, `nfs`, `krb5`, `ntp`, `dhcp`, `rfb`, `rdp`,
    `snmp`, `tftp`, `sip`, `mqtt`, `quic`, …). **Pull the canonical list from
    Suricata's own documentation/source at implementation time** — don't
    hand-type it from memory or from just the issue's examples, or a
    legitimate rule using a real-but-obscure protocol will start failing.
  - **Sagan-only keyword rejection**: reject when any option name is in the
    Sagan-only set (`program`, `meta_content`, `meta_nocase`,
    `parse_src_ip`, `parse_dst_ip`, `parse_port`, `bro-intel`, `after`,
    `normalize`, `flexbits`).
  - This alone closes failure categories #1 and #2 from the table above —
    **6,686 + 22 + 412 = 7,120 rules, 98.8% of all reported failures** —
    with zero new external dependencies.
- **Smaller, separable follow-up** (own PR, doesn't block Sagan): the 29
  "sticky-buffer keyword with no preceding `content:`" failures.
  `suricataparser` already exposes `rule.options` in declaration order, so
  this is a linear scan — flag when a buffer-modifier keyword (`http_uri`,
  `http_raw_uri`, `http_header`, `http_method`, etc.) appears with no
  `content:` earlier in the same rule's option list.
- **Explicitly out of scope for this plan** (flag for a decision, don't
  quietly build it): the issue's suggestion #1 — running real
  `suricata-language-server` (or plain `suricata -T`) validation on every
  upload. That would additionally catch the remaining ~7 rules (bad file
  paths, decode-event names, `isdataat` range) but means depending on an
  external Suricata installation in every deployment, subprocess execution
  on the upload/import path, and a real performance evaluation for bulk
  imports (30k+ rule batches). No part of this app currently shells out to a
  real engine for any format — even the Rule Tester's own "Suricata driver"
  (`app/features/rule_tester/drivers/suricata_driver.py`) is pure regex
  static analysis, not a real engine run. Recommend treating a real
  engine-backed validator as a separate, opt-in instance setting (e.g. "path
  to a local `suricata` binary — enables deep validation when set") rather
  than a hard requirement folded into this fix.

## 3. Retroactive reclassification of the ~7,119 already-mistagged rules

These are already-imported `Rule` rows with `format='suricata'` that need to
become `format='sagan'` — a one-time data migration, not a code fix.

- New function in `rule_core.py`, modeled directly on the existing
  `replace_rule_format()` (same ORM-loop-and-commit shape), but filtered by
  content fingerprint instead of a blanket format swap:
  `reclassify_mistagged_suricata_rules(dry_run=False)` — matches active
  `format='suricata'` rules whose content shows the Sagan fingerprint
  (protocol `any`/`syslog`, or a Sagan-only keyword — same detection logic
  §1/§2 use, factored so this function calls it rather than re-deriving its
  own regex), sets `rule.format = 'sagan'` through the ORM.
- **Must run *after* §1's `_extract_corpus_identifier` change ships.**
  `Rule.format`'s SQLAlchemy `'set'` event listener
  (`app/core/db_class/db.py`, `_rule_format_set`) recomputes
  `corpus_identifier` via `compute_rule_corpus_identifier(new_format,
  content)` the moment `.format` is assigned. Today that falls into
  `_extract_corpus_identifier`'s default `None` branch for an unrecognized
  format — reclassifying through the ORM *before* `'sagan'` is a known
  branch would silently null out `corpus_identifier` on every one of the
  ~7,100 rows, breaking their SID-collision protection.
- Run as a background job (`register_handler('reclassify_suricata_to_sagan')`,
  same `create_job`/`log_job`/progress pattern used everywhere else in this
  codebase) given the volume — expose it from a one-time admin trigger (a
  button on the Manage Rule Formats admin page, or a `manage.py` subcommand;
  either is fine). Support a **dry-run/count-only mode first** — this is a
  one-way bulk change to 7k+ rows, worth a preview before committing to it.
- Non-destructive otherwise: history, votes, favorites, tags, and bundle
  membership are untouched — only `format` (and the now-correctly-scoped
  `corpus_identifier`) changes.

## 4. SID collision cleanup (issue suggestion #3)

- `check_identifier_uniqueness()` (`rule_core.py`) **already exists and
  already blocks new Suricata submissions from colliding** — confirmed in
  code, this is not a gap. The issue's finding is about rows that predate
  that guard being added.
- **Verified on this instance**: 69 duplicate-SID groups / 76 extra rows
  among currently-active Suricata rules — small enough to review by hand,
  not a systemic backlog.
- Recommend a small **read-only admin report** (SID → list of colliding
  rule ids/titles/sources), not an automatic delete — several collisions
  look like independent authors all reusing an obvious "example/dev" SID
  block (`1000001`–`1000004`, claimed by DCRat/Mirai SORA/Remcos/KARSTORAT/
  test rules per the issue), so a human should pick which one keeps the SID
  rather than an algorithm guessing.
- **Do this after §3**, not before — some of today's collisions are a
  Suricata rule and a soon-to-be-Sagan rule sharing a SID placeholder that
  stop colliding for free once the Sagan one moves to its own corpus.
  Re-run the report post-reclassification before spending review time on it.

## 5. Snort mistagging (2 rules) — not a new format

Only 2 known rules (KarstoRat `sid:1000012`/`1000013`) use a genuinely
Snort-only construct (`dst-ip:<addr>;` as an option, where Suricata
expresses the destination address positionally in the rule header instead).
Building and maintaining a full new `RuleType` for 2 rules isn't
proportionate. Recommend a manual fix via the existing bad-rule edit flow
(drop the `dst-ip:` option, move the address into the header) rather than a
new format — revisit only if more Snort-only rules turn up later.

## Rollout order

1. Ship §1 (SaganRule + corpus-identifier registration + init_db seed) and
   §2 (Suricata's new `detect()` + tightened `validate()`) **together** —
   this stops new imports from being mistagged immediately, in both
   directions.
2. Run §3's reclassification job (dry-run first) once step 1 is deployed.
3. Re-run §4's SID collision report after step 2, review the residual list.
4. §5 (the 2 Snort rules) whenever convenient — independent of the rest.

## Verification

- New unit tests for `SaganRule` (`validate`/`detect`/`parse_metadata`)
  against the two example rules quoted in the issue.
- New tests asserting `SuricataRule.detect()` rejects both of those same
  examples, and that `validate()` rejects a `protocol any` / `program:`
  rule even when submitted directly (bypassing the ambiguous-extension
  disambiguation path entirely).
- **Regression test**: a real, currently-valid Suricata rule using a less
  common but legitimate protocol/keyword still validates after the
  tightening — an allowlist is exactly the kind of change that can
  false-reject a rule the allowlist just didn't cover. Build the protocol
  list from Suricata's own docs, then run it against a sample of this
  instance's existing passing Suricata corpus before shipping, and fix any
  new false rejections it introduces.
- Dry-run §3's reclassification job against this dev instance's own
  7,119-row candidate set and spot-check ~20 by hand before running for
  real anywhere.

## Files touched

- `app/features/rule/rule_format/available_format/sagan_format.py` (new)
- `app/features/rule/rule_format/available_format/suricata_format.py` —
  `detect()` (new), `validate()` protocol/keyword tightening
- optional: `_snort_family_common.py` (new, shared msg/sid/rev helper)
- `app/features/rule/rule_core.py` — `_CORPUS_IDENTIFIER_LABEL` +
  `_extract_corpus_identifier` gain a `'sagan'` branch;
  `reclassify_mistagged_suricata_rules()` (new); SID-collision report query
- `app/core/utils/init_db.py` — seed the `sagan` `FormatRule` row
- `app/features/jobs/job_handlers.py` — `reclassify_suricata_to_sagan`
  background-job handler (new)
- new tests under `tests/rules/` for both formats
