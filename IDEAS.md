# Future ideas — design directions deferred from v1

A running list of ideas considered during design conversations but not built into v1. These are not commitments. Each entry should carry enough context that the idea can be picked up from cold.

## Autonomous evaluator loop in sub-phase 2 of `/dev-execute` (deferred 2026-05-19)

### The idea

Replace the simple "orchestrator drafts → show to user → approve/refine" flow of sub-phase 2 (implementation plan) with a bounded autonomous self-review loop driven by two subagents:

- **Drafter subagent (Sonnet)** writes the impl plan
- **Evaluator subagent (Sonnet, critical-reviewer prompt)** runs a rubric and returns `{approved: bool, reasons: [...]}`
- If rejected, drafter receives the reasons and re-drafts → loop
- Hard cap: 3 iterations
- After 3 strikes, escalate to the user — they pick from v1/v2/v3, edit manually, or abandon

User is not in the loop while it runs.

### What it would have added

- Two-subagent dispatch with independent context windows
- Judgment rubric items: concreteness, pattern grounding, gotcha handling, scope discipline, self-sufficiency
- Iteration log artifact (`impl-plan-log.md`) capturing each draft + verdict + reasons
- Autonomy — drafter and evaluator converge without user in the planning loop

### Why deferred for v1

- No data yet that drafter plans are actually bad — premature optimization
- Same-model subagent separation provides less independence than it suggests (rubber-stamp risk persists)
- Judgment-rubric items are noisy without ground truth to tune against
- Cost: up to 6 subagent calls per subtask × ~5 subtasks per issue ≈ 25–30 calls just for impl planning
- The user checkpoint at sub-phase 2 is cheap; catching disagreement there beats catching it at execute time

### When to reconsider

- After v1 has been used on several real issues
- If observed drafter plans need substantive refinement on ≥30% of subtasks
- If batch / overnight execution becomes desired and manual approval is the bottleneck
- If a clear rubric emerges from the kinds of mistakes drafters actually make

### What v1 has instead

- Orchestrator drafts impl plan directly (no subagent)
- Mechanical checks only (no judgment rubric)
- User reviews and either approves, refines with comments, or abandons
- Capped at 2 internal re-drafts for mechanical-check failures + user refinements
- Artifacts: `execution/NN-<slug>/impl-plan.md` + `execution/NN-<slug>/impl-plan-log.md`
