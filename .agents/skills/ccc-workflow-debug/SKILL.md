---
name: ccc-workflow-debug
description: Diagnose CCC workflow failures involving run-all, session state, LLM monitor state, prompt/output contract mismatches, and DB-backed step transitions.
---

1. Confirm the user-facing scope first: `app_session_id`, failing route, visible UI symptom, and which workflow step appears affected.
2. Map identifiers before deeper analysis:
   - resolve `app_session_id` to `session_id`
   - identify relevant `run_id`, `answer_id`, `attempt_id`, `request_id`, or entity IDs if present
3. Reconstruct the workflow state in canonical 7-step order:
   - `summary`
   - `regulations`
   - `processes`
   - `case_groups`
   - `process_steps`
   - `effort`
   - `total_cost`
4. Check the failure boundary across layers:
   - router orchestration and validation
   - core prompt/orchestration/monitor behavior
   - DB state, integrity rules, and transaction effects
5. Distinguish the class of failure explicitly:
   - prompt/backend contract mismatch
   - stale or duplicate UI/monitor state
   - DB integrity or migration issue
   - run-all orchestration or retry behavior
   - frontend state/setup issue
6. When monitor or streaming state looks wrong, compare in-memory monitor status with persisted DB state before concluding work is still running.
7. Prefer evidence-backed explanations:
   - identify the exact failing step
   - point to the exact validator, prompt rule, or persistence rule involved
   - note when timestamps, attempt IDs, or request IDs indicate multiple runs
8. Give the smallest safe next action:
   - user workaround if needed
   - minimal code fix direction
   - one focused regression test or diagnostic check
9. Keep outputs findings-first and repo-specific. Do not convert this into a generic framework review or a formal branch review.
