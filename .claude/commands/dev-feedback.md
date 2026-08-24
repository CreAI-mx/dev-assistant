---
description: Walk one round of the PR review feedback loop — pulls new comments, triages by severity+type, clusters them, drafts code fixes and replies, applies fixes as commits, batch-reviews ALL replies in one go, then pushes and posts them
argument-hint: <issue-id> [subtask-n]
model: opus
allowed-tools: Bash(dev-assistant:*), Bash(git:*), Bash(gh:*), Read, Write, Edit, Grep, Glob, Agent
---

You are running the **feedback** phase for issue `$ARGUMENTS`.

This phase handles **one round** of PR review iteration. Each invocation = one round. New review comments arrive → re-invoke `/dev-feedback <issue-id>` → another round runs.

## Argument parsing

`$ARGUMENTS` is the issue ID, optionally followed by a subtask number. Take the first whitespace-separated token as the issue ID.

- **`<issue-id>` alone** — the round targets the issue's main PR (`pr_url` in `plan.md` frontmatter). This is the only form valid in `single-branch` mode.
- **`<issue-id> <N>`** — only valid when `plan.md` has `branching_mode: sub-branches`: the round targets subtask `N`'s sub-PR (`sub_pr_url` in the subtask's frontmatter) on its `sub_branch`. If the plan is `single-branch`, stop with *"This issue uses single-branch mode — there are no sub-PRs. Run `/dev-feedback <issue-id>`."*

In `sub-branches` mode with no subtask argument: if the parent `pr_url` is not yet set but open sub-PRs exist, list them and ask which one to run the round against, rather than failing on the missing parent PR. (This is an escalation — an ambiguous target — so it asks at every autonomy level.)

A trailing `--guided` / `--balanced` / `--auto` token overrides the issue's autonomy level for this invocation only; strip it before parsing the issue ID and subtask number.

## Current state of the issue

!`dev-assistant issue show --id $1`

(`$1` is the issue ID alone — the optional subtask number must never reach the CLI; it takes exactly one `--id` value.)

Then read these files directly for state:

- `.dev-assistant/issues/<issue-id>/issue.md`
- `.dev-assistant/issues/<issue-id>/plan/plan.md`
- `.dev-assistant/issues/<issue-id>/execution/wrap-up-report.md` (if it exists — confirms execute finished)

## Pre-flight (stop early on failure)

Before doing anything, verify all of:

1. **Issue workspace exists** — if `.dev-assistant/issues/<issue-id>/` is missing, stop with *"No workspace for `<issue-id>`. Run `/dev-gather` first."*.
2. **Plan exists** — if `plan/plan.md` is missing, stop with *"No plan for `<issue-id>`. Run `/dev-plan` first."*.
3. **Target PR has been opened** — resolve per the argument parsing above: the parent `pr_url` from `plan.md` frontmatter, or subtask `N`'s `sub_pr_url`. If the resolved URL is missing or null, stop with *"`pr_url` is not set in `plan.md`. Run `/dev-execute <issue-id>` through wrap-up to open the PR first."* (or, for a subtask target: *"Subtask `N` has no `sub_pr_url`. Run `/dev-execute <issue-id> <N>` through sub-phase 3.8 to open the sub-PR first."*). Everywhere below, "the PR" / `pr_url` means this resolved target.
4. **Working tree clean** — `git status --porcelain` returns nothing. If dirty, stop with *"Working tree has uncommitted changes. Commit, stash, or discard them before running feedback."*.
5. **On the right branch** — current branch matches the target PR's branch: `plan.md`'s `branch_name`, or the subtask's `sub_branch` when targeting a sub-PR. If not, stop with *"Expected to be on `<branch>`, found `<current>`. Check out the right branch first."*.
6. **Not experimental** — read `issue.md` frontmatter. If `experimental: true`, stop with *"Experimental mode is active for `<issue-id>`. No PR exists to review. `/dev-feedback` is skipped."*. (Experimental mode never opens a PR, so there is nothing to feed back on.)
7. **`gh` CLI authenticated** — `gh auth status` exits cleanly. If not, stop with *"`gh` is not authenticated. Run `gh auth login` first."*.
8. **PR base is what the plan says** — `gh pr view <pr_url> --json baseRefName` matches `plan.md`'s `target_branch` (default `develop` when the field is missing; for a sub-PR target, the base must be the parent `branch_name`). On mismatch, stop with *"PR base is `<actual>` but the plan targets `<expected>`. Fix the PR base (`gh pr edit --base`) or the plan before running feedback."* — fixes verified against the wrong base are worthless.

If any check fails, stop. Do not attempt sub-phase 1.

## Strategies that shape this phase

### Comment style (drives the tone of replies)

!`dev-assistant strategies show comment-style`

### Branching strategy (drives commit messages for code fixes)

!`dev-assistant strategies show branching-strategy`

### Code economy (drives how big a fix is allowed to get)

!`dev-assistant strategies show code-economy`

Review rounds are where issues quietly double in size: a comment asks for a rename and the fix arrives as a refactor. Every cluster's fix is sized, and **a fix that outgrows its comment is a follow-up ticket, not a bigger commit** — see sub-phase 3.2.

### Output style — how to write the artifacts this phase produces

!`dev-assistant strategies show output-style`

### Repo context — repo-specific rules to respect

!`dev-assistant repo-context show`

The above is the target repo's own guideline documents. Apply when triaging and fixing review comments — reviewers will often anchor their feedback in these rules, so the triage classifier should recognize references and the fixes should respect the same conventions. If a repo-context rule conflicts with a strategy, the repo-context rule wins.

---

## Confirmation principle (non-negotiable)

**Nothing touches the outside world without explicit user confirmation.** This holds at every autonomy level and under Claude Code's auto-accept-edits mode. For this phase that includes:

- `git push` (any branch, any time)
- Posting replies to GitHub PR comments
- Resolving review threads on GitHub
- Editing the PR body via `gh pr edit`

Local operations (file edits, drafting impl-plans / replies, `git commit`) do not require confirmation — they are reversible and contained.

**Reply-batch rule (critical, from user feedback):** All drafted replies must be presented as **one single batch** for user review **before any reply is posted to GitHub**. Replies are drafted in sub-phase 3 and held locally until the batch-review checkpoint in sub-phase 5. Do not post reply-by-reply as code fixes are applied. **This rule holds at every autonomy level — `auto` included.** It is the reason the sub-phase 5 batch is never skippable.

## Autonomy level — how many checkpoints this round fires

The `## Autonomy` block in the `dev-assistant issue show` output above resolves this issue's level (`guided` | `balanced` | `auto`). Issues created before the field existed resolve to `guided`.

| Kind of stop | `guided` | `balanced` | `auto` |
|---|---|---|---|
| **Approval** — triage (2.3), per-cluster impl plans (4.1) | both, per cluster | **one checkpoint, at 3.5** — triage + every impl plan + every drafted reply in one view | none — but every classification and skip is recorded in the round report |
| **External** — push, post replies, resolve threads, edit PR body | one confirmation per operation | **one batch, at 5.1** — the reply batch *is* the external batch | same one batch |
| **Escalation** — a post that fails, a remote-state ✗, an ambiguous PR target | stops | stops | stops |

So a round costs about nine stops at `guided`, **two** at `balanced`, and **one** at `auto` — and that one is the reply batch, which no level removes.

**Never removed at any level in this phase:** the sub-phase 5 reply batch. Replies go out under the user's name, to their colleagues, on their PR. They are reviewed as a complete set before a single one posts.

At `balanced` / `auto`, add `autonomy: <level>` to the round report's frontmatter and a **`## Decided without review`** section listing the classifications, cluster skips, and reply wordings the user did not vet.

## How to interact with the user

- **Announce which sub-phase you're entering** before each one.
- **Be terse during work, full during decisions.** Per-cluster progress is one line; the triage view and the reply-batch view are full.
- **Show summaries, link to files.** When displaying triage, impl-plans, or replies for review, show the structured view in chat and link to the full markdown file the user can open separately.

---

## Round detection

Before sub-phase 1, determine which round number this invocation is. Rounds are tracked **per PR**: rounds for the main PR live in `feedback/round-NN/`; rounds for a sub-PR live in `feedback/sub-<N>/round-NN/` (so sub-PR rounds and parent-PR rounds never share a numbering).

- Read the round base dir — `.dev-assistant/issues/<issue-id>/feedback/` for the main PR, `feedback/sub-<N>/` for a sub-PR target (create it if missing — `mkdir -p`).
- List existing `round-NN/` folders under that base. The next round is `NN = max(existing) + 1`, or `01` if none exist.
- Create `<base>/round-<NN>/` and `<base>/round-<NN>/clusters/`.
- Determine the `since` timestamp for pulling new comments:
  - If this is round 01: `since = null` (pull all comments).
  - Otherwise: read `<base>/round-<NN-1>/report.md` frontmatter for `pulled_at` and use that.

Surface to the user: *"Round NN — pulling comments since `<since>` (or "from PR open" if round 01)."*

---

## Sub-phase 1 — Pull

Fetch comments from the PR. There are three sources on a GitHub PR:

1. **Issue-level comments** — general comments on the PR (not anchored to a line). Endpoint: `gh api repos/{owner}/{repo}/issues/{pr#}/comments`.
2. **Review-thread comments** — inline comments anchored to file lines. Endpoint: `gh api repos/{owner}/{repo}/pulls/{pr#}/comments`. These have a `pull_request_review_id` and `in_reply_to_id` for threading.
3. **Review summaries** — the overall body of a "Request changes" / "Approve" / "Comment" review. Endpoint: `gh api repos/{owner}/{repo}/pulls/{pr#}/reviews`. The `body` field is the summary text.

Extract the PR owner / repo / number from `pr_url` (e.g. `https://github.com/<owner>/<repo>/pull/<num>`).

For each source:

- Pull all entries.
- **Filter to entries newer than `since`** (using `created_at`).
- **Filter out entries authored by the current `gh` user** (your own replies / responses to past rounds — `gh api user --jq .login`).
- **Filter out resolved threads** (for inline review-thread comments, use the GraphQL `reviewThreads.isResolved` field via `gh api graphql`).
- **Filter out praise-only patterns** is NOT done at pull — leave classification for sub-phase 2.

Combine all three sources into one list with a unified shape:

```
- id: <numeric id from GitHub>
  source: issue-comment | review-thread | review-summary
  thread_id: <review thread id, only for review-thread comments; null otherwise>
  in_reply_to: <id of the comment this replies to, if any>
  author: <login>
  created_at: <ISO timestamp>
  path: <file path, only for review-thread comments>
  line: <line number, only for review-thread comments>
  body: <full comment text>
  url: <html_url back to the comment on GitHub>
```

Save the raw pulled list to `feedback/round-NN/pulled.md` for traceability:

```markdown
---
issue: <issue-id>
round: <NN>
pulled_at: <ISO timestamp of this fetch>
pr_url: <url>
since: <ISO or "from PR open">
total: <count>
---

# Pulled comments — round NN

(One section per comment, ordered by `created_at`.)
```

**If `total == 0`**, stop here with *"No new comments since round <NN-1>. Nothing to do."*. Do not create empty triage / cluster folders.

Report to the user: *"Pulled N new comments (X issue-level, Y inline, Z review-summaries)."*

---

## Sub-phase 2 — Triage

Classify each pulled comment on two axes:

- **Severity** — one of:
  - `blocking-correctness` — bugs, security, broken contracts; must fix before merge
  - `blocking-design` — design pushback, missing test coverage for real branch, wrong abstraction; must address or justify
  - `should-fix` — perf, naming, important readability, edge case worth handling
  - `nit` — style, taste, micro-suggestions
  - `question` — reviewer wants clarification, not a code change
  - `praise` — positive feedback, no action needed

- **Type** — one of: `bug`, `security`, `design`, `perf`, `tests`, `style`, `docs`, `question`, `discussion`

Severity drives priority order. Type drives how the fix is approached.

### 2.1 — Auto-classify

For each comment, read the body and the surrounding context (file + line for inline comments) and assign severity + type.

Also assign a **cluster key** — a short slug grouping related comments. Group when:

- They touch the same file or function
- They concern the same underlying issue (e.g., multiple reviewers raising the same point)
- They are all nits in the same area (nits can batch into one commit)

Each cluster needs:

- `id` — `NN` (01, 02, ...), assigned in priority order after sorting
- `slug` — short kebab-case label, e.g. `oauth-redirect-bug`
- `severity` — the highest severity among included comments
- `type` — the type of the lead comment (or `mixed` if genuinely cross-cutting)
- `action` — `code-fix`, `reply-only` (for questions, discussion, praise), or `discussion-deferred` (set by user during review if they want to push back)

### 2.2 — Write triage.md

Sort comments by severity in this order: `blocking-correctness` → `blocking-design` → `should-fix` → `nit` → `question` → `praise`.

Write `feedback/round-NN/triage.md`:

```markdown
---
issue: <issue-id>
round: <NN>
pr_url: <url>
total_comments: <count>
total_clusters: <count>
status: pending-user-review
---

# Triage — round <NN>

## Summary

- N blocking-correctness, M blocking-design, P should-fix, Q nits, R questions, S praise
- Clustered into K actionable units

## Comments

[ ] #<id>  severity · type  short paraphrase of the comment
    by <author> on <path>:<line> (or "PR-level")
    quote: "first ~120 chars of the comment, verbatim, in quotes"
    link: <url>
    cluster: <NN-slug>

[ ] #<id>  ...

## Clusters

| # | Slug | Severity | Type | Action | Comments |
|---|------|----------|------|--------|----------|
| 01 | oauth-redirect-bug | blocking-correctness | bug | code-fix | #34 |
| 02 | redirect-tests | blocking-design | tests | code-fix | #36, #38 |
| 03 | style-nits-auth | nit | style | code-fix | #44, #45, #46 |
| 04 | jose-question | question | question | reply-only | #47 |
```

### 2.3 — User review checkpoint

**At `balanced` / `auto`: skip this checkpoint.** Set `status: approved` in `triage.md` with `approved_by: autonomy-<level>` and go to sub-phase 3 — at `balanced` the triage is shown for approval at 3.5, together with the plans and replies it produced, which is a better view of the same decision. Deferring a cluster to manual discussion is a call only the user makes: at these levels, classify it and let them defer it at the checkpoint (or, at `auto`, in the round report).

**At `guided`:** display the triage view to the user (the summary table + the cluster table, NOT the full per-comment list — link to the file for that). Ask:

```
Triage saved at feedback/round-NN/triage.md.

K clusters identified (N blocking-correctness, M blocking-design, P should-fix, Q nits, R questions).

Review the classification. Options:
  (a) Approve — proceed to drafting fixes and replies
  (b) Reclassify — tell me which clusters or comments to re-tag
  (c) Defer a cluster — mark one as "discussion-deferred" (skip in this round, you'll handle manually)
  (d) Abandon round
```

Wait for the user's decision. **Pause and wait — Claude Code's auto-accept mode does not answer this.**

- **Approve** → set `status: approved` in triage.md frontmatter, proceed.
- **Reclassify / defer** → apply the user's edits (rewrite triage.md), then re-show the cluster table and ask again.
- **Abandon** → leave round folder as-is with `status: abandoned` and stop.

---

## Sub-phase 3 — Plan (draft impl-plans + replies for every cluster)

For each cluster in `triage.md`'s cluster table, in order:

### 3.1 — Create the cluster folder

`feedback/round-NN/clusters/<id>-<slug>/`

Write `meta.md`:

```markdown
---
cluster_id: <NN>
slug: <slug>
severity: <severity>
type: <type>
action: <code-fix | reply-only | discussion-deferred>
comments: [<id1>, <id2>, ...]
status: planned
---

# Cluster <NN> — <slug>

## Included comments
- #<id1> by <author> — <one-line paraphrase> — <url>
- #<id2> ...

## What the reviewers want

2–3 sentences synthesizing the request across all included comments.
```

### 3.2 — Draft `impl-plan.md` (only for `action: code-fix` clusters)

Each cluster's plan carries a **size band** (`S` ≤50 added lines / `M` ≤150 / `L` ≤400) alongside its approach, and the scope rule that goes with it:

- **Most review fixes are S.** A nit is a handful of lines; a bug fix is usually one function and its test.
- **An `M` fix needs a sentence** saying why the comment requires that much.
- **An `L` fix is not a fix.** If a review comment can only be satisfied by an L change, it is a new piece of work: reply saying so, propose a follow-up ticket, and mark the cluster `discussion-deferred` rather than landing a refactor inside a review round. The exception is a reviewer explicitly asking for the big change — then it belongs in the round, sized honestly, and flagged in the round report.
- **The comment is the scope.** Fix what was raised. Adjacent code you noticed while in there is a separate ticket; say so in the reply if it matters.

Measure before committing, the same way `/dev-execute` 3.2 does: `dev-assistant issue size --id <issue-id> --worktree --band <cluster band>`. Over budget → one trim pass → still over → stop and ask (an escalation, so it fires at every autonomy level).

Read the files referenced by the comments to understand current state. Then write `impl-plan.md`:

```markdown
---
cluster: <NN-slug>
status: pending
---

# Impl plan — cluster <NN>

## Approach
2–3 sentences. Concrete, names specific functions/files.

## Files to touch
- `path/file.py` — what changes

## Patterns to follow
- Reference to sibling code if relevant

## Gotchas
- Anything non-obvious

## Commit planned
- `<type>(<scope>): <Description>` — one commit per cluster by default
```

For `discussion-deferred` clusters: skip impl-plan (no code change), only write `reply.md` (sub-phase 3.3).

For `reply-only` clusters: skip impl-plan, only write `reply.md`.

### 3.3 — Draft `reply.md` (every cluster gets one)

Every cluster — code-fix, reply-only, or deferred — gets a `reply.md`. It's the message that will be posted to each of the included comments / threads.

```markdown
---
cluster: <NN-slug>
threads: [<thread_id or comment_id per included comment>]
status: drafted
---

# Reply — cluster <NN>

## Per-thread reply

### Thread #<id> (in reply to <author>)

<the reply text, following comment-style strategy — short, action-oriented, no filler>
```

If multiple comments in a cluster share the same review thread, write one reply for the thread. If they are separate threads, write one reply per thread. (For `question`-action clusters, the reply answers the question. For `code-fix`, the reply will be something like "Fixed in <sha>." — the sha is filled in during sub-phase 4 after the commit.)

Use the `comment-style` strategy verbatim: lead with the verb / outcome, no salutations, no filler, no emojis, short.

### 3.4 — Report planning summary

After all clusters are planned, report to the user:

```
Planned K clusters:
  - 01 oauth-redirect-bug (blocking-correctness · code-fix · 1 commit, 1 reply · S)
  - 02 redirect-tests (blocking-design · code-fix · 1 commit, 2 replies · S)
  - 03 style-nits-auth (nit · code-fix · 1 commit, 3 replies · S)
  - 04 jose-question (question · reply-only · 1 reply)

Round size estimate: ~<n> added lines.

Files at feedback/round-NN/clusters/*/

Proceeding to apply.
```

At `guided` and `auto`, no user confirmation here — proceed to sub-phase 4. (The user gets to see all replies as a batch in sub-phase 5; at `guided`, per-cluster impl-plan approval also happens inside sub-phase 4.)

### 3.5 — Round-plan checkpoint (`balanced` only)

This is the round's single approval, placed here because everything that will happen is now drafted and nothing has been applied yet. One view:

```
================================================================
ROUND NN PLAN — <n> comments → <k> clusters
================================================================

TRIAGE
  01 oauth-redirect-bug   blocking-correctness · bug     → code-fix (1 commit, 1 reply)
  02 redirect-tests       blocking-design · tests        → code-fix (1 commit, 2 replies)
  03 style-nits-auth      nit · style                    → code-fix (1 commit, 3 replies)
  04 jose-question        question                       → reply-only (1 reply)

PLANS (code-fix clusters)               size
  01 → auth.py — store state on session before redirect; fix(auth): …      S
  02 → tests/test_auth.py — add expired-token case; test(auth): …          S
  03 → auth.py, parser.py — naming pass; style(auth): …                    S
                                          round total: ~<n> added lines

DRAFTED REPLIES  (final wording; commit SHAs filled in after the fixes land)
  <the same per-thread view as 5.1, reviewer quote + drafted reply>

================================================================
Approve / reclassify a cluster / defer a cluster to manual discussion /
skip a cluster / edit a reply / abandon round
```

Wait for the decision. On any change, apply it and re-show the whole view. On approve, every cluster is approved — sub-phase 4 applies them without further per-cluster prompts, and sub-phase 5 still shows the reply batch with real SHAs before anything posts.

---

## Sub-phase 4 — Apply (execute fixes in severity order)

For each `code-fix` cluster, in severity order:

### 4.1 — Show impl-plan summary, ask approval

**At `guided`:** per-cluster approval as described here.

**At `balanced`:** the plans were approved as a set at 3.5 — print the one-line summary per cluster and apply, no prompt.

**At `auto`:** print the one-line summary per cluster and apply. A cluster is skipped only when its fix would contradict the plan or the repo context — record any such skip, with its reason, in the round report's `## Decided without review`.

```
Cluster 01 (oauth-redirect-bug, blocking-correctness · bug):
  Approach: <one sentence>
  Files: auth.py
  Commit: fix(auth): preserve state param through OAuth redirect
  Size: S (planned S)
  Replies queued: 1

Full plan at feedback/round-NN/clusters/01-oauth-redirect-bug/impl-plan.md

Approve / refine / skip?
```

- **Approve** → proceed to 4.2
- **Refine** → take comments, re-draft `impl-plan.md`, re-show
- **Skip** → mark cluster `status: skipped` in `meta.md`, continue to next cluster (its reply is also skipped in 5)

**Nits-batching shortcut (`guided`):** if the next-up cluster is severity `nit`, and there are multiple consecutive nit clusters, offer a single "approve all remaining nit clusters" prompt instead of per-cluster confirmation. The user can still say no and approve individually.

### 4.2 — Subagent writes the fix

Dispatch the **Agent tool** with these parameters:

- `subagent_type: general-purpose`
- `description`: "Apply review-fix cluster `<NN-slug>`"
- Model: `sonnet`
- `prompt`: include the impl-plan, the included comment bodies (verbatim), the relevant file contents, and instructions:
  - "Make the file changes described in the impl plan, addressing the included reviewer comments."
  - "Do not commit, do not push, do not touch git. Just write the files."
  - "Output: brief summary of what you changed."

### 4.3 — Orchestrator reviews diff

Run `git diff`. Sanity check:

- Only files in `files to touch` are touched? If extras appear, surface to the user before committing.
- Changes plausibly address the reviewer's point?

### 4.4 — Commit

Build the commit message per the branching strategy (and `meta.md`'s planned commit). Format follows `/dev-execute`:

```
<type>(<scope>): <Description>

- addresses: review comments #<id1>, #<id2>

refs <issue-id>
```

Pass via HEREDOC to `git commit`. **No `--no-verify`.** If the commit fails, surface verbatim and stop.

Record the resulting short SHA in `meta.md` as `commit_sha`. Update `reply.md` — replace any `<sha>` placeholder in the per-thread replies with the real short SHA.

Print: *"committed cluster <NN>: `<commit subject>` (<short sha>)"*.

### 4.5 — Loop

Continue to the next cluster. After all `code-fix` clusters are processed, proceed to sub-phase 5.

`reply-only` and `discussion-deferred` clusters are not iterated here — their replies were already drafted in sub-phase 3.3 and are simply waiting for the batch review.

---

## Sub-phase 5 — Wrap (batch-review replies, push, post, resolve)

### 5.1 — Assemble the reply batch

Read every cluster's `reply.md`. Skip any cluster with `status: skipped`. Build one consolidated view:

```
================================================================
ALL DRAFTED REPLIES — review the full set before any go out
================================================================

──────────────────────────────────────────────────────────────
Cluster 01 (blocking-correctness · bug · oauth-redirect-bug)
Thread #34 — in reply to @reviewer-a on auth.py:142

  reviewer said:
  > the state param isn't preserved through the redirect, which
  > breaks anti-CSRF...

  drafted reply:
  > Fixed in abc123. State is now stored on the session before
  > redirect and verified on return.

──────────────────────────────────────────────────────────────
Cluster 02 (blocking-design · tests · redirect-tests)
Thread #36 — in reply to @reviewer-b on tests/test_auth.py

  reviewer said:
  > no test for the expired-token branch

  drafted reply:
  > Added test_expired_token in def456.

Thread #38 — in reply to @reviewer-c on tests/test_auth.py
  ...

──────────────────────────────────────────────────────────────
Cluster 04 (question · jose-question, reply-only)
Thread #47 — in reply to @reviewer-a (PR-level)

  reviewer said:
  > why not use jose?

  drafted reply:
  > jose pulls in node-forge which we excluded last quarter for
  > the bundle-size audit. Sticking with the current lib.

================================================================
Total: K replies across J threads.

Options:
  (a) Approve batch — post all replies, then prompt to resolve threads
  (b) Edit a specific reply — tell me which one, I'll open it for editing
  (c) Skip specific replies — tell me which to omit (commits stay; just don't reply)
  (d) Abandon posting — don't post any replies (commits stay; you can re-run later)
```

**At `balanced` / `auto`, this view carries the rest of the round's external operations** — the reply batch *is* the external batch. Append to it:

```
Also about to fire, in order:
  PUSH             <branch> → origin (force-with-lease, <n> new commits)
  POST             <k> replies across <j> threads
  RESOLVE          <t> threads (code-fix clusters only; questions/discussions stay open)
  UPDATE PR BODY   commit map += <n> rows

Options:
  (a) Approve — push, post, resolve, update the commit map
  (b) Edit a specific reply
  (c) Skip specific replies (commits stay; those threads get no reply)
  (d) Drop one of the four operations (e.g. "don't resolve anything")
  (e) Abandon posting — nothing goes out; commits stay local
```

**Wait for the user's decision at every autonomy level. Claude Code's auto-accept mode does not answer this, and neither does `--auto`.** Fire the approved ops in listed order; if one fails, stop there (that is 5.3's `partial_post` path) rather than continuing.

- **Approve** → proceed to 5.2.
- **Edit** → re-open the specified `reply.md`, let user edit, re-assemble, re-show.
- **Skip specific** → mark those clusters `reply_skipped: true` in `meta.md`, re-show without them.
- **Abandon posting** → record `posting_abandoned: true` in the round report, jump to 5.7 (still write the round report and update state; skip 5.5–5.6 — nothing was pushed or posted, so there's no commit map to update or remote state to verify).

### 5.2 — Push (CONFIRM)

Before posting any reply, the commits must be on origin so the reviewers see them. At `balanced` / `auto` this was approved as part of the 5.1 batch — push without re-asking. At `guided`:

- Ask: *"About to push `<branch>` to origin (force-with-lease). Proceed?"*
- On confirm: `git push --force-with-lease origin <branch>`.
- On decline: stop the round. Replies remain unposted; commits stay local. User can re-run `/dev-feedback` after pushing manually.

Report: *"Pushed `<branch>` (<count> new commits since round <NN-1> or PR open)."*

### 5.3 — Post replies

For each thread in the approved batch:

- **Review-thread comments** (line-anchored): use `gh api -X POST repos/{owner}/{repo}/pulls/{pr#}/comments -f body=... -F in_reply_to=<id>` to thread the reply correctly.
- **Issue-level comments** (PR-level): use `gh api -X POST repos/{owner}/{repo}/issues/{pr#}/comments -f body=...`. There's no in-reply-to for these; the reply is a new top-level comment that quotes the author.
- **Review summary** (the body of a Request changes / Comment review): treat as an issue-level reply.

If any post fails, surface the error, stop, and record `partial_post: true` in the round report — track which replies went through. User can re-run with manual cleanup.

After successful posting, print a terse confirmation per reply: *"posted reply to thread #34"*.

### 5.4 — Resolve threads (CONFIRM per cluster, with batch shortcut)

For each cluster where action is `code-fix` and the commit landed, the included review threads can be marked resolved on GitHub. Resolution uses the GraphQL mutation `resolveReviewThread`.

**At `balanced` / `auto`:** resolution was covered by the 5.1 batch — resolve every candidate thread (code-fix clusters with a landed commit) unless the user dropped that operation, and report the count. Question / discussion clusters are never auto-resolved at any level.

**At `guided`,** ask the user:

```
K threads are candidates for resolution (across N clusters with applied fixes).
Question / discussion clusters are NOT auto-resolved — those stay open.

Options:
  (a) Resolve all — mark every candidate thread as resolved
  (b) Resolve per cluster — confirm cluster-by-cluster
  (c) Skip resolution — leave threads open, user resolves manually
```

- **Resolve all** → run `gh api graphql -f query='...resolveReviewThread...' -f thread_id=...` for each candidate. Report counts.
- **Per cluster** → walk each cluster, ask, resolve those approved.
- **Skip** → record `resolution_skipped: true`, move on.

For `question` / `discussion` clusters (action `reply-only` or `discussion-deferred`): never auto-resolve. The user decides when those conversations are done.

### 5.5 — Update the PR body's commit map (CONFIRM)

The PR body carries a `## Commit map` table (written at execute wrap-up) mapping each commit to its subtask / Jira subtask. This round added commits, so the map is now stale. Append one row per new commit:

```
| <short-sha> | review round <NN> — <cluster slug> | — | <commit subject> |
```

**At `guided`: display the rows to append and ask — "Update the PR body's commit map with this round's <n> commits? Proceed?"** At `balanced` / `auto` this was in the 5.1 batch; apply it without re-asking. On confirm: `gh pr edit <pr_url> --body "<updated body>"`. On decline: skip (note it in the round report). If the PR body has no commit map (pre-0.6 PRs), offer to add the full table instead.

Separately: if any cluster commit changed material the original PR body *prose* summarized (rare), offer to regenerate those sections in the same edit. Default: skip unless the user opts in.

### 5.6 — Verify remote state (before writing the report)

The report must record what is actually true on GitHub, not what this session believes it did. Verify:

1. **Replies landed** — re-fetch the PR comments and confirm every reply posted in 5.3 actually exists remotely (match by our author + body prefix). List any missing.
2. **Branch in sync** — `git rev-parse HEAD` equals `git rev-parse origin/<branch>` after `git fetch origin`. If not, the reviewers can't see the fixes the replies reference.
3. **Threads resolved as claimed** — for threads resolved in 5.4, spot-check `isResolved` via the GraphQL query used at pull time.
4. **PR state** — `gh pr view <pr_url> --json state,isDraft,reviewDecision,baseRefName`: still open, not draft, base unchanged, and the current review decision (`APPROVED` / `CHANGES_REQUESTED` / none).

Surface a compact checklist to the user (✓/✗ per item). Any ✗ is not auto-fixed — surface it and let the user decide; record it in the report either way.

### 5.7 — Write round report

Write `feedback/round-NN/report.md`:

```markdown
---
issue: <issue-id>
round: <NN>
status: complete | abandoned | partial
autonomy: <guided | balanced | auto>
pr_url: <url>
pulled_at: <timestamp from sub-phase 1>
posted_at: <timestamp of successful reply posting, or null>
total_comments: <n>
total_clusters: <n>
clusters_applied: <n>
clusters_skipped: <n>
clusters_reply_only: <n>
clusters_deferred: <n>
threads_resolved: <n>
commits_added: [<sha1>, <sha2>, ...]
added_lines: <n>
deleted_lines: <n>
clusters_deferred_as_too_big: <n>
remote_state:
  replies_confirmed: <n>/<n>
  branch_in_sync: <true | false>
  threads_resolved_confirmed: <true | false | skipped>
  pr_state: <open | draft | merged | closed>
  review_decision: <APPROVED | CHANGES_REQUESTED | none>
  commit_map_updated: <true | false>
---

# Feedback round <NN> — <issue-id>

## Summary
1–2 sentences: what came in, what was addressed, what was deferred.

## Remote state (verified at 5.6)
What GitHub actually shows after this round: replies confirmed present, branch sync, thread resolution, PR state + review decision. Call out any ✗ explicitly.

## Clusters
| # | Slug | Severity | Action | Outcome |
|---|------|----------|--------|---------|
| 01 | oauth-redirect-bug | blocking-correctness | code-fix | committed abc123, replied, resolved |
| 02 | redirect-tests | blocking-design | code-fix | committed def456, replied, resolved |
| 03 | style-nits-auth | nit | code-fix | committed 789abc, replied (3), resolved |
| 04 | jose-question | question | reply-only | replied, NOT resolved (open discussion) |

## Deferred for discussion
- Cluster X — reason

## Decided without review

(`balanced` / `auto` only — omit the section at `guided`.) Classifications the user never vetted (severity, type, cluster grouping), clusters skipped and why, reply wordings sent as drafted, and — at `auto` — the fact that no impl plan in this round was reviewed before it was applied.

## Notes for /dev-evaluate
What was hard, what reviewers cared about, what we got wrong the first time.
```

### 5.8 — Update plan.md state

In `plan.md` frontmatter, record:

- `last_feedback_round: <NN>`
- `last_feedback_pulled_at: <pulled_at>`
- `last_feedback_posted_at: <posted_at>`

### 5.9 — Final report

```
Feedback round NN complete for <issue-id>.
  - K comments pulled, M clusters
  - C clusters applied (X commits), R replies posted, T threads resolved
  - Remote state: <one line — all verified, or what's off>
  - Deferred: D clusters (see report.md)
  - PR: <url> (review decision: <APPROVED | CHANGES_REQUESTED | none>)
  - Round folder: .dev-assistant/issues/<issue-id>/feedback/round-NN/

Next: re-run `/dev-feedback <issue-id>` when new review comments arrive.
      If the review decision is APPROVED and nothing is deferred: `/dev-merge <issue-id>`.
```

Reminder to surface alongside the final report (once per round): review feedback also arrives through the Slack channel where the PR was announced — anything received there can be pasted into the next `/dev-feedback` round and will be triaged with the GitHub comments.

---

## Re-running and state behavior

`/dev-feedback` is designed to be re-invokable safely. Each round is a fresh folder; state lives in `plan.md` (`last_feedback_round`, `last_feedback_pulled_at`) and per-round files.

- **Re-running while a round folder is incomplete** (status `pending-user-review` or `approved` but no `report.md` yet): treat it as a resume. Read the latest `feedback/round-NN/` folder; pick up at the earliest sub-phase whose artifact is missing.
- **Re-running after a complete round**: starts a new round with `since = <prior round's pulled_at>`.
- **No new comments**: stop at sub-phase 1 with the "nothing to do" message; do not create a round folder.
- **Mid-apply interruption** (some clusters committed, some not): on re-entry, detect which clusters in the current round have `commit_sha` set and resume from the first cluster without one.
- **Mid-posting interruption** (some replies posted, some not): the round report's `partial_post: true` flag plus the per-cluster `posted: true/false` in `meta.md` tell which threads still need replies. On re-entry, offer to finish posting the remaining ones (still with batch review of the unposted subset).

## If something fails in a destructive-feeling way

Always prefer pausing and asking over rolling back or resetting state automatically.

- Commit fails due to hook → surface and stop; user fixes and re-runs
- Push fails due to remote rejection → surface and stop; don't force or rebase silently
- Reply posting fails partway → surface and stop; record `partial_post`; user can re-invoke to finish the unposted batch
- Thread resolution mutation fails → surface and continue with the next thread; threads are independent
- `gh` auth expired mid-run → surface and stop; user re-auths and re-invokes
