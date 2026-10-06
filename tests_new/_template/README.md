# Template for a new feature

Copy this folder to `tests/<feature>/`, rename nothing, add an empty
`__init__.py`, then replace the examples. Each file is one layer of
docs/design/test_restructure.md:

| File | Layer | Question it answers |
|---|---|---|
| `test_access.py` | 1. Access | Who (anonymous / user / owner / admin / special role) can do what? |
| `test_crud.py` | 2. CRUD | Do create / read / edit / delete leave the database right? |
| `test_api.py` | 3. API | Same rights and CRUD through `/api/` with an API key? |
| `test_robustness.py` | 4. Robustness | Do bad inputs get a clean 4xx — never a 500, never half-written data? |

Rules of thumb: backend only (no HTML/CSS/JS assertions), one behaviour per
test, name = `test_<action>_<who/what>_<expected>`, fixtures from
`tests/conftest.py` and `tests_new/helpers/` instead of hand-made setup.
