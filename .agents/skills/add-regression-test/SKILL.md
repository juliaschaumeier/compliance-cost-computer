---
name: add-regression-test
description: Add the smallest regression test after a bug fix or behavior change. Use when a bug was fixed or logic changed; do not use for docs-only edits.
---

1. Reproduce the behavior.
2. Add the smallest failing test that captures it.
3. Implement or verify the fix.
4. Run the narrowest relevant test target first.
5. Confirm the test maps to the intended fix item acceptance checks.
6. Avoid broad test rewrites; keep scope local to changed behavior.
