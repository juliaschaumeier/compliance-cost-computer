---
name: bug-triage
description: Triage a bug report into reproducibility, impact, likely root cause, and next best fix/test action.
---

1. Confirm scope: affected route/module/user flow.
2. Reproduce or infer minimal failing path from logs/tests.
3. Classify severity and regression risk.
4. Identify likely root cause in code and data flow.
5. Propose smallest safe fix plus one focused regression test.
6. Include explicit quality verdict: optimal, acceptable-with-debt, or corners-cut.
7. Provide a fixer-ready action list with scoped, testable tasks when the user is asking for a fix path.
8. Stay scoped to the reported issue. Do not turn bug triage into a branch-wide review.
9. Do not write review artifacts under `review/`; use the `reviewer` agent for formal branch reviews and review artifact generation.
