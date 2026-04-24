| Item | Status | Summary |
| --- | --- | --- |
| Item 1 | done | Moved legacy migrations ahead of `answer_state` index/normalization work in `init_db` and added a regression test covering legacy `llm_answers` migration. |
| Item 2 | done | Fixed `process_steps` migration symmetry so both edited expense columns are ensured, and extended migration assertions accordingly. |
| Item 3 | done | Updated admin step-cost validation to allow time-only inputs when active session pay rates can resolve cost, and added a route-level regression test. |

Files changed per item

Item 1
- `backend/core/db.py`
- `tests/test_db_migration_process_steps.py`

Item 2
- `backend/core/db.py`
- `tests/test_db_migration_process_steps.py`

Item 3
- `backend/routers/costs.py`
- `tests/test_costs_flow.py`

Tests run and results

Item 1
- `./venv/bin/python -m pytest tests/test_db_migration_process_steps.py`
- Result: passed (`2 passed`)

Item 2
- `./venv/bin/python -m pytest tests/test_db_migration_process_steps.py`
- Result: passed (`2 passed`)

Item 3
- `./venv/bin/python -m pytest tests/test_costs_flow.py`
- Result: passed (`6 passed`)

Deviations from scope

- None.

Metadata check status

- passed
- Resolved review context from the review report `Review Context` block and filename.
- Expected `head_short`: `29c4f13`
- Current `HEAD`: `29c4f13`
- Review mode: `commits_only`
- Working tree dirtiness did not block execution under `commits_only`.
