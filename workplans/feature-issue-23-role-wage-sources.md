# Feature Workplan: Issue 23 Role Wage Sources

## Task

Rebuild PR #35 from current `develop` to address Issue #23: effort roles for
administration and business should expose the wage-table row used for their
hourly wage. Business roles use `wirtschaftsabschnitt`; administration roles use
`verwaltungsebene`. Citizens remain unchanged.

## What Changed Since Last Update

- 2026-05-21
  - Scope changed from repairing the old PR branch to rebuilding the existing
    PR #35 branch from current `develop`.
  - Plan changed to reuse PR #35 only as a reference, not as a rebase target.
  - Decision made to keep cost calculation behavior unchanged in this feature.
  - Risk identified from old PR: missing role wage sources were accepted
    silently; the rebuilt implementation must reject missing or invalid sources
    when a role carries effort values.

## Open Questions

- None blocking approval.

## Approved Scope

Not yet approved:
- Implement the Issue #23 rebuild on branch `issue-23-role-wage-source`.

Approved by user:
- Overwrite the old PR #35 branch with current `develop`.
- Treat the old PR implementation as disposable and use it only as reference.

Explicitly deferred or out of scope:
- Changing the cost calculation formula.
- Adding Bund/Länder/Kommunen rollups to total-cost reporting.
- Broad prompt cleanup unrelated to role wage-source fields.

## Current Plan

- [ ] Add DB persistence for current/proposed role wage-source metadata.
- [ ] Extend effort prompt schema and guidance minimally for administration and business.
- [ ] Parse and validate `wirtschaftsabschnitt` for business roles.
- [ ] Parse and validate `verwaltungsebene` for administration roles.
- [ ] Reject roles with effort values when the required wage-source field is missing or invalid.
- [ ] Expose role wage sources through editable process-step APIs.
- [ ] Show compact read-only wage-source provenance in the EA effort editor.
- [ ] Add focused backend and frontend regression tests.

## Decisions

- Keep PR #35 as the GitHub PR shell and rebuild its branch from `develop`.
- Store wage-source metadata separately from editable effort values so manual edits do not rewrite provenance.
- Validation belongs in effort parsing, before persistence.
- Citizens do not get role wage-source fields because citizen effort is not monetized by role.

## Implementation Status

- [x] PR #35 branch reset to current `origin/develop`.
- [ ] Workplan approved.
- [ ] Backend persistence implemented.
- [ ] Effort prompt and parser implemented.
- [ ] Editable API implemented.
- [ ] Frontend display implemented.
- [ ] Regression tests implemented.
- [ ] Tests run and results recorded.

## Verification

- Planned: targeted backend tests for effort parsing, persistence, editable API, undo/reset behavior.
- Planned: targeted frontend tests for the EA effort role-source display.
- Planned: `git diff --check`.
