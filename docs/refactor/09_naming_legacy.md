# 09 — Legacy naming

> Status: skeleton

## Facts
- `github_*` names now mean "any git host" (tables `github_repo`, `github_proposal`, `github_sync_*`, column `github_path`,
  routes `/rule/github/...`, permission `github.manage`, folder `rule_from_github/`).
- French identifiers (`valider_repo_github`, `get_licst_license`…) and typos (`multiTagFIlter.js`).

## To write
- Rename list (code / DB / URL), with migration and redirect strategy
