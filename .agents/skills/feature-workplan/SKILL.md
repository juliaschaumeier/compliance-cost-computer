---
name: feature-workplan
description: Manage approval-gated feature work through a markdown workplan that records clarifications, plan changes, decisions, and implementation status without requiring mental diffs.
---

1. Before any code edits, create or update `workplans/feature-<slug>.md`.
2. Keep the file short, current, and readable in a single pass. Prefer replacing stale sections over accumulating duplicate prose.
3. Always include these sections in this order:
   - `# Feature Workplan: <title>`
   - `## Task`
   - `## What Changed Since Last Update`
   - `## Open Questions`
   - `## Approved Scope`
   - `## Current Plan`
   - `## Decisions`
   - `## Implementation Status`
   - `## Verification`
4. `What Changed Since Last Update` is mandatory and must remove the need for a mental diff. For each loop, append a new bullet block with the date and:
   - what changed in scope
   - what changed in the plan
   - what decisions were made
   - what new risks or questions appeared
5. `Open Questions` should contain only unresolved items that block approval or safe implementation.
6. `Approved Scope` must clearly separate:
   - not yet approved
   - approved by user
   - explicitly deferred or out of scope
7. `Current Plan` should be checkbox-based and reflect only the latest intended implementation path.
8. `Decisions` should record stable conclusions and their rationale in one line each.
9. `Implementation Status` should track concrete work items with checkboxes and short status notes.
10. `Verification` should list planned or completed tests/checks with results when available.
11. Before requesting approval, make sure the file clearly shows:
   - current understanding
   - unanswered questions
   - the exact plan to be approved
12. If implementation reveals new ambiguity or material scope change, update the file first, then ask for approval again before editing more code.
