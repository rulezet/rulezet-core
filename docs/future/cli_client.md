# Rulezet CLI client (issue #13)

A small command-line tool and Python library that fetches rules from a Rulezet instance through
its API and writes them as local files, so YARA, Suricata, a SIEM or a CI pipeline can use them
without going through the website. Same idea as PyMISP / the vulnerability-lookup client.

New repository: `rulezet/rulezet-client` (`pip install rulezet-client`, command `rulezet`).

## What it does

```bash
rulezet config --url https://rulezet.org --api-key XXX   # any instance, key optional

rulezet fetch --format yara --tag tlp:clear -o ./rules/   # rules by format / tag / author…
rulezet fetch --cve CVE-2024-3400 -o ./cve/               # CVE kit
rulezet fetch --attack T1059 --format sigma               # ATT&CK technique
rulezet fetch --bundle <uuid> -o ./bundle/                # a bundle, with its folders

rulezet sync ./rules/                                     # only what changed since last time
rulezet search "cobalt strike" --format suricata
rulezet show <uuid>
```

- **Library first, CLI on top**: everything usable from a Python script.
- **Ready-to-use files**: one file per rule (or one per format), plus an `index.json`
  (uuid, version, source, last change).
- **Incremental sync**: a small local state file, only new / changed / deleted rules are
  downloaded — meant to run from cron.
- **Without an API key**: public rules. **With a key**: also the user's private bundles.

## What Rulezet needs

- An API endpoint "rules changed since <date>" (new, updated, deleted uuids) for `sync`.
- Check that the existing endpoints (rules, bundles, CVE, ATT&CK, search) return what the
  client needs, and are documented in the swagger (`/api/`).

## Steps

1. Rulezet: "changed since" endpoint.
2. Library: client for the existing endpoints + tests.
3. CLI: `config`, `fetch`, `show`, `search`.
4. `sync` with its state file.
5. Publish on PyPI, README with examples, link from the Rulezet docs.
