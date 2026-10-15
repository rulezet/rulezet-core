# 03 — Routes / blueprints

> Status: skeleton

## Facts (measured)
- `app/features/rule/rule.py`: **6,764 lines, 225 routes** in one blueprint.
- `app/features/rule/rule_core.py`: 5,822 lines; `app/home.py`: 1,894 lines.
- Git import/update/sync code under `rule/rule_from_github/`, `rule/github_repo_core.py`, routes `/rule/github/...`.

## To write
- Split of `rule.py` into sub-blueprints (crud, import, git sources, bad rules, history, similarity…)
- URL naming convention and redirects for old URLs
