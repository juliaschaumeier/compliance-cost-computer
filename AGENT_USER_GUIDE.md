# Agent User Guide

## Purpose

This is the human-facing guide for the repo-local agent setup.

Use it to answer these questions:

| Question | See |
| --- | --- |
| Where do the repo rules live? | `Runtime Model` |
| How do I invoke roles in Codex or Claude Code? | `Runtime Model`, `Invoking Roles` |
| Which role or helper should I ask for? | `Choose A Starting Point`, `Roles`, `Skills` |
| What should I expect next? | `Roles`, `Example Timeline` |
| What does a typical feature flow look like? | `Example Timeline`, `Quick Prompt Examples` |

## Runtime Model

- `AGENTS.md` and `.agents/skills/*` are the shared guidance layers.
- `CODING_ASSISTANT.md` is the canonical engineering guide for repo rules and layering expectations.
- `.codex/agents/*.toml` define Codex role behavior.
- When you name a Codex role, Codex should decide whether to use native role/subagent support or to follow the corresponding `.codex/agents/*.toml` role spec in the current session.
- If a native Codex role cannot start because its model is unavailable in the current runtime, Codex should fall back to the matching `.codex/agents/*.toml` behavior spec with an available default subagent or mimic the role locally.
- Naming a role should imply its full behavior contract. For example, `feature_developer` should inspect the code, ask clarifying questions, create or update a workplan, and wait for approval before editing.
- `.claude/agents/*` are Claude Code-native subagent definitions.
- `CLAUDE.md` is the Claude Code entrypoint for this repo.

Important local artifact folders you may see during work:
- `workplans/`
  - feature planning artifacts
- `review/`
  - reviewer output
- `fixer/`
  - fixer output

## Invoking Roles

### Codex

- Open the repo from the project root.
- Ask for the work and name the role you want to use.
- If the role is `feature_developer`, expect questions and a plan before any implementation starts.
- If the role is `reviewer`, expect review artifacts under `review/`.
- If the role is `fixer`, point it to the relevant review output when needed.

### Claude Code

- Open the repo from the project root.
- Claude Code reads `CLAUDE.md` and can use subagents from `.claude/agents/`.
- Use `/agents` if you want to inspect available subagents.
- Ask for the work and name the subagent you want to use.
- For feature work, expect questions and a plan before implementation starts.

## Choose A Starting Point

- Use `feature_developer` for new features, scoped improvements, or exploratory implementation.
- Use `reviewer` for a formal branch review or working-tree review.
- Use `fixer` when you already have formal review findings and want narrow follow-up changes.
- Use `code_mapper` when you want a read-only map of files, paths, and likely risk areas.
- Use `docs_researcher` when framework or API behavior needs confirmation from authoritative docs.
- Use `bug-triage` or `ccc-workflow-debug` when the main question is what is broken and why.

## Roles

### `code_mapper`

Use when:
- you want read-only discovery before a review or non-trivial change

What it should do:
- map changed files, execution paths, and cross-layer dependencies
- identify risky modules and likely regression edges
- stay read-only

What to expect:
- a concrete map of likely files, call paths, and risk areas

### `feature_developer`

Use when:
- the task is a new feature, scoped improvement, or exploratory implementation

What it should do:
- inspect relevant code first
- ask clarifying questions when scope or contracts are unclear
- create or update `workplans/feature-<slug>.md`
- propose a plan
- wait for explicit approval before editing code
- implement in small increments after approval

What to expect:
- questions if something is unclear
- a workplan and approval checkpoint before implementation

### `reviewer`

Use when:
- you want a formal branch review or working-tree review

What it should do:
- produce findings-first review output
- focus on correctness, regressions, security, missing tests, and simplification opportunities
- write review artifacts under `review/`

What to expect:
- review findings
- a fixer-ready action list

### `fixer`

Use when:
- there is already a concrete review output or Fixer Input Pack to apply

What it should do:
- implement reviewed follow-up items narrowly
- validate review compatibility where applicable
- add the smallest useful regression test when behavior changes

What to expect:
- a narrow follow-up patch scoped to the review findings

### `docs_researcher`

Use when:
- framework or API behavior needs confirmation from authoritative docs

What it should do:
- verify behavior against documentation
- return concise findings with exact references

What to expect:
- a short answer grounded in docs rather than repo guesswork

## Skills

Skills are smaller workflow helpers. They usually support a role rather than replacing it as the main strategy for a larger task.

### `feature-workplan`

Typically used by:
- `feature_developer`

Purpose:
- manages the approval-gated workplan loop in `workplans/feature-<slug>.md`
- keeps plan updates readable without mental diffs

### `bug-triage`

Typically used for:
- direct bug investigation

Purpose:
- classify a concrete bug
- identify likely root cause
- suggest the smallest safe fix direction

### `ccc-workflow-debug`

Typically used for:
- CCC workflow failures involving run-all, session state, LLM monitor state, or prompt/output contract mismatches

Purpose:
- provide repo-specific debugging guidance for the core workflow

### `add-regression-test`

Typically used by:
- `feature_developer`
- `fixer`

Purpose:
- add the smallest targeted regression test after a bug fix or behavior change

### `api-doc-check`

Typically used by:
- `docs_researcher`
- any role that needs confirmation of API or framework behavior

Purpose:
- verify assumptions against authoritative docs

## Example Timeline

### Example: session PDF export

Assume you are already working on branch `45-session-pdf-export`.

1. Optional read-only discovery
   - User: `Please use the code mapper to map the files and execution paths involved in adding PDF session export on branch 45-session-pdf-export.`
   - Purpose: get a read-only picture of likely frontend, backend, and test touch points.

2. Start feature work
   - User: `Please use the feature developer to create a new button in the frontend that lets the user export the session as a PDF.`
   - Purpose: start the planning workflow for the feature.

3. Respond to clarification and planning
   - User answers questions and approves the proposed plan.
   - Purpose: let `feature_developer` proceed to implementation.

4. Request formal review after implementation
   - User: `Please use the reviewer to review branch 45-session-pdf-export vs develop.`
   - Purpose: get a formal findings-first review and review artifacts for the implemented feature.

5. Apply review follow-up if needed
   - User: `Please use the fixer to apply the review findings for branch 45-session-pdf-export from review/review_output.md.`
   - Purpose: implement reviewed follow-up items narrowly.

6. Re-review after fixes if needed
   - User: `Please use the reviewer to re-review branch 45-session-pdf-export vs develop after the fixes.`
   - Purpose: confirm the branch is ready.

## Quick Prompt Examples

### Codex

- `Please use the code mapper to map the affected files and execution paths.`
- `Please use the feature developer for this task.`
- `Please use the reviewer to review this branch vs develop.`
- `Please use the fixer to apply the review findings from review/review_output.md.`
- `Please use the docs researcher to verify the API behavior.`

### Claude Code

- `Use the code-mapper subagent to map the affected files and execution paths.`
- `Use the feature-developer subagent for this task.`
- `Use the reviewer subagent to review this branch vs develop.`
- `Use the fixer subagent to apply the review findings.`
- `Use the docs-researcher subagent to verify the API behavior.`

### Shared repo-specific examples

- `Use the repo's workflow-debug guidance to diagnose why this app_session_id is stuck in run-all.`
- `Use the bug-triage skill to classify this regression, identify the likely root cause, and suggest the smallest safe fix.`
- `After the fix, use the add-regression-test skill and add the smallest targeted regression test.`
