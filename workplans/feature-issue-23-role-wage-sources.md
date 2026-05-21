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

- 2026-05-21
  - Current `develop` inspection confirmed that effort roles are parsed directly
    in `backend/routers/effort.py`; there is no active role Pydantic model to
    update for this path.
  - DB inspection confirmed that `process_steps` has no role-source columns yet
    and editable process-step rows are resolved through `db_edit_metrics`.
  - Plan refined to keep legacy flat effort fields readable, while requiring
    source metadata only for the role-array format that the prompt now asks the
    LLM to emit.

- 2026-05-21
  - Minimality review reduced the stored metadata shape to provenance only:
    `slot`, `role`, `source_kind`, `source_value`. Do not duplicate hourly
    rates or time values in `role_sources`, because editable values can change.
  - Plan refined to avoid changing the legacy admin-only
    `update_process_step_effort_split` helper unless a test proves it is needed;
    the production path is `upsert_process_step_effort_split_by_addressee`.
  - Explicitly decided not to validate whether the reported hourly wage matches
    the handbook table row in this issue; the feature documents the selected row
    and preserves it for review.

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

- [ ] Add `role_sources_current_json` and `role_sources_proposed_json` to
      `process_steps`, including table creation, legacy migration, decoding,
      encoding, and clearing during effort undo/reset.
- [ ] Extend `EFFORT_JSON_SCHEMA_DEFAULT` and `EFFORT_METHOD_GUIDANCE` only for
      `administration` and `business`: roles should include
      `verwaltungsebene` or `wirtschaftsabschnitt`; citizens stay role-free.
- [ ] Extend `_parse_role_entries` to return role-source metadata alongside the
      existing hourly-rate and time dictionaries.
- [ ] Keep each role-source item minimal: `slot`, `role`, `source_kind`,
      `source_value` only.
- [ ] Validate business sources as WZ sections `A` through `N` and `P` through
      `S`; normalize labels such as `I Gastgewerbe` or `WZ I` to `I`.
- [ ] Validate administration sources as `bund`, `laender`, `kommunen`,
      `sozialversicherung`, or `durchschnitt`; normalize common German aliases
      such as `Länder`.
- [ ] Reject role-array entries that contain `stundenlohn` or
      `zeitaufwand_in_min` but omit the required source field. Legacy flat
      fields remain accepted without role-source metadata.
- [ ] Persist parsed role-source metadata through
      `upsert_process_step_effort_split_by_addressee`; preserve it naturally
      when users edit effort values through the editable metrics API.
- [ ] Expose decoded role-source arrays in `EditableProcessStepRow` and frontend
      types.
- [ ] Show compact read-only provenance tags below the relevant time inputs in
      `EaEffortMetricsTab`; do not make role sources editable in this issue.
- [ ] Add focused backend and frontend regression tests for prompts, parsing,
      persistence, editable API preservation, undo/reset clearing, and UI tags.

## Decisions

- Keep PR #35 as the GitHub PR shell and rebuild its branch from `develop`.
- Store wage-source metadata separately from editable effort values so manual edits do not rewrite provenance.
- Validation belongs in effort parsing, before persistence.
- Citizens do not get role wage-source fields because citizen effort is not monetized by role.
- Legacy flat effort fields are a compatibility path and do not get synthetic
  role-source metadata.
- The implementation does not validate wage amounts against handbook table
  values; it records the source row chosen by the LLM for auditability.
- Do not change `update_process_step_effort_split` unless needed by a failing
  regression test; prefer the addressee-aware upsert path for new behavior.

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
