---
description: Close out the review phase for one issue — verifies merge readiness (approvals, CI, threads, branch sync), builds the merge-commit message with the (#PR) suffix, merges with a merge commit, deletes the branch, and in the hotfix flow walks both PRs (uat, then develop)
argument-hint: <issue-id>
model: opus
allowed-tools: Bash(dev-assistant:*), Bash(git:*), Bash(gh:*), Read, Write, Edit, Grep, Glob
---

You are running the **merge** phase for issue `$ARGUMENTS`.

This phase is the explicit close of the feedback loop: reviews are done, the PR is approved, and the work integrates into the target branch. One invocation per PR merge (so the hotfix flow walks it twice — uat PR, then develop sync PR — in one invocation).

## Argument parsing

`$ARGUMENTS` is the issue ID. Take the first whitespace-separated token. The only other accepted token is a trailing `--guided` / `--balanced` / `--auto`, which overrides the issue's autonomy level for this invocation. Sub-PRs (`sub-branches` mode) are **not** merged here — the user merges those on GitHub between subtasks per `/dev-execute` 3.8; this phase merges the parent PR only.

## Current state of the issue

!`dev-assistant issue show --id $1`

Then read these files directly for state:

- `.dev-assistant/issues/<issue-id>/issue.md`
- `.dev-assistant/issues/<issue-id>/plan/plan.md`
- `.dev-assistant/issues/<issue-id>/execution/wrap-up-report.md`
- `.dev-assistant/issues/<issue-id>/feedback/round-*/report.md` (all rounds, if any)

## Strategies that shape this phase

### Branching strategy (drives the merge method and merge-commit format)

!`dev-assistant strategies show branching-strategy`

### Comment style (drives the Jira close-of-review comment)

!`dev-assistant strategies show comment-style`

### Repo context — repo-specific rules to respect

!`dev-assistant repo-context show`

If a repo-context rule conflicts with a strategy (e.g. the repo mandates squash merges), the repo-context rule wins — but surface the traceability cost to the user before proceeding.

---

## Confirmation principle (non-negotiable)

**Nothing touches the outside world without explicit user confirmation.** This holds at every autonomy level and under Claude Code's auto-accept-edits mode. For this phase that includes:

- Merging a PR (`gh pr merge`) — the least reversible operation in the whole lifecycle
- Deleting the remote branch
- Posting Jira comments

Local operations (report writing, local branch cleanup on your own clone) do not require confirmation.

## Autonomy level — how many checkpoints this phase fires

The `## Autonomy` block in the `dev-assistant issue show` output above resolves this issue's level (`guided` | `balanced` | `auto`). Issues created before the field existed resolve to `guided`.

| Kind of stop | `guided` | `balanced` | `auto` |
|---|---|---|---|
| **External** — merge, branch deletion, Jira comment | one confirmation each | **one confirmation per PR merged**, covering the merge commit, the branch deletion, and the Jira comment | same |
| **Escalation** — any ✗ on the readiness checklist, a rejected merge, a missing hotfix sync PR | stops | stops | stops |

**This phase has no approval-only stops, so `auto` and `balanced` behave identically here.** The merge confirmation is the hardest floor in the whole system: it is the least reversible operation dev-assistant performs, and no autonomy level fires it unattended. A hotfix merges two PRs and therefore asks twice — one confirmation per irreversible act.

The readiness checklist in sub-phase 1 is also never waived. `auto` does not mean "merge anyway"; an override is something the user says, per item, and it is recorded in the report.

## Pre-flight (stop early on failure)

1. **Issue workspace + plan exist** — else stop, pointing at `/dev-gather` / `/dev-plan`.
2. **Not experimental** — `experimental: true` in `issue.md` → stop with *"Experimental mode — no PR exists to merge."*.
3. **`pr_url` is set** in `plan.md` — else stop with *"No PR recorded. Run `/dev-execute <issue-id>` through wrap-up first."*.
4. **`gh` CLI authenticated.**
5. **Working tree clean** — a dirty tree may signal unfinished feedback work.
6. **Not already merged** — `gh pr view <pr_url> --json state,merged`. If merged, report the merge commit and skip to sub-phase 4 (state update + report) so re-runs are idempotent.

Read `flow` and `target_branch` from `plan.md` frontmatter (defaults: `feature`, `develop`). In the hotfix flow, also read `develop_pr_url` — if it is missing or null, offer to open the sync PR now (same shape as `/dev-execute` 4.5b) before anything merges; per the branching strategy a hotfix without its develop PR loses the fix on the next promotion.

---

## Sub-phase 1 — Merge readiness (verify remote reality, then show one checklist)

Gather, for the PR being merged:

- `gh pr view <pr_url> --json state,isDraft,reviewDecision,baseRefName,headRefName,mergeable,statusCheckRollup,reviews`
- Unresolved review threads (GraphQL `reviewThreads` with `isResolved: false`)
- Branch sync: after `git fetch origin`, local `branch_name` tip vs `origin/<branch_name>` — and whether the branch is behind `origin/<target_branch>` (merge conflicts ahead?)
- Feedback state: latest `feedback/round-NN/report.md` — any clusters `discussion-deferred`, any `partial_post`, any replies unposted
- Base check: `baseRefName` equals `plan.md`'s `target_branch`

Display one checklist:

```
Merge readiness — <pr_url> (→ <target_branch>)
  [✓] PR open, not draft
  [✓] Review decision: APPROVED (2 approvals)
  [✓] CI green (n/n checks)
  [✓] Base branch matches plan (<target_branch>)
  [✓] Mergeable (no conflicts)
  [✓] Branch in sync with origin
  [✗] 2 unresolved review threads   → <links>
  [✗] Round 03 has 1 deferred discussion cluster → <slug>
```

**Any ✗ → stop by default.** Show what's blocking and how to clear it (`/dev-feedback` for open threads/deferred clusters; push for sync; fix base). The user may explicitly override per item (*"merge anyway"*) — record any overrides in the report. **Pause and wait at every autonomy level; Claude Code's auto-accept mode does not answer this either.**

## Sub-phase 2 — Build the merge-commit message

Per the branching strategy, the merge is a **merge commit** (never squash / rebase-merge — commit SHAs are referenced across Jira comments, review replies, and phase artifacts; squashing orphans them all; this is the traceability default). Subject format:

```
[<TICKET>] <imperative summary, no trailing period> (#<PR number>)
```

The `(#N)` suffix makes GitHub autolink the commit to its PR. Derive the summary from the PR title (sharpen it if it drifted from what actually landed). Body:

```
- <outcome bullet 1>
- <outcome bullet 2>

refs <TICKET>
PR: <pr_url>
```

Display subject + body.

**At `guided`, ask:** *"Merge `<pr_url>` into `<target_branch>` with this merge commit? Proceed?"* — then confirm the branch deletion and the Jira comment separately in sub-phases 3 and 4.

**At `balanced` / `auto`, ask once for the whole close-out:**

```
MERGE <pr_url> → <target_branch>

  Merge commit:  [<TICKET>] <subject> (#<n>)
                 <body>
  Then:          delete origin/<branch_name>        (hotfix: deferred until PR 2 merges)
                 comment on Jira <TICKET>: "Merged into <target>: <sha>"

Approve / edit the merge message / merge but keep the branch / merge without the Jira comment / abandon
```

Iterate on the message if the user edits it. Approval covers the merge, the branch deletion, and the Jira comment — nothing else. If the merge itself is rejected by GitHub, stop there: the rest of the list does not fire.

## Sub-phase 3 — Merge and clean up (CONFIRM each external op)

1. **Merge:** `gh pr merge <pr_url> --merge --subject "<subject>" --body "<body>"`. If GitHub rejects (branch protection, new push since check), surface verbatim and stop — never retry with a different merge method silently.
2. **Verify the merge landed:** `gh pr view <pr_url> --json merged,mergeCommit` — record the merge commit SHA. Don't trust the exit code alone.
3. **Delete the remote branch (CONFIRM at `guided`; covered by the sub-phase 2 approval at `balanced` / `auto`):** *"Delete `origin/<branch_name>`? (Strategy: branches are deleted after merge.)"* — `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch_name>` (or `--delete-branch` on the merge call if the user pre-approves both together). **Hotfix flow: do NOT delete until the second PR is also merged** — it shares the branch.
4. **Local cleanup (no confirm):** `git checkout <target_branch>`, `git pull origin <target_branch>`, `git branch -d <branch_name>`. If `-d` refuses (unmerged locally — normal after a remote merge commit), verify the PR merge SHA is in the pulled target branch, then `git branch -D` is acceptable; say so.

**Hotfix flow — second PR:** repeat sub-phases 1–3 for `develop_pr_url` (→ `develop`). Subject gets the sync marker: `[<TICKET>] <summary> (sync to develop) (#<N>)`. Only after both are merged: delete the branch.

## Sub-phase 4 — Record and hand off

1. **Update `plan.md` frontmatter:** `pr_state: merged`, `merge_commit: <sha>`, `merged_at: <ISO>` (hotfix flow: also `develop_merge_commit`, `develop_merged_at`).
2. **Jira comment (optional, Atlassian MCP only; CONFIRM at `guided`, covered by the sub-phase 2 approval at `balanced` / `auto`):** per `comment-style`, e.g. `"Merged into <target_branch>: <merge commit sha> (<pr_url>)."` — one comment on the parent ticket. Status transitions stay in `/dev-evaluate`; this phase only records the merge.
3. **Write `merge/report.md`** (`mkdir -p .dev-assistant/issues/<issue-id>/merge/`):

```markdown
---
issue: <issue-id>
phase: merge
status: complete
autonomy: <guided | balanced | auto>
pr_url: <url>
target_branch: <target_branch>
merge_commit: <sha>
merged_at: <ISO>
develop_pr_url: <url or n/a>
develop_merge_commit: <sha or n/a>
branch_deleted: <true | false>
readiness_overrides: [<any ✗ the user overrode, or empty>]
---

# Merge report — <issue-id>

## What merged
Merge-commit subject(s) verbatim, PR link(s), final review decision, feedback rounds count.

## Readiness at merge time
The sub-phase 1 checklist as it stood, including anything overridden and why.

## Notes for /dev-evaluate
Anything about the review-close worth retrospecting (stale threads, override reasons, base drift caught, etc.).
```

4. **Final report:**

```
Merge complete for <issue-id>.
  - <pr_url> → <target_branch>, merge commit <sha> ("[TICKET] ... (#N)")
  - Branch <branch_name>: deleted (remote + local)
  - Report: .dev-assistant/issues/<issue-id>/merge/report.md

Next: /dev-evaluate <issue-id>.
```

---

## Re-running and state behavior

- **Already merged** (pre-flight 6): skip to sub-phase 4 — fill in whatever state/report is missing. Never attempt a second merge.
- **Merge fired but cleanup/report didn't** (interruption): pre-flight 6 catches it; branch deletion and the report are completed on re-run.
- **Hotfix with PR 1 merged, PR 2 not**: readiness runs only for the develop PR; branch deletion unlocks after it merges.

## If something fails in a destructive-feeling way

- Merge rejected by branch protection → surface verbatim, stop. Never switch merge method to get through.
- Branch deletion fails → surface, continue (deletion is cosmetic; the merge already landed).
- Jira comment fails → skip with a message; never blocks.
