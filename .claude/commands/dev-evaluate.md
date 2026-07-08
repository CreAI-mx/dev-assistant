---
description: Walk the evaluate (retrospective) phase for one issue — reads all prior artifacts, distills lessons, posts a closure summary on the GitHub issue, transitions Jira parent + subtasks, closes the GH issue (gated on PR state), and archives lessons both per-issue and repo-wide
argument-hint: <issue-id>
model: opus
allowed-tools: Bash(dev-assistant:*), Bash(git:*), Bash(gh:*), Read, Write, Edit, Grep, Glob
---

You are running the **evaluate** phase for issue `$ARGUMENTS`.

This is the final phase. It produces the retrospective, archives lessons, and closes the loop externally (GH issue comment + close, Jira transitions). Each invocation runs once; on re-runs, already-completed external ops are detected and skipped silently.

## Argument parsing

`$ARGUMENTS` is the issue ID. Take the first whitespace-separated token. No other arguments are supported in v1.

## Current state of the issue

!`dev-assistant issue show --id $ARGUMENTS`

Then read these files directly:

- `.dev-assistant/issues/<issue-id>/issue.md`
- `.dev-assistant/issues/<issue-id>/gathering/objectives.md`
- `.dev-assistant/issues/<issue-id>/gathering/report.md`
- `.dev-assistant/issues/<issue-id>/plan/plan.md`
- `.dev-assistant/issues/<issue-id>/plan/report.md`
- `.dev-assistant/issues/<issue-id>/execution/*/execution-notes.md` (all subtasks)
- `.dev-assistant/issues/<issue-id>/execution/wrap-up-report.md`
- `.dev-assistant/issues/<issue-id>/feedback/round-*/report.md` (all rounds, if any)
- `.dev-assistant/issues/<issue-id>/merge/report.md` (if it exists — the PR was merged via `/dev-merge`)

## Pre-flight (stop early on failure)

1. **Issue workspace exists** — if missing, stop with *"No workspace for `<issue-id>`. Nothing to evaluate."*.
2. **Execute completed at least to the point of wrap-up** — `execution/wrap-up-report.md` should exist (in normal mode) or all subtasks should be `status: done` in `plan.md` (in experimental mode). If not, stop with *"Execute is not complete for `<issue-id>`. Run `/dev-execute` through wrap-up before evaluating."*.
3. **`gh` CLI authenticated** (skipped in experimental mode) — `gh auth status` clean. If not, stop with *"`gh` not authenticated."*.
4. **Working tree clean** — `git status --porcelain` empty. If not, stop. (Evaluate doesn't commit code, but a dirty tree may signal incomplete work the user has forgotten.)

## Experimental mode

Read `issue.md` frontmatter. If `experimental: true`:

- Surface: *"Experimental mode — sub-phase 4 (External) will be skipped entirely. Retro and lessons are still produced locally."*
- Sub-phases 1, 2, 3, 5 run normally; **sub-phase 4 is skipped wholesale**.

## Strategies that shape this phase

### Comment style (drives the GH issue closure comment + any Jira comments)

!`dev-assistant strategies show comment-style`

### Output style — how to write the artifacts this phase produces

!`dev-assistant strategies show output-style`

### Repo context — repo-specific rules to respect

!`dev-assistant repo-context show`

The above is the target repo's own guideline documents. Reference them in the retro when assessing outcomes — did we follow the rules they describe? Lessons that surface deviations from these rules are especially valuable. If a repo-context rule conflicts with a strategy, the repo-context rule wins.

---

## Confirmation principle (non-negotiable)

**Anything that touches the outside world requires explicit user confirmation, regardless of auto / auto-accept-edits modes.** For this phase that includes:

- Posting the GitHub issue closure comment
- Transitioning Jira parent or subtasks (any status change)
- Closing the GitHub issue
- Archiving the local workspace (`dev-assistant issue archive`) — reversible but a state change worth confirming

Local operations (writing retro / lessons / archive files) do not require confirmation — they are reversible and contained.

**Batch-review rule (from user feedback, applies broadly):** All external-facing text + all proposed status changes are assembled into a **single batch view** before any of them fire. The user approves, edits per item, or skips per item. Reference: [[feedback-dev-feedback-batch-reply-review]] — same principle.

## How to interact with the user

- **Announce which sub-phase you're entering** before each one.
- **Be terse during fact-gathering, full during the retro draft.** The retro and lesson distillation is where the user wants depth; the load/analyze passes are background.
- **Show summaries, link to files.** The full retro is in `retro.md`; in chat, show structured highlights and let the user open the file.

---

## Sub-phase 1 — Load

Read every artifact listed in "Current state" above. Determine the PR state by reading `plan.md`'s `pr_url`, then running (in normal mode):

```
gh pr view <pr_url> --json state,merged,mergedAt,closedAt,headRefName,baseRefName
```

Classify the PR into one of:

- **`merged`** — `merged: true`
- **`closed-unmerged`** — `state: CLOSED` and `merged: false` (abandoned)
- **`open`** — `state: OPEN` (if reviews are done and it's approved, the missing step is `/dev-merge <issue-id>` — suggest it)
- **`n/a`** — experimental mode, no PR opened

### Verify remote state (don't trust the local artifacts alone)

The retro must be grounded in what GitHub/Jira actually show, not what the phase reports claim. In normal mode, verify:

1. **PR** — the classification above, plus `mergeCommit` (matches `merge/report.md`?), `reviewDecision`, and review-round count vs local `feedback/round-*` folders.
2. **Replies posted** — for each feedback round report, spot-check that the replies it records as posted actually exist on the PR (comments authored by the current `gh` user). A round with `partial_post: true` or missing replies is a finding for the retro.
3. **GH issue** — `gh issue view <num> --json state,assignees` (exists? still open? assigned?).
4. **Branch** — does `origin/<branch_name>` still exist? (Post-merge it should be deleted per the strategy; still existing after merge is a loose end.)
5. **Jira** — via Atlassian MCP if available: parent + subtask statuses as they stand now.

Record the results — they feed the retro's "Remote state" section and the report frontmatter.

Build a timeline mentally (no need to write it out yet): gather start → plan written → execute first subtask → ... → PR opened → feedback rounds → merge → current state.

Surface to the user: *"Loaded artifacts for `<issue-id>`. PR state: `<state>` (verified remotely). <N> subtasks, <M> feedback rounds. Remote checks: <all consistent | list of discrepancies>."*

## Sub-phase 2 — Analyze (outcomes + drift)

Two passes over the loaded data.

### 2.1 — Outcomes against original objectives

Read `gathering/objectives.md` — both the general objective and the specific items (3–7 testable items). For each:

- **Did it land?** — yes / partially / no / deferred / dropped
- **Evidence** — point at execution-notes commits, verified criteria, feedback-round outcomes
- **If not landed** — why

### 2.2 — Drift from plan

Compare `plan/plan.md` against actual execution + feedback:

- Subtasks planned vs subtasks actually executed (any added, skipped, merged?)
- Files planned to touch vs files actually touched (via execution-notes + `git log`)
- Branch / commit count vs plan estimate
- Anything reviewers raised that the plan missed (from feedback rounds)
- Anything in the plan that turned out not to be needed

Don't write this out yet — hold it for sub-phase 3.

## Sub-phase 3 — Retro (draft, user reviews)

### 3.1 — Draft `evaluation/retro.md` (the thinking artifact)

```markdown
---
issue: <issue-id>
phase: evaluation
status: draft
pr_url: <url or null>
pr_state: <merged | closed-unmerged | open | n/a>
total_subtasks: <n>
total_feedback_rounds: <n>
total_commits: <n>
experimental: <true | false>
---

# Retrospective — <issue-id>

## Timeline

Chronological account from gather to current state. One short paragraph per major beat: gathering, planning, executing, feedback rounds, merge, PR outcome.

## Remote state

What GitHub/Jira actually showed at evaluation time (from the sub-phase 1 verification): PR + merge commit, replies-posted spot-check, GH issue state, branch cleanup, Jira statuses. Discrepancies between local reports and remote reality are retro findings — list them here.

## Outcomes against objectives

| Objective | Landed | Evidence |
|---|---|---|
| <general objective> | <yes/partial/no> | <ref> |
| <specific 1> | <yes/partial/no/deferred> | <ref> |
| ... |

## Drift from plan

What changed between plan and reality:

- **Subtasks**: <added X / skipped Y / merged Z>
- **Files**: <plan said A, reality touched B>
- **Commit count**: planned <n>, actual <m>
- **Reviewer-driven additions**: <list, from feedback rounds>
- **Plan items that proved unneeded**: <list>

## What went well

3–5 specific things. Cite evidence.

## What didn't go well

3–5 specific things. Cite evidence. Blameless tone — observations, not judgments.

## Surprises

Things you didn't expect at gather time that emerged later.

## Decisions worth noting

Non-obvious calls made during the issue that future-you might want to remember.

## Suggested follow-ups

Things identified during this issue that should become future tickets. Format:

- <one-line description> — (suggested: file as new ticket, not done in this issue)

These are surfaced in the GH closure comment so they don't get lost.
```

### 3.2 — Draft `evaluation/lessons.md` (the per-issue decision artifact)

```markdown
---
issue: <issue-id>
phase: evaluation
status: draft
total_lessons: <n>
---

# Lessons — <issue-id>

(One section per lesson. Categorize as process / technical / collaboration.)

## Lesson 01 — <short title>

- **Category**: process | technical | collaboration
- **What happened**: 1–2 sentences with evidence (commit, file, PR comment, etc.)
- **What to do differently**: 1–2 sentences, actionable
- **Promotion candidate**: true | false  (true = likely generalizable beyond this repo)

## Lesson 02 — ...
```

### 3.3 — Show to user, get decision

Display a structured summary:

```
Retro drafted for <issue-id> (PR state: <state>).

Outcomes:
  - <general objective>: <landed/partial/no>
  - <X> of <Y> specific items landed
  - <N> deferred to follow-up tickets

Drift:
  - <one-line summary>

Distilled <K> lessons:
  01 (process)     <title>
  02 (technical)   <title>
  03 (collaboration) <title>

Files:
  .dev-assistant/issues/<id>/evaluation/retro.md     (thinking)
  .dev-assistant/issues/<id>/evaluation/lessons.md   (decisions)

Approve / edit retro / edit lessons / abandon?
```

Wait for the user's decision. **Pause and wait even under auto mode.**

- **Approve** → set `status: approved` in both frontmatters, proceed to sub-phase 4.
- **Edit retro / lessons** → re-open the file, let user edit, re-show summary.
- **Abandon** → leave files as drafts; stop. No external ops, no archive.

---

## Sub-phase 4 — External (skipped in experimental mode)

If experimental mode, skip this sub-phase entirely. Print *"experimental mode — skipping external ops"* and proceed to sub-phase 5.

### 4.1 — Detect already-completed external ops (re-run idempotency)

Before drafting anything, check current state of each external endpoint:

- **GH issue closure comment** — did a comment from us already get posted on the GH issue announcing closure? Check `gh issue view <num> --json comments` and look for a comment authored by the current user that mentions the PR URL or contains a closure phrase. Mark as `already_done` if present.
- **Jira parent state** — fetch current status via Atlassian MCP. If already in `Done` / `Won't Do`, mark `already_done`.
- **Jira subtasks** — same, per subtask.
- **GH issue closed** — `gh issue view <num> --json state`. If `CLOSED`, mark `already_done`.

Any op marked `already_done` is dropped silently from the batch.

If everything is `already_done`, skip to sub-phase 5 with *"All external ops already complete from a prior evaluate run. Proceeding to archive."*.

### 4.2 — Determine what fires based on PR state

| PR state | GH comment | Jira subtasks | Jira parent | Close GH issue |
|----------|-----------|---------------|-------------|----------------|
| `merged` | yes (summary + follow-ups) | → Done | → Done | yes |
| `closed-unmerged` | yes (explain why dropped, surface lessons) | → Won't Do | → Won't Do | yes |
| `open` | yes (interim retro, link to retro.md location) | unchanged | unchanged | **no** |

In the `open` case, sub-phase 4 still runs but only posts the interim-retro comment. All status transitions and the close action are deferred to a future re-run after the PR resolves.

### 4.3 — Draft the GH issue closure comment

Use `comment-style` strategy (lead with verb / outcome, short, no filler, no emojis). Template per PR state:

**Merged:**

```
Closed via <PR URL>.

What worked:
- <bullet 1>
- <bullet 2>

What didn't:
- <bullet 1>
- <bullet 2>

Follow-ups identified (suggest filing as new tickets):
- <bullet 1>
- <bullet 2>

Retro: see internal notes.
```

**Closed-unmerged (abandoned):**

```
Closing without merge. PR <URL> was abandoned.

Reason: <one sentence>.

Lessons captured for future work.
```

**Open (interim):**

```
Interim retro posted while PR <URL> is still under review.

Status so far:
- <bullet>
- <bullet>

Will follow up at merge / close.
```

Save the drafted comment to `evaluation/closure-comment.md` so it's reviewable as a file.

### 4.4 — Draft Jira transition messages (if Atlassian MCP available)

For each Jira transition that will fire (parent + each subtask), draft a one-line transition comment if `comment-style` calls for one (e.g., parent gets a comment with the PR URL; subtasks transition silently unless the user wants individual comments).

Default: parent gets a transition comment; subtasks transition silently.

If Atlassian MCP is **not** available in this session: skip all Jira ops with a clear message ("Atlassian MCP not available — skipping Jira transitions; do them manually if needed").

### 4.5 — Batch-review the full external set

Assemble everything that's about to fire into one consolidated view:

```
================================================================
EXTERNAL OPERATIONS BATCH — review everything before any go out
================================================================

PR state: <state>

──────────────────────────────────────────────────────────────
1. GH ISSUE COMMENT — issue #<num>
   action: POST
   body:
   > <full closure comment text from 4.3>

──────────────────────────────────────────────────────────────
2. JIRA SUBTASK TRANSITIONS
   <SUBTASK-KEY-1>  current: In Review  →  new: Done   (silent)
   <SUBTASK-KEY-2>  current: In Review  →  new: Done   (silent)
   <SUBTASK-KEY-3>  already in Done — skipped

──────────────────────────────────────────────────────────────
3. JIRA PARENT TRANSITION
   <PARENT-KEY>  current: In Review  →  new: Done
   transition comment:
   > Closed via <PR URL>.

──────────────────────────────────────────────────────────────
4. GH ISSUE CLOSE — issue #<num>
   action: CLOSE (state will become CLOSED)
   gating: PR is <state> → allowed
              (in `open` state this row reads: "skipped — PR still open")

================================================================
Total: <count> external operations.

Options:
  (a) Approve batch — fire all in order
  (b) Edit a specific item — tell me which (1–4), I'll open it for editing
  (c) Skip specific items — tell me which to omit
  (d) Abandon all external ops (retro + lessons stay local)
```

**Wait for user decision. Pause even under auto mode.**

- **Approve** → proceed to 4.6.
- **Edit / skip** → apply changes, re-show the batch.
- **Abandon** → record `external_abandoned: true` in `retro.md` frontmatter, skip to sub-phase 5.

### 4.6 — Fire the batch in order

Execute in this exact order; each step is a single API call and surfaces its result before the next:

1. **Post GH issue comment**: `gh issue comment <num> --body-file evaluation/closure-comment.md`. Print *"posted closure comment on issue #<num>"*.
2. **Transition Jira subtasks** (in order listed). For each: post optional comment (if any) → transition. Print *"transitioned `<KEY>` → Done"* per subtask.
3. **Transition Jira parent**: post transition comment → transition. Print *"transitioned `<PARENT-KEY>` → Done"*.
4. **Close GH issue** (only if PR state allows): `gh issue close <num>`. Print *"closed issue #<num>"*.

If any step fails: surface the error verbatim, stop the batch, record what completed in `retro.md` frontmatter (`external_partial: true` plus per-op status). User can re-invoke `/dev-evaluate` — the idempotency check in 4.1 will pick up where it left off.

---

## Sub-phase 5 — Archive

### 5.1 — Per-issue lessons file (already saved)

`evaluation/lessons.md` is already at `status: approved` from sub-phase 3.3. Nothing to do here except confirm it exists.

### 5.2 — Repo-wide lessons archive (organized by category, deduplicated, indexed)

The archive is organized so lessons can actually be found and so recurring lessons accumulate weight instead of piling up as near-duplicates.

**Layout:**

```
.dev-assistant/lessons/
  INDEX.md                 ← regenerated on every archive run
  process/
    <YYYY-MM-DD>-<issue-id>-<lesson-slug>.md
  technical/
    ...
  collaboration/
    ...
```

`mkdir -p` the category folders as needed. **Migration:** if flat lesson files exist at the `lessons/` root (pre-0.6 layout), move each into its category folder (read `category:` from its frontmatter) before archiving — say what was moved.

**Dedupe before writing.** For each lesson in `evaluation/lessons.md`, scan the existing archive (titles in `INDEX.md` + frontmatter of files in the same category) for a lesson making the same point. Judge by meaning, not string match.

- **New lesson** → create `.dev-assistant/lessons/<category>/<YYYY-MM-DD>-<issue-id>-<lesson-slug>.md`.
- **Recurrence of an existing lesson** → do NOT create a new file. Update the existing one: append a row to its `## Recurrences` section (`<date> — <issue-id> — <one line on how it showed up>`) and bump `recurrences:` in its frontmatter. A lesson that keeps recurring is the strongest promotion candidate there is — flip `promotion_candidate: true` at 2+ recurrences if not already set.

The individual file mirrors the per-issue lesson section, with extra frontmatter for retrieval:

```markdown
---
source_issue: <issue-id>
issue_title: <from issue.md>
category: process | technical | collaboration
promotion_candidate: <true | false>
recurrences: <n>            # 0 for a first occurrence
archived_at: <ISO timestamp>
pr_url: <url or null>
pr_state: <state>
---

# <lesson title>

## What happened
...

## What to do differently
...

## Recurrences

(Empty for a first occurrence. One line per later sighting: `<YYYY-MM-DD> — <issue-id> — <how it showed up>`.)

## Context
- Issue: <id> — <title>
- PR: <url> (<state>)
- Related artifacts: `.dev-assistant/issues/<id>/evaluation/`
```

If a file with the same name already exists (same-issue re-run case), overwrite it — the per-issue lessons.md is the source of truth.

**Regenerate `INDEX.md`** from the files on disk (never hand-maintained; a full rebuild each run keeps it honest):

```markdown
# Lessons index

Regenerated by /dev-evaluate on <date>. <N> lessons (<P> promotion candidates, <R> with recurrences).

## Promotion candidates

| Lesson | Category | Source issue | Recurrences |
|---|---|---|---|
| [<title>](<category>/<file>.md) | technical | VN-742 | 2 |

## process
| Date | Issue | Lesson | Recurs |
|---|---|---|---|
| 2026-07-08 | VN-788 | [<title>](process/<file>.md) | — |

## technical
...

## collaboration
...
```

Report: *"Archived <K> lessons (<new> new, <merged> merged into existing as recurrences) to `.dev-assistant/lessons/` — <P> promotion candidates. Index rebuilt."*

### 5.3 — Write the evaluation report

Write `evaluation/report.md`:

```markdown
---
issue: <issue-id>
phase: evaluation
status: complete | partial
completed_at: <ISO timestamp>
pr_state_at_evaluation: <state>
remote_state_verified: <true | discrepancies listed in retro.md>
external_ops:
  gh_comment: <posted | already_done | skipped | failed | n/a>
  jira_subtasks: <transitioned: N, already_done: M, skipped: P, failed: Q>
  jira_parent: <transitioned | already_done | skipped | failed | n/a>
  gh_issue_close: <closed | already_done | skipped (pr_open) | failed | n/a>
lessons_archived: <count>
promotion_candidates: <count>
---

# Evaluation report — <issue-id>

## Summary
1–2 sentences. End state + biggest takeaway.

## External outcomes
What fired, what was already done, what was skipped, what failed.

## Where lessons live
- Per-issue: `.dev-assistant/issues/<id>/evaluation/lessons.md`
- Repo-wide: `.dev-assistant/lessons/<category>/<YYYY-MM-DD>-<id>-*.md` (<new> new, <merged> merged as recurrences) — see `.dev-assistant/lessons/INDEX.md`

## Suggested follow-up tickets
Lifted from `retro.md`. User to file manually.

- <follow-up 1>
- <follow-up 2>

## Workspace location
- If archived: `.dev-assistant/archive/issues/<id>/`
- If kept in place: `.dev-assistant/issues/<id>/`
```

### 5.4 — Workspace archive offer

Ask the user:

```
Evaluate complete. Workspace `.dev-assistant/issues/<issue-id>/` is under active issues.

Options:
  (a) Archive — move to `.dev-assistant/archive/issues/<issue-id>/` (recommended)
       Keeps the workspace for future reference; clears it out of active listings.
       Reversible (it's just a directory move).
  (b) Leave in place — keep under `.dev-assistant/issues/`
       Use this if you expect more work on this issue (re-opened PR, follow-up rounds).
```

- If **(a)**: run `!dev-assistant issue archive --id <issue-id>`. The CLI moves the directory and updates `issue.md` frontmatter to `status: archived` with an `archived_at` timestamp. Report the new path.
- If **(b)**: no-op, report *"workspace kept at `.dev-assistant/issues/<id>/`"*.
- **No `rm -rf` option exists** — archive is always non-destructive. If a user later wants to truly delete an archived workspace, they can `rm -rf .dev-assistant/archive/issues/<id>/` manually (intentionally not exposed as a command).

### 5.5 — Final report

```
Evaluate complete for <issue-id>.
  - PR state at evaluation: <state>
  - External: <one-line summary>
  - Lessons archived: <K> (<P> promotion candidates)
  - Workspace: kept at .dev-assistant/issues/<id>/

Retro:    .dev-assistant/issues/<id>/evaluation/retro.md
Lessons:  .dev-assistant/issues/<id>/evaluation/lessons.md
Report:   .dev-assistant/issues/<id>/evaluation/report.md
Archive:  .dev-assistant/lessons/
```

---

## Re-running and state behavior

`/dev-evaluate` is designed to be re-invokable safely.

- **Re-running after a complete evaluate**: idempotency check in 4.1 detects all external ops as `already_done`. The retro + lessons can be re-drafted (user opts to edit) but external ops are skipped.
- **Re-running after a partial evaluate** (some external ops fired, some failed): the idempotency check picks up only the un-fired ops. The batch view shows only those.
- **Re-running while PR was `open` last time and is now `merged`**: re-runs naturally pick up the new transitions / close that weren't possible before.
- **Re-running to refresh the retro after new feedback rounds**: editing the retro is always allowed; sub-phase 3 will offer to re-draft from current artifacts.

## If something fails in a destructive-feeling way

- GH comment post fails → surface, stop, mark partial. Re-run picks up.
- Jira transition fails → surface, stop on that op. Already-completed transitions stay. Re-run picks up.
- GH issue close fails → surface, leave issue open. User can close manually or re-run.
- Atlassian MCP unavailable mid-batch → skip remaining Jira ops with a message; GH ops still proceed.
- Workspace archive is opt-in via `dev-assistant issue archive`. There is no wipe operation by design — archived workspaces stay on disk for future reference.
