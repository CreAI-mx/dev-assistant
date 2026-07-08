---
description: Walk the plan phase for one issue — produces plan/plan.md (subtasks, coverage, dependencies) and plan/report.md (planning process narrative)
argument-hint: <issue-id>
model: opus
allowed-tools: Bash(dev-assistant:*), Read, Write, Edit
---

You are running the **plan** phase for issue `$ARGUMENTS`.

## Current state of the issue

!`dev-assistant issue show --id $ARGUMENTS`

## Strategies that shape this phase

The branching strategy drives commit message format, branch naming, and commit type selection. The PR template informs subtask sizing. The output style governs how `plan.md` and `report.md` are written.

### Branching strategy (resolved: per-repo override → source default)

!`dev-assistant strategies show branching-strategy`

### PR template (resolved: per-repo override → source default)

!`dev-assistant strategies show pr-template`

### Output style — how to write the artifacts this phase produces

!`dev-assistant strategies show output-style`

**Follow the output style above when writing `plan.md` and `report.md` in sub-stage 5.** Frontmatter, headings, voice, quoting rules, length per section, what to avoid — all of it. The style applies to both files.

### Repo context — repo-specific rules to respect

!`dev-assistant repo-context show`

The above is the target repo's own guideline documents (workflows, naming, lifecycle constraints, PR checklists, etc.). Apply on top of the strategies. When planning, weave repo-context rules into the decomposition: if a rule requires a `MANIFEST.md` for new artifacts, or a `CHANGELOG.md` bump for dataset versions, or specific naming, the subtasks and their passing criteria must reflect that. If a repo-context rule conflicts with a strategy, the repo-context rule wins.

---

## Decomposition model

A subtask is a **logical unit of work that produces 1–3 commits**. The dependency graph operates at subtask level. The goal is fewer subtasks while letting each subtask span multiple commits when the work naturally clusters that way.

- **Subtasks per issue: 2–5**, biased toward the low end.
- **Commits per subtask: 1–3**, hard cap at 3.
- **Total commits per PR: aim 4–8**, hard backstop at 10.

When a subtask would need 4 commits, that's a signal it should be two subtasks. When a subtask is "really just one commit," set `commits: 1`.

### Branching mode

Every issue is executed in one of two branching modes. The choice is made in sub-stage 4 and recorded as `branching_mode` in `plan.md` frontmatter:

- **`single-branch`** (default) — one `feat/<TICKET>-<slug>` branch (off `develop`) for the whole issue. Subtasks land as commits on it. A draft PR → `develop` opens at execute start (sub-phase 1c) and is marked Ready at wrap-up. The per-PR commit backstop (≤10) applies to the issue total.
- **`sub-branches`** — each subtask gets its own `feat/<TICKET>-<slug>-sub-N` branch off the parent feature branch, with its own sub-PR (target: the parent feature branch) opened at subtask completion. The parent's draft PR → `develop` still opens at execute start and is marked Ready at wrap-up once all sub-PRs are merged. The per-PR backstop applies per sub-PR (trivially satisfied at ≤3 commits each); the issue-level commit total may exceed 10.

Recommend `sub-branches` when the total commit estimate pushes past the 8–10 band, when subtasks are independent enough to review in isolation, or when the user wants work landing incrementally instead of one big PR at the end. Otherwise default to `single-branch`. The user always decides.

## What this phase produces

Two artifacts in `.dev-assistant/issues/$ARGUMENTS/plan/`:

1. **`report.md`** — the *thinking artifact*. Process narrative: how the decomposition was approached, why this sequencing, alternatives considered and rejected, viability outcomes, risks going into execute.
2. **`plan.md`** — the *decision artifact*. Single canonical file with everything `/dev-execute` will need: branch info, coverage map, dependency graph, full subtask specs inline with frontmatter (`id`, `depends_on`, `covers_objectives`, `strategies`, `status`, `commits`).

Two files, two purposes. Don't merge them.

## What this phase does NOT do

- No GitHub issue created
- No git branch created
- No commits, no push, no PR, no Jira comment
- No reading of source code to assess feasibility (that's `/dev-execute`'s implementation-plan sub-stage)

Plan is read-only on the world, write-only on `.dev-assistant/issues/$ARGUMENTS/plan/`. All side effects are deferred to `/dev-execute`.

## How to interact with the user

This phase requires real conversation. **Every sub-stage has a user pause — when one of them is reached, stop and wait for the user's actual response.** Do not synthesize answers on the user's behalf, even when running in autonomous / auto-accept modes.

Backtracking is allowed at any time. If the user says "go back to sub-stage 2", do so — earlier decisions are not locked in until the write step in sub-stage 5.

## How to run this phase — five sub-stages

Announce which sub-stage you're entering before each one so the user knows where they are. Don't move on until the current sub-stage has a settled outcome.

### Sub-stage 1 — Context load

Use Read to load:

- `.dev-assistant/issues/$ARGUMENTS/gathering/objectives.md` (the decision artifact from gather — required)
- `.dev-assistant/issues/$ARGUMENTS/gathering/report.md` (the thinking artifact from gather — context only, do not paraphrase)

If `gathering/objectives.md` does not exist, stop and tell the user to run `/dev-gather $ARGUMENTS` first.

Summarize for the user:

- The number of specific objectives this phase will plan against
- Any constraints or open questions carried over from gather
- Which strategies were resolved (note whether each came from per-repo override or source default — visible in the HTML comment at the top of each strategy)

Then confirm: *"Is this the right context to plan from?"*

**Pause for user confirmation.** If they want to go back to gather, stop here.

### Sub-stage 2 — Decomposition proposal

Propose a first-pass decomposition: 2–5 subtasks at a high level. Don't fill in full specs yet — just shape, and a rough sense of how many commits each will be.

Present a table to the user with one row per subtask:

| # | Title (imperative) | One-line purpose | Covers objectives | Estimated commits (1–3) |

Constraints to enforce:

- **Subtask count must be in the 2–5 band, biased toward the low end.** Each subtask is a *logical unit of work*, not a single commit — a subtask can produce 1–3 commits when the work naturally clusters that way. Below 2 → ask "is this issue really big enough to need a plan, or just do it?" Above 5 → push back: "should this be two issues, or can two subtasks be merged?"
- **Every specific objective from `objectives.md` must be covered by ≥1 subtask.** Flag any uncovered.
- **Every subtask must trace to ≥1 objective.** If a proposed subtask doesn't, flag it as scope creep — drop it or fold it into another.
- **Each commit's type (set in sub-stage 3) must be one of the types listed in the loaded branching-strategy.** A `feat/` branch should carry predominantly `feat | refactor | test | chore | docs` types; `fix` only when the issue is bug-driven.
- **Estimated commit total across all subtasks should aim for 4–8, hard backstop at 10.** If the early estimate is above 10, you're either oversizing subtasks (split the issue) or over-committing within them (merge logically related commits).

**Pause for user input.** Iterate with the user — "merge 1 and 2", "subtask 4 only needs 1 commit not 3", "you're missing coverage of O3" — until the shape settles.

### Sub-stage 3 — Subtask elaboration

For each subtask agreed in sub-stage 2, **in order**, fill in the full spec. Walk one subtask at a time. Show the user the elaborated spec, iterate, lock it in, move to the next.

For each subtask, produce:

- **Objectives** (1–3 lines) — what done looks like for this specific subtask
- **What's affected** — files / modules / external systems this subtask touches. **Keep to ≤4 bullets** (slightly more permissive than the per-commit rule since a subtask can span multiple commits). If you can't, the subtask is hiding a fourth commit — split into two subtasks.
- **Passing criteria** — 3–5 checkbox items. Each one is something `/dev-execute` will be able to verify mechanically (a file exists, a test passes, a function returns X). Criteria are at the subtask level, not per-commit.
- **Strategies that apply** — list by name (e.g. `[branching-strategy, output-style]`); never embed their content
- **Commit count** — confirm with the user: "1, 2, or 3 commits for this subtask?" Default to the estimate from sub-stage 2; ask before changing. Hard cap at 3.
- **Commit message previews** — one per commit. Each follows the loaded branching strategy's Conventional Commits format:
  - Type: from the strategy's allowed types (`feat | fix | refactor | chore | docs | test | perf | ci`), chosen per commit based on what that specific commit does
  - Scope: the primary module the commit touches
  - Description: capitalized, imperative, no trailing period
  - Body bullets: `- <keyword>: <very short summary>` form
  - Footer: `refs $ARGUMENTS` on every commit

**Pause for user input, per subtask.** This is the longest and most important sub-stage — vague specs here become bad commits later. Push back on hand-wavy passing criteria ("works correctly" → what does that mean?). Push back on commit message previews that don't tell you what the commit actually does.

### Sub-stage 4 — Sequencing and branch info

Now propose the full picture:

- **Dependency graph**: for each subtask, set `depends_on: [<ids>]`. Default linear (subtask N depends on N-1). Mark any safe parallels (`depends_on: []` when truly independent) — useful metadata for future fan-out, even though `/dev-execute` is per-subtask serial. Dependencies are between subtasks, not between commits within a subtask.
- **Flow**: `feature` (default) or `hotfix`. Hotfix is for emergency fixes that must reach UAT before the next normal deploy — the ticket usually says so explicitly; when in doubt, it's a feature. Choosing `hotfix` forces: branch pattern `hotfix/$ARGUMENTS-<slug>`, base + target branch `uat`, `single-branch` mode, 1–2 subtasks, `fix`-type commits, and a second sync PR → `develop` at the end (opened at execute wrap-up, merged by `/dev-merge` — per the branching strategy, every hotfix needs two PRs or the branches drift). Record as `flow` in frontmatter.
- **Branch slug**: `feat/$ARGUMENTS-<short-slug>` (`hotfix/$ARGUMENTS-<short-slug>` in the hotfix flow) where `<short-slug>` is 2–4 kebab-case words derived from the issue purpose. Keep it short and specific.
- **Branching mode**: propose `single-branch` or `sub-branches` per the criteria in the decomposition model, with a one-line rationale (e.g. "total estimate is 9 commits and subtasks 02–04 are independent — recommend `sub-branches`"). The user decides; record the outcome. (Hotfix flow: always `single-branch`.)
- **Target branch**: resolved from the loaded branching strategy — never assumed. In the default strategy that means `develop` for the feature flow and `uat` for the hotfix flow; if the per-repo strategy override names different long-lived branches, use those. State where the value came from (which strategy document, which section). Record as `target_branch` in frontmatter — `/dev-execute` reads it from there and verifies it exists on `origin` before branching.
- **Coverage map**: a table showing which subtasks cover which objectives. Mechanical check — confirm every specific objective is covered.

Present all six to the user.

**Pause for user input.** They may redirect on order ("3 must come before 2"), slug ("call it `oauth-flow`, not `add-oauth-flow`"), or coverage gaps.

### Sub-stage 5 — Viability check and write

The final rigor pass + write.

**Mechanical checks (you verify):**

- Every specific objective from `objectives.md` is covered by ≥1 subtask
- Every subtask traces to ≥1 objective
- Dependency graph is acyclic and well-formed
- Subtask count is in the 2–5 band
- No subtask has more than 3 commits (`commits` field ≤3)
- Total commits across all subtasks ≤10 (backstop against giant PRs) — **waived in `sub-branches` mode** (each sub-PR is ≤3 commits by construction); a total above 10 in `single-branch` mode is instead a prompt to switch to `sub-branches` or split the issue
- Each commit's `type` is in the branching strategy's allowed types
- Commit types match branch purpose (on a `feat/` branch, no `fix` unless the issue is bug-driven; on a `hotfix/` branch, predominantly `fix`)
- Branch slug matches the strategy's pattern for the chosen flow (`feat/<TICKET>-<slug>`, or `hotfix/<TICKET>-<slug>` for hotfixes)
- Hotfix flow: `branching_mode` is `single-branch`, subtask count is 1–2, `target_branch` is the strategy's UAT branch

If any mechanical check fails, loop back to whichever sub-stage needs to change (2 for decomposition, 3 for spec, 4 for sequencing).

**Conversational checks (ask the user, one at a time):**

1. *"For each subtask: is the commit count honest? A 1-commit subtask hiding 2 deserves to be 2 commits; a 3-commit subtask hiding 4 deserves to be split into two subtasks."*
2. *"External dependencies — any other tickets, people, APIs, feature flags we haven't called out?"*
3. *"What's the riskiest subtask, and what's plan B if it doesn't pan out?"*
4. *"Would you be surprised if this took two times as long as the plan suggests?"*

If the user surfaces issues, loop back to the relevant earlier sub-stage.

**When viability passes**, show the user a preview of both files (don't write yet). Ask for final confirmation.

On confirm, write **two files** in this order.

**First**: `.dev-assistant/issues/$ARGUMENTS/plan/report.md`

~~~markdown
---
issue: $ARGUMENTS
phase: plan
status: complete
---

# Planning report — $ARGUMENTS

## Summary

One paragraph: what we set out to plan, how the decomposition crystallized, the key tension or judgment call that emerged.

## Decomposition approach

How the objectives were mapped to subtasks. Which decompositions were tried before settling on this one. Why this number of subtasks rather than fewer or more. How commits-per-subtask were decided (when the work clusters into a single commit vs spans 2–3).

## Sequencing rationale

Why this order. Where dependencies come from (technical, logical, or just convenient). Any places where order was a judgment call rather than a hard constraint.

## Alternatives considered

Approaches discussed and rejected, with why. Brief — one or two lines per alternative.

## Viability outcomes

What the mechanical checks said. What the conversational rubric surfaced (risks the user flagged, surprises, plan-B thinking).

## Risks going into execute

Things to keep an eye on during execution. Open uncertainties that may force replanning. Subtasks the user identified as riskiest.
~~~

**Second**: `.dev-assistant/issues/$ARGUMENTS/plan/plan.md`

~~~markdown
---
issue: $ARGUMENTS
phase: plan
status: complete
flow: <feature | hotfix>
proposed_branch: <feat | hotfix>/$ARGUMENTS-<slug>
branching_mode: <single-branch | sub-branches>
target_branch: <develop | uat | per-repo override>
total_subtasks: <n>
total_commits: <sum of commits across subtasks>
---

# Plan — $ARGUMENTS

See [report.md](./report.md) for the planning process, alternatives, and viability discussion.

## Branch info (proposed — `/dev-execute` creates the branches)

- **Flow**: `feature` (normal work targeting the integration branch) or `hotfix` (emergency fix off `uat`, plus a sync PR → `develop` at the end)
- **Feature branch**: `feat/$ARGUMENTS-<slug>` (off the target branch) — `hotfix/$ARGUMENTS-<slug>` in the hotfix flow
- **Branching mode**: `single-branch` (subtasks land as commits on the feature branch; draft PR → target at start, marked Ready at wrap-up) or `sub-branches` (each subtask gets `feat/$ARGUMENTS-<slug>-sub-N` off the feature branch with its own sub-PR at completion; parent draft PR → target at start, marked Ready at wrap-up)
- **Target branch**: `<target_branch>`, resolved from the branching strategy (`<which document/section it came from>`). `/dev-execute` verifies it exists on `origin` before branching and every branch/rebase/PR operation uses it — nothing downstream hardcodes `develop`.
- **GitHub issue**: not yet created — `/dev-execute` creates it on the first subtask. One GH issue per Jira parent ticket, regardless of branching mode (Jira subtasks never get their own GH issue)

## Coverage map

| Specific objective (from `gathering/objectives.md`) | Subtask(s) |
|---|---|
| O1: ... | 01 |
| O2: ... | 02, 03 |

## Dependency graph

01 → 02 → 03 → ...

(Or describe explicitly which subtasks have non-trivial deps; mark any parallel-safe ones with `depends_on: []`.)

## Subtasks

### Subtask 01 — <imperative title>

- **id:** 01
- **depends_on:** []
- **covers_objectives:** [O1]
- **strategies:** [branching-strategy, output-style]
- **status:** pending
- **commits:** 2

**Objectives**

- What done looks like for this subtask

**What's affected**

- `path/to/file.py`
- `path/to/other.py`
- `path/to/test.py`

**Passing criteria**

- [ ] Mechanically verifiable item
- [ ] Mechanically verifiable item

**Commits**

Commit 1:

```
feat(scope): Description for first commit

- add: very short summary
- add: very short summary

refs $ARGUMENTS
```

Commit 2:

```
test(scope): Description for second commit

- test: very short summary

refs $ARGUMENTS
```

### Subtask 02 — ...

(Same shape as Subtask 01. For a 1-commit subtask, show only `Commit 1:`.)
~~~

After writing both files, give the user a one-paragraph summary of what was decided.

Then run a **final revision pass**. Ask the user:

> *"Anything you want to revisit now that the plan is on paper? Common things to change at this point — too many subtasks, a redundant one to drop or merge, one that's hiding two and should be split, passing criteria that look too vague on a second read, a commit count that feels off (too low for the work, or too high and worth merging), or a dependency order that feels wrong."*

This is a deliberate pause point. The user is seeing the concrete artifacts for the first time and may react to them differently than they did to the previews. If they want changes:

- Edit the relevant sections of both files directly (keep `plan.md` and `report.md` in sync — e.g., dropping a subtask means updating the coverage map, the dependency graph, the total_commits frontmatter field, and the report's decomposition section).
- Show the user the updated state and confirm.
- The final revision pass can be re-asked once if a chain of changes warrants it, but don't loop indefinitely — two revision passes maximum, then close out.

When the user confirms they're done, remind them:

- They can re-run `/dev-plan $ARGUMENTS` anytime later for more substantial revisions (the command handles re-runs idempotently — see below).
- The next phase will be `/dev-execute $ARGUMENTS` (not yet implemented).

## If the files already exist

The user is re-running plan. Show them the current contents of both files, ask which sections they want to revise, and only edit those sections rather than starting over. Keep both files in sync if changes affect both.
