# 05 — Hard-coded configuration

> Status: skeleton

## Facts (measured)
- **66** Python files define module-level constant lists/dicts/tuples (`NAME = [ ... ]`, `{ ... }`), e.g. format catalog
  (`rule_format/format_catalog.py`), git providers (`git_provider.py`), permissions/roles (`roles_core.py`),
  log icons (`log_action_defaults.py`), task types (`task_scheduler/task_types.py`), licenses (`licenses.txt`),
  `default_platform_tag_configs.json`.

## To write
- Inventory: each constant → keep in code / DB setting editable in an admin page / fetched from an API (latest version)
- Generic admin "settings" model and page
- Example: formats served by an API route so clients always get the current list
