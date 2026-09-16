# Integrating `suricata-language-server` — Feasibility Analysis

> Status: **implemented**, per the recommendation below. `SURICATA_BINARY_PATH`
> (`.env`, empty = disabled), `app/features/rule/rule_format/deep_validate.py`,
> a single-rule "Deep validate" button on the rule detail page, and an
> admin-triggered bounded-batch background job (Manage Rule Formats page)
> all exist and were verified end-to-end against this machine's real
> Suricata 8.0.3 + suricata-language-server 2.1.2 — a Sagan-shaped rule
> correctly comes back `severity=1`/`protocol "any" cannot be used...`, a
> valid rule passes clean, ~0.5s per call. Off by default; nothing runs
> unless an admin sets `SURICATA_BINARY_PATH` and separately
> `pip install suricata-language-server`.
>
> Answers the question deferred in
> [`suricata_sagan_rework.md`](./suricata_sagan_rework.md) (§2, "explicitly
> out of scope for this plan") and directly addresses issue #61's
> suggestion #1: *"Run suricata-language-server (or plain Suricata)
> validation on uploads tagged `format: suricata` and reject / re-tag on
> failure. SLS emits per-signature JSON diagnostics so you can report
> exactly which rule failed and why."*
>
> Every claim below was verified against the actual source of
> [StamusNetworks/suricata-language-server](https://github.com/StamusNetworks/suricata-language-server)
> (pinned reading: `main` @ the commit current as of 2026-09-16 —
> `pyproject.toml` version `2.2.0`), not the README summary alone —
> file/function references are given so they can be re-checked against a
> newer version before implementing.

## What the tool actually is

`suricata-language-server` (PyPI: `suricata-language-server`, import name
`suricatals`, GPL-3.0, Python ≥3.7) is an LSP (Language Server Protocol)
implementation for Suricata `.rules` files, built by Stamus Networks. Its
one real architectural idea, stated in its own `CLAUDE.md`: *"the language
server delegates signature validation and keyword discovery to Suricata
itself"* — it is a thin wrapper that shells out to a **real Suricata
binary** (or a Docker container running one) and turns its output into
structured diagnostics. It does not reimplement Suricata's rule grammar or
keyword semantics itself.

Three CLI entry points ship in `pyproject.toml`'s `[project.scripts]`:
- `suricata-language-server` — the LSP server itself, and also the
  `--batch-file` one-shot mode the issue used.
- `suricata-read` — runs a ruleset against a PCAP, emits EVE JSON alerts.
- `suricata-ruleset-analyze` — whole-ruleset quality report (text or
  `--json`), a different tool from what this doc is about.

**No public Python API.** Everything is CLI-only (`argparse`-driven
`main()` in `src/suricatals/__init__.py`); there is nothing importable to
call in-process — any integration means invoking it as a subprocess, the
same way the issue's author did.

## Batch mode, exactly as it behaves

```
suricata-language-server --batch-file <path> [--no-engine-analysis] [--error-on-warning]
```

Verified in `src/suricatals/__init__.py`: this builds a `LangServer(...,
batch_mode=True)`, calls `analyse_file(path, engine_analysis=not
no_engine_analysis)`, then for every diagnostic prints one line of
`json.dumps(diag.to_message())` to stdout. Exit code is `1` if any
diagnostic has `severity == 1` (Error), or also on `severity == 2`
(Warning) when `--error-on-warning` is passed.

**Exact diagnostic JSON shape** (`DiagnosticBuilder.to_message()` in
`signature_parser.py`):
```json
{
  "range": {"start": {"line": 11, "character": 0}, "end": {"line": 11, "character": 87}},
  "message": "protocol \"any\" cannot be used in a signature",
  "source": "Suricata Language Server",
  "severity": 1,
  "content": "alert any $EXTERNAL_NET any -> $HOME_NET any (msg:...)",
  "sid": 6107000
}
```
`severity` is the standard LSP scale: `1`=Error, `2`=Warning,
`3`=Information, `4`=Hint. This is precisely what the issue described
("SID, exact line, severity, and error message") and is a clean,
machine-parseable line-delimited stream — easy to consume from Python.

**A real file on disk is required.** `SuricataFile.load_from_disk()`
(`signature_parser.py`) opens `self.path`, and `check_file()` **re-opens
`self.path` again** to hand its content to the validator. There is a
`load_from_buffer(str)` method too, but it's only reachable through the
LSP server's own live-editor code path, not `--batch-file` — batch mode
always needs the rule content physically written to a file first. For
Rulezet this means: `tempfile.NamedTemporaryFile(suffix='.rules')`,
write, validate, delete — a few extra syscalls, not a real obstacle.

## What actually runs underneath (and why it's slow)

Traced through `signature_validator.py`'s `_analyze_rule_buffer()` and
`suricata_command.py`'s `SuriCmd`:

1. `SuriCmd.prepare()` — `mkdtemp()`, then writes a **complete** generated
   `suricata.yaml` + `reference.config` + `classification.config` into it.
2. `subprocess.run([suricata_binary, "-T", "-v", ...])` — Suricata's own
   config self-test. This is the pass that catches everything the issue
   reported (bad protocol, unknown keyword, bad content quoting, ...).
3. **Only if step 2 passed**, and `engine_analysis` wasn't disabled: a
   *second* subprocess run with `--engine-analysis`, parsed for
   structural/performance hints (MPM info, fast_pattern suggestions) —
   this is additive polish, never what catches a syntax/protocol error,
   since it only runs after `-T` already succeeded.
4. Local mode subprocess-execs a real installed `suricata` binary; Docker
   mode (`--container`) spins a container per call instead
   (`docker.from_env()`, mounts the temp dir at `/tmp/`) — a heavier
   cold-start per call unless something pools containers, which this
   project doesn't do.

Each call is a **full Suricata engine boot** — loading every keyword
parser and protocol registration, not a lightweight parse. Rule count or
complexity barely matters; engine startup dominates.

### The performance number, sourced from the maintainers themselves

`CLAUDE.md`'s own "Multiprocessing Architecture" section states the
workspace-analysis parallel path (`ProcessPoolExecutor`, 4 workers
default) is *"Expected 3-4x speedup for large rulesets (e.g., 100 files in
~2 minutes vs ~8 minutes sequential)"*. That's **~4.8s/file sequential,
~1.2s/file at 4-way parallelism** — a real, maintainer-stated number, not
a guess.

Applied to this instance's own numbers (86,231 rules currently tagged
`suricata`, per `suricata_sagan_rework.md`):
- Sequential: 86,231 × 4.8s ≈ **115 hours**
- 4-way parallel: ≈ **29 hours**

This confirms the earlier design doc's instinct was correct, now with a
citation instead of a guess: **bulk/full-corpus deep validation is not
viable as an automatic step on upload or import.** It's entirely viable,
though, for:
- **A single rule, synchronously** (create/edit page, bad-rule review) —
  2-5 seconds is the same order of magnitude Rulezet's own AI Fixer/
  Generator buttons already ask a user to wait for.
- **A slow, explicitly-triggered, resumable background job** over the
  full corpus — the exact shape of the `audit_suricata_rules` job just
  built for issue #61 (`app/features/jobs/job_handlers.py`), which
  already supports pause/cancel and periodic progress commits.

## A separate, genuinely useful find: the keyword data file

`src/suricatals/data/suricata-keywords.json` — 423 entries, **static,
versioned per Suricata release**, no binary or subprocess needed to read
it:
```json
{"name": "sid", "description": "set rule ID", "app layer": "Unset",
 "features": "supports firewall",
 "documentation": "https://docs.suricata.io/en/suricata-8.0.0/rules/meta.html#sid-signature-id",
 "initial_version": "4.1.5", "last_version": "8.0.0"}
```
This is exactly the *"pull the canonical list from Suricata's own docs at
implementation time"* sourcing `suricata_sagan_rework.md` (§2) already
called for when building `SAGAN_ONLY_KEYWORDS`/`SURICATA_PROTOCOLS` in
`_snort_family_common.py` — except here it's already machine-readable and
versioned, no hand-transcription needed.

**Caveat, checked directly**: this file lists rule **options** (`content`,
`sid`, `flow`, ...), not header **protocol** tokens (`tcp`, `http`, ...).
The protocol list only comes from calling the live binary
(`suricata --list-app-layer-protos`, confirmed in
`suricata_discovery.py`'s `get_app_layer_protos_list()`) — there's no
static file for that half. Still useful, just a one-time/rarely-refreshed
call, not a per-rule one.

**Recommendation**: don't depend on this file live — vendor a copy
(fetched from a **pinned release tag**, not `main`, to avoid supply-chain
surprise) via a manual refresh script, and use it to *validate/refresh*
`SAGAN_ONLY_KEYWORDS` by diff rather than building the allowlist from it
at import time. It's part of a GPL-3.0 codebase, so copying the file in
needs a clear attribution/source comment — Rulezet itself is AGPL-3.0
(confirmed via this repo's own `LICENSE`), and the two are copyleft/
compatible, but the file's provenance should stay visible, not silently
absorbed as if hand-written.

## Syntax highlighting — not directly reusable

`SuricataSemanticTokenParser` (`signature_tokenizer.py`) implements LSP
**semantic tokens**, which only exist inside a live LSP session, tied to a
specific open editor buffer's token positions via JSON-RPC — there is no
portable grammar file shipped (no TextMate `.tmLanguage`, no highlight.js
definition) that could just be dropped into Rulezet's existing
`app/static/js/components/hljs-suricata.js`. Reusing it would mean
running the full LSP protocol as a persistent child process per highlight
request — a much heavier integration than Rulezet's current lightweight
regex-based `hljs-suricata.js` grammar, for a purely cosmetic feature
already covered. **Not recommended.**

## License

SLS is GPL-3.0; Rulezet is AGPL-3.0. Invoking it as a subprocess/CLI tool
(never importing/linking its Python package into the Flask process) is
"mere aggregation," the standard way copyleft CLI tools get shelled out
to from a project under a different license — no blocker there. The only
thing needing a visible attribution note is vendoring a copy of its
`suricata-keywords.json` data file, as noted above.

## Recommendation

Treat this exactly as the earlier design doc proposed, now concrete
instead of a placeholder:

1. **New optional instance setting** — a Suricata binary path (empty =
   deep validation disabled), same off-by-default pattern already used
   for `OLLAMA_URL`/the chatbot. Never a hard dependency; Rulezet must
   keep working with zero config for anyone who doesn't want this.
2. **Two integration points, both opt-in, never automatic on bulk
   upload:**
   - A **"Deep validate with Suricata engine"** button next to the
     existing grammar-only check on the rule create/edit page and the
     Suricata/Sagan bad-rule review flow — synchronous, ~2-5s tolerable.
   - A **slow, resumable background job**, reusing `audit_suricata_rules`'s
     shape, for an admin-triggered full-corpus pass — labeled with an
     ETA computed from the ~1.2-4.8s/rule cost above, off unless
     explicitly started.
3. **Implementation shape**: write rule content to a
   `tempfile.NamedTemporaryFile(suffix='.rules')`, run
   `suricata-language-server --batch-file <path> --no-engine-analysis`
   (skip the slower second pass — it never catches what a syntax/protocol
   check needs, see above) via `subprocess.run(..., timeout=N)`, parse
   stdout line-by-line as JSON, map `severity 1` → bad-rule error /
   `2,3,4` → warning (mirrors `ValidationResult.errors`/`.warnings`
   already used everywhere in this codebase), always clean up the temp
   file in a `finally`.
4. **Packaging**: `suricata-language-server` as an *optional* pip extra,
   plus a real `suricata` binary the host admin installs and points the
   new setting at (Docker/`--container` mode is a bigger, separate
   decision — it adds a `docker` Python dependency and Docker-daemon
   access from the app process; flag it, don't default to it).
5. **Keyword data**: periodically re-vendor `suricata-keywords.json` from
   a pinned upstream release tag (manual refresh, e.g. a `manage.py`
   subcommand) to keep `_snort_family_common.py`'s allowlists honest
   against real Suricata data, without any runtime dependency on the tool.

## Status

Items 1-4 above are implemented — see the status note at the top of this
document. Item 5 (periodically re-vendoring `suricata-keywords.json` to
keep `_snort_family_common.py`'s allowlists honest) is still a manual,
occasional maintenance task, not automated.
