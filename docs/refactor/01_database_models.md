# 01 — Database models

> Status: step 1 done — `db.py` split into one module per feature

## Done
- `app/core/db_class/db.py` (5,141 lines, 106 classes) is gone. Models now live in `app/core/db_class/<feature>.py`:
  `user`, `role`, `rule`, `rule_proposal`, `rule_relation`, `rule_tester`, `comment`, `report`, `tag`, `bundle`,
  `git`, `attack`, `similarity`, `alert`, `notification`, `workspace`, `blog`, `connector`, `misp`, `velociraptor`,
  `ai`, `pivotick`, `gamification`, `job`, `task_scheduler`, `activity_log`, and `common` (shared column types).
- Every import in the project points at the feature module (`from app.core.db_class.rule import Rule`);
  the 4 `import *` from the old file were replaced by explicit imports.
- `app/core/db_class/__init__.py` loads all modules — required because relationships are declared by class name
  and event listeners register at import time.
- Models that a module only uses inside methods are imported at the bottom of that module, to avoid circular imports.
- Table and column names are unchanged: no migration.

## Next

## To write
- Target: `app/core/db/` (or `app/models/`) package, one module per domain (rule, bundle, git, user, tag, job, connector, ai…)
- Proposed mapping class → module
- Import compatibility during the transition (re-exports from the old path)
- Table/column names: keep, or rename with migrations
