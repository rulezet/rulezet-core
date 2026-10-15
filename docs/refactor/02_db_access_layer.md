# 02 — DB access layer

> Status: skeleton

## Facts (measured)
- **354** `.query` calls outside `*_core.py` files (routes, API, jobs call the ORM directly).
- Rule access must go through `_active()` (soft delete) — not enforced structurally.

## To write
- One access module per domain; routes and API never touch `Model.query`
- How `_active()`-style rules are enforced
- Call sites to move, per feature
