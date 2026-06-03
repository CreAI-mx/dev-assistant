---
description: Execute one subtask of an issue (or wrap up after all subtasks are done) — writes code, verifies passing criteria, commits, opens the subtask's sub-PR in sub-branches mode, and at wrap-up opens the (parent) PR
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

Parse `$ARGUMENTS` accordingly at the start. The issue ID is the first whitespace-separated token.

## Current state of the issue

!`dev-assistant issue show --id $ARGUMENTS`

(If `$ARGUMENTS` contains the subtask number or `wrap-up` token, the CLI may print a not-found error — that's fine, we'll work directly with the issue files below.)

## Experimental mode

Read `.dev-assistant/issues/<issue-id>/issue.md` and check for `experimental: true` in the frontmatter. If set, **experimental mode is active for this entire invocation**, which changes behavior in specific places (called out below). Summary of what experimental mode does:

- **Sub-phase 1a** (external preparation): all prompts SKIPPED entirely. No Jira / GH ops attempted, no asking.
- **Sub-phase 1b** (local branch): `git fetch origin` is SKIPPED. Branch is created from the current HEAD instead of from the latest `version/x.y.z` on origin.
- **Branching mode**: forced to `single-branch` behavior regardless of `plan.md`'s `branching_mode` — sub-PRs can't open without external ops, so sub-branches would be pointless. Note this to the user if the plan says `sub-branches`.
- **Sub-phase 3.8** (sub-PR): never runs (follows from the forced single-branch behavior).
- **Sub-phase 4** (wrap-up): rebase, push, PR open, and Jira comment are all SKIPPED. Wrap-up report and team message are still written locally.

Surface "experimental mode active — external ops will be skipped" up front so the user knows what's happening.

## Strategies that shape this phase

### Branching strategy (drives branch operations, commit messages)

!`dev-assistant strategies show branching-strategy`

### PR template (drives PR title and body at wrap-up)

!`dev-assistant strategies show pr-template`

### Comment style (drives Jira/GH comments)

!`dev-assistant strategies show comment-style`

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

**Anything that touches the outside world requires explicit user confirmation, regardless of auto / auto-accept-edits modes.** This includes:

- `git push` (any branch, any time)
- `gh pr create`, `gh pr edit`, `gh pr close`
- Issue creation on GitHub or Jira
- Comments on Jira or GitHub
- Jira transitions
- Any other operation that publishes state outside the local repo

Local operations (file edits, `git commit`, `git rebase`, branch creation) do **not** require confirmation — they are reversible and contained.

If the user is in auto mode and an external op is about to fire, **still pause and ask explicitly**. Phrase confirmations clearly: *"About to push `feat/VN-742-oauth-flow` to origin. Proceed? (y/n)"*

## How to interact with the user

- **Announce which sub-phase you're entering** before each one.
- **Be terse during work, full during decisions.** Per-commit progress is one line; per-subtask report is brief; sub-phase 4 wrap-up summarizes don't narrate.
- **Read the impl plan when shown to the user as a summary** (3–5 lines: approach, files affected, commit count). Full text is in the impl-plan.md file the user can open if they want.

---

## Sub-phase 1 — Preparation

This sub-phase prepares everything needed before the work begins. It has two halves: external (1a) and local (1b). 1a is fully optional and prompts per item; 1b is automatic.

### Sub-phase 1a — External preparation (skipped entirely in experimental mode)

If experimental mode is active, **skip this sub-phase entirely**. Print "experimental mode — skipping external prep" and proceed to sub-phase 1b.

Otherwise, for the current subtask `N`:

1. **Check issue-level state in `plan.md`:** has the GitHub issue been created? (`gh_issue_created` field)
   - If **no** and this is the first subtask being executed: ask the user *"Create the GitHub issue for `<issue-id>` now? (y/n, default n)"*.
   - On yes: build the issue body from `gh-issue-template`, populated with content from `gathering/objectives.md` + `plan/plan.md`. **CONFIRM the proposed title + body with the user before calling `gh issue create`.** On success, record `gh_issue_created: true` and `gh_issue_number: <num>` in `plan.md` frontmatter.
   - On no: skip and continue. Will be offered again at wrap-up.

2. **Check subtask-level state:** has subtask `N`'s Jira subtask been pushed? (`jira_pushed` field in the subtask)
   - If **no**: ask *"Create Jira subtask for subtask `N` (`<title>`) now? (y/n, default n)"*.
   - On yes: check whether Atlassian MCP tools are available in this Claude Code session.
     - If yes: build the description from `jira-subtask-template`, populated with the subtask spec. **CONFIRM the proposed summary + description with the user before creating.** On success, record `jira_pushed: true`, `jira_subtask_key: <key>`, `jira_description_populated: true` in the subtask frontmatter.
     - If no: tell the user "Atlassian MCP not available in this session — skipping Jira subtask creation. Push manually if needed." Skip without erroring.
   - On no: skip and continue. Will be offered again at wrap-up.

3. **(Edge case)** If `jira_pushed: true` but `jira_description_populated: false`: the user created the subtask manually but the description is empty. Offer to populate it now. Same flow.

After 1a, summarize what was done: "Created Jira subtask VN-742-3; GH issue already exists (#42); skipped one optional step."

### Sub-phase 1b — Local branch preparation (automatic, no confirm)

Local-only ops. **No user confirmation needed.** Just do it and report.

Read `branching_mode` from `plan.md` frontmatter. Treat a missing field as `single-branch` (plans written before the field existed). In experimental mode, force `single-branch` behavior regardless of the plan.

**Pre-flight:** verify the working tree is clean. If dirty, stop and tell the user *"Working tree has uncommitted changes. Commit, stash, or discard them before running execute."*

**If `plan.md` frontmatter has `branch_created: false`** (this is the first subtask being executed for this issue):

- **In experimental mode:** branch from current HEAD. Record the base commit SHA.
  - `git checkout -b feat/<TICKET>-<slug>` (slug from `plan.md`'s `proposed_branch` field)
- **In normal mode:** branch from the latest `version/x.y.z` on origin.
  - `git fetch origin`
  - Identify the highest `version/x.y.z` ref under `origin/` by semver. If there are none, stop with *"No `version/x.y.z` branch found on origin. Per the branching strategy, you need a sprint version branch before opening a feature branch."* (No confirmation; just stop.)
  - `git checkout -b feat/<TICKET>-<slug> origin/<latest version>`
- Record `branch_created: true`, `branch_name: feat/<TICKET>-<slug>`, `branch_base: <version branch or HEAD>` in `plan.md` frontmatter.
- **In `sub-branches` mode, additionally:** create the first subtask's sub-branch off the parent just created: `git checkout -b feat/<TICKET>-<slug>-sub-<N>`. Record `sub_branch: feat/<TICKET>-<slug>-sub-<N>` in subtask `N`'s frontmatter in `plan.md`.

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

Report (mode-dependent): "On `feat/VN-742-oauth-flow` (created from `version/1.2.0`, base sha abc123)", "On `feat/VN-742-oauth-flow` (existing branch)", or "On `feat/VN-742-oauth-flow-sub-2` (off `feat/VN-742-oauth-flow` @ abc123)".

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
iterations: 1
---

# Implementation plan — Subtask <N>

## Approach
2–4 sentences. Concrete, names specific functions/classes/files. Not vague.

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
- Each commit's `<type>` is in the branching-strategy's allowed types

If any check fails: orchestrator re-drafts the plan addressing the specific failure. **Capped at 2 internal re-drafts.** Append each iteration to `impl-plan-log.md` in the same folder (frontmatter `iteration:`, then the full plan + checks results).

If after 2 re-drafts the mechanical checks still fail, surface to the user with the specific failures and let them decide: approve anyway, abandon, or edit `impl-plan.md` manually.

### 2.3 — Show to user, get decision

Display a **summary** of the impl plan (not the whole file):

```
Implementation plan for subtask N:
  Approach: <one sentence>
  Files: file1.py, file2.py, test.py
  Commits: 2
  Drift: <one line, or "none">
  Gotchas: <one line, or "none">

Full plan at .dev-assistant/issues/<id>/execution/<NN-slug>/impl-plan.md

Approve as-is / refine with comments / abandon?
```

Wait for the user's decision.

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
- `prompt`: the full impl plan + the specific commit's scope + relevant file contents + instructions:
  - "Make the file changes described for commit K of this impl plan."
  - "Do not commit, do not push, do not touch git. Just write the files."
  - "Output: a brief summary of what you changed and which files."

### 3.2 — Orchestrator reviews diff

After the subagent returns:

- Run `git diff` to see what changed
- Brief sanity check:
  - Are only the files in `files to touch` touched? If extras appear, surface to user.
  - Are the changes plausibly aligned with the commit's intent? (Not a full code review — just a "does this look like what we asked for" pass.)

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
commits: <count>
commit_shas: [sha1, sha2, ...]
verified_criteria: <passed>/<total>
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
```

Update `plan.md` subtask frontmatter: `status: done`.

### 3.8 — Open the sub-PR (`sub-branches` mode only; CONFIRM each external op)

In `single-branch` mode, skip this step entirely. (Experimental mode never reaches here in sub-branches form — it forces single-branch behavior.)

After verification passes, land this subtask as its own PR against the parent feature branch:

1. **Rebase onto the parent tip:** `git fetch origin`, then `git rebase origin/<branch_name>` (or local `<branch_name>` if the parent isn't on origin yet). If this subtask was `stacked_on` a prior sub-branch whose PR has since merged, this rebase is what untangles it. Conflicts → **hard stop**, same protocol as wrap-up rebase: list conflicting files, user resolves, re-invoke.
2. **Push the parent first if needed:** if `origin/<branch_name>` doesn't exist, the sub-PR has no base. **Ask: "About to push parent branch `<branch_name>` to origin (needed as sub-PR base). Proceed?"** On confirm: `git push -u origin <branch_name>`.
3. **Push the sub-branch (CONFIRM):** *"About to push `<sub_branch>` to origin. Proceed?"* — `git push -u origin <sub_branch>` (first push) or `--force-with-lease` (re-push after rebase).
4. **Open the sub-PR (CONFIRM):** build title + body from `pr-template` scoped to this subtask (subtask objectives, passing-criteria results, commit list, link to the GH issue if `gh_issue_created`). **Display proposed title + body. Ask: "Open this sub-PR? Target: `<branch_name>`. Proceed?"** On confirm: `gh pr create --base <branch_name> --head <sub_branch> --title ... --body ...`. Record `sub_pr_url` in the subtask's frontmatter in `plan.md`.
5. **Comment on the Jira subtask (optional, CONFIRM):** only if Atlassian MCP is available and `jira_subtask_key` is recorded — short comment per `comment-style`, e.g. `"Sub-PR opened: <url>. Targets <branch_name>."`

Any step declined → stop here gracefully; record whatever state was reached. The user can finish manually (and paste `sub_pr_url` into `plan.md`) or re-invoke `/dev-execute <issue-id> <N>` to resume — sub-phase 1b will detect the existing `sub_branch` and skip to whatever's missing.

Sub-PRs merge into the **parent feature branch**, never into the version branch, and merge sequentially (`sub-1` before `sub-2`) per the branching strategy. The user merges on GitHub after review; `/dev-feedback <issue-id> <N>` handles review rounds on a sub-PR.

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
- In normal mode: `origin/<target version branch>` exists (will be needed for rebase)
- **In `sub-branches` mode additionally:** every subtask has a `sub_pr_url` and every sub-PR is **merged** (`gh pr view <url> --json state,merged` per subtask). If any are missing or still open, stop and list them: *"Sub-PRs not merged: subtask 2 (<url>, OPEN), subtask 4 (no sub-PR). Merge them into `<branch_name>` first, then re-invoke wrap-up."*

If any fail → stop with a clear message. No external ops attempted.

### 4.2 — Catch-up on deferred external prep (skipped in experimental mode)

In experimental mode, skip this entire sub-stage.

Otherwise: scan all subtasks for incomplete external prep.

- For any subtask with `jira_pushed: false`, list it: "Subtask 2 (`Wire OAuth callback`) — Jira not pushed."
- For issue-level `gh_issue_created: false`, list it.

If anything is incomplete, ask: *"Handle deferred external prep now before PR opens? Options: yes (one prompt per item), no (proceed without)."*

If user says yes, walk each item with the same flow as sub-phase 1a. If user says no, proceed with whatever state is recorded.

### 4.3 — Rebase (skipped in experimental mode)

In experimental mode, skip rebase entirely.

Otherwise:

- `git fetch origin`
- `git rebase origin/<target version branch>` (from `plan.md`'s `branch_base` or by re-resolving latest)
- If the rebase has conflicts → **hard stop**. List conflicting files. Tell the user: *"Rebase has conflicts. Resolve them manually (`git rebase --continue` after fixing), then re-invoke `/dev-execute <issue-id> wrap-up`."*
- If clean → report "Rebased onto `version/1.2.0` (no conflicts)."

### 4.4 — Push (skipped in experimental mode; otherwise CONFIRM)

In experimental mode, skip push entirely.

Otherwise:

- **Ask user: "About to push `<branch>` to origin (force-with-lease, post-rebase). Proceed?"**
- On confirm: `git push --force-with-lease origin <branch>`
- On decline: stop wrap-up. Tell user they can manually push and re-invoke wrap-up later, or skip the rest of wrap-up.
- Report: "Pushed `feat/VN-742-oauth-flow` to origin."

### 4.5 — Open PR (skipped in experimental mode; otherwise CONFIRM)

In experimental mode, skip PR open entirely.

Otherwise:

- Build the PR title and body from `pr-template`, populated with subtask summaries, the GH issue link (if `gh_issue_created`), and commit references. In `sub-branches` mode, include a "Sub-PRs" section listing each subtask's merged sub-PR (`#num — title`) so reviewers know the pieces were already reviewed individually.
- **Display the proposed title + body. Ask user: "Open this PR? Target: `<version branch>`. Proceed?"**
- On confirm: `gh pr create --title "<title>" --body "<body>" --base "<version branch>"`. Capture the returned URL.
- On decline: stop wrap-up. PR can be opened manually later.
- Record `pr_url` in `plan.md` frontmatter.
- Report: "PR opened: `<url>`"

### 4.6 — Comment on Jira parent (skipped in experimental mode; otherwise CONFIRM)

In experimental mode, skip Jira comment entirely.

Otherwise (and only if Atlassian MCP is available):

- Build the comment from `comment-style` strategy — short, e.g. `"PR opened: <PR URL>\nTargets version/<x.y.z>. Awaiting review."`
- **Display the comment. Ask user: "Post this comment on Jira `<issue-id>`? Proceed?"**
- On confirm: post via Atlassian MCP.
- On decline: skip. User can comment manually.

If MCP is unavailable, skip with a brief message.

### 4.7 — Generate team message (local-only, no confirm needed; always runs)

Build the Spanish team message from `team-update-template`, populated with:

- PR URL (or "[PR not opened]" in experimental mode)
- Issue ticket and title
- 2–3 bullets summarizing what changed (derived from subtask titles and commit messages)
- Target version branch

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
pr_url: <url or null>
target_version: <x.y.z or "experimental">
total_subtasks: <n>
total_commits: <count>
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

## Deviations from plan

Differences between what `plan.md` proposed and what actually got committed.

## Notes for /dev-evaluate

What worked, what didn't, anything worth retrospecting.
```

### 4.9 — Final report

Terse summary to the user:

```
Wrap-up complete for <issue-id>.
- N subtasks, M commits
- PR: <url or "not opened">
- Team message ready at .dev-assistant/issues/<issue-id>/execution/team-message.txt (and shown above for copy)
- Wrap-up report at .dev-assistant/issues/<issue-id>/execution/wrap-up-report.md

Next: /dev-evaluate <issue-id> (not yet implemented).
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
