# Agent One-Pager

Use this repo’s local agents and skills by intent, not by model strength.

## Portability

- `.codex/` contains Codex-native agent configs.
- `.agents/skills/` contains more portable markdown workflows.
- `AGENTS.md` and `CODING_ASSISTANT.md` are the repo-wide rule sources other assistants can also follow.

## How To Use

### Codex

- Open the repo in Codex from the project root.
- Codex reads the repo-local instructions from `AGENTS.md` and the `.codex/` agent definitions.
- For normal use, ask directly for the task and name the role when helpful:
  - `Use the feature_developer agent for this feature`
  - `Use the reviewer agent to review this branch vs develop`
  - `Use the fixer agent to apply the review output`
- For feature work, expect the `feature_developer` flow:
  - code inspection
  - clarifying questions
  - workplan update in `workplans/feature-<slug>.md`
  - explicit approval checkpoint before code edits

### Claude Code

- Open the repo in Claude Code from the project root.
- Claude Code reads `CLAUDE.md`, which imports the shared repo guidance.
- Project subagents are available from `.claude/agents/`.
- Use `/agents` to inspect available subagents, or invoke one explicitly:
  - `Use the feature-developer subagent to plan this feature`
  - `Use the reviewer subagent to review this branch vs develop`
  - `Use the fixer subagent to apply the review findings`
- For feature work, the `feature-developer` subagent follows the same workplan-and-approval loop used in the repo’s Codex setup.

## Agents

- `code_mapper`
  - Use for read-only mapping of changed files, execution paths, and risk areas.
  - Good first step before a review or a non-trivial fix.
  - Does not edit code.

- `feature_developer`
  - Use for new features, scoped improvements, or exploratory implementation work.
  - First inspects code, then asks clarifying questions, writes a workplan, proposes a plan, and waits for approval before editing.
  - Uses `workplans/feature-<slug>.md` as the running source of truth for multi-loop work.

- `reviewer`
  - Use for formal branch review or working-tree review.
  - Produces findings-first output plus review artifacts under `review/`.
  - Only authority for review artifact generation.

- `fixer`
  - Use after a formal review when there is a `Fixer Input Pack` to apply.
  - Performs minimal, test-backed patches and validates review/HEAD compatibility before editing.
  - Not intended for open-ended feature work.

- `docs_researcher`
  - Use when framework/API behavior is uncertain and needs authoritative documentation.
  - Read-only.

## Skills

- `bug-triage`
  - Use for a specific bug report: reproducibility, impact, likely root cause, and smallest safe fix/test direction.
  - Not for branch-wide review or `review/` artifacts.

- `ccc-workflow-debug`
  - Use for CCC workflow failures involving run-all, session state, LLM monitor state, prompt/output contract mismatches, or DB-backed step transitions.

- `feature-workplan`
  - Use with `feature_developer`.
  - Keeps the approval loop readable by requiring a `What Changed Since Last Update` section in the markdown workplan.

- `add-regression-test`
  - Use after a bug fix or behavior change to add the smallest relevant regression test.

- `api-doc-check`
  - Use when an API/framework assumption needs confirmation from authoritative docs.

## Recommended Flows

- Feature work:
  - `feature_developer`
  - optional `reviewer`
  - optional `fixer` for follow-up review findings

- Bug investigation:
  - `bug-triage` or `ccc-workflow-debug`
  - optional `add-regression-test`
  - `feature_developer` or `fixer` depending on whether the change is exploratory or review-driven

- Branch review:
  - optional `code_mapper`
  - `reviewer`
  - `fixer`
  - optional `docs_researcher`

## Permissions Summary

- Read-only: `code_mapper`, `docs_researcher`
- Writes review artifacts only: `reviewer`
- Writes code directly: `feature_developer`, `fixer`

## Rule of Thumb

- If the task needs discovery, questions, plan approval, and a few loops: use `feature_developer`.
- If the task already has a review action list and should be implemented narrowly: use `fixer`.
- If the task is “what is broken and why?”: use `bug-triage` or `ccc-workflow-debug`.
- If the task is “is this branch good enough to merge?”: use `reviewer`.
