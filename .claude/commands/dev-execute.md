---
description: Execute one subtask of an issue (or wrap up after all subtasks are done) — opens a draft PR to the plan's target branch at start, writes code, verifies passing criteria, commits, opens the subtask's sub-PR in sub-branches mode, and at wrap-up marks the (parent) PR ready for review (hotfix flow adds the develop sync PR)
argument-hint: <issue-id> [subtask-n | wrap-up]
model: opus
allowed-tools: Bash(dev-assistant:*), Bash(git:*), Bash(gh:*), Read, Write, Edit, Grep, Glob, Agent
---

You are running the **execute** phase for issue `$ARGUMENTS`.

## Argument parsing

`$ARGUMENTS` is one of:

- **`<issue-id>` alone** — pick up the next pending subtask from `plan.md`. If all subtasks are `status: done`, automatically enter **wrap-up mode**.
- **`<issue-id> <N>`** — explicitly target subtask `N` (1-indexed). Useful for re-running.
- **`<issue-id> wrap-up`** — force wrap-up mode (only valid if all subtasks are done).

Any of these may carry a trailing `--guided` / `--balanced` / `--auto` token, which overrides the issue's autonomy level for this invocation only.

Parse `$ARGUMENTS` accordingly at the start. The issue ID is the first whitespace-separated token; strip the autonomy token before interpreting the rest.

## Current state of the issue

!`dev-assistant issue show --id $1`

(`$1` is the issue ID alone — the subtask number / `wrap-up` token must never reach the CLI; it takes exactly one `--id` value.)

## Experimental mode

Read `.dev-assistant/issues/<issue-id>/issue.md` and check for `experimental: true` in the frontmatter. If set, **experimental mode is active for this entire invocation**, which changes behavior in specific places (called out below). Summary of what experimental mode does:

- **Sub-phase 1a** (external preparation): all prompts SKIPPED entirely. No Jira / GH ops attempted, no asking.
- **Sub-phase 1b** (local branch): `git fetch origin` is SKIPPED. Branch is created from the current HEAD instead of from `origin/<target_branch>`. The empty "open draft pr" commit is also SKIPPED (its only purpose is to seed the draft PR, which experimental mode never opens).
- **Sub-phase 1c** (draft PR at start): never runs — no push, no PR.
- **Branching mode**: forced to `single-branch` behavior regardless of `plan.md`'s `branching_mode` — sub-PRs can't open without external ops, so sub-branches would be pointless. Note this to the user if the plan says `sub-branches`.
- **Sub-phase 3.8** (sub-PR): never runs (follows from the forced single-branch behavior).
- **Sub-phase 4** (wrap-up): rebase, push, PR ready, and Jira comment are all SKIPPED. The reduction pass (4.2b), wrap-up report, and team message still run — they are local. Size is measured against `branch_base` instead of `origin/<target_branch>`.

Surface "experimental mode active — external ops will be skipped" up front so the user knows what's happening.

## Flow and target branch (read once, use everywhere)

Read from `plan.md` frontmatter, with defaults for plans written before the fields existed:

- **`flow`** — `feature` (default when missing) or `hotfix`. In the hotfix flow the branch is `hotfix/<TICKET>-<slug>`, base + target is the strategy's UAT branch, branching mode is forced `single-branch`, and wrap-up additionally opens a **sync PR → `develop`** (sub-phase 4.5b) — per the branching strategy, every hotfix needs two PRs.
- **`target_branch`** — the base and PR target for this issue (default `develop` when missing). **Every** branch, rebase, and PR operation below uses `<target_branch>` — the literal `develop` in examples means "the resolved target branch"; never hardcode it.

Surface both up front: *"Flow: feature · target branch: `develop` (from plan.md)."*

## Strategies that shape this phase

### Branching strategy (drives branch operations, commit messages)

!`dev-assistant strategies show branching-strategy`

### PR template (drives PR title and body at wrap-up)

!`dev-assistant strategies show pr-template`

### Comment style (drives Jira/GH comments)

!`dev-assistant strategies show comment-style`

### Code economy (drives how much code gets written, and the reduction pass)

!`dev-assistant strategies show code-economy`

**This one binds the code, not the prose.** Every impl plan, every subagent dispatch, and every diff review in this phase applies it. Size is measured, not eyeballed: `dev-assistant issue size --id <issue-id> [--worktree] [--band S|M|L]`.

### GH issue template (drives the GH issue body at sub-phase 1a — first subtask only)

!`dev-assistant strategies show gh-issue-template`

### Jira subtask template (drives the Jira subtask description at sub-phase 1a)

!`dev-assistant strategies show jira-subtask-template`

### Team update template (drives the Spanish team announcement at sub-phase 4)

!`dev-assistant strategies show team-update-template`

### Output style — how to write the artifacts this phase produces

!`dev-assistant strategies show output-style`

### Repo context — repo-specific rules to respect

!`dev-assistant repo-context show`

The above is the target repo's own guideline documents (workflows, naming, lifecycle constraints, PR checklists, etc.). Apply on top of the strategies during implementation. Commits must follow conventions described there (e.g., `data:` prefix for data PRs, MANIFEST/CHANGELOG updates), and the impl-plan in sub-phase 2 must address any repo-context requirements as explicit commits or passing criteria. If a repo-context rule conflicts with a strategy, the repo-context rule wins.

---

## Confirmation principle (non-negotiable)

**Nothing touches the outside world without explicit user confirmation.** This holds at every autonomy level and under Claude Code's auto-accept-edits mode. It covers:

- `git push` (any branch, any time)
- `gh pr create`, `gh pr edit`, `gh pr close`
- Issue creation on GitHub or Jira
- Comments on Jira or GitHub
- Jira transitions
- Any other operation that publishes state outside the local repo

Local operations (file edits, `git commit`, `git rebase`, branch creation) do **not** require confirmation — they are reversible and contained.

What the autonomy level changes is **how many times you ask**, never **whether** you ask.

## Autonomy level — how many checkpoints this phase fires

The `## Autonomy` block in the `dev-assistant issue show` output above resolves this issue's level (`guided` | `balanced` | `auto`). Issues created before the field existed resolve to `guided`.

| Kind of stop | `guided` | `balanced` | `auto` |
|---|---|---|---|
| **Approval** — the impl plan (2.3) | approve / refine / abandon | approve / refine / abandon | none — the plan is written, the mechanical checks still run, and the summary is reported as you start coding |
| **External** — push, PR, GH issue, Jira | one confirmation per operation | **one batch per sub-phase** (see below) | one batch per sub-phase |
| **Escalation** — commit hook failure, rebase conflict, criteria failing after auto-fix, unexpected files touched, sub-PR unmerged | stops | stops | stops |

**Never removed at any level in this phase:** the external-operations batch, the passing-criteria verification in 3.5, and every escalation in sub-phase 3. Code that fails its own criteria never proceeds silently.

### The external-operations batch (`balanced` / `auto`)

Instead of asking per operation, collect every external op due at this point in the phase and ask **once**:

```
EXTERNAL OPERATIONS — <sub-phase>, issue <issue-id>

1. CREATE GH ISSUE      title: "<title>"
                        body:  <first 3 lines…>  (full text at <path>)
2. CREATE JIRA SUBTASK  <parent>: "<summary>"  assignee: <you>
3. PUSH                 <branch_name> → origin  (<n> commits)
4. OPEN DRAFT PR        <branch_name> → <target_branch>
                        title: "<title>"       body: <first 3 lines…>
5. JIRA COMMENT         on <TICKET>: "Draft PR opened: …"

Approve all / drop specific ops (say which numbers) / abandon
```

Rules for the batch:

- **Show the real payload**, not a description of it. Titles and bodies in full or first-lines-plus-path; never "the usual PR body".
- **Fire in listed order** after approval, reporting each result on one line. If one fails, **stop** — do not continue down the list. That is an escalation.
- **Dropped ops** are recorded exactly as a declined per-op confirmation is today: state persists (`gh_issue_created: false`, `pr_url` unset) and the op is offered again at wrap-up.
- **At most one batch per sub-phase.** Sub-phase 1 (1a + 1c together), sub-phase 3.8 (`sub-branches` only), and wrap-up each get their own — they are separated by real work, so a single batch for the whole invocation would ask for approval on things that do not exist yet.
- **Merge is never part of a batch.** It does not happen in this phase at all (see `/dev-merge`).

At `balanced` / `auto`, add `autonomy: <level>` to the frontmatter of `impl-plan.md`, `execution-notes.md`, and `wrap-up-report.md`, and a **`## Decided without review`** section to the wrap-up report.

## How to interact with the user

- **Announce which sub-phase you're entering** before each one.
- **Be terse during work, full during decisions.** Per-commit progress is one line; per-subtask report is brief; sub-phase 4 wrap-up summarizes don't narrate.
- **Read the impl plan when shown to the user as a summary** (3–5 lines: approach, files affected, commit count). Full text is in the impl-plan.md file the user can open if they want.

---

## Sub-phase 1 — Preparation

This sub-phase prepares everything needed before the work begins. It has two halves: external (1a) and local (1b). 1a is fully optional and prompts per item; 1b is automatic.

### Sub-phase 1a — External preparation (skipped entirely in experimental mode)

If experimental mode is active, **skip this sub-phase entirely**. Print "experimental mode — skipping external prep" and proceed to sub-phase 1b.

**At `balanced` / `auto`, 1a asks nothing on its own.** Work out which items are due (using the checks below), draft their payloads, and hold them for the sub-phase 1 external batch — which fires at the end of 1c, together with the push and the draft PR. If 1c does not run (no new branch this invocation), fire the batch at the end of 1a instead. The rest of this sub-phase describes the `guided` per-item flow; the *content* of each item (what gets created, from which template, assigned to whom) is identical at every level.

Otherwise, for the current subtask `N`:

1. **Check issue-level state in `plan.md`:** has the GitHub issue been created? (`gh_issue_created` field)
   - If **no** and this is the first subtask being executed: ask the user *"Create the GitHub issue for `<issue-id>` now? (y/n, default n)"*.
   - On yes: build the issue body from `gh-issue-template`, populated with content from `gathering/objectives.md` + `plan/plan.md`. **CONFIRM the proposed title + body with the user before calling `gh issue create`.** Create with `--assignee @me` so the issue is assigned to whoever is authenticated in `gh` — never a hardcoded username. On success, record `gh_issue_created: true` and `gh_issue_number: <num>` in `plan.md` frontmatter.
   - On no: skip and continue. Will be offered again at wrap-up.

2. **Check subtask-level state:** has subtask `N`'s Jira subtask been pushed? (`jira_pushed` field in the subtask)
   - If **no**: ask *"Create Jira subtask for subtask `N` (`<title>`) now? (y/n, default n)"*.
   - On yes: check whether Atlassian MCP tools are available in this Claude Code session.
     - If yes: build the description from `jira-subtask-template`, populated with the subtask spec. Resolve the current Jira user via the Atlassian MCP (`atlassianUserInfo`) and set the subtask's **assignee** to that account ID — always the authenticated user running the phase, never a hardcoded name. **CONFIRM the proposed summary + description (and the assignee) with the user before creating.** On success, record `jira_pushed: true`, `jira_subtask_key: <key>`, `jira_description_populated: true` in the subtask frontmatter.
     - If no: tell the user "Atlassian MCP not available in this session — skipping Jira subtask creation. Push manually if needed." Skip without erroring.
   - On no: skip and continue. Will be offered again at wrap-up.

3. **(Edge case)** If `jira_pushed: true` but `jira_description_populated: false`: the user created the subtask manually but the description is empty. Offer to populate it now. Same flow.

After 1a, summarize what was done: "Created Jira subtask VN-742-3; GH issue already exists (#42); skipped one optional step." At `balanced` / `auto`, this summary comes after the batch fires, not after 1a itself.

### Sub-phase 1b — Local branch preparation (automatic, no confirm)

Local-only ops. **No user confirmation needed.** Just do it and report.

Read `branching_mode` from `plan.md` frontmatter. Treat a missing field as `single-branch` (plans written before the field existed). In experimental mode, force `single-branch` behavior regardless of the plan.

**Pre-flight:** verify all of, and stop on the first failure:

- Working tree is clean. If dirty: *"Working tree has uncommitted changes. Commit, stash, or discard them before running execute."*
- (Normal mode, first subtask only) the target branch actually exists on the remote: `git ls-remote --heads origin <target_branch>` returns a ref. If not: *"`origin/<target_branch>` does not exist — the plan's `target_branch` doesn't match this repo's branches. Fix `plan.md` or the per-repo branching strategy first."* Don't silently fall back to another branch.

**If `plan.md` frontmatter has `branch_created: false`** (this is the first subtask being executed for this issue):

- **In experimental mode:** branch from current HEAD. Record the base commit SHA. No empty commit (sub-phase 1c never runs).
  - `git checkout -b <proposed_branch>` (the full branch name from `plan.md`'s `proposed_branch` field — `feat/<TICKET>-<slug>`, or `hotfix/<TICKET>-<slug>` in the hotfix flow)
- **In normal mode:** branch from `origin/<target_branch>`.
  - `git fetch origin`
  - `git checkout -b <proposed_branch> origin/<target_branch>`
  - **Empty "open draft pr" commit** — the branch needs a commit that diverges from the target branch before sub-phase 1c can open a draft PR. Make it now, before any feature code:
    - `git commit --allow-empty -m "chore: open draft pr <proposed_branch>"` (pass via HEREDOC if your shell needs it)
- Record `branch_created: true`, `branch_name: <proposed_branch>`, `branch_base: <target_branch or HEAD>` in `plan.md` frontmatter.
- **In `sub-branches` mode, additionally:** create the first subtask's sub-branch off the parent just created: `git checkout -b feat/<TICKET>-<slug>-sub-<N>`. Record `sub_branch: feat/<TICKET>-<slug>-sub-<N>` in subtask `N`'s frontmatter in `plan.md`. (The empty commit lives on the parent branch; sub-branches inherit it as their base.)

**Otherwise** (the parent feat branch already exists for this issue):

- **In `single-branch` mode:** verify the current branch matches `plan.md`'s `branch_name`. If not, stop with *"Expected to be on `<branch>`, found `<current>`. Check out the right branch or reset state."* Proceed.
- **In `sub-branches` mode:**
  - **Re-entering a subtask that already has `sub_branch` recorded:** verify the current branch matches it. If not, stop with the same message shape. Proceed.
  - **Starting a new subtask `N`:** the sub-branch must be created from a tip that contains all prior subtasks' work.
    - Check the previous subtask's `sub_pr_url` state: `gh pr view <sub_pr_url> --json state`.
    - **If merged:** `git fetch origin`, `git checkout <branch_name>`, fast-forward to `origin/<branch_name>`, then `git checkout -b feat/<TICKET>-<slug>-sub-<N>`.
    - **If not merged (or no `sub_pr_url` recorded):** stop and ask the user, two options:
      - **(a) wait** — merge the previous sub-PR first, then re-invoke `/dev-execute`.
      - **(b) stack** — create `sub-<N>` off the previous sub-branch tip. Record `stacked_on: <previous sub_branch>` in the subtask frontmatter. Warn: the sub-PR will show the stacked commits until the previous sub-PR merges; sub-phase 3.8 will rebase before opening it.
  - Record `sub_branch` in subtask `N`'s frontmatter.

Report (mode-dependent): "On `feat/VN-742-oauth-flow` (created from `develop`, empty open-draft-pr commit at abc123)", "On `feat/VN-742-oauth-flow` (existing branch)", or "On `feat/VN-742-oauth-flow-sub-2` (off `feat/VN-742-oauth-flow` @ abc123)".

### Sub-phase 1c — Open the draft PR at start (first subtask only; skipped in experimental mode; CONFIRM each external op)

Per the branching strategy, work starts by opening a **Draft PR** before writing feature code — it's the start-of-work signal. This runs only when the parent branch was just created in 1b (`branch_created` flipped to true this invocation) and `pr_url` is not yet set. Skip entirely in experimental mode (no external ops). Skip if a `pr_url` is already recorded (re-entry).

In `sub-branches` mode this opens the **parent** feature branch's draft PR → `<target_branch>`. The empty commit is what gives it a base; sub-PRs still target the parent feature branch (sub-phase 3.8), not `<target_branch>`.

**At `balanced` / `auto`:** do the local preparation for all three steps below — build the PR title and body, resolve the base, draft the Jira comment — then present them, together with whatever 1a held back, as the **sub-phase 1 external batch** (see the batch spec above) and fire the approved ops in order. The verification steps (checking `baseRefName` after creation, recording `pr_url`) still run per op. The rest of this sub-phase describes the `guided` per-op flow.

1. **Push the feature branch (CONFIRM):** *"About to push `<branch_name>` to origin to open its draft PR. Proceed?"* — `git push -u origin <branch_name>`. (In `sub-branches` mode this is the parent branch; check out the parent first if currently on the sub-branch, then return to the sub-branch after.)
2. **Open the draft PR (CONFIRM):** build title + body from `pr-template`, populated with the issue objectives from `gathering/objectives.md` + planned subtasks from `plan.md` (the work isn't done yet, so frame it as scope/plan, not results). Link the GH issue if `gh_issue_created`. Before creating, verify the base: the target in the create command must be exactly `plan.md`'s `target_branch`. **Display the proposed title + body. Ask: "Open this draft PR? Target: `<target_branch>`. Proceed?"** On confirm: `gh pr create --draft --base <target_branch> --head <branch_name> --title ... --body ...`. Then verify what was actually created — `gh pr view <url> --json baseRefName` matches `target_branch` (repo default-branch settings can silently redirect a base). Record `pr_url: <url>` and `pr_state: draft` in `plan.md` frontmatter.
3. **Comment on the Jira parent (optional, CONFIRM):** only if Atlassian MCP is available and the parent ticket is known — short comment per `comment-style`, e.g. `"Draft PR opened: <url>. Targets <target_branch>. Work in progress."`

Any step declined → continue without the draft PR (record whatever state was reached). The work can still proceed locally; sub-phase 4.5 will open the PR as Ready at wrap-up if no `pr_url` exists by then.

---

## Sub-phase 2 — Implementation plan

Orchestrator drafts the implementation plan directly (no subagent for drafting). The plan is a contract for the code in sub-phase 3.

### 2.1 — Draft

Read the subtask spec from `plan.md` (the section for subtask `N`). Read the files listed in `what's affected` to understand current state. Identify patterns from sibling code that the implementation should follow.

Draft `impl-plan.md` with these sections:

```markdown
---
issue: <issue-id>
subtask: <N>
status: pending
autonomy: <guided | balanced | auto>
size: <S | M | L>          # from plan.md's subtask spec
iterations: 1
---

# Implementation plan — Subtask <N>

## Approach
2–4 sentences. Concrete, names specific functions/classes/files. Not vague.

## Size budget
Planned band from `plan.md` (`S` ≤50 / `M` ≤150 / `L` ≤400 added lines) and how this approach fits inside it — roughly how many lines per file, split src vs test. If the approach doesn't fit, say so **here**, before any code exists: either the approach is doing more than the subtask asks, or the plan under-sized it. Both are worth one sentence now instead of an overshoot later.

## What this deliberately does not do
Per the code-economy strategy: the abstraction not introduced, the config surface not added, the adjacent code not refactored, the extra test cases not written. One line each. An empty section here almost always means the plan absorbed something it shouldn't.

## Files to touch
- `actual/path/file.py` — what changes here
- `actual/path/test.py` — what changes here

## Patterns to follow
- Reference to sibling code: `existing/similar_provider.py` — the pattern this subtask mirrors

## Gotchas
- Things the planning phase couldn't see (entry-point quirks, hidden dependencies, etc.)
- Each gotcha has a corresponding mitigation in the approach

## Drift from subtask spec
- Any differences from what `plan.md` said (file paths shifted, files renamed, etc.)
- Empty section if no drift

## Commits planned
1. <type>(<scope>): <Description> — files it touches
2. ...
```

Save the file at `.dev-assistant/issues/<issue-id>/execution/<NN-slug>/impl-plan.md`. (Use the same `<NN-slug>` derivation as the subtask folder.)

### 2.2 — Mechanical checks

Run these against the drafted plan:

- Every passing criterion in the subtask is addressed by something in the approach
- Every file in `what's affected` (from `plan.md`) appears in the plan's `files to touch` — or the drift section explains why not
- Files in `files to touch` that aren't in `what's affected` are flagged as drift (don't silently expand scope)
- Files referenced in the approach actually exist in the repo (or are explicitly marked "new file")
- Commit count in the plan matches the subtask's `commits:` field (or drift is noted)
- The plan's `size:` matches the subtask's planned band, and the approach plausibly fits it — a plan that introduces a new class, its registry entry, and a test matrix is not an `S`
- Nothing in the approach is unrequired by a passing criterion or an objective (code-economy checklist items 1–10). Anything that is gets moved to *What this deliberately does not do*
- Each commit's `<type>` is in the branching-strategy's allowed types

If any check fails: orchestrator re-drafts the plan addressing the specific failure. **Capped at 2 internal re-drafts.** Append each iteration to `impl-plan-log.md` in the same folder (frontmatter `iteration:`, then the full plan + checks results).

If after 2 re-drafts the mechanical checks still fail, surface to the user with the specific failures and let them decide: approve anyway, abandon, or edit `impl-plan.md` manually.

### 2.3 — Show to user, get decision

**At `guided` / `balanced`:** this is the phase's approval checkpoint — the one place a human sees what the code is about to become before it exists. It stays at `balanced`; a subtask's impl plan is exactly the kind of thing that is cheap to redirect now and expensive to redirect after four commits.

**At `auto`:** no checkpoint. Write `impl-plan.md` with `status: approved` and `approved_by: autonomy-auto` in its frontmatter, print the same summary as a statement of what you are about to do, and go to sub-phase 3. The mechanical checks in 2.2 still gate the plan — and if they still fail after 2 re-drafts, that is an escalation: stop and ask, at every level.

Display a **summary** of the impl plan (not the whole file):

```
Implementation plan for subtask N:
  Approach: <one sentence>
  Files: file1.py, file2.py, test.py
  Commits: 2   ·   Size: M (planned M — ~90 src / ~40 test)
  Not doing: <the one-line version of "deliberately does not do">
  Drift: <one line, or "none">
  Gotchas: <one line, or "none">

Full plan at .dev-assistant/issues/<id>/execution/<NN-slug>/impl-plan.md

Approve as-is / refine with comments / abandon?
```

Wait for the user's decision (at `auto`, the last line is dropped and you proceed).

- **Approve** → write the final state to `impl-plan.md` (`status: approved`), append to log, move to sub-phase 3.
- **Refine** → take their comments, re-draft (this counts as another iteration, but the cap of 2 mechanical re-drafts doesn't apply to user-driven refines; allow up to 2 refines). Then re-show.
- **Abandon** → stop execute, leave the impl-plan.md as-is (status: draft, iterations counted) so the user has a record of the attempt.

---

## Sub-phase 3 — Execute the work

The work happens here. Subagent dispatch IS used in this sub-phase because the work is mechanical and the user doesn't need to be conversational.

For each commit listed in the impl plan, in order:

### 3.1 — Subagent writes code

Dispatch the **Agent tool** with these parameters:

- `subagent_type: general-purpose`
- `description`: "Write code for subtask `N`, commit `K`"
- Model: `sonnet` (per-repo execute model default; configurable later)
- `prompt`: the full impl plan + the specific commit's scope + relevant file contents + **the code-economy strategy text loaded above** + instructions:
  - "Make the file changes described for commit K of this impl plan."
  - "Write the least code that satisfies the plan and stays obvious to the next reader. The strategy above is binding: extend existing code before adding files, no abstraction before the third occurrence, no configurability the plan doesn't name, no defensive checks for states the caller rules out, one test per behavior plus the named failure modes, comments explain why and not what."
  - "When the shorter version takes longer to explain, write the longer one. Short and obvious beats short and clever."
  - "This commit's budget is roughly <n> added lines. If you find yourself well past it, stop and report what is driving the size instead of writing more."
  - "Do not commit, do not push, do not touch git. Just write the files."
  - "Output: a brief summary of what you changed, which files, and anything you left out on purpose."

### 3.2 — Orchestrator reviews diff (and sizes it)

After the subagent returns:

- Run `git diff` to see what changed
- Brief sanity check:
  - Are only the files in `files to touch` touched? If extras appear, surface to user.
  - Are the changes plausibly aligned with the commit's intent? (Not a full code review — just a "does this look like what we asked for" pass.)
- **Measure it** — the work is uncommitted, so:

  ```
  dev-assistant issue size --id <issue-id> --worktree --band <subtask's planned band>
  ```

  Report the one-line result: *"+118 / -12, band M vs planned M — within budget."*

**If the measurement says over budget** (more than 25% past the band's ceiling), run **one trim pass** before committing — don't ask first, and don't just accept it:

1. Read the diff against the code-economy checklist and list what can go: an abstraction used once, a wrapper that only forwards, config nobody asked for, defensive checks for impossible states, tests that repeat each other, comments restating code, anything absent from *files to touch* or from the passing criteria.
2. Apply the removals yourself (local edits, no confirmation needed) — or dispatch the Agent with the specific list when the trim is substantial.
3. Re-measure with the same command, and re-run any tests the subtask's passing criteria name. **A trim that breaks a criterion is not a trim — revert it.**
4. Report what came out: *"trimmed 46 lines — dropped the ProviderRegistry wrapper and three duplicate tests. Now +72 / -12, band M."*

**If it is still over budget after the trim, stop and ask** — at every autonomy level, `auto` included. This is an escalation, not an approval: the plan and the code disagree about how big this is, and only the user can settle which one is wrong.

```
Subtask N is over its size budget after trimming.
  Planned: M (≤150 added)      Landed: 214 added / 12 deleted
  What's driving it: <the honest reason — e.g. "the callback needs its own
  error taxonomy; the plan assumed one exception type">
  Already trimmed: <what came out in the pass above>

Options:
  (a) Trim further — tell me what to cut, or I'll propose a deeper list
  (b) Accept — the size is justified; I'll record the reason in the plan and the notes
  (c) Re-plan the subtask — the impl plan was wrong about the shape of this
  (d) Split — land what's coherent now, move the rest to a follow-up ticket
```

Record the outcome in `execution-notes.md` either way. An accepted overshoot with a written reason is fine; an unnoticed one is what produces a 1,300-line issue.

### 3.3 — Commit

Build the commit message using the preview from the impl plan (which itself was built from the branching strategy). Format:

```
<type>(<scope>): <Description>

- <keyword>: <very short summary>

refs <issue-id>
```

Pass via HEREDOC to `git commit` to preserve newlines. **No `--no-verify`** — let any repo hooks fire naturally. If the commit fails (hook failure, conflict, etc.), surface the output verbatim and stop. The user decides whether to fix and retry or abandon.

Print a terse one-liner: "committed K/M: `<type>(<scope>): <Description>` (<short SHA>)"

### 3.4 — Loop

If more commits remain in this subtask, return to 3.1 for the next one. Otherwise proceed to 3.5.

### 3.5 — Verify passing criteria

After all commits in this subtask are done, verify the subtask's `passing criteria` from `plan.md`. For each criterion:

- Mechanically verifiable (e.g., "file X exists", "tests in Y pass", "function Z defined") → run the check, mark ✓/✗ with the actual result
- Judgment-only (e.g., "approach is clean") → mark "manual" — these get reported to the user but not auto-judged

Display the results:

```
Subtask N verification:
  [✓] OAuthProvider class extends BaseProvider
  [✓] Registered in entry_points
  [✗] Unit tests pass — failure: 2 tests failing in test_providers.py
```

### 3.6 — Handle verification outcomes

- **All pass** → proceed to 3.7
- **Any fail** → attempt one auto-fix:
  - Dispatch the Agent again with the failure details
  - Subagent makes targeted changes
  - Re-verify
  - If still failing → escalate to user with three options:
    - (a) Try another auto-fix
    - (b) `git reset` and redo this subtask from scratch (user does the reset)
    - (c) Abandon execute
- **Any "manual"** items → report them; don't block on them

### 3.7 — Write execution notes and update state

Write `.dev-assistant/issues/<issue-id>/execution/<NN-slug>/execution-notes.md`:

```markdown
---
issue: <issue-id>
subtask: <N>
status: complete
autonomy: <guided | balanced | auto>
commits: <count>
commit_shas: [sha1, sha2, ...]
verified_criteria: <passed>/<total>
planned_size: <S | M | L>
added_lines: <n>
deleted_lines: <n>
size_outcome: <within | trimmed | accepted-over | re-planned>
---

# Execution notes — Subtask <N>

## What was done
1–2 sentences.

## Commits
- <sha>: <commit message subject>
- <sha>: <commit message subject>

## Drift from impl-plan
What deviated, if anything.

## Verification results
- [✓] criterion 1
- [✗] criterion 2 — <reason>
- [manual] criterion 3 — needs human eyes

## Size
Planned band vs landed (`+<added> / -<deleted>`). What the trim pass removed, if it ran. If the overshoot was accepted, the reason — in the user's words where they gave one.
```

Update `plan.md` subtask frontmatter: `status: done`.

### 3.8 — Open the sub-PR (`sub-branches` mode only; CONFIRM each external op)

In `single-branch` mode, skip this step entirely. (Experimental mode never reaches here in sub-branches form — it forces single-branch behavior.)

After verification passes, land this subtask as its own PR against the parent feature branch.

**At `balanced` / `auto`:** the rebase (step 1) is local — just do it, and treat conflicts as the hard stop they already are. Steps 2–5 become **one external batch** (parent push if needed, sub-branch push, sub-PR with its title + body, Jira subtask comment), approved once and fired in order.

The `guided` per-op flow:

1. **Rebase onto the parent tip:** `git fetch origin`, then `git rebase origin/<branch_name>` (or local `<branch_name>` if the parent isn't on origin yet). If this subtask was `stacked_on` a prior sub-branch whose PR has since merged, this rebase is what untangles it. Conflicts → **hard stop**, same protocol as wrap-up rebase: list conflicting files, user resolves, re-invoke.
2. **Push the parent first if needed:** if `origin/<branch_name>` doesn't exist, the sub-PR has no base. **Ask: "About to push parent branch `<branch_name>` to origin (needed as sub-PR base). Proceed?"** On confirm: `git push -u origin <branch_name>`.
3. **Push the sub-branch (CONFIRM):** *"About to push `<sub_branch>` to origin. Proceed?"* — `git push -u origin <sub_branch>` (first push) or `--force-with-lease` (re-push after rebase).
4. **Open the sub-PR (CONFIRM):** build title + body from `pr-template` scoped to this subtask (subtask objectives, passing-criteria results, commit list, link to the GH issue if `gh_issue_created`). **Display proposed title + body. Ask: "Open this sub-PR? Target: `<branch_name>`. Proceed?"** On confirm: `gh pr create --base <branch_name> --head <sub_branch> --title ... --body ...`. Record `sub_pr_url` in the subtask's frontmatter in `plan.md`.
5. **Comment on the Jira subtask (optional, CONFIRM):** only if Atlassian MCP is available and `jira_subtask_key` is recorded — short comment per `comment-style`, e.g. `"Sub-PR opened: <url>. Targets <branch_name>."`

Any step declined → stop here gracefully; record whatever state was reached. The user can finish manually (and paste `sub_pr_url` into `plan.md`) or re-invoke `/dev-execute <issue-id> <N>` to resume — sub-phase 1b will detect the existing `sub_branch` and skip to whatever's missing.

Sub-PRs merge into the **parent feature branch**, never directly into `develop`, and merge sequentially (`sub-1` before `sub-2`) per the branching strategy. The user merges on GitHub after review; `/dev-feedback <issue-id> <N>` handles review rounds on a sub-PR.

### 3.9 — Report to user

Terse summary:

```
Subtask N complete: 2 commits, 3/3 criteria verified.
Next: subtask N+1 (`/dev-execute <issue-id>` to continue) — or all subtasks done, ready for wrap-up.
```

In `sub-branches` mode, add the sub-PR line: `Sub-PR: <url> → <branch_name> (merge before starting subtask N+1, or stack)`.

If this was the last pending subtask, suggest `/dev-execute <issue-id> wrap-up` as the explicit next step (or note that re-invoking `/dev-execute <issue-id>` will auto-enter wrap-up mode). In `sub-branches` mode, note that wrap-up requires all sub-PRs merged first.

---

## Sub-phase 4 — Wrap-up (one-time, after all subtasks are done)

Triggered automatically when all subtasks are `status: done` and the user re-invokes `/dev-execute <issue-id>` (or explicitly via `wrap-up`). One pass per issue.

### 4.1 — Pre-flight

Verify:

- All subtasks `status: done` in `plan.md`
- Working tree clean (`git status` shows nothing)
- Current branch matches `plan.md`'s `branch_name` — in `sub-branches` mode, check out the parent branch first if currently on a sub-branch (`git checkout <branch_name>`, then fast-forward to `origin/<branch_name>`)
- In normal mode: `origin/<target_branch>` exists (will be needed for rebase), verified via `git ls-remote --heads origin <target_branch>`
- **In `sub-branches` mode additionally:** every subtask has a `sub_pr_url` and every sub-PR is **merged** (`gh pr view <url> --json state,merged` per subtask). If any are missing or still open, stop and list them: *"Sub-PRs not merged: subtask 2 (<url>, OPEN), subtask 4 (no sub-PR). Merge them into `<branch_name>` first, then re-invoke wrap-up."*

If any fail → stop with a clear message. No external ops attempted.

### 4.2 — Catch-up on deferred external prep (skipped in experimental mode)

In experimental mode, skip this entire sub-stage.

Otherwise: scan all subtasks for incomplete external prep.

- For any subtask with `jira_pushed: false`, list it: "Subtask 2 (`Wire OAuth callback`) — Jira not pushed."
- For issue-level `gh_issue_created: false`, list it.

**At `guided`:** if anything is incomplete, ask *"Handle deferred external prep now before PR opens? Options: yes (one prompt per item), no (proceed without)."* If yes, walk each item with the same flow as sub-phase 1a; if no, proceed with whatever state is recorded.

**At `balanced` / `auto`:** don't ask separately. Draft the payloads for the incomplete items and put them at the top of the **wrap-up external batch** (4.4–4.6 below), where the user can drop any of them by number. Items dropped there stay recorded as incomplete in the wrap-up report.

### 4.2b — Reduction pass (always runs; local only)

The subtasks were each sized on their own. Nobody has yet read the issue's diff **as one change** — and that is where accumulated bloat lives: the helper two subtasks both grew, the abstraction that made sense in subtask 1 and has one caller, the tests that overlap across subtasks, the interface that ended up wider than anything uses.

1. **Measure the whole issue:**

   ```
   dev-assistant issue size --id <issue-id>
   ```

   (Against `origin/<target_branch>`; in experimental mode pass `--base <branch_base>`.) Report planned vs landed: *"Issue total: +412 / -58, band L vs planned M."*

2. **Read the full diff** — `git diff origin/<target_branch>...HEAD` — as a reviewer seeing it for the first time, against the code-economy checklist. Look for what only shows up at issue scale:
   - Functions, classes, or files with exactly one caller that could be inlined
   - Two subtasks that grew near-duplicate helpers
   - An abstraction introduced for a second occurrence that never got a third
   - Tests asserting the same behavior from different subtasks
   - Options, flags, or parameters nothing in the diff passes
   - Docstrings and comments that restate their code
   - Code no passing criterion and no objective requires

3. **Propose the removals as a list**, each with the line count it saves and the criterion or objective that proves it is safe to remove.

4. **Apply and verify.** Local edits, no confirmation needed. Then **re-run every subtask's passing criteria** (they are in `plan.md`). A removal that breaks one is reverted, no argument. Commit what survives as one commit — `refactor(<scope>): Trim <what>` with a `- remove:` bullet per item, `refs <issue-id>`. **This commit is exempt from the commit budget** — it subtracts.

5. **If nothing should come out, say so in one line** and move on: *"Reduction pass: nothing to remove — the diff is what the objectives require."* That is a legitimate outcome; a pass that always finds something is a pass that is inventing work.

At `guided`, show the proposed removals and wait before applying. At `balanced` / `auto`, apply the ones that are clearly safe (verified by the criteria) and report what came out — deletions that keep every criterion green are the one edit that never needs approval.

Record the outcome for the wrap-up report: lines removed, what was removed, what was left and why.

### 4.3 — Rebase (skipped in experimental mode)

In experimental mode, skip rebase entirely.

Otherwise:

- `git fetch origin`
- `git rebase origin/<target_branch>`
- If the rebase has conflicts → **hard stop**. List conflicting files. Tell the user: *"Rebase has conflicts. Resolve them manually (`git rebase --continue` after fixing), then re-invoke `/dev-execute <issue-id> wrap-up`."*
- If clean → report "Rebased onto `<target_branch>` (no conflicts)."

### 4.4–4.6 at `balanced` / `auto` — one wrap-up batch

Sub-phases 4.4 (push), 4.5 (PR body + ready), 4.5b (hotfix sync PR), and 4.6 (Jira comment) — plus any deferred prep from 4.2 — are **one external batch**, approved once and fired in listed order:

```
EXTERNAL OPERATIONS — wrap-up, issue <issue-id>

1. CREATE JIRA SUBTASK   (deferred from subtask 2) "<summary>"
2. PUSH                  <branch> → origin  (force-with-lease, post-rebase, <n> commits)
3. UPDATE PR BODY        <pr_url>            body: <first 3 lines…>  (commit map: <n> rows)
4. MARK PR READY         <pr_url> → <target_branch>
5. OPEN SYNC PR          <branch> → develop  (hotfix flow only)
6. JIRA COMMENT          on <TICKET>: "PR ready for review: <url>…"

Approve all / drop specific ops / abandon
```

The rebase (4.3) happens **before** the batch — it is local, and its conflicts are a hard stop at every level. Anything dropped from the batch behaves exactly as declining its per-op confirmation does below (the PR stays draft, the sync PR is recorded as `null` with the drift warning, and so on). If an op fails mid-batch, stop there and report — do not continue down the list.

The rest of 4.4–4.6 describes the `guided` per-op flow.

### 4.4 — Push (skipped in experimental mode; otherwise CONFIRM)

In experimental mode, skip push entirely.

Otherwise:

- **Ask user: "About to push `<branch>` to origin (force-with-lease, post-rebase). Proceed?"**
- On confirm: `git push --force-with-lease origin <branch>`
- On decline: stop wrap-up. Tell user they can manually push and re-invoke wrap-up later, or skip the rest of wrap-up.
- Report: "Pushed `feat/VN-742-oauth-flow` to origin."

### 4.5 — Mark the PR ready for review (skipped in experimental mode; otherwise CONFIRM)

In experimental mode, skip entirely.

The draft PR was normally opened at sub-phase 1c. Wrap-up refreshes its body and converts it to Ready. Build the PR body from `pr-template`, now populated with the finished work: subtask summaries, the GH issue link (if `gh_issue_created`), and commit references. In `sub-branches` mode, include a "Sub-PRs" section listing each subtask's merged sub-PR (`#num — title`) so reviewers know the pieces were already reviewed individually.

**Commit map (reviewer aid — always include):** append a `## Commit map` section to the PR body — one table row per commit, grouped by subtask, so a reviewer can review commit-by-commit and trace each one back to its Jira subtask:

```markdown
## Commit map

| Commit | Subtask | Jira | What it does |
|---|---|---|---|
| <short-sha> | 01 — <subtask title> | <jira_subtask_key or —> | <commit subject> |
| <short-sha> | 01 — <subtask title> | <jira_subtask_key or —> | <commit subject> |
| <short-sha> | 02 — <subtask title> | <jira_subtask_key or —> | <commit subject> |
```

Source the rows from each subtask's `execution-notes.md` (`commit_shas` + subjects) and `plan.md`'s per-subtask `jira_subtask_key`. Fixes from later feedback rounds aren't known yet — `/dev-feedback` appends its commits to this same table. Use the pushed SHAs (post-rebase), not stale pre-rebase ones.

**If `pr_url` is already set** (the normal case — draft opened at start):

- **Display the refreshed body. Ask user: "Update PR body and mark `<pr_url>` ready for review? Target: `<target_branch>`. Proceed?"**
- On confirm: `gh pr edit <pr_url> --body "<body>"` then `gh pr ready <pr_url>`. Update `pr_state: ready` in `plan.md`.
- On decline: stop wrap-up. The PR stays as a draft; the user can mark it ready manually.

**If `pr_url` is not set** (1c was declined or this is an old single-branch plan): open the PR fresh as Ready.

- **Display the proposed title + body. Ask user: "Open this PR? Target: `<target_branch>`. Proceed?"**
- On confirm: `gh pr create --title "<title>" --body "<body>" --base <target_branch>`. Capture the returned URL; verify `baseRefName` matches `target_branch`; record `pr_url` and `pr_state: ready`.
- On decline: stop wrap-up. PR can be opened manually later.

Report: "PR ready: `<url>`" (or "PR opened (ready): `<url>`" in the fresh-open case).

### 4.5b — Hotfix sync PR (hotfix flow only; CONFIRM)

Per the branching strategy, every hotfix needs **two PRs** — the one just marked ready (→ `uat`) and a sync PR → `develop`, or the branches drift out of sync. Only runs when `flow: hotfix`.

- Build the sync PR from the same branch: title `[<TICKET>] <summary> (sync to develop)`, body pointing at the primary PR (`Sync of <pr_url> — see it for review context and the commit map.`).
- **Display it. Ask: "Open the develop sync PR? Target: `develop`. Proceed?"** On confirm: `gh pr create --base develop --head <branch_name> --title ... --body ...`. Record `develop_pr_url` in `plan.md` frontmatter.
- On decline: continue wrap-up, but record `develop_pr_url: null` and warn — *"No sync PR: the fix will be lost from `develop` on the next promotion unless one is opened before `/dev-merge`."* `/dev-merge` re-checks this.
- If `uat` and `develop` have diverged so far that the same branch can't cleanly target both, surface it and fall back to the strategy's cherry-pick guidance (manual for now).

### 4.6 — Comment on Jira parent (skipped in experimental mode; otherwise CONFIRM)

In experimental mode, skip Jira comment entirely.

Otherwise (and only if Atlassian MCP is available):

- Build the comment from `comment-style` strategy — short, e.g. `"PR ready for review: <PR URL>\nTargets <target_branch>. Awaiting review."` (hotfix flow: mention the sync PR too)
- **Display the comment. Ask user: "Post this comment on Jira `<issue-id>`? Proceed?"**
- On confirm: post via Atlassian MCP.
- On decline: skip. User can comment manually.

If MCP is unavailable, skip with a brief message.

### 4.7 — Generate team message (local-only, no confirm needed; always runs)

Build the Spanish team message from `team-update-template`, populated with:

- PR URL (or "[PR not opened]" in experimental mode)
- Issue ticket and title
- 2–3 bullets summarizing what changed (derived from subtask titles and commit messages)
- Target branch (`<target_branch>`; in the hotfix flow mention both PRs)

Write it to `.dev-assistant/issues/<issue-id>/execution/team-message.txt`.

**Display it in chat verbatim** so the user can select and copy.

(Generation is local; no external op happens. The user copy-pastes into their team's chat themselves.)

### 4.8 — Write wrap-up report

Write `.dev-assistant/issues/<issue-id>/execution/wrap-up-report.md`:

```markdown
---
issue: <issue-id>
phase: execution
status: complete
autonomy: <guided | balanced | auto>
pr_url: <url or null>
target_branch: <develop or "experimental">
total_subtasks: <n>
total_commits: <count>
planned_size: <S | M | L>
added_lines: <n>
deleted_lines: <n>
reduction_removed_lines: <n>
experimental: <true | false>
---

# Wrap-up report — <issue-id>

## Outcome

One paragraph: what was achieved against the original objectives from `gathering/objectives.md`.

## Subtasks completed

| # | Title | Commits | Notes |
|---|---|---|---|
| 01 | <title> | <n> | (any drift, manual criteria, etc.) |
| 02 | ... | ... | ... |

## External operations summary

- Jira parent ticket: <key>
- Jira subtasks created: [list keys, or "none" if experimental / all deferred]
- GitHub issue: #<num> or "not created"
- PR opened: <url> or "not opened (experimental / deferred)"
- Sub-PRs: [list of merged sub-PR URLs per subtask, or "n/a (single-branch)"]
- Branch: <branch> → <target>

## Size

Planned band vs landed (`+<added> / -<deleted>`, measured with `dev-assistant issue size`). Per-subtask outcomes (within / trimmed / accepted-over). What the reduction pass removed, and what it deliberately left. If the issue landed a band above plan, the honest reason — this is the number `/dev-evaluate` retrospects and the one that turns into a lesson when it keeps happening.

## Deviations from plan

Differences between what `plan.md` proposed and what actually got committed.

## Notes for /dev-evaluate

What worked, what didn't, anything worth retrospecting.

## Decided without review

(`balanced` / `auto` only — omit the section at `guided`.) What you settled without a checkpoint: at `auto`, every impl plan that went straight to code (with its drift from the subtask spec); at both levels, any external op the batch dropped and what that leaves undone, and any judgment call made while writing code that the plan did not anticipate.
```

### 4.9 — Final report

Terse summary to the user:

```
Wrap-up complete for <issue-id>.
- N subtasks, M commits, +A / -D lines (band <X> vs planned <Y>; reduction pass removed R)
- PR: <url or "not opened">   (hotfix flow: also the develop sync PR, or the warning that it's missing)
- Team message ready at .dev-assistant/issues/<issue-id>/execution/team-message.txt (and shown above for copy)
- Wrap-up report at .dev-assistant/issues/<issue-id>/execution/wrap-up-report.md

Next: /dev-feedback <issue-id> for each review round → /dev-merge <issue-id> once approved → /dev-evaluate <issue-id>.
```

---

## Re-running and state behavior

`/dev-execute` is designed to be re-invokable safely. State lives in `plan.md` and per-subtask files; the slash command always reads state before acting.

- **Re-running on the same subtask while its `status: pending`**: re-enters at sub-phase 2 (impl plan). Any prior `impl-plan.md` is shown for context; the user can refine or restart.
- **Re-running on a subtask with `status: done`**: warn the user — "Subtask N is already complete. To redo it, `git reset --hard <prior sha>` first and reset the subtask status in `plan.md`. Proceed only if you've done that."
- **Re-running for wrap-up after wrap-up already ran**: detect `pr_url` in `plan.md` — if present, this is an update-mode invocation. Offer to update the PR body (re-render from current state and `gh pr edit`), but **do not open a second PR**.
- **Mid-subtask interruption**: state may be inconsistent (some commits made, criteria not yet verified). On re-entry, detect commits ahead of `branch_base` for this subtask and either resume verification or surface the inconsistency for user resolution.
- **Sub-branches mode state** lives in per-subtask frontmatter: `sub_branch`, `sub_pr_url`, and (when stacked) `stacked_on`. A subtask with `status: done` but no `sub_pr_url` means 3.8 was declined or interrupted — re-invoking `/dev-execute <issue-id> <N>` resumes at 3.8 rather than redoing the work.

## If something fails in a destructive-feeling way

Always prefer pausing and asking over rolling back or resetting state automatically. Examples:

- Commit fails due to hook → surface and stop; user fixes the issue and re-runs
- Push fails due to remote rejection → surface and stop; don't try to force or rebase silently
- PR creation fails → don't retry; surface and stop
- Jira API errors → log and skip with a clear message; don't block local progress
