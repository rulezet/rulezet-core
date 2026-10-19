# rulezet-editor — a standalone, pluggable rule editor

> Status: design draft. Comes **before** `yara_editor.md`: YARA becomes the first
> *language pack* of this editor instead of a Rulezet-only feature.

## 1. Goal

Build the rule editor as its **own project** (`rulezet-editor`, separate repo, MIT/AGPL like Rulezet)
that:

- works **anywhere**: Rulezet, MISP, a static HTML page, a VS Code webview, an internal SOC tool;
- has **one common base** (editing, highlight, completion, diagnostics, hover, format, multi-rule,
  test panel, AI hooks) identical for every format;
- gets its **format knowledge from plug-ins** (“language packs”): YARA, Sigma, Suricata, Zeek,
  Wazuh, Kunai, Nuclei, CRS…;
- gets its **server knowledge from a host adapter**: inside Rulezet the adapter calls the Rulezet API
  (validation, rule search, tests, Rulezy); outside, it can be another backend or nothing at all
  (local features keep working);
- makes it **easy for a newcomer to add a format**: one folder, one interface, a template, a test kit.

Rulezet then just imports it (`SmartEditor` is replaced by / wraps `RulezetEditor`).

## 2. Three layers

```
┌──────────────────────────────────────────────────────────┐
│  Host app (Rulezet, MISP, plain page, VS Code webview)   │
│      new RulezetEditor(el, { language, host, ... })      │
└───────────────┬──────────────────────────┬───────────────┘
                │                          │
        ┌───────▼────────┐         ┌───────▼────────┐
        │  Core          │◄───────►│  Host adapter  │  validate / search rules /
        │  RulezetEditor │         │  (optional)    │  test / AI / save drafts
        └───────┬────────┘         └────────────────┘
                │ registry
   ┌────────────┼─────────────┬──────────────┐
┌──▼───┐   ┌────▼───┐   ┌─────▼────┐   ┌─────▼────┐
│ yara │   │ sigma  │   │ suricata │   │  ...     │   language packs
└──────┘   └────────┘   └──────────┘   └──────────┘
```

- **Core** — knows nothing about any format. Owns the editor engine, UI panels, the extension
  pipeline, theming, i18n, events.
- **Language pack** — knows one format. Pure data + pure functions, no network, no DOM.
- **Host adapter** — knows one backend. Only network calls. Every method is optional; the core hides
  the feature when the method is missing.

This split is the key rule: *a pack never calls a server, an adapter never parses a rule.*

## 3. Engine choice

| | CodeMirror 6 | Monaco |
|---|---|---|
| Size | ~150–300 kB for what we need | ~2–5 MB, workers |
| Modularity | everything is an extension → fits “packs” naturally | one big editor, languages registered globally |
| Grammars | Lezer (real incremental parser, gives a syntax tree) or StreamLanguage (simple tokenizer) | Monarch tokenizer (no tree) |
| Multiple editors on a page | cheap | heavy |
| Mobile | good | weak |
| VS Code look & feel | close enough | identical |

**Recommendation: CodeMirror 6** for a reusable library (light, plug-in model, syntax tree usable by
packs for multi-rule split / outline / go-to-definition). This replaces the “Monaco?” proposal in
`yara_editor.md` — to confirm with a 1-day prototype (YARA grammar + completion + lint).

The core must **not leak** CodeMirror types into the pack API, so the engine could be swapped later.

## 4. Repository structure

```
rulezet-editor/
├── package.json              # ESM, "exports" per pack, no framework dependency
├── README.md                 # quick start (3 lines of HTML)
├── CONTRIBUTING.md           # "add a language in 30 minutes"
├── src/
│   ├── core/
│   │   ├── RulezetEditor.js  # public class
│   │   ├── registry.js       # registerLanguage / getLanguage / listLanguages
│   │   ├── pipeline.js       # turns a pack into engine extensions
│   │   ├── diagnostics.js    # merges local lint + remote validation, debounced
│   │   ├── completion.js     # merges pack completions + host completions
│   │   ├── hover.js
│   │   ├── documents.js      # multi-rule: split, per-rule status, outline
│   │   ├── commands.js       # command palette, keymap
│   │   ├── events.js         # tiny emitter: change, validate, save, select-rule…
│   │   ├── i18n.js           # en + fr to start
│   │   └── theme.js          # light/dark from CSS variables
│   ├── ui/                   # framework-free panels (DOM), optional Vue wrapper below
│   │   ├── StatusBar.js
│   │   ├── ProblemsPanel.js
│   │   ├── OutlinePanel.js
│   │   ├── TestPanel.js
│   │   └── AiPanel.js
│   ├── host/
│   │   ├── HostAdapter.js    # interface + no-op default
│   │   └── RulezetHost.js    # adapter for the Rulezet REST API (base URL + API key/CSRF)
│   ├── wrappers/
│   │   └── vue.js            # <rulezet-editor v-model=... :language=...> for Vue 3 UMD
│   └── languages/
│       ├── _template/        # copy this to start a new pack
│       ├── plain/            # fallback: no highlight, no lint
│       ├── yara/
│       ├── sigma/
│       └── suricata/
├── test/
│   ├── conformance/          # same suite run against every pack
│   └── core/
├── playground/               # index.html: pick a pack, type, see everything (also the demo site)
└── dist/                     # built bundles: core.js, languages/<id>.js, rulezet-editor.css
```

Distribution: npm package **and** prebuilt ESM files on a CDN / copied into Rulezet `static/vendor/`
(Rulezet has no build step — it just imports `dist/`).

## 5. The core class

```js
import { RulezetEditor } from 'rulezet-editor';
import yara from 'rulezet-editor/languages/yara';
import { RulezetHost } from 'rulezet-editor/host/rulezet';

RulezetEditor.registerLanguage(yara);

const editor = new RulezetEditor(document.getElementById('ed'), {
  language: 'yara',                 // or 'auto' → pack.detect() on the content
  value: '',
  theme: 'auto',                    // light | dark | auto (follows CSS vars)
  readOnly: false,
  multiRule: true,                  // split the document into rules
  panels: ['problems', 'outline', 'test', 'ai'],
  host: new RulezetHost({ baseUrl: '/api', csrfToken }),   // optional
  locale: 'en',
});

editor.on('change', (value) => {});
editor.on('diagnostics', (list) => {});
editor.getValue(); editor.setValue(v); editor.setLanguage('sigma');
editor.getRules();      // [{ name, range, text, status }]
editor.format(); editor.validate(); editor.focus(); editor.destroy();
```

Rules for the core:
- no global state except the language registry;
- every feature is **capability-driven**: shown only if the pack *or* the host provides it;
- everything async is debounced and cancellable (typing never waits on the network);
- accessible (keyboard only, screen reader labels), responsive.

## 6. Language pack interface

A pack is one plain object. Only `id` and `name` are required; everything else lights up a feature.

```js
export default {
  id: 'yara',
  name: 'YARA',
  version: '0.1.0',
  extensions: ['.yar', '.yara'],
  detect(text) { return /\brule\s+\w+/.test(text) ? 0.9 : 0; },   // score 0..1 for 'auto'

  // ── Base (same for all formats, data only) ──
  syntax: { /* Lezer grammar OR simple token rules */ },
  comments: { line: '//', block: ['/*', '*/'] },
  brackets: ['{}', '()', '[]'],
  folding: 'braces',              // or 'indent' (Sigma), or function(tree)
  snippets: [ { label: 'rule', body: 'rule ${1:name}\n{\n  strings:\n    $a = "${2}"\n  condition:\n    $a\n}' } ],
  keywords: [...],                // used by default completion + hover
  docs: { 'pe.imphash': 'Returns the import hash…' },             // hover text

  // ── Smarter, optional functions (pure: text/tree in, data out) ──
  complete(ctx) { return [...] },          // ctx: { text, pos, tree, word, rule }
  hover(ctx) { return '…markdown…' },
  lint(text, tree) { return [{ from, to, severity, message, fix? }] },
  format(text) { return text },
  splitRules(text, tree) { return [{ name, from, to }] },
  outline(text, tree) { return [...] },
  definitions(ctx) { return { from, to } },  // go to $string / rule
  references(ctx) { return [...] },
  dependencies(rule) { return ['other_rule'] },  // names this rule needs (for host lookup)

  // ── Hints for the host (no network here) ──
  testInput: 'binary',            // binary | text | json-event | pcap | log-line
  validateAs: 'yara',             // format name the host's validate() expects
};
```

Packs can also be split in files (`grammar.js`, `completions.js`, `docs.json`…) and assembled in
`index.js` — the template shows that layout.

## 7. Host adapter interface

```js
class HostAdapter {
  async validate(language, text)          // → [{from,to,severity,message}] (real compiler)
  async searchRules(language, query)      // → completion of other rule names, "similar rules"
  async getRule(language, name)           // → hover / go-to-definition on a remote rule
  async test(language, text, sample)      // → { matched, details }
  async ai(action, payload)               // generate | fix | explain → streamed text/diff
  async saveDraft(id, text) / loadDraft(id)
  async publish(language, rules)          // host-specific, the core just calls it
}
```

- `RulezetHost` maps these to existing Rulezet endpoints (rule validation API, rule search,
  `rule_tester`, AI agents, drafts — new endpoints only where nothing exists yet).
- A local-only adapter can exist too (e.g. YARA compiled in WebAssembly in the browser — later).
- Missing method → the matching UI is hidden. No adapter at all → pure offline editor.

## 8. What the common base gives every format for free

| Feature | Comes from |
|---|---|
| Highlight, brackets, folding, comment toggle | pack `syntax`/`comments`/`folding` |
| Keyword + snippet completion | pack `keywords`/`snippets` |
| Hover docs | pack `docs` |
| Problems panel, squiggles, quick fixes | pack `lint` + host `validate`, merged |
| Format document | pack `format` |
| Multi-rule page: outline, per-rule status, “publish all” | pack `splitRules` + host |
| Completion of existing Rulezet rule names, dependency links | pack `dependencies` + host `searchRules` |
| Test panel | pack `testInput` + host `test` |
| Rulezy generate/fix/explain (diff to accept) | host `ai` |
| Find/replace, multi-cursor, command palette, themes, i18n, drafts | core |

So a minimal pack (grammar + keywords + snippets) already gives a decent editor; each extra function
adds a feature without touching the core.

## 9. Adding a new editor (contributor flow)

1. `cp -r src/languages/_template src/languages/<format>`
2. Fill `index.js`: `id`, `name`, `extensions`, `detect`, `comments`.
3. Add highlighting: start with simple token rules; switch to a Lezer grammar when you need the tree.
4. Add `keywords.json`, `snippets.json`, `docs.json`.
5. Optional: `lint`, `format`, `splitRules`, `complete`.
6. Add samples in `test/fixtures/<format>/` (valid, invalid, multi-rule).
7. `npm test` → the **conformance suite** checks every pack: loads, detects its own fixtures, does
   not throw on garbage input, `splitRules` covers the whole text, lint ranges are inside the text,
   no network calls, no DOM access.
8. `npm run playground` → try it; open a PR. A pack needs no core change.

`CONTRIBUTING.md` documents this with one complete small example (e.g. Zeek or a toy format).
Maturity badge per pack in the README: *basic* (highlight) → *standard* (+completion, lint) →
*full* (+format, multi-rule, definitions).

## 10. Integration in Rulezet

- Copy `dist/` to `app/static/vendor/rulezet-editor/<version>/` (or load from a CDN pinned version),
  add it to the import map in `base.html`.
- `SmartEditor` becomes a thin wrapper around `RulezetEditor` (same props: `v-model`, `language`),
  so create/edit pages, edit proposals, bundles, Night Shift… switch without changes.
- `RulezetHost` gets the CSRF token from the page; formats list from `GET /api/config/formats`
  (map Rulezet format names → pack ids).
- Server work in Rulezet: one stable endpoint `POST /api/rule/validate` (exists in some form — reuse),
  rule-name search for completion, draft storage. Listed in `yara_editor.md` steps.

## 11. Plan

| Step | Content | Done when |
|---|---|---|
| 0 | Prototype CM6 vs Monaco with YARA (1 day) | engine decided |
| 1 | Repo skeleton, build (esbuild), core class, registry, `plain` pack, playground | editor loads in a plain HTML page |
| 2 | Pack API v0 + YARA pack *basic* (highlight, folding, snippets, keywords) | YARA looks right |
| 3 | Diagnostics pipeline + HostAdapter + RulezetHost.validate | errors underlined from Rulezet |
| 4 | Completion + hover (pack + host rule names) | `$str`, modules, other rules complete |
| 5 | Multi-rule (split, outline, per-rule status) | several rules on one page |
| 6 | Integrate in Rulezet (replace SmartEditor internals) | create/edit use it |
| 7 | `_template`, conformance tests, CONTRIBUTING, Sigma + Suricata packs *basic* | someone else can add a pack |
| 8 | Test panel, AI panel, drafts | features of `yara_editor.md` P0 |
| 9 | Publish v1 (npm + docs site from playground), VS Code webview demo | used outside Rulezet |

## 12. Open questions

- Engine: CodeMirror 6 (recommended) or Monaco?
- Repo: `github.com/ngsoti/rulezet-editor`? Licence: same as Rulezet (AGPL) or MIT to ease reuse in
  other tools?
- Build: allow a build step in the editor repo only (esbuild), Rulezet keeps importing prebuilt files?
- UI panels: framework-free DOM (reusable anywhere) + Vue wrapper — OK, or Vue only?
- Real compilers in the browser (YARA-X / libyara in WebAssembly) later, or always server-side?
- Pack versioning: all packs in the same repo/version at first, separate packages later?
