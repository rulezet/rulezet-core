# YARA Editor — a VS Code–like workspace for YARA on Rulezet

> Status: **planning** — feature inventory and action plan, nothing built yet.
> First format of the [Rule Workbench](./ROADMAP.md#1-rule-workbench--a-full-environment-for-every-rule)
> (roadmap item #1). Everything learned here is meant to be reused for Sigma,
> Suricata and the other formats afterwards.

## 1. Goal

Writing a YARA rule on Rulezet should feel like writing it in VS Code with a
good extension — and then go further, because Rulezet knows things an editor
on a laptop doesn't: 380k+ rules, their dependencies, their tests, their
authors, their quality scores, the CVEs and ATT&CK techniques they cover.

One page where you can:

- write **one or many** rules, in a real code editor (highlighting,
  completion, hover help, errors as you type);
- **compile and test** them against samples without leaving the page;
- see and create the **links** with other rules (a condition that uses
  another rule, includes, related rules);
- get help from **Rulezy** (generate, explain, fix, suggest tests);
- **publish** everything at once — each rule parsed, validated and saved with
  its metadata — or keep it as a draft.

## 2. What already exists (building blocks)

| Piece | Where | Reuse for |
|---|---|---|
| `SmartEditor` — textarea + highlight.js overlay, auto-closing pairs | `static/js/components/smart-editor.js` | Today's create / edit pages; to be replaced by a real editor engine for YARA |
| CodeMirror bits (diff) | `static/js/codeMirror/` | Diff view between versions |
| YARA validation — compiles with yara-python, adds missing `import`s, resolves another rule's name to that rule (recursively) and compiles them together | `yara_format.py` → `YaraRule.validate()` | Live diagnostics, dependency detection |
| Dependency links (`yara_condition_ref`), Dependencies view, download with dependencies | `yara_format.py`, `rule_relation/` | "Linked rules" panel, go-to-definition across Rulezet |
| Rule tester — YARA driver (string / hex / base64 file input, matched strings with offsets) | `rule_tester/drivers/yara_driver.py` | Test panel |
| AI agents — generator, fixer, analysis, deep analysis; "thinking steps" UI | `features/ai/agents/` | Rulezy panel |
| Quality score + checklist | `rule/rule_quality/` | Live score panel |
| Similarity / duplicates | `similarity` models | "Similar rules" warning before publish |
| Metadata parsing (title, author, tags, CVE, ATT&CK) | `yara_format.parse_metadata()` | Auto-filled side form from `meta:` |
| Public validate API (used by misp-modules) | `/api/rule/public/validate` | Same validation engine for the editor |

## 3. Feature inventory

Priority: **P0** = first usable version, **P1** = next, **P2** = later / nice to have.

### 3.1 Editor core

| Feature | Priority | Notes |
|---|---|---|
| Real code editor engine (Monaco or CodeMirror 6) | P0 | Decision in §5 |
| YARA syntax highlighting (keywords, strings, hex, regex, modifiers, modules, comments) | P0 | TextMate grammar or Monarch tokenizer |
| Line numbers, folding per rule / per section (`meta`, `strings`, `condition`) | P0 | |
| Bracket matching, auto-closing `{ } ( ) " /`, auto-indent | P0 | |
| Find / replace (regex), multi-cursor, column selection | P0 | Comes with the engine |
| Minimap, sticky headers (current rule name) | P1 | |
| Command palette (`Ctrl+Shift+P`) — every editor action in one place | P1 | |
| Keyboard shortcuts: compile, test, save draft, publish, format | P0 | `Ctrl+S` = save draft, `Ctrl+Enter` = test |
| Formatter (consistent indentation, aligned `=` in `strings:`) | P1 | YARA-X has a formatter (to check: `yr fmt`) |
| Light / dark theme following Rulezet's theme | P0 | |
| Split view: rule ↔ sample (hex) / rule ↔ another rule | P2 | |
| Settings (font size, tab size, word wrap, vim keys) | P2 | Stored per user |

### 3.2 Language intelligence

| Feature | Priority | Notes |
|---|---|---|
| **Diagnostics as you type** — compile errors and warnings underlined, with the message on hover | P0 | Debounced call to the validate endpoint (§5.2) |
| Completion: keywords (`rule`, `private`, `global`, `meta`, `strings`, `condition`, `import`, `include`, `of`, `them`, `for`, `any`, `all`, `none`, `at`, `in`, `filesize`, `entrypoint`…) | P0 | Static list |
| Completion: string identifiers (`$a`, `#a`, `@a[1]`, `!a`) from the current rule's `strings:` | P0 | Parsed client-side |
| Completion: string modifiers (`nocase`, `wide`, `ascii`, `xor`, `base64`, `fullword`, `private`) with their arguments | P0 | |
| Completion: modules — `import "pe"` then `pe.` lists fields and functions (`pe.imports()`, `pe.sections[i].name`, `math.entropy()`, `hash.md5()`, `elf`, `dotnet`, `magic`, `cuckoo`, `time`, `console`…) | P0 | A JSON description of each module, versioned with the yara-python in use |
| Auto-add the `import` when a module is used | P0 | Same logic as `validate()` |
| Completion: **other rules' names** — from this page, then from Rulezet (same source / same author first) | P1 | Makes cross-rule conditions easy; ranked |
| Hover help: keyword, modifier, module field / function (signature, return type, example, link to the YARA docs) | P0 | Same JSON as completion |
| Hover on a hex string: decoded ASCII / UTF-16; on a text string: its hex | P1 | |
| Hover on a rule name used in a condition: that rule's summary (author, score, link) | P1 | |
| Go to definition (`F12`) — on `$a` → its declaration; on a rule name → that rule (on the page or on Rulezet) | P1 | |
| Find all references of a string or a rule | P1 | |
| Rename symbol (`F2`) — a string identifier in its rule, a rule name everywhere on the page | P1 | |
| Snippets / templates — empty rule with Rulezet's `meta` fields, PE file, ELF, document macro, webshell, hex pattern with jumps, `for` loop… | P0 | Stored as a setting in `app/config/` |
| Signature help in function calls (`pe.exports(` → parameters) | P2 | |
| Outline (symbol tree): rules → strings → condition | P1 | Side panel |
| Code actions (quick fixes): add the missing `import`, remove an unused string, declare an undefined `$x`, rename a duplicate rule | P1 | Diagnostics + one click |

### 3.3 Linting and quality (beyond "it compiles")

| Feature | Priority | Notes |
|---|---|---|
| Unused strings, undefined identifiers, duplicate rule names on the page | P0 | Compiler + client parse |
| **Performance warnings** — strings too short / too common (slow atoms), unbounded regex (`.*`), huge hex jumps, `filesize` checked last | P1 | YARA-X reports slow patterns (to check); otherwise our own rules |
| Missing / incomplete `meta` (author, description, date, reference, TLP…) per Rulezet's quality checklist | P0 | Same checks as the quality score |
| Naming conventions (rule name pattern, tags) — configurable | P2 | Setting in `app/config/` |
| **YARA-X compatibility** check — does the rule also compile with YARA-X? | P1 | Second engine, warning only |
| Live quality score with its checklist, updated on every change | P1 | Existing score engine |
| Duplicate / similar rule already on Rulezet (similarity) — before publishing | P1 | Existing similarity |

### 3.4 Many rules on one page

| Feature | Priority | Notes |
|---|---|---|
| Write any number of rules in one document | P0 | |
| **Auto-parse on the fly** — each rule detected, listed in the outline with its own status (✓ compiles / ✗ error / ⚠ warnings) | P0 | Same split as the Git import (`extract_rules_from_file`) |
| Rules on the page that use each other compile together (no "undefined identifier" for a rule defined 10 lines below) | P0 | Compile the whole document as one source |
| Per-rule side panel: title, description, tags, ATT&CK, CVE, license, visibility — prefilled from `meta`, editable | P1 | `parse_metadata()` |
| **Publish all** — every valid rule saved in one go, the invalid ones listed with their error (or kept as drafts) | P0 | Same path as the bulk import |
| Publish selected / publish as a bundle (one click: page → bundle) | P1 | |
| Open several existing rules in tabs; open a rule's dependencies in tabs | P1 | |
| Paste or drop a `.yar` file / a ZIP → opened in the editor | P1 | |

### 3.5 Test as you write

| Feature | Priority | Notes |
|---|---|---|
| Test panel: paste text, hex, or upload a file; run the page's rules against it | P0 | yara_driver, sandboxed, size / time limits |
| Results per rule: matched / not matched, **matched strings with offsets**, highlighted in a hex/text view of the sample | P0 | Driver already returns offsets |
| Click a match → jump to the string in the editor; click a string → its matches in the sample | P1 | |
| **Test sets saved with the rule** — samples that must match / must not match, re-run on every change | P1 | Shared with the Lab (`docs/future/testing_lab.md`) |
| Regression badge: "this change breaks 1 of 5 saved tests" | P1 | |
| Run against a goodware corpus (false-positive check) | P2 | Needs a curated corpus |
| Hashes of the sample (MD5, SHA-1, SHA-256) shown, with a VirusTotal link | P1 | Hash computed in the browser; nothing uploaded anywhere |
| Condition debugger — for each sub-expression, true / false on this sample | P2 | Our own evaluator or YARA-X's (to check) |

### 3.6 Links with other rules

| Feature | Priority | Notes |
|---|---|---|
| **Linked rules panel** — rules this rule needs (condition refs, includes), rules that need it, manual relations | P0 | `rule_relation` + Dependencies view |
| Typing a rule name that exists on Rulezet → offer to link it (it will be compiled with it, like `validate()` does) | P1 | Only trusted rules (same source / owner / existing link — current rule) |
| Mini dependency graph of the page / of the rule | P1 | Existing DependencyFlow |
| Add a manual relation ("related", "variant of", "replaces") from the editor | P1 | Existing relation types |
| Warn when a rule it depends on is deleted or changes upstream | P2 | Alert feature |

### 3.7 Rulezy (AI) in the editor

| Feature | Priority | Notes |
|---|---|---|
| **Generate** — describe the threat (or give a CVE, a technique, a sample's strings) → rule(s) inserted in the editor, not published | P0 | Existing generator agent, "thinking steps" UI |
| **Explain** the selected rule / condition in plain words | P1 | Analysis agent |
| **Fix** — send the compile error and the rule, get a corrected version as a **diff to accept or reject** | P0 | Existing fixer agent + DiffViewer |
| Suggest strings from a sample (most distinctive strings / byte sequences) | P2 | Must run locally, no sample sent to an external model unless the admin allows it |
| Suggest test cases (strings that should and should not match) | P2 | |
| Inline completion (ghost text) | P2 | Cost and latency — only with a local model (Ollama) |
| Permission: admins and `ai.use` holders only (same check as the generator today) | P0 | `can_draft_with_ai()` |

### 3.8 Drafts, history, collaboration

| Feature | Priority | Notes |
|---|---|---|
| **Autosave draft** (server-side, per user) — never lose work | P0 | |
| Version history of a rule with diff, restore | P1 | Existing history + DiffViewer |
| Edit proposals: editing someone else's rule opens a proposal, same editor | P1 | Existing proposal flow |
| Shareable draft link (read-only) for review | P2 | |
| Comments on a line of the rule (review) | P2 | |
| Real-time co-editing | P2 | Large; only if there is demand |

### 3.9 Shortcuts to the outside world

| Feature | Priority | Notes |
|---|---|---|
| Download the page as `.yar` / ZIP (with dependencies) | P0 | Existing download |
| Open a selected string in CyberChef (decode), regex101 (regex string) | P1 | URL only, nothing sent from the server |
| YARA documentation for the keyword under the cursor | P0 | Through the hover |
| Copy as Velociraptor / MISP object / JSON | P1 | Existing exports |
| VS Code: "Open in Rulezet" / "Push to Rulezet" through the API (a small VS Code extension) | P2 | Uses the existing API keys |

### 3.10 Other ideas

- **Rule from a hash**: give a hash, get the sample's metadata from an
  allowed intel source (if configured), pre-fill `meta.hash` and references.
- **"Why didn't it match?"** — for a sample that should match, show which
  strings were found and which part of the condition failed.
- **Coverage hints** — "no YARA rule on Rulezet for CVE-XXXX yet" when the
  `meta` mentions a CVE (the CVE response kit already knows).
- **Learning mode** — hover explanations more detailed, a guided first rule
  (the Night Shift game's tutorial, but serious).
- **Rule templates shared by the community** — a template is just a rule
  marked as template.
- **Bulk edit across rules** — e.g. add a `meta` field to every rule on the
  page or of a bundle.
- **Performance budget** — estimated scan cost of the rule (from atoms) shown
  next to the score.

## 4. User flow (P0)

1. *Create rule → YARA* opens the editor with a template (or empty).
2. The user writes; errors appear underlined within ~0.5 s; completion and
   hovers help; the outline lists the rules found on the page with their
   status.
3. Optional: *Generate with AI* inserts a draft; *Fix with AI* proposes a diff
   for a rule in error.
4. *Test*: paste or drop a sample → matches per rule, highlighted.
5. *Publish all*: each valid rule is saved (meta parsed into fields, default
   TLP/PAP tags, links recorded); the page shows what was published and what
   was not, and why. The draft is kept until everything is published.

## 5. Technical decisions to make

### 5.1 Editor engine

| | Monaco (VS Code's editor) | CodeMirror 6 |
|---|---|---|
| Feel | Exactly VS Code (command palette, minimap, multi-cursor, peek definition built in) | Lighter, very flexible, accessible |
| Loading without a build step | AMD loader from a pinned CDN — works with our no-build setup | ES modules, but split in many packages — easiest with a small pre-built bundle committed to `static/` |
| Size | Heavy (several MB, workers) — load only on the editor page | Small |
| Language support | Monarch tokenizer + completion / hover / diagnostics providers in JS; can talk to a language server with an adapter | Lezer grammar or stream parser + extensions |
| Mobile | Poor | Good |

**Proposal**: Monaco, because the target is literally "VS Code in Rulezet",
loaded only on the editor page; keep `SmartEditor` for every other form.
To validate with a quick prototype (highlighting + diagnostics) before
committing.

### 5.2 Where the language intelligence runs

- **Client side (JS)**: highlighting, completion of keywords / modifiers /
  module fields (from a JSON description), string identifiers, outline,
  rename — instant, no server call.
- **Server side**: compilation and diagnostics (yara-python, the same
  `validate()` as publishing, so the editor never says "OK" for a rule the
  server would refuse), dependency resolution against Rulezet, rule-name
  completion from the database, tests. One endpoint per need, debounced,
  rate-limited, size-limited.
- **Option — a real language server**: if YARA-X ships a usable language
  server (to check: `yara-x-ls` / the VirusTotal VS Code extension), run it
  server-side and bridge it to Monaco over a WebSocket. Gives diagnostics,
  completion and hovers maintained upstream; the cost is an extra binary on
  the instance (off by default, like `SURICATA_BINARY_PATH`).

### 5.3 Security

- Rules compile on the server: keep the existing protections — no `include`
  of server files, compile and scan timeouts, size limits (the public
  validate endpoint caps at 512 KB), rate limits per user.
- Samples for tests stay small, are never stored unless the user saves a
  test set, and are never sent to an AI provider unless the admin allows it.
- AI features keep today's permission check (admins and `ai.use`).

## 6. Action plan

| Step | Content | Size |
|---|---|---|
| 0. Prototype | Monaco on a hidden page: YARA highlighting, server diagnostics on one rule. Decide Monaco vs CodeMirror. | S |
| 1. Editor MVP | Engine + highlighting + completion (keywords, modifiers, modules, `$` strings) + hovers + diagnostics + snippets + autosave draft, on the YARA create page behind a setting | M |
| 2. Many rules | Auto-parse into the outline with per-rule status, compile the page as one source, publish all / selected | M |
| 3. Test panel | Samples (text / hex / file), matches with offsets highlighted, saved test sets | M |
| 4. Links | Linked-rules panel, rule-name completion from Rulezet, go to definition, dependency graph | M |
| 5. Rulezy | Generate into the editor, fix as a diff, explain | S–M (agents exist) |
| 6. Quality | Live score, performance warnings, YARA-X check, similar rules before publish | M |
| 7. Edit everywhere | Same editor on edit / proposal pages, history and diff | M |
| 8. Other formats | Extract what is generic (engine, panels, publish flow) and add Sigma next | L |

Each step ships on its own and is usable; the old create page stays available
until step 7.

## 7. Open questions

- Monaco or CodeMirror 6 — decided after the prototype?
- Replace the YARA create page directly, or ship the editor as a new page
  ("YARA editor") first and switch once it's complete?
- Should drafts be private only, or shareable from the start?
- Which YARA version / modules do we describe for completion — the
  yara-python installed on the instance, or YARA-X?
- Test samples: allow file upload for everyone, or only for logged-in users
  with a size cap?
- AI inline completion: worth it only with a local model — do we want it at
  all?
- A companion VS Code extension (push / pull rules with the API) — now, or
  once the web editor is done?
