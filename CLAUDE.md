@AGENTS.md
@AGENT_USER_GUIDE.md

# Claude Code

- Use the imported repo guidance above as the default workflow and engineering contract.
- In this repo, `.codex/agents/*.toml` are role specifications for Codex behavior; the active Claude-native subagents are defined under `.claude/agents/`.
- For new features or exploratory implementation, use the `feature-developer` subagent.
- `feature-developer` must inspect the code, ask clarifying questions when needed, write/update `workplans/feature-<slug>.md`, propose a plan, and wait for explicit approval before editing code.
- For formal branch or working-tree review, use the `reviewer` subagent.
- For review-driven implementation from a review action list, use the `fixer` subagent.
- For CCC workflow/session-state/LLM-monitor diagnosis, follow the repo-local workflow debugging guidance and use the matching subagent when helpful.
- Keep changes aligned with the existing repo structure, layering, and testing style described in the imported files.
