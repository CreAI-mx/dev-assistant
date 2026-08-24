# dev-assistant — User guide

This guide teaches you to use dev-assistant day-to-day: setting it up in a repo, walking one issue through the full lifecycle, and understanding the concepts the phases rely on. For architecture and rationale, see [DESIGN.md](../DESIGN.md); for a one-screen overview, the [README](../README.md).

**Contents**

1. [What it is, in one minute](#1-what-it-is-in-one-minute)
2. [Prerequisites](#2-prerequisites)
3. [Setup in a target repo](#3-setup-in-a-target-repo)
4. [Try it first with experimental mode (no remote changes)](#4-try-it-first-with-experimental-mode-no-remote-changes)
5. [The lifecycle, end to end](#5-the-lifecycle-end-to-end)
6. [Key concepts](#6-key-concepts)
7. [The workspace on disk](#7-the-workspace-on-disk)
8. [CLI reference](#8-cli-reference)
9. [Reviewing someone else's PR](#9-reviewing-someone-elses-pr)
10. [The terminal dashboard](#10-the-terminal-dashboard)
11. [Troubleshooting / FAQ](#11-troubleshooting--faq)

---

## 1. What it is, in one minute

dev-assistant standardizes how a development ticket moves from "vague Jira ticket" to "merged PR with a written retrospective". The work is split into phases, each driven by one Claude Code slash command:

```
refine (opt) → gather → plan → execute → feedback → merge → evaluate
```

Each phase is a guided conversation: the assistant does the mechanical work, you make the decisions at explicit pause points, and every phase writes its artifacts to a local `.dev-assistant/` workspace so the whole history of an issue is traceable. Two hard rules run through everything:

- **Nothing touches the outside world without your explicit confirmation.** Pushes, PRs, Jira/GitHub comments, transitions — every external operation is shown to you and confirmed first, even in auto-accept modes. Local file edits and commits don't need confirmation (they're reversible).
- **External text goes out in reviewed batches.** Review replies, closure comments, Jira transitions — you always see the complete set before anything is posted, never a drip of individual sends.

## 2. Prerequisites

| Requirement | Needed for | Notes |
|---|---|---|
| Python ≥ 3.10 + dev-assistant installed | everything | see [README → Install](../README.md#install) |
| [Claude Code](https://claude.com/claude-code) | the phase commands | the slash commands are the primary interface |
| `gh` CLI, authenticated | execute / feedback / merge / evaluate | `gh auth login` once per machine |
| Atlassian MCP in your Claude Code session | Jira reads/writes | optional — every Jira step degrades gracefully to "skipped, do it manually" |
| A git repo with a `develop` branch (or a customized branching strategy) | execute onward | see [Strategies](#strategies-defaults-you-can-override-per-repo) |

## 3. Setup in a target repo

Run these once inside the repo where you'll do the work (not the dev-assistant repo):

```bash
# 1. Scaffold .dev-assistant/ and point it at your repo's own rules docs (optional)
dev-assistant init --with-context CONTRIBUTING.md

# 2. Symlink the /dev-* slash commands into this repo, then restart Claude Code
dev-assistant commands install
```

`init` also adds `.dev-assistant/` to `.git/info/exclude`, so the workspace never shows up in `git status` and is never committed — it's your private working memory, not part of the repo.

Then, for each ticket you work on:

```bash
dev-assistant issue create --id PROJ-123 --title "Refactor payments"
```

The issue ID should match your Jira ticket key — it's used in branch names, commit footers, and issue titles.

## 4. Try it first with experimental mode (no remote changes)

Before running the workflow on a real ticket, do a dry run where **nothing leaves your machine**. Create the issue with the `--experimental` flag:

```bash
dev-assistant issue create --id TEST-1 --title "Try out dev-assistant" --experimental
```

Experimental mode is recorded in the issue's frontmatter and every phase respects it:

- **No GitHub issue, no Jira subtasks, no comments, no transitions** — all external prep is skipped silently.
- **No push, no PR** — `/dev-execute` branches from your current HEAD instead of `origin/develop`, skips the draft PR entirely, and wrap-up skips rebase/push/PR-ready. Commits are made locally on a normal feature branch you can delete afterwards.
- **`/dev-feedback` and `/dev-merge` refuse to run** — there is no PR to review or merge, and they say so.
- **`/dev-evaluate` still works** — the retro and lessons are produced locally; only the external close-out (GH comment, Jira transitions, issue close) is skipped.

So the full safe tour is:

```
/dev-refine TEST-1      # optional — conversation only, Jira write is skipped
/dev-gather TEST-1      # local artifacts only
/dev-plan TEST-1        # local artifacts only
/dev-execute TEST-1     # local branch + local commits, repeat once per subtask
/dev-evaluate TEST-1    # local retro + lessons
```

Afterwards, clean up with `git checkout - && git branch -D <the-test-branch>`, and either archive the workspace (`dev-assistant issue archive --id TEST-1`) or leave it as a reference.

You can also flip the flag on an existing issue: `dev-assistant issue set-flag --id TEST-1 --experimental` (or `--no-experimental`). Note that going *from* experimental *to* normal mid-issue is not a supported path — the branch and PR state won't line up; start a fresh issue instead.

## 5. The lifecycle, end to end

What follows is one issue walked through every phase, with what the assistant does, what it asks you, and what lands on disk. Every phase is **re-invokable**: if a session dies or you decline a step, running the command again picks up from recorded state rather than starting over.

### Phase 0 — `/dev-refine PROJ-123` *(optional)*

For tickets that arrive too thin to work from ("Improve the export flow" and nothing else).

- Fetches the ticket from Jira (or asks you to paste it), scaffolding the workspace if this is the first phase to touch it.
- Runs an intense exploration conversation: what's the *real* ask, is it feasible (grounded in actual repo reads), 2–4 genuinely different directions with trade-offs, scope edges. "Split this ticket" and "don't do it" are valid outcomes.
- Proposes a rewritten title + description side-by-side with the originals, iterates until you approve.
- **The only external write:** updating the Jira ticket — gated on your approval.
- Artifact: `refinement/report.md` — the only record of that conversation.

Skip this phase when the ticket is already well-specified.

### Phase 1 — `/dev-gather PROJ-123`

Collects everything needed to work the issue and distills it into objectives.

- Inventories sources with you: the refinement report (if any), the Jira ticket, the repository, meeting notes, direct input. You confirm which to use.
- Collects from each source, asks you targeted questions where information is missing.
- Synthesizes **objectives**: one general objective plus 3–7 specific, testable ones, with constraints and open questions.
- Artifacts: `gathering/report.md` (full context — the *thinking*) and `gathering/objectives.md` (the distilled contract — the *decision*). Every later phase traces back to these objectives.

### Phase 2 — `/dev-plan PROJ-123`

Decomposes the objectives into an executable plan. Read-only on the world — no branch, no issue, nothing external.

- Proposes 2–5 **subtasks** (each producing 1–3 commits; 4–8 commits total is the target), you iterate on the shape.
- Elaborates each subtask with you: objectives, affected files, mechanically-verifiable passing criteria, commit message previews.
- Settles sequencing and branch info: dependency graph, branch slug, **flow** (`feature`, or `hotfix` for emergency fixes — see [Flows](#flows-feature-vs-hotfix)), **branching mode** (`single-branch` vs `sub-branches` — see [Branching modes](#branching-modes-one-pr-or-several)), and the **target branch** resolved from the branching strategy.
- Runs viability checks (coverage of every objective, commit budget, honest commit counts) before writing.
- Artifacts: `plan/plan.md` (the canonical decision file `/dev-execute` runs from) and `plan/report.md` (the reasoning).

### Phase 3 — `/dev-execute PROJ-123` *(once per subtask, then wrap-up)*

The coding phase. Each invocation executes **one subtask**; when all are done, the next invocation enters wrap-up.

Per subtask:

1. **External prep** (optional, each item confirmed): create the GitHub issue (first subtask only; assigned to you via `--assignee @me`) and the subtask's Jira subtask (assigned to the authenticated Jira user). Decline freely — everything is offered again at wrap-up.
2. **Branch prep** (automatic, local): first subtask creates `feat/PROJ-123-<slug>` off `origin/<target branch>` with an empty `chore: open draft pr` commit; later subtasks verify you're on the right branch.
3. **Draft PR opens at start** (first subtask, each step confirmed): push + `gh pr create --draft`. Per the branching strategy, the draft PR is the start-of-work signal, not the finish line.
4. **Implementation plan**: the assistant drafts `impl-plan.md` (approach, files, gotchas, commits), checks it mechanically, and shows you a summary. **You approve, refine, or abandon.**
5. **Code + commits**: a subagent writes the changes commit-by-commit; the orchestrator reviews each diff and commits with the planned Conventional Commit message. You see one line per commit.
6. **Verification**: every passing criterion from the plan is checked mechanically and reported ✓/✗; failures get one auto-fix attempt, then escalate to you.
7. In `sub-branches` mode: the subtask's sub-PR opens now (confirmed), targeting the parent feature branch.

Wrap-up (after the last subtask):

- Pre-flight (all subtasks done, tree clean, sub-PRs merged), catch-up on any deferred external prep, rebase onto the target branch, push (confirmed).
- Refreshes the PR body with the finished work — including the **commit map**, a table linking every commit to its subtask and Jira subtask so reviewers can review commit-by-commit — and marks the PR **Ready for review** (confirmed).
- Hotfix flow only: opens the second PR → `develop` (the sync PR).
- Generates a team announcement message (local; you paste it into your team channel yourself, e.g. Slack).
- Artifacts: per-subtask `execution/<NN-slug>/impl-plan.md` + `execution-notes.md`, plus `execution/wrap-up-report.md` and `team-message.txt`.

### Phase 4 — `/dev-feedback PROJ-123` *(one review round per invocation)*

Runs one round of the PR review loop. Re-invoke it each time new review comments arrive.

1. **Pull**: fetches all new comments since the last round (inline threads, PR-level comments, review summaries), filtering out your own and resolved threads.
2. **Triage**: classifies each by severity (`blocking-correctness` → `praise`) and type, clusters related comments. **You review the triage** — approve, reclassify, or defer clusters you'd rather argue about yourself.
3. **Plan + apply**: each `code-fix` cluster gets an impl-plan (you approve per cluster; consecutive nits can be batch-approved), a subagent writes the fix, one commit per cluster.
4. **Batch review of ALL replies**: every drafted reply — fixes ("Fixed in abc123."), answers, pushback — is shown as **one consolidated set**. Nothing posts until you approve the batch; you can edit or skip individual replies.
5. **Push, post, resolve**: push (confirmed), post the approved replies, offer thread resolution, update the PR's commit map with the round's commits.
6. **Verify remote state**: before writing the round report, the assistant re-checks GitHub — did the replies actually land, is the branch in sync, what's the review decision — and records it in the report.
7. Artifacts: `feedback/round-NN/` (pulled comments, triage, clusters, report).

Review feedback that arrives through Slack (from your PR announcement) isn't pulled automatically — paste it into the next round and it's triaged alongside the GitHub comments.

### Phase 5 — `/dev-merge PROJ-123` *(when the PR is approved)*

The explicit close of the review loop.

1. **Merge readiness**: one checklist verified against live GitHub state — approvals, CI, unresolved threads, deferred discussion clusters, branch sync, base branch matches the plan. Any ✗ blocks by default; you can override per item, and overrides are recorded.
2. **Merge-commit message**: built for you with the trackable subject `[PROJ-123] <summary> (#<PR number>)` — the `(#N)` makes GitHub autolink the commit to its PR. You approve or edit it.
3. **Merge**: always a **merge commit**, never squash — every commit SHA referenced in Jira comments, review replies, and phase artifacts stays valid. Then branch deletion (remote + local) and a state update.
4. Hotfix flow: walks both PRs — `uat` first, then the `develop` sync — and only deletes the branch after both merge.
5. Artifact: `merge/report.md` (what merged, the readiness checklist as it stood, notes for the retro).

### Phase 6 — `/dev-evaluate PROJ-123`

The retrospective — closes the loop and captures what was learned.

1. **Load + verify**: reads every artifact from every phase and verifies them against remote reality (PR/merge commit, replies actually posted, GH issue state, branch cleanup, Jira statuses). Local-vs-remote discrepancies become retro findings.
2. **Retro + lessons**: drafts `evaluation/retro.md` (timeline, outcomes against the original objectives, drift from plan, surprises) and `evaluation/lessons.md` (categorized lessons: process / technical / collaboration). **You review both before anything fires.**
3. **External close-out** (one confirmed batch): GH issue closure comment, Jira subtask + parent transitions, GH issue close — all gated on the PR actually being merged.
4. **Lessons archive**: each lesson lands in `.dev-assistant/lessons/<category>/`; a lesson that repeats an existing one updates that lesson's recurrence count instead of duplicating it, and `INDEX.md` is regenerated. Recurring lessons are your strongest signals.
5. Offers to archive the workspace (a reversible directory move — nothing is ever deleted).

## 6. Key concepts

### Strategies: defaults you can override per repo

The assistant's conventions — branching, PR template, comment style, Jira/GH issue templates, output style, code economy — live as **strategy** documents. Each resolves per-repo-override-first:

```bash
dev-assistant strategies show branching-strategy         # what's in effect here
dev-assistant strategies customize branching-strategy    # copy the default into .dev-assistant/strategies/ and edit
```

The default branching strategy is trunk-friendly: `develop` integration branch, `uat` mirror, `feat/<TICKET>-<slug>` branches, draft PR at start, Conventional Commits, rebase before review, merge commits at integration. If your repo works differently, customize the override — the phases read whatever is in effect.

### Repo context: your repo's own rules

`init --with-context` points the workspace at documents your repo already owns (CONTRIBUTING, style guides, PR checklists). Every phase re-reads them at invocation, and **repo-context rules beat strategy defaults** on conflict. The source of truth stays in your repo.

### Flows: feature vs hotfix

Decided at plan time (`flow` in `plan.md`):

- **`feature`** (default) — branch off `develop`, PR into `develop`.
- **`hotfix`** — for emergencies that must reach UAT before the next normal deploy: branch `hotfix/<TICKET>-<slug>` off `uat`, PR into `uat`, forced single-branch with 1–2 subtasks, **plus a second sync PR into `develop`** (opened at wrap-up, merged by `/dev-merge` after the UAT PR) so the fix isn't lost on the next promotion.

### Branching modes: one PR or several

Also decided at plan time (`branching_mode`):

- **`single-branch`** (default) — all subtasks land as commits on one branch, one PR.
- **`sub-branches`** — each subtask gets its own `-sub-N` branch and sub-PR targeting the parent feature branch, merged sequentially; the parent PR to `develop` collects them. Recommended when the commit estimate pushes past 8–10 or subtasks are independently reviewable.

### Code economy: how much code the phases write

Every subtask carries a size band, and the pipeline measures rather than guesses:

| Band | Added lines |
|---|---|
| `S` | ≤ 50 |
| `M` | 51–150 |
| `L` | 151–400 (needs a written reason in the plan) |
| `XL` | > 400 — not a size, a signal to split the subtask |

Deletions are never charged: a `+40 / -90` change is a small change. Lockfiles, generated output, and vendored trees don't count.

```bash
dev-assistant issue size --id PROJ-123                 # landed diff vs the target branch
dev-assistant issue size --id PROJ-123 --worktree --band S   # uncommitted work vs one subtask's budget
```

What each phase does with it:

- **plan** sizes every subtask and writes down what it deliberately left out.
- **execute** measures each commit before it lands; over budget it trims once by itself, and only stops to ask if it's *still* over. At wrap-up it runs a **reduction pass** over the issue's whole diff — the one-caller abstraction and the duplicate tests only become visible at that scale — and removes what it can while every passing criterion stays green.
- **feedback** keeps review fixes proportionate: an `L` "fix" for a review comment is a follow-up ticket, not a bigger commit.
- **review** runs an economy dimension that produces `bloat` findings, each naming the smaller alternative.
- **evaluate** compares planned to landed; a mis-size that keeps recurring becomes a promoted lesson.

The balance is written into the strategy, not left implicit: **when the shorter version takes longer to explain, the longer one wins.** Clever compression — dense comprehensions, chained ternaries, one-letter names — is flagged exactly like bloat. Correctness, the objectives, repo conventions, boundary validation, and tests for named failure modes are all explicitly exempt.

Customize the whole standard per repo with `dev-assistant strategies customize code-economy` — including the band ceilings if your repo's work is shaped differently.

### Autonomy: how much the phases ask you

Set once, at issue creation, and changeable any time:

```
dev-assistant issue create --id PROJ-123 --title "..." --autonomy balanced
dev-assistant issue set-flag --id PROJ-123 --autonomy auto
```

| Level | What it does | A full issue costs about |
|---|---|---|
| `guided` | Every checkpoint fires: each sub-stage approval, each external operation confirmed on its own. | ~75 stops |
| `balanced` **(default)** | One approval checkpoint per phase, and each phase's external operations confirmed as one batch. | ~20 stops |
| `auto` | No approval checkpoints — decisions are made and recorded in the phase report. External operations are still confirmed as one batch per phase. | ~12 stops |

Three things never change with the level:

- **Questions only you can answer.** Refine's exploration conversation and gather's direct-input questions run at every level — `auto` asks them as one block instead of one at a time, but it asks. A phase that invents your constraints produces objectives grounded in nothing.
- **External writes.** Nothing is pushed, opened, posted, transitioned, or merged without you saying yes. `auto` means fewer prompts, not unattended publishing. The merge confirmation in particular is asked once per PR at every level.
- **Escalations.** Rebase conflicts, failing passing criteria, a readiness ✗, a reply that fails to post — these stop and ask regardless.

Below `guided`, each phase's report gains a **`## Decided without review`** section listing what the assistant settled alone. That audit trail is what makes the lower levels safe: you can read back what you didn't watch.

A single phase can be walked at a different level with a trailing token — `/dev-plan PROJ-123 --guided` — without changing the issue's setting. Issues created before the field existed run as `guided`.

The full map of every stop, per phase, is in [interaction-map.md](interaction-map.md).

### The confirmation principle and batch reviews

Worth restating because it's the safety model: **local = free, external = confirmed, external text = reviewed in one batch**. If you decline an external step, the phase records where it stopped and the next invocation resumes there — declining is never destructive. The autonomy level changes how many times you are asked; it never changes whether you are asked.

## 7. The workspace on disk

Everything lives under `.dev-assistant/` in the target repo (excluded from git):

```
.dev-assistant/
├── repo-context.md              # pointers to your repo's own rules docs
├── strategies/                  # per-repo strategy overrides (only the customized ones)
├── issues/
│   └── PROJ-123/
│       ├── issue.md             # id, title, status, experimental flag, autonomy level
│       ├── refinement/report.md
│       ├── gathering/{report,objectives}.md
│       ├── plan/{plan,report}.md
│       ├── execution/
│       │   ├── 01-<slug>/{impl-plan,execution-notes}.md
│       │   ├── wrap-up-report.md
│       │   └── team-message.txt
│       ├── feedback/round-01/   # (or sub-N/round-NN/ in sub-branches mode)
│       ├── merge/report.md
│       └── evaluation/{retro,lessons,report}.md
├── reviews/pr-50/               # reviewer-side workspaces (/dev-review)
├── lessons/
│   ├── INDEX.md                 # regenerated index, promotion candidates first
│   ├── process/ …               # one file per lesson, categorized
│   ├── technical/ …
│   └── collaboration/ …
└── archive/issues/              # archived workspaces (moved, never deleted)
```

A useful habit: the `report.md` files are the *thinking* (read when you want to know why), while `objectives.md` / `plan.md` / `lessons.md` are the *decisions* (read when you want to know what).

## 8. CLI reference

The CLI is the deterministic layer under the slash commands; you'll mostly use it for setup and inspection.

| Command | What it does |
|---|---|
| `dev-assistant init [--with-context <files…>]` | Scaffold `.dev-assistant/` in the current repo |
| `dev-assistant commands install` | Symlink the `/dev-*` slash commands into `.claude/commands/` |
| `dev-assistant issue create --id <ID> --title <T> [--experimental] [--autonomy guided\|balanced\|auto]` | Create an issue workspace |
| `dev-assistant issue show --id <ID>` | Phase-by-phase progress of one issue |
| `dev-assistant issue size --id <ID> [--worktree] [--band S\|M\|L]` | Measure the diff and band it against the plan |
| `dev-assistant issue set-flag --id <ID> --experimental/--no-experimental [--autonomy <level>]` | Toggle experimental mode / change the autonomy level |
| `dev-assistant issue archive --id <ID>` | Move a finished workspace to `archive/` (reversible) |
| `dev-assistant strategies show\|customize <name>` | Inspect / override a strategy for this repo |
| `dev-assistant repo-context show` | Print the repo rules docs in effect |
| `dev-assistant review create\|show --pr <n>` | Reviewer-side workspaces (see below) |
| `dev-assistant tui` | The terminal dashboard |

All commands support `--help`.

## 9. Reviewing someone else's PR

`/dev-review <pr-number-or-url>` is the mirror image of `/dev-feedback`: it gathers the PR + linked issue + Jira context, writes you a plain-words brief, runs background reviewers while you ask questions, then an objective-coverage pass. **You pick exactly which findings post** — unselected findings never reach GitHub — and everything submits as one review (one notification for the author). Read-only apart from that single gated submission.

## 10. The terminal dashboard

```bash
pipx install -e '/path/to/dev-assistant[tui]'   # needs the optional Textual extra
dev-assistant tui
```

A read-only browser for the workspace: issues and their phase timelines (refine → … → merge → eval), subtasks and review rounds, PR/branch status from live git, hotfix sync-PR state, the lessons archive, and a raw viewer for any artifact. It never writes anything — it's a viewer, not a controller.

## 11. Troubleshooting / FAQ

**A phase stopped with "Working tree has uncommitted changes."**
Deliberate: execute/feedback/merge/evaluate refuse to run on a dirty tree so your in-progress edits never get mixed into generated commits. Commit, stash, or discard, then re-invoke.

**"PR base is `X` but the plan targets `Y`."**
The PR's base branch on GitHub doesn't match `plan.md`'s `target_branch`. Fix whichever is wrong (`gh pr edit --base <branch>`, or correct the plan) and re-run.

**A session died mid-phase. Did I lose the work?**
No. State lives in the artifacts, not the conversation. Re-invoke the same command — every phase detects recorded state (commits made, PR opened, replies posted, clusters applied) and resumes at the first missing step.

**I declined a push/PR/comment. How do I finish later?**
Re-invoke the phase. Declined external ops are recorded as not-done and offered again (execute offers deferred prep again at wrap-up).

**`/dev-merge` says threads are unresolved / clusters deferred.**
That's the readiness gate doing its job — run another `/dev-feedback` round to close them out, or explicitly override per item ("merge anyway"); overrides are recorded in the merge report.

**Jira steps are being skipped.**
The Atlassian MCP isn't available in the session. Everything else proceeds; do the Jira ops manually or reconnect and re-invoke.

**Rebase conflicts at wrap-up.**
The assistant hard-stops and lists the conflicting files. Resolve manually (`git rebase --continue`), then re-invoke `/dev-execute <id> wrap-up`.

**Can I go back a phase?**
Yes — re-run the earlier command. Gather and plan handle re-runs by showing current artifacts and editing the sections you want changed rather than starting over.

**How do I delete a workspace?**
You archive it (`dev-assistant issue archive`). There is deliberately no delete command; if you truly want one gone, `rm -rf .dev-assistant/archive/issues/<id>/` by hand.
