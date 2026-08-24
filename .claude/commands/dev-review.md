---
description: Review someone else's PR — gathers PR + linked issue + Jira context, writes a plain-words brief, answers your questions while small-scale reviewers run in the background, then runs the objective-coverage pass, lets you pick which findings post, and submits ONE GitHub review
argument-hint: <pr-number-or-url>
model: opus
allowed-tools: Bash(dev-assistant:*), Bash(git:*), Bash(gh:*), Read, Write, Edit, Grep, Glob, Agent
---

You are running a **PR review** round for PR `$ARGUMENTS`.

This is the **reviewer side**: the user is reviewing *someone else's* PR, not receiving feedback on their own (that's `/dev-feedback`). The job: build the user a genuine understanding of the PR, review it like a good human reviewer — large scale first (does it solve what it's supposed to solve?), small scale second (are the lines right?) — and post only the findings the user explicitly selects, as **one** GitHub review.

## Argument parsing

`$ARGUMENTS` is either a PR number (`123`) or a full PR URL (`https://github.com/<owner>/<repo>/pull/123`). Extract the number; if a URL was given, verify its owner/repo matches the current repo's `origin` remote — if not, stop with *"PR `<url>` belongs to `<owner>/<repo>`, but this repo's origin is `<origin>`. Open Claude Code in the right repo first."*

## Current state of the review

!`dev-assistant review show --pr $ARGUMENTS`

If the workspace doesn't exist yet (the command above errors), this is the first round — create it in pre-flight step 8.

## Pre-flight (stop early on failure)

1. **Workspace root exists** — if `.dev-assistant/` is missing, stop with *"No `.dev-assistant/` here. Run `dev-assistant init` first."*
2. **`gh` CLI authenticated** — `gh auth status` exits cleanly. If not, stop with *"`gh` is not authenticated. Run `gh auth login` first."*
3. **PR exists and is open** — `gh pr view <n> --json state,title,author,headRefName,headRefOid,baseRefName,body,url,closingIssuesReferences`. If `state` is `MERGED` or `CLOSED`, stop with *"PR #<n> is <state> — there is nothing to review. (Re-run against an open PR.)"*
4. **Not the user's own PR** — compare `author.login` with `gh api user --jq .login`. If they match, warn: *"This is your own PR — GitHub will not let you approve or request changes on it; only COMMENT is possible."* Continue, but remember the verdict restriction for sub-phase 5.
5. **Working tree clean** — `git status --porcelain` returns nothing. If dirty, stop with *"Working tree has uncommitted changes. Commit, stash, or discard them before reviewing — the review checks out the PR branch."*
6. **Record the return branch** — note the current branch name. The wrap-up offers to switch back to it.
7. **Reviews folder exists** — `mkdir -p .dev-assistant/reviews` (repos initialized before the reviews/ subfolder existed won't have it).
8. **Workspace exists** — if `review show` failed above, run `dev-assistant review create --pr <n> --url <url> --title "<title>"`.

## Strategies that shape this round

### Comment style (drives the tone of review comments and the attribution footer)

!`dev-assistant strategies show comment-style`

### Output style — how to write the artifacts this round produces

!`dev-assistant strategies show output-style`

### Repo context — repo-specific rules to respect

!`dev-assistant repo-context show`

The repo-context documents are review ammunition: the PR author was supposed to follow these rules. Reviewers that know the house rules catch what generic reviewers miss. If a repo-context rule conflicts with a strategy, the repo-context rule wins.

---

## Confirmation principle (non-negotiable)

**The only external write this command performs is the final review submission in sub-phase 5 — and it fires only after the user approves the assembled batch.** Everything else is local and read-only with respect to the outside world:

- Checking out the PR branch is local (pre-flight guaranteed a clean tree).
- All artifacts are files under `.dev-assistant/reviews/pr-<n>/`.
- No commits, no pushes, no Jira writes. The reviewer comments; the author fixes.

**Selection rule (critical):** no finding reaches GitHub unless the user explicitly selected it in sub-phase 4 and approved the assembled batch in sub-phase 5. Pause for both checkpoints **at every autonomy level and under Claude Code's auto-accept mode.**

## Autonomy level — not applicable here

The `autonomy` setting is a property of an *issue* workspace (`.dev-assistant/issues/<id>/issue.md`) and this command works on a *review* workspace (`.dev-assistant/reviews/pr-<n>/`) — someone else's PR, not your ticket. Nothing in this command varies by level, and there is no override token.

That is deliberate rather than an omission. This command has exactly three stops — the Q&A (2.3), the selection (4), and the batch (5.1) — and each one is the point of the command: your questions shape the deep review, your selection decides what exists on GitHub, and your approval is what puts your name on it. There is nothing here to collapse.

## How to interact with the user

- **Announce which sub-phase you're entering** before each one.
- **Be terse during work, full during decisions.** The brief summary, the findings table, and the batch view are full; everything else is one-liners.
- **Show summaries, link to files** so the user can open the full artifact separately.

---

## Round detection

Rounds live at `.dev-assistant/reviews/pr-<n>/round-NN/`. The next round is `NN = max(existing) + 1`, or `01` if none exist. Create `round-NN/` and `round-NN/comments/`.

Scope of the round, from `review.md` frontmatter's `last_reviewed_sha`:

- **Round 01** (`last_reviewed_sha: null`): review the whole PR.
- **Later rounds**: review the **delta** — `git diff <last_reviewed_sha>..<headRefOid>` — plus anything the delta invalidates from prior rounds. Read the prior rounds' `findings.md` and `report.md` first: the brief gets *updated*, not rewritten, and prior findings the author addressed get noted as resolved.

If `headRefOid` equals `last_reviewed_sha`, stop with *"No new commits since round <NN-1>. Nothing to review."*

Surface: *"Round NN — reviewing <full PR | delta since `<short sha>`> (<k> commits, <m> files)."*

---

## Sub-phase 1 — Gather (intent first, code second)

Collect everything that explains what this PR is **supposed to do**, then what it **actually does**.

### 1.1 — Intent sources

- **PR description** — title, body, author, base/head branches (already fetched in pre-flight).
- **Linked GitHub issue** — from `closingIssuesReferences`, plus any `#<n>` / `Closes/Fixes <n>` references in the body. Fetch each with `gh issue view <n> --json title,body,labels,comments`.
- **Linked Jira ticket** — extract Jira keys (`[A-Z][A-Z0-9]+-\d+`) from the PR title, body, and branch name. If a key is found and the Atlassian MCP is available, fetch the ticket (summary, description, acceptance criteria). If MCP is unavailable, ask the user once: *"Found Jira key <KEY> but no Atlassian MCP. Paste the ticket content, or skip?"* If no key is found, note "no Jira ticket linked" and move on — don't interrogate the user.

### 1.2 — Code sources

- **Commits** — `gh pr view <n> --json commits`: the per-commit story, in order. The order things were built often explains the diff better than the diff.
- **Diff** — `gh pr diff <n>` plus `--name-status` for the file map.
- **CI status** — `gh pr checks <n>`; failing checks are pre-made findings.
- **Checkout** — `gh pr checkout <n>` so reviewers can read full files, callers, and tests — not just hunks.
- **Blast radius** — for each non-trivial changed function/class, Grep for its call sites. Changed-but-not-updated callers are review gold.

### 1.3 — Write `context.md` (thinking artifact)

Frontmatter: `pr`, `round`, `head_sha`, `gathered_at`, plus `issue_refs` and `jira_refs` lists. Sections: Intent (PR description, issue content, Jira content — quoted where it matters), Code (commit list, file map, CI status, blast-radius notes), and **Objectives** — the distilled checklist of what this PR is supposed to accomplish, each item traced to its source (description / issue / Jira). 3–7 testable items, checkbox style. If the intent sources *disagree* with each other, say so here — that's a finding in the making.

Report: *"Gathered: PR + <issue refs> + <jira refs>, <k> commits, <m> files, CI <status>. Objectives distilled: <count>."*

---

## Sub-phase 2 — Brief, background reviewers, and Q&A

### 2.1 — Write `understanding.md` (decision artifact)

The plain-words brief. Frontmatter: `pr`, `round`, `status: draft`. Sections:

- **What was asked** — the objectives from 1.3, in one breath.
- **What the PR claims to do** — the author's framing.
- **What it actually changes** — your reading of the diff, in simple words, no jargon beyond what the repo forces. Per-commit narrative where it helps.
- **Gaps** — daylight between the three sections above. This is the heart of the brief.
- **Risk map** — what could break, what the PR touches that it didn't need to, callers not updated.
- **Open questions** — things the brief can't settle from the artifacts alone.

### 2.2 — Launch the small-scale reviewers (background, immediately)

The moment `understanding.md` is written — before the user starts asking questions — dispatch **three background subagents** (Agent tool, `run_in_background: true`, model `sonnet`, `subagent_type: general-purpose`). Each gets: the brief, the diff (or delta), the repo-context rules, and one dimension:

1. **Correctness** — bugs, broken contracts, edge cases, error handling, security. *Small scale: read the lines like they'll run at 3am.*
2. **Tests** — are the changed behaviors tested? Do the tests test the right thing? Missing branches?
3. **Conventions** — style, naming, docs, repo-context rule violations.

Each subagent returns findings as a list: `{file, line, category, severity, what, why, suggestion}`. Instruct them: findings must cite real file:line positions from the diff; no speculation about code they haven't read; an empty list is a valid answer.

These dimensions barely depend on the discussion — that's why they can start now. The **objective-coverage pass does not start yet**: it's exactly the dimension the user's questions inform, so it waits for the discussion to settle (sub-phase 3).

### 2.3 — Q&A (the user reads, you answer — this is a working conversation, not idle time)

Show the brief's summary in chat (What was asked / What it changes / Gaps / Risks — compressed), link to `understanding.md`, and say:

```
Brief ready at round-NN/understanding.md. Small-scale reviewers are running in the background.

Ask me anything about the PR. Three things you can do here:
  - ask questions — I'll answer from the gathered context, reading more code if needed
  - "add as finding: ..." — anything you spot becomes a finding, attributed to you
  - "correction: ..." — if the brief got something wrong (stale ticket, different objective), I'll fix the brief and the correction feeds the objective pass

Say "done" when you're ready for the deep review.
```

**Stop and wait. Claude Code's auto-accept mode does not answer this.** During the discussion:

- Answer from `context.md` / the checked-out code; read more when needed.
- **User findings**: append to a `discussion-findings` list (kept in memory, written to `findings.md` in sub-phase 3) with `source: user`.
- **Corrections**: update `understanding.md` in place and append a `## Corrections from discussion` section recording what changed and why. If a correction invalidates a *small-scale* dimension's premise (rare), note it — that dimension's findings get re-checked against the correction in sub-phase 3 rather than re-run.
- When the user says done, set `status: discussed` in `understanding.md` frontmatter and proceed.

---

## Sub-phase 3 — Deep review (large scale, then merge)

### 3.1 — Objective-coverage pass (the one that waited)

Now run the large-scale pass yourself (orchestrator, no subagent — this is judgment work). Inputs: the corrected `understanding.md` including discussion corrections, `context.md`'s objectives, the diff, blast radius. Questions a good senior reviewer asks:

- Is **every objective** actually met by the code — not the description, the code? Walk each checkbox.
- Is anything in the objectives **missing entirely**? (A beautifully written 70% PR is worse than an off-by-one.)
- Does the **approach fit this repo** — right abstraction, right layer, consistent with how siblings do it?
- **Scope**: does the PR change things the objectives didn't ask for? Why?
- **Side effects**: what does this break for the untouched callers in the blast radius?

### 3.2 — Collect the background reviewers

Retrieve the three background subagents' results (they've had the entire Q&A to work). If one is still running, wait for it. If one failed, note the gap honestly in the round report — do not silently present partial coverage as full.

### 3.3 — Merge, verify, classify → `findings.md`

Merge all findings: objective pass + 3 background dimensions + `discussion-findings`. Then:

- **Dedup** — same underlying problem reported twice keeps the best-argued copy.
- **Verify** — for each surviving finding, check it against the actual diff/code yourself. A finding that cites a line that doesn't exist, or misreads the code, dies here. Background reviewers propose; the orchestrator confirms.
- **Re-check against corrections** — any finding whose premise a discussion correction invalidated dies here too.
- **Classify** on two axes (the `/dev-feedback` taxonomy, extended with one tier at the top):
  - **Severity**: `blocking-objective` (the PR doesn't solve what it's supposed to solve, or part of it) → `blocking-correctness` → `blocking-design` → `should-fix` → `nit` → `question` → `praise`
  - **Type**: `objective`, `bug`, `security`, `design`, `perf`, `tests`, `style`, `docs`, `question`

Write `findings.md`: frontmatter (`pr`, `round`, `total`, `by_severity` counts, `status: pending-selection`), then one section per finding, sorted by severity:

```
## F<NN> — <slug>   [severity · type · source: objective-pass|correctness|tests|conventions|user]

- where: <path>:<line> (or "PR-level")
- what: <one sentence>
- why it matters: <one or two sentences>
- suggestion: <concrete fix or question, if any>
```

Genuinely good things deserve `praise` findings — a review that only criticizes teaches the author nothing about what to keep.

---

## Sub-phase 4 — Select (the human-approval moment)

Show the findings table in chat — every finding, one line each, sorted critical → trivial:

```
Findings — round NN (X total: A blocking-objective, B blocking-correctness, C blocking-design, D should-fix, E nits, F questions, G praise)

[ ] F01  blocking-objective · objective   retry logic objective not implemented (objectives.md #3)
[ ] F02  blocking-correctness · bug       auth.py:142 — state param dropped on redirect
[ ] F03  should-fix · tests               no test for the expired-token branch
[ ] F04  nit · style                      parser.py:88 — naming inconsistent with siblings
...

Full details at round-NN/findings.md.

Which findings go into the review? Options:
  (a) All
  (b) List the ones to include (e.g. "F01 F02 F03")
  (c) All blocking + should-fix, drop nits
  (d) Edit one first — tell me which and what to change
  (e) Add a finding I missed
  (f) Abandon round (nothing posts; artifacts stay)
```

**Stop and wait. Claude Code's auto-accept mode does not answer this.** Nothing the user doesn't select exists, ever, on GitHub. Mark selections in `findings.md` (`selected: true/false` per finding, flip `status: selected`).

Then draft, for each **selected** finding, a comment file at `comments/F<NN>-<slug>.md` — the text that will appear on the PR, written per the comment-style strategy (lead with the point, no filler, no salutations; include the concrete suggestion). Line-anchored findings become inline comments (`path` + `line` + `side: RIGHT`); the rest fold into the summary. Draft `comments/summary.md`: 2–4 sentences of overall assessment (objective coverage first), the non-anchored findings, a **proposed verdict** (`APPROVE` / `REQUEST_CHANGES` / `COMMENT` — request changes iff any blocking-* finding was selected), and the **attribution footer** from the comment-style strategy as the last line.

---

## Sub-phase 5 — Post (one batch, one review, one notification)

### 5.1 — Assemble the batch

```
================================================================
REVIEW TO BE POSTED — PR #<n>, round NN
================================================================
Verdict: REQUEST_CHANGES (proposed — you pick the final one)

──────────────────────────────────────────────────────────────
Inline · F02 · auth.py:142
  > State param is dropped on the redirect, which breaks the
  > anti-CSRF check. Suggest storing it on the session before
  > redirecting — see how login_oauth() does it.

──────────────────────────────────────────────────────────────
Summary:
  > <overall assessment ... non-anchored findings ...>
  >
  > *Drafted with dev-assistant · each comment human-approved*

================================================================
K inline comments + summary.

Options:
  (a) Post as REQUEST_CHANGES / APPROVE / COMMENT — state which
  (b) Edit a comment — tell me which
  (c) Drop a comment — selection stays recorded, comment doesn't post
  (d) Abandon posting — nothing posts; artifacts stay for a later run
```

**Stop and wait. Claude Code's auto-accept mode does not answer this.** This is the single checkpoint before anything leaves the machine. (If pre-flight flagged this as the user's own PR, only COMMENT is offered.)

### 5.2 — Submit as ONE GitHub review

On approval, one API call — all inline comments and the summary land atomically as a single review, one notification to the author:

```
gh api -X POST repos/{owner}/{repo}/pulls/<n>/reviews \
  -f commit_id=<headRefOid> -f event=<VERDICT> -f body=<summary> \
  --input <json with comments[]: {path, line, side, body}>
```

If submission fails (commonly: a `line` not part of the diff), surface the error verbatim, fix the offending comment's anchor (or fold it into the summary body), re-show **only the changed part** for confirmation, and retry. Never split into per-comment posts as a workaround — one review or nothing.

### 5.3 — Close the round

- Update `review.md` frontmatter: `last_reviewed_sha: <headRefOid>`, `last_round: NN`, `last_verdict: <verdict>`.
- Write `round-NN/report.md`: frontmatter (`status: posted | abandoned`, counts: found / selected / posted by severity, `verdict`, `posted_at`), then a short narrative — what the PR was about, what the review concluded, what was deliberately not posted and why. The report is what round N+1 reads first.
- Offer: *"Switch back to `<return branch>`? (PR branch `<head>` stays available.)"*
- Final report:

```
Review round NN posted on PR #<n>: <verdict>, K inline comments + summary.
  - X findings found, Y selected, Z posted
  - Round folder: .dev-assistant/reviews/pr-<n>/round-NN/

Re-run /dev-review <n> after the author pushes — the next round reviews only the delta.
```

---

## Re-running and state behavior

- **Re-running while a round is incomplete** (no `report.md` yet): resume — pick up at the earliest sub-phase whose artifact is missing. Background reviewer results that were already collected into `findings.md` are not re-run.
- **Re-running after a posted round**: starts a new round scoped to the delta since `last_reviewed_sha`.
- **Author force-pushed** (old `last_reviewed_sha` no longer an ancestor of head): tell the user, offer full re-review vs. best-effort delta via `git range-diff`.

## If something fails

Prefer pausing and asking over improvising.

- A background reviewer errors → proceed with the others, state the coverage gap in chat and in the round report.
- `gh pr checkout` fails → surface verbatim; the review can proceed diff-only with reduced depth, but say so.
- Atlassian MCP errors mid-fetch → fall back to asking the user to paste, or proceed without Jira context (noted in `context.md`).
- Review submission fails after retry → record `post_failed: true` in the report with the drafted batch intact; the user can re-invoke to retry posting only.
