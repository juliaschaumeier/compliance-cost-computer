# Codex Agents (Project Local)

This project defines custom agents in `.codex/agents/` and shared skills in `.agents/skills/`.

## Portability Model

- `.codex/` is Codex-native configuration and agent wiring.
- `.agents/skills/` contains portable workflow guidance in Markdown where practical.
- `AGENTS.md` and `AGENT_ONE_PAGER.md` are the cross-tool, human-readable entry points for repo rules and agent usage.
- Repo-specific engineering expectations should live in `CODING_ASSISTANT.md` first, then be summarized here as needed.

## Canonical Project Rules

- Canonical technical/source-of-truth guide: `CODING_ASSISTANT.md`.
- Keep this `AGENTS.md` concise and agent-oriented.
- When behavior/rules change:
  1. update `CODING_ASSISTANT.md` first
  2. update `AGENTS.md` only if a critical invariant changed

## Critical Invariants (Quick Reference)

- Workflow is the 7-step pipeline (`summary` -> `total_cost`); EA editing is post-step (outside run-all).
- Run-all skips completed steps and only re-runs them after `undo` (revert/reset) of state.
- Step 6 (`effort`) performs paired parallel prompt calls (`cases_calculation` + `effort_calculation`).
- Keep layering boundaries:
  - routers orchestrate/validate requests
  - core services handle prompts/LLM/orchestration
  - DB layer owns persistence/integrity/transactions
- Change policy: implement first, then do a focused cleanup/refactor pass in the same work item.

## Portable Implementation Norms

- Match the existing code structure, naming, and style of the repo.
- Preserve layering boundaries:
  - routers orchestrate/validate
  - core services handle prompts/LLM/orchestration
  - DB layer owns persistence/integrity/transactions
- Keep changes focused; avoid parallel patterns and broad rewrites without strong reason.
- Ask clarifying questions when scope, UX, contracts, or data-model impact are unclear.
- Run the narrowest relevant tests first, then broaden only as needed.

## Intended Review Workflow

1. `code_mapper` maps changed files, call paths, and risk areas (read-only).
2. `reviewer` performs final review for correctness, regressions, security, and missing tests (artifact-only write under `review/`), starting with a change-intent summary.
3. `fixer` applies Fixer Input Pack items in strict priority order with minimal scoped patches and targeted tests (workspace-write).
4. `docs_researcher` verifies version-specific API behavior when uncertainty remains.

## Intended Feature Workflow

1. `feature_developer` inspects the code, asks clarifying questions, and writes/updates a workplan under `workplans/`.
2. User approves scope and plan explicitly before implementation starts.
3. `feature_developer` implements in small increments and updates the workplan after each meaningful loop.
4. `reviewer` can be used after implementation for formal review.
5. `fixer` applies any resulting Fixer Input Pack items.

## Short Prompts You Can Use

- `Please do an in-depth review of the currently checked-out branch compared to develop.`
- `Review this branch vs develop and list only critical/high findings.`
- `Quick review vs develop before I open a PR.`

Notes:
- Reviewer defaults to `origin/develop` when no base branch is specified.
- Output defaults to findings-first with severity ordering and test suggestions.
- Reviewer output includes a fixer-ready action pack for later implementation by a separate fixer run.
- Reviewer writes local review artifacts to `review/` (mandatory, overwrite each run):
  - `review/change_intent.md`
  - `review/review_output.md`
- Reviewer includes a short machine-readable `Review Context` block in section (1) and in `change_intent.md`:
  - base ref
  - base SHA
  - branch
  - review mode
  - compare spec
  - head short hash
  - scope clean
  - working-tree dirty (informational)
- Reviewer also writes commit-aware snapshots and metadata:
  - `review/<branch>_<base7>_<head7>_commits_change_intent.md` and `..._review_output.md` for `commits_only`
  - `review/<branch>_<head7>_workingtree_<clean|dirty>_change_intent.md` and `..._review_output.md` for `working_tree`
  - `review/review_meta.json`
- A review run is incomplete if either review artifact file is missing.
- Fixer writes local execution output to:
  - `fixer/FIXER_RUN_REPORT.md`

## Shared Skills

- `bug-triage`: classify a specific issue, impact, and likely root cause.
- `feature-workplan`: manage approval-gated feature work in a markdown workplan.
- `add-regression-test`: add smallest targeted test after bug fix.
- `api-doc-check`: verify framework/API assumptions against docs.
- `ccc-workflow-debug`: diagnose run-all/session-state/LLM-monitor failures in the CCC workflow.

## Guardrails

- Reviewers and docs agents do not edit code.
- Reviewer may write review artifacts under `review/` only.
- Reviewer is the only review-artifact authority; do not use `bug-triage` for branch reviews or artifact generation.
- Feature work that needs clarification or planning should use `feature_developer`, not `fixer`.
- `feature_developer` must ask clarifying questions when needed, write/update a workplan, and wait for explicit approval before editing code.
- Fixer should use reviewer Fixer Input Pack as primary scope and report explicit done/partial/blocked per item.
- Fixer should enforce HEAD-hash preflight by auto-resolving expected hash from metadata/report context/snapshot filename and block on mismatch unless user explicitly overrides.
- If review/fix scope is ambiguous, agents should ask the user before proceeding.
- Fixes should include the narrowest relevant tests first.
- Prefer focused, test-backed changes over broad refactors.
