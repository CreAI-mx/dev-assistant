# Dev Assistant — Design

## Vision

A developer assistant integrated with Claude Code. Standardizes how I work through development tasks across the five stages of any meaningful piece of work: gather information, plan, execute, get feedback during execution, and evaluate — plus an optional phase 0, refine, for tickets that arrive too thin to gather against.

## Architecture (slash-commands-first)

The primary interface is **Claude Code slash commands**. They drive the workflow — each phase is one slash command. Underneath them sits a small Python CLI that provides the deterministic operations the slash commands need (scaffolding folders, reading and writing state, validating structure).

Three layers, top to bottom:

```
┌───────────────────────────────────────────────────────────────┐
│ Slash commands   — markdown in .claude/commands/dev-*.md      │
│ "What should Claude do this phase?"                           │
│ Drives Claude through the phase; calls helpers via !shell     │
└──────────────────────────────┬────────────────────────────────┘
                               │ !dev-assistant <subcommand>
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ Python CLI       — dev-assistant <subcommand>                 │
│ Deterministic helpers: scaffold, read/write state, validate   │
└──────────────────────────────┬────────────────────────────────┘
                               │ filesystem
                               ▼
┌───────────────────────────────────────────────────────────────┐
│ Per-repo state   — .dev-assistant/issues/<id>/...             │
│ The data: issue.md, gathering/info.md, plan/..., evaluation/  │
└───────────────────────────────────────────────────────────────┘
```

Phases (refine / gather / plan / execute / feedback / evaluate) are *reasoning* work — they live in slash commands. The CLI does *not* have one subcommand per phase. It has one subcommand per deterministic operation.

## Status

Experimental. Single-user. Local-only. No distribution planned yet.

## The Five Stages (plus phase 0)

0. **Refine** *(optional)* — turn a thin ticket into a well-specified one *before* gathering. An intense exploration conversation: the real ask, feasibility against the actual repo, alternative approaches/algorithms/ideas, scope edges. Converges on a chosen direction, rewrites the Jira title + description (applied only after approval — the one external side effect), and records the whole exploration in `refinement/report.md`, which gather consumes as a source. Well-specified tickets skip this phase entirely.
1. **Gather information** — pull context from meetings, repo state, Slack, conversations into one structured document.
2. **Plan** — produce a main issue with subtasks (linear, parallel, or delegated).
3. **Execute** — work through subtasks, following the repo's coding standards. Creates the GitHub issue at this point (distinct from the workspace-issue that exists locally).
4. **Feedback during execution** — share updates, get PR feedback, iterate. Closed out by an explicit **merge** step (`/dev-merge`, added in 0.6): readiness checks against live GitHub state, then a merge commit titled `[<TICKET>] <summary> (#<PR>)`.
5. **Evaluate** — retro, distill lessons, close out.

"Checking" is transversal — present at every stage, not its own stage.

## Autonomy levels

Every stop a phase makes is one of four kinds, and only two of them are safe to remove: **content** (only the user knows it), **approval** (approving a draft the assistant produced), **external** (something leaving the machine), **escalation** (a failure or ambiguity). At `guided` — the original behavior — a full issue costs around 75 stops, and roughly 45% of them are approvals.

The `autonomy` field in `issue.md` moves the approvals and batches the external confirmations:

- **`guided`** — every checkpoint, every external operation confirmed on its own.
- **`balanced`** (default) — one approval checkpoint per phase; each phase's external operations confirmed as one batch. ~20 stops.
- **`auto`** — no approval checkpoints; what would have been approved is decided and recorded in the phase report's `## Decided without review` section. External batches remain. ~12 stops.

Content questions, external writes, and escalations are floors: no level removes them, and `auto` never publishes unattended. `/dev-review` does not vary by level — its selection gate is the point of the command.

The complete stop-by-stop inventory lives in [docs/interaction-map.md](docs/interaction-map.md).

## Three Zones of Storage

### Zone 1 — Program (global)

The CLI code, slash command definitions, agent prompts. Lives in the dev-assistant project repo. Slash commands are installed into Claude Code's command paths (see "Where do slash commands live?" below).

### Zone 2 — Active workspace (per-target-repo)

A hidden `.dev-assistant/` folder created inside each target repo by `dev-assistant init`. Contains all in-flight issue workspaces. Disposable per issue once closed. **Never tracked in the target repo's git** — the CLI adds `.dev-assistant/` to the target repo's `.git/info/exclude` automatically on init.

### Zone 3 — Archive / lessons (split)

- **General lessons** — stay global with the program.
- **Repo-specific lessons** — live in `.dev-assistant/lessons/` of the target repo.

When a pattern recurs across multiple repos, it can be promoted from repo-specific to global. The promotion mechanism itself is deferred.

## Per-Repo Folder Layout

After `dev-assistant init` in a target repo:

```
.dev-assistant/
├── issues/             # workspaces — one folder per active work item (author side)
├── reviews/            # PR review workspaces — one folder per reviewed PR (reviewer side)
├── archive/issues/     # archived issue workspaces (kept after /dev-evaluate); created on demand
├── strategies/         # empty by default; holds per-repo strategy overrides
└── lessons/            # repo-specific lessons archive (zone-3 slice)
```

`strategies/` is empty on init. Strategy files are resolved at runtime via `dev-assistant strategies show <name>`, which checks the per-repo `strategies/` first, then falls back to the source default in `<dev-assistant>/templates/`. This means updates to the source defaults reach every repo automatically.

Available templates (each becomes a strategy):

- **`process-objectives.md`** — standard per-issue process expectations (loaded by `/dev-gather`).
- **`output-style.md`** — how dev-assistant writes artifacts: frontmatter, headings, voice, quoting vs paraphrasing, length per section, what to avoid. Consumed by every slash command that writes a file.
- **`branching-strategy.md`** — branch structure (`develop` integration, `uat` mirror, `feat/` off `develop`, sub-branches, `--xrepo`, hotfix), conventional commits, rules, step-by-step workflow including the draft-PR-at-start + empty-commit flow. Consumed by `/dev-execute` when creating branches and crafting commit messages.
- **`pr-template.md`** — PR title format, body structure, description style. Consumed by `/dev-execute` when opening the draft PR at start and refreshing it at wrap-up.
- **`comment-style.md`** — style for comments on GitHub / Jira. Consumed when a slash command posts a comment externally.
- **`gh-issue-template.md`** — default GitHub issue body for the issue that mirrors a Jira ticket. Consumed at `/dev-execute` sub-phase 1a when the user opts in to GH issue creation.
- **`jira-subtask-template.md`** — default Jira subtask description format. Consumed at `/dev-execute` sub-phase 1a per dev-assistant subtask when the user opts in.
- **`team-update-template.md`** — default Spanish team announcement message format. Consumed at `/dev-execute` sub-phase 4 to draft the message the user copies into team chat.

To opt in to customizing a strategy for one repo, run `dev-assistant strategies customize <name>` — it copies the source default into `.dev-assistant/strategies/<name>.md`. From then on, that repo uses the local file. Delete the file to revert to the source default.

## Repo context (repo-owned rules dev-assistant must respect)

Strategies are *dev-assistant's* own operational rules. **Repo context** is a separate concept: pointers to *the target repo's* own guideline documents that every phase must consult. Examples: a `data/README.md` describing DVC workflow and MANIFEST/CHANGELOG formats, a `CONTRIBUTING.md` with team conventions, a `docs/STYLE.md` with coding patterns.

The pointer file lives at `.dev-assistant/repo-context.md`. Each H2 header is either a repo-relative file path (the file is inlined when read, so the source of truth stays in the repo and dev-assistant always sees the latest version) or a freeform section title (shown as-is, useful for short rules that don't merit their own file). The prelude before the first H2 is freeform notes.

Resolution is via `dev-assistant repo-context show`, called by every slash command alongside `dev-assistant strategies show <name>`. If a strategy and a repo-context rule conflict, the repo-context rule wins — the repo's own rules are authoritative.

Configuration:

- At init: `dev-assistant init --with-context <path>...` seeds the pointer file with one or more existing rules documents.
- Later: `dev-assistant repo-context add <path> [--note "..."]`, `dev-assistant repo-context remove <path>`, `dev-assistant repo-context list`.

Repo context is consumed by all phase slash commands (`/dev-refine`, `/dev-gather`, `/dev-plan`, `/dev-execute`, `/dev-feedback`, `/dev-evaluate`) and by `/dev-review`.

After `dev-assistant issue create --id PROJ-123 --title "..."`:

```
.dev-assistant/issues/PROJ-123/
├── issue.md            # frontmatter metadata + description
├── refinement/         # refine phase output (report.md) — empty if the ticket skipped phase 0
├── gathering/          # gather phase output (objectives.md)
├── plan/               # plan phase output
├── execution/          # execution notes / decisions
├── feedback/           # review rounds — created on demand by /dev-feedback
├── merge/              # merge report — created on demand by /dev-merge
└── evaluation/         # retro / lessons-to-promote
```

After `dev-assistant review create --pr 123` (invoked by `/dev-review`):

```
.dev-assistant/reviews/pr-123/
├── review.md           # frontmatter state: pr, pr_url, last_reviewed_sha, last_verdict
└── round-NN/           # one folder per /dev-review invocation
    ├── context.md      # thinking artifact — everything gathered (PR + issue + Jira + code)
    ├── understanding.md# decision artifact — the plain-words brief (+ corrections from Q&A)
    ├── findings.md     # merged, verified, classified findings with selection marks
    ├── comments/       # one draft per selected finding + summary.md
    └── report.md       # round outcome; what round N+1 reads first
```

## Where Do Slash Commands Live?

Claude Code looks for slash commands in two places:

- **Project-local**: `<repo>/.claude/commands/` — available only when Claude Code is opened in that repo.
- **Global**: `~/.claude/commands/` — available everywhere.

**During development the slash commands live project-local**, inside the dev-assistant repo itself at `/home/juan/documents/creai/research/dev_assistant/.claude/commands/`. This avoids polluting global Claude config while the design is in flux.

To use them in any *other* repo, run `dev-assistant commands install` inside that target repo. It creates `<target>/.claude/commands` as a symlink pointing back at the dev-assistant project's source `.claude/commands/`. After restarting Claude Code in the target repo, the `/dev-*` commands are available there too. Edits to the slash command markdown in the dev-assistant repo apply live in every linked target — one source of truth.

The dev-assistant repo itself doesn't need `commands install` — its own `.claude/commands/` is already in place, so opening Claude Code in the dev-assistant repo gives you the commands directly (good for dogfooding).

Once the tool is mature, slash commands can be promoted to global by copying or symlinking them into `~/.claude/commands/` — at that point `commands install` becomes redundant.

## CLI Surface

The CLI is the deterministic substrate. It does not implement phases (those are slash commands). It implements operations the slash commands invoke.

### Implemented

- `dev-assistant init [--with-context <path>]...` — scaffold `.dev-assistant/` in cwd; add it to target repo's `.git/info/exclude`. The optional repeatable `--with-context` flag seeds `.dev-assistant/repo-context.md` with pointers to existing rules documents (paths are validated against the repo at init time; missing paths are warned and skipped).
- `dev-assistant issue create --id <id> --title <t> [--description <d>] [--force] [--experimental] [--autonomy <level>]` — scaffold one issue workspace. `--experimental` sets `experimental: true` in `issue.md` frontmatter; `/dev-execute` then skips all external operations (Jira, GitHub, push, PR, comments) for this issue's lifecycle. `--autonomy` (`guided` | `balanced` | `auto`, default `balanced`) sets how many checkpoints the phase commands fire — see *Autonomy levels* below.
- `dev-assistant issue show --id <id>` — print the issue's metadata, the resolved autonomy level (an `## Autonomy` block — this is how every phase command receives the level), and which phase folders have content. Used by slash commands to load context.
- `dev-assistant issue set-flag --id <id> [--experimental/--no-experimental] [--autonomy <level>]` — toggle the experimental flag or change the autonomy level on an existing issue's `issue.md` frontmatter. Inserts a field if absent, updates in place if present.
- `dev-assistant issue archive --id <id> [--force]` — move an issue workspace from `issues/<id>/` to `archive/issues/<id>/`. Non-destructive (reversible by a manual `mv`). Updates `issue.md` frontmatter to `status: archived` with an `archived_at` timestamp. Refuses collisions unless `--force`. Used by `/dev-evaluate` sub-phase 5.4 at the user's option.
- `dev-assistant review create --pr <n> [--url <u>] [--title <t>] [--force]` — scaffold one PR review workspace at `reviews/pr-<n>/` (reviewer-side counterpart of `issue create`). Round folders are created by `/dev-review`, not here.
- `dev-assistant review show --pr <n>` — print the review's metadata (review.md) and per-round file progress. Called by `/dev-review` to load context at the start of a round.
- `dev-assistant commands install [--force]` — symlink the dev-assistant project's `.claude/commands/` into the current directory's `.claude/commands/` so the `/dev-*` slash commands are available when Claude Code is opened here. Source is auto-detected via the editable install.
- `dev-assistant strategies show <name>` — print the effective content of a strategy. Resolves the per-repo override at `.dev-assistant/strategies/<name>.md` first; falls back to the source default at `templates/<name>.md`. Output is prefixed with an HTML comment noting which source was used.
- `dev-assistant strategies customize <name> [--force]` — copy a source-default strategy into the per-repo workspace so the user can edit it. After this, the strategy resolves to the per-repo file. Delete the file to revert.
- `dev-assistant repo-context show` — print the resolved repo-context: the pointer file plus inlined content from every H2 whose text resolves to an existing repo-relative file. H2s that don't resolve are treated as freeform section titles. Consumed by every phase slash command.
- `dev-assistant repo-context list` — list entries with status (`[file]` resolves, `[MISSING]` looks like a path but file not found, `[section]` freeform title).
- `dev-assistant repo-context add <path> [--note "..."] [--force]` — append a pointer (refuses if the path doesn't exist; `--force` allows forward references). Creates `.dev-assistant/repo-context.md` with a standard preamble if it doesn't exist yet.
- `dev-assistant repo-context remove <path>` — drop an entry (the H2 header text matches verbatim; the section runs to the next `## ` or end of file).

### Likely future helpers

- `dev-assistant issue list` — list all issue workspaces with status (active vs archived).
- `dev-assistant phase complete --issue <id> --phase <name>` — mark a phase done in state.
- `dev-assistant lesson add --issue <id>` — append a lesson to the repo-specific archive.
- `dev-assistant commands uninstall` — remove the symlink.

## Slash Command Surface

One issue flows top-to-bottom through the author-side commands. Middle column: what each phase writes locally (under `.dev-assistant/issues/<id>/`). Right column: its external side effects — every one individually gated on user confirmation; experimental issues skip the entire right column.

```
                       local artifacts                     external side effects
                       (.dev-assistant/issues/<id>/)       (each confirmed; none if experimental)

   Jira ticket
       │
       ▼
 ┌───────────────┐     refinement/report.md                Jira title + description
 │  /dev-refine  │     (optional phase 0 — skip            rewritten (after approval)
 └───────┬───────┘      when the ticket is solid)
         ▼
 ┌───────────────┐     gathering/report.md                 —
 │  /dev-gather  │     gathering/objectives.md
 └───────┬───────┘
         ▼
 ┌───────────────┐     plan/plan.md                        —
 │  /dev-plan    │     plan/report.md                      (read-only on the world)
 └───────┬───────┘
         ▼
 ┌───────────────┐     execution/<NN-slug>/…               GH issue (assigned) + Jira subtasks
 │ /dev-execute  │◀─┐  execution/wrap-up-report.md         (assigned), push, draft PR at start;
 └───────┬───────┘  │  execution/team-message.txt          at wrap-up: PR Ready + commit map
         │──────────┘                                      (sub-branches: sub-PR per subtask)
         │  one subtask per invocation, then wrap-up       (hotfix: + develop sync PR)
         ▼
 ┌───────────────┐     feedback/round-NN/                  fix commits pushed; replies posted
 │ /dev-feedback │◀─┐  (pulled, triage, clusters,          as ONE reviewed batch; threads
 └───────┬───────┘  │   report with remote-state check)    resolved; PR commit map updated
         │──────────┘
         │  one review round per invocation
         ▼
 ┌───────────────┐     merge/report.md                     merge commit "[TICKET] … (#PR)",
 │  /dev-merge   │     (readiness checklist recorded)      branch deleted, Jira comment
 └───────┬───────┘                                         (hotfix: uat PR, then develop PR)
         ▼
 ┌───────────────┐     evaluation/retro.md                 ONE batch, gated on PR state:
 │ /dev-evaluate │     evaluation/lessons.md               GH closure comment + issue close,
 └───────────────┘     …plus repo-wide                     Jira transitions
                       lessons/<category>/… + INDEX.md

 Standalone (reviewer side — you review someone else's PR; not a lifecycle phase):

 ┌───────────────┐     reviews/pr-<n>/round-NN/            ONE GitHub review, submitted
 │  /dev-review  │◀─┐  (context, understanding,            atomically; only user-selected
 └───────────────┘  │   findings, comments, report)        findings are posted
         │──────────┘
            one round per invocation (round 02+ reviews only the delta)
```

### Implemented

Each command below carries a sub-phase diagram. Conventions: **(pause)** = stops and waits for the user's actual response, even in auto modes; **(CONFIRM)** = external operation, individually gated on explicit confirmation; "repeat" marks internal loops.

- `/dev-refine <issue-id>` — optional phase 0, run when a ticket arrives too thin to gather against. Five announced sub-stages: **1 load** (fetch the ticket from Jira via Atlassian MCP, paste fallback; scaffold the issue workspace via `issue create` if it doesn't exist — refine is usually the first phase to touch a ticket), **2 exploration** (the heart: an intense conversation over the real ask, feasibility grounded in repo reads, 2–4 genuinely different candidate directions with trade-offs, scope edges, constraints — Claude is expected to contribute ideas, not just transcribe), **3 narrowing** (chosen direction + alternatives set aside with honest reasons + surviving open questions; "split this ticket" or "don't do it" are valid outcomes), **4 rewrite proposal** (new title + description side-by-side with the originals, iterated until explicit approval), **5 apply + report** (the ONLY external write of the phase: update Jira title/description after approval — skipped for experimental issues, manual-paste fallback without MCP; then sync local `issue.md`; then write `refinement/report.md` — deliberately allowed to be extensive, it is the only record of the exploration). The GH issue is untouched (still created at `/dev-execute`). `/dev-gather` consumes the report as its first source. Model: Opus.

  ```
  ┌─────────────────────┐
  │ 1  load             │  fetch ticket from Jira (paste fallback) · scaffold workspace if missing
  ├─────────────────────┤
  │ 2  exploration      │  the real ask · feasibility from repo reads · 2–4 candidate directions (conversation)
  ├─────────────────────┤
  │ 3  narrowing        │  direction chosen — "split it" / "don't do it" are valid outcomes (pause)
  ├─────────────────────┤
  │ 4  rewrite proposal │  new title + description side-by-side with the original, iterated (pause: approval)
  ├─────────────────────┤
  │ 5  apply + report   │  Jira update (CONFIRM; skipped if experimental) → refinement/report.md
  └─────────────────────┘
  ```

- `/dev-gather <issue-id>` — walks the gather phase in five announced sub-stages (source inventory → information collection per source → process objectives confirmation → draft issue objectives → validation and write). Produces **two artifacts**: a thinking artifact (`gathering/report.md`) preserving full source content + analysis, and a decision artifact (`gathering/objectives.md`) with distilled objectives that later phases consume.

  ```
  ┌──────────────────────────┐
  │ 1  source inventory      │  refinement report · Jira · repo · meeting notes · direct input (pause: pick subset)
  ├──────────────────────────┤
  │ 2  information collection│  per chosen source; direct input = five fixed questions, one at a time (pause each)
  ├──────────────────────────┤
  │ 3  process objectives    │  confirm / trim the standard process expectations (pause)
  ├──────────────────────────┤
  │ 4  draft issue objectives│  general objective + 3–7 specific testable items · constraints · open questions
  ├──────────────────────────┤
  │ 5  validate + write      │  gathering/report.md (thinking) + gathering/objectives.md (decision) — no external ops
  └──────────────────────────┘
  ```

- `/dev-plan <issue-id>` — walks the plan phase in five announced sub-stages (context load → decomposition proposal → subtask elaboration → sequencing and branch info → viability check and write). Produces **two artifacts**: a thinking artifact (`plan/report.md`) covering decomposition approach, sequencing rationale, alternatives considered, viability outcomes, and risks; and a decision artifact (`plan/plan.md`) with branch info (feature branch off `develop`, target `develop`), branching mode (`single-branch` default — one feat branch, draft PR → `develop` at start, marked Ready at wrap-up — or `sub-branches` — one `feat/<TICKET>-<slug>-sub-N` branch + sub-PR per subtask, parent draft PR marked Ready at wrap-up; chosen in sub-stage 4, recommended when the commit estimate runs past the 8–10 band), coverage map, dependency graph, and full subtask specs inline. Pure planning — no side effects (no GitHub issue, no branch, no commits, no PR). Model: Opus.

  ```
  ┌────────────────────────┐
  │ 1  context load        │  objectives + strategies; "is this the right context to plan from?" (pause)
  ├────────────────────────┤
  │ 2  decomposition       │  2–5 subtasks proposed as a table, iterated with the user (pause)
  ├────────────────────────┤
  │ 3  subtask elaboration │  one at a time: spec · passing criteria · commit previews (pause per subtask)
  ├────────────────────────┤
  │ 4  sequencing + branch │  deps · slug · flow (feature|hotfix) · branching mode · target branch
  │                        │  resolved from the branching strategy (pause)
  ├────────────────────────┤
  │ 5  viability + write   │  mechanical checks + conversational rubric → plan/plan.md + plan/report.md,
  │                        │  then a final revision pass on the written files (pause)
  └────────────────────────┘
  ```

- `/dev-execute <issue-id> [subtask-n | wrap-up]` — executes one subtask per invocation, or runs wrap-up after all subtasks are done. Four sub-phases per invocation: **1a external preparation** (optional, always-ask: create Jira subtask, populate description, create GH issue), **1b local branch preparation** (automatic, no confirm: fetch + branch-off-`develop` + an empty "open draft pr" commit, or branch-from-HEAD in experimental mode; in `sub-branches` mode also creates the subtask's `-sub-N` branch off the parent — starting a new subtask before the prior sub-PR merges offers wait-or-stack), **1c draft PR at start** (first subtask, non-experimental: push + open a draft PR → `develop`, each external op confirmed), **2 implementation plan** (orchestrator drafts, mechanical checks with up to 2 internal re-drafts, user approves / refines / abandons via a summary), **3 execute the work** (per-commit subagent dispatch with Sonnet, orchestrator reviews diff, commits with no `--no-verify`, verifies subtask-level passing criteria with one auto-fix retry; in `sub-branches` mode a 3.8 step then rebases onto the parent feature branch and opens the per-subtask sub-PR, each external op confirmed), then **4 wrap-up** at the end of all subtasks (rebase onto `develop`, push, mark the draft PR Ready — opening it fresh if 1c was declined — Jira comment, all individually confirmed; in `sub-branches` mode pre-flight requires all sub-PRs merged and the parent PR body lists them; team message generated locally in Spanish; wrap-up report written). Experimental mode (set via `issue create --experimental`) skips all external operations. Model: Opus orchestrator, Sonnet subagent for code writing.

  ```
  one subtask per invocation — repeat until all subtasks are done:
  ┌─────────────────────┐
  │ 1a external prep    │  GH issue (--assignee @me) · Jira subtask (assigned) — optional, each CONFIRM
  ├─────────────────────┤
  │ 1b branch prep      │  verify origin/<target_branch> exists · branch + empty commit (automatic, local)
  ├─────────────────────┤
  │ 1c draft PR         │  first subtask only: push (CONFIRM) → draft PR → <target_branch> (CONFIRM)
  ├─────────────────────┤
  │ 2  impl plan        │  draft → mechanical checks (≤2 redrafts) → summary (pause: approve/refine/abandon)
  ├─────────────────────┤
  │ 3  execute          │  repeat per commit: subagent writes → orchestrator reviews diff → commit;
  │                     │  then verify passing criteria (1 auto-fix retry) · sub-branches: sub-PR (CONFIRM)
  └─────────────────────┘
  after the last subtask — wrap-up invocation:
  ┌─────────────────────┐
  │ 4  wrap-up          │  pre-flight → deferred-prep catch-up → rebase onto <target_branch> → push (CONFIRM)
  │                     │  → PR body + commit map, mark Ready (CONFIRM) → hotfix: develop sync PR (CONFIRM)
  │                     │  → Jira comment (CONFIRM) → team message (local) → wrap-up report
  └─────────────────────┘
  ```

- `/dev-feedback <issue-id> [subtask-n]` — walks **one round** of the post-PR review loop, against the issue's main PR or (with the subtask argument, `sub-branches` mode only) a subtask's sub-PR. Re-invokable: each call processes only comments newer than the last round's pull timestamp; rounds are tracked per PR (`feedback/round-NN/` for the main PR, `feedback/sub-<N>/round-NN/` for a sub-PR). Five sub-phases per round: **1 pull** (fetch new comments from PR issue-comments + review-thread comments + review summaries, filtering own replies and resolved threads), **2 triage** (auto-classify each comment by severity `blocking-correctness | blocking-design | should-fix | nit | question | praise` and type `bug | security | design | perf | tests | style | docs | question | discussion`, cluster by file/area/concern, user reviews and can reclassify / defer / abandon), **3 plan** (per cluster: draft `impl-plan.md` for code-fix clusters; draft `reply.md` for every cluster), **4 apply** (per code-fix cluster in severity order: orchestrator shows impl-plan summary, user approves / refines / skips with a nits-batching shortcut, Sonnet subagent writes the fix, orchestrator reviews diff, commits one per cluster with no `--no-verify`), **5 wrap** (assemble **ALL** drafted replies into one batch view paired with reviewer quotes — this is a non-negotiable single user checkpoint before any reply leaves the local machine — then push with confirmation, post replies, optionally resolve threads with confirmation, write round report). Experimental issues are blocked at pre-flight since they have no PR. Output structure: `feedback/round-NN/` with `pulled.md`, `triage.md`, `clusters/<NN-slug>/{meta,impl-plan,reply}.md`, and `report.md`. Model: Opus orchestrator, Sonnet subagent for code writing.

  ```
  one review round per invocation — only comments newer than the last round:
  ┌────────────────────┐
  │ 0  round detection │  next feedback/round-NN/; since = the previous round's pull timestamp
  ├────────────────────┤
  │ 1  pull            │  issue comments + inline threads + review summaries; 0 new → stop here
  ├────────────────────┤
  │ 2  triage          │  severity × type → clusters (pause: approve / reclassify / defer / abandon)
  ├────────────────────┤
  │ 3  plan            │  per cluster: impl-plan (code-fix only) + drafted reply (every cluster)
  ├────────────────────┤
  │ 4  apply           │  repeat per code-fix cluster, severity order: approve (pause) → subagent fix
  │                    │  → diff review → one commit per cluster
  ├────────────────────┤
  │ 5  wrap            │  ALL replies in ONE batch (pause) → push (CONFIRM) → post replies → resolve
  │                    │  threads (CONFIRM) → commit-map update (CONFIRM) → verify remote state → report
  └────────────────────┘
  ```

- `/dev-merge <issue-id>` — closes the review loop once the PR is approved. Four sub-phases: **1 merge readiness** (one checklist verified against live GitHub state — approvals, CI, unresolved threads, deferred discussion clusters, branch sync, base branch matches the plan's `target_branch`; any ✗ blocks by default, per-item user overrides are recorded), **2 merge-commit message** (subject `[<TICKET>] <summary> (#<PR>)` so GitHub autolinks commit → PR; user approves/edits), **3 merge + cleanup** (always a **merge commit**, never squash — commit SHAs referenced across Jira comments, review replies, and phase artifacts must stay valid; then branch deletion remote + local, both confirmed), **4 record** (update `plan.md` state, optional Jira comment, write `merge/report.md`). Hotfix flow walks both PRs — `uat` first, then the `develop` sync — and deletes the shared branch only after both merge. Idempotent: an already-merged PR skips to sub-phase 4. Model: Opus.

  ```
  ┌─────────────────────┐
  │ pre-flight          │  workspace · PR recorded · gh auth · clean tree; already merged → skip to 4
  ├─────────────────────┤
  │ 1  merge readiness  │  approvals · CI · unresolved threads · deferred clusters · branch sync ·
  │                     │  base matches plan — one checklist, any ✗ blocks (pause: per-item override)
  ├─────────────────────┤
  │ 2  merge message    │  subject "[<TICKET>] <summary> (#<PR>)" + outcome bullets (pause: approve/edit)
  ├─────────────────────┤
  │ 3  merge + cleanup  │  merge commit (CONFIRM) → verify landed → delete branch remote (CONFIRM) + local;
  │                     │  hotfix: repeat 1–3 for the develop sync PR before any branch deletion
  ├─────────────────────┤
  │ 4  record           │  plan.md state · Jira comment (CONFIRM) · merge/report.md → next: /dev-evaluate
  └─────────────────────┘
  ```

- `/dev-evaluate <issue-id>` — final phase. Reads every prior-phase artifact (gathering, plan, execution, feedback rounds, PR state) and produces a retrospective + archives lessons + closes the loop externally. Five sub-phases: **1 load** (read all artifacts, classify PR as `merged | closed-unmerged | open | n/a`), **2 analyze** (outcomes against original objectives + drift from plan, both held in memory), **3 retro** (draft `evaluation/retro.md` thinking artifact and `evaluation/lessons.md` per-issue decision artifact with category process/technical/collaboration and `promotion_candidate` flag; user reviews and edits before approval), **4 external** (idempotency check skips already-completed ops; then PR-state-gated batch of: GH issue closure comment, Jira subtask transitions, Jira parent transition, GH issue close — assembled into ONE batch view for user approval before any fires; on `open` PR only the interim-retro comment posts, all transitions and close deferred), **5 archive** (writes one file per lesson to the categorized repo-wide archive `.dev-assistant/lessons/<category>/<YYYY-MM-DD>-<id>-<slug>.md` — a lesson that repeats an existing one updates that file's recurrence count instead of duplicating it, and `INDEX.md` is regenerated; writes `evaluation/report.md`; offers the non-destructive workspace archive via `dev-assistant issue archive`). Experimental mode skips sub-phase 4 entirely. Re-runnable: PR-state changes pick up newly-allowed transitions on next invocation. Model: Opus orchestrator, no subagent (pure retrospective work).

  ```
  ┌─────────────┐
  │ 1  load     │  read every prior artifact · verify remote state (PR/merge commit, replies actually
  │             │  posted, GH issue, branch cleanup, Jira) — discrepancies become retro findings
  ├─────────────┤
  │ 2  analyze  │  outcomes vs the original objectives · drift from plan (held in memory)
  ├─────────────┤
  │ 3  retro    │  draft evaluation/retro.md + evaluation/lessons.md (pause: approve / edit / abandon)
  ├─────────────┤
  │ 4  external │  idempotency check → ONE batch (pause): GH closure comment · Jira subtask + parent
  │             │  transitions · GH issue close — gated on PR state (open PR → interim comment only)
  ├─────────────┤
  │ 5  archive  │  lessons → lessons/<category>/ (recurrence dedupe) · INDEX.md rebuilt · report ·
  │             │  optional non-destructive workspace archive (pause)
  └─────────────┘
  ```

- `/dev-review <pr-number-or-url>` — **reviewer side**: review *someone else's* PR (the mirror image of `/dev-feedback`, which handles incoming review on your own PR). Re-invokable: round 01 reviews the whole PR; after the author pushes, the next round reviews only the delta since `last_reviewed_sha` (tracked in `reviews/pr-<n>/review.md`). Five sub-phases per round: **1 gather** (intent first — PR description, linked GH issue, linked Jira ticket via Atlassian MCP with paste/skip fallback — then code: per-commit narrative, diff, CI status, PR-branch checkout, blast-radius scan of changed-function call sites; writes `context.md` with distilled objectives traced to sources), **2 brief + Q&A** (writes `understanding.md` — what was asked / what the PR claims / what it actually changes / gaps / risk map — then immediately launches three background Sonnet reviewers for the small-scale dimensions (correctness, tests, conventions) while the user reads the brief and asks questions in the foreground; user questions can become findings (`source: user`) and corrections update the brief), **3 deep review** (the objective-coverage pass deliberately waits for the Q&A to settle since it's the dimension the discussion informs — hybrid sequencing; then collect background results, dedup, orchestrator-verify every finding against the real diff, classify with the `/dev-feedback` severity taxonomy extended with `blocking-objective` at the top: objective gaps rank above bugs), **4 select** (findings table sorted critical → trivial; the user explicitly picks which findings become review comments — nothing unselected ever reaches GitHub; drafts per-finding comment files + a summary with proposed verdict and the attribution footer from `comment-style`), **5 post** (one batch view of all comments + summary + verdict — single checkpoint — then submits everything atomically as **one** GitHub review via the pulls/reviews API: one notification to the author; never falls back to comment-by-comment posting). Read-only by design: no commits, no pushes; the only external write is the gated review submission. Attribution: one footer line in the review summary only, never per-comment. Workspace: `.dev-assistant/reviews/pr-<n>/round-NN/` with `context.md`, `understanding.md`, `findings.md`, `comments/`, `report.md`. Model: Opus orchestrator, Sonnet background reviewers.

  ```
  one round per invocation — round 02+ reviews only the delta since last_reviewed_sha:
  ┌─────────────────┐
  │ 1  gather       │  intent first (PR description, GH issue, Jira), then code (commits, diff, CI,
  │                 │  checkout, blast radius) → context.md with distilled objectives
  ├─────────────────┤
  │ 2  brief + Q&A  │  understanding.md; 3 background Sonnet reviewers (correctness, tests,
  │                 │  conventions) start now; user reads + asks questions in the foreground (pause)
  ├─────────────────┤
  │ 3  deep review  │  objective-coverage pass (waits for the Q&A — it's the dimension discussion
  │                 │  informs) → collect background results → dedup → verify → classify
  ├─────────────────┤
  │ 4  select       │  findings table, critical → trivial; user picks EXACTLY what posts (pause) —
  │                 │  unselected findings never reach GitHub
  ├─────────────────┤
  │ 5  post         │  one batch view: comments + summary + verdict (pause) → submitted atomically
  │                 │  as ONE GitHub review (CONFIRM) — never comment-by-comment
  └─────────────────┘
  ```

### Gather phase output structure

Two files in `.dev-assistant/issues/<id>/gathering/`:

**`report.md` — the thinking artifact.** Full record of what was gathered. Sections:
- Summary
- Sources (one section per consulted source: JIRA, Repository, Meeting notes, Direct input — with actual content, quoted where it matters)
- Analysis (patterns, tensions, assumptions called out, things excluded from objectives and why)
- How this maps to objectives (traces objectives back to evidence)
- What's missing (gaps and unanswered things)

**`objectives.md` — the decision artifact.** Tight, focused, what later phases read:
- Pointer to `report.md` for full context
- Process objectives (from `strategies/process-objectives.md`, possibly trimmed)
- Issue objectives: general (one sentence) + specific (3–7 testable items)
- Constraints
- Open questions

Both use checkbox-style for objectives so later phases can flip items as work proceeds.

Sources of information feeding the gather phase: the refinement report (`refinement/report.md` from `/dev-refine`, proposed as the first source when present — its decisions are treated as settled unless the user reopens them), JIRA (via Atlassian MCP when available), the repo (via Read/Grep/Glob), meeting notes (pasted by user), direct conversation. The slash command asks which subset to consult at the start of every run.

**Direct input** sub-stage is guided by five fixed questions (problem-in-own-words → background-not-in-ticket → other-people-with-context → undocumented-constraints → most-uncertain-thing) asked one at a time. The slash command explicitly instructs Claude to **stop and wait for the user's response** in this sub-stage and the other interactive ones, including under autonomous / auto-accept modes — earlier runs were skipping interactive prompts in those modes.

### Next up

All lifecycle phase slash commands are implemented (`/dev-refine` through `/dev-evaluate`, including the `/dev-merge` close of the review loop added in 0.6), plus the reviewer-side `/dev-review` (not a lifecycle phase — it stands alone, since the user is the reviewer, not the author). Remaining work is in CLI helpers and quality-of-life additions — see "Deferred / Next Up" below.

## CLI Conventions

- **Subcommand pattern**: noun-verb (`issue create`, `issue show`), like `gh`, `docker`, `kubectl`.
- **Active issue**: every command takes an explicit `--issue <id>` (or `--id` for the `issue` subapp). No ambient state, no wrong-pointing.
- **Folder collision on `issue create`**: errors unless `--force`.
- **Help style**: plain Unix-style (Typer's Rich integration disabled with `rich_markup_mode=None`), matching the helper-tool role.

## MCP Integration Model

MCP servers are only accessible inside Claude Code, not from a raw terminal. So integrations like Atlassian/Jira lookup live in the **slash command** layer, not in the CLI itself.

For example, `/dev-refine <issue-id>` (sub-stage 1) does exactly this:

1. Check: is Atlassian MCP available?
2. If yes → fetch issue from Jira → confirm with user → invoke `!dev-assistant issue create --id <id> --title <fetched-title>`.
3. If no → fall back to the user pasting the ticket, then invoke the CLI.

The CLI itself stays dumb — it just scaffolds folders with whatever the slash command hands it.

## Stack

- Python ≥ 3.10
- [Typer](https://typer.tiangolo.com/) for the CLI framework (Rich off for plain help)
- Installed via `pip install --user --break-system-packages -e .` during dev (or `pipx install -e .` when pipx is available)

No PyPI distribution. No tests / lint / CI yet. The project itself is a normal git repo and is version-controlled. The `.dev-assistant/` folders the tool *creates* in target repos are intentionally untracked.

## How to Pick This Up in a Future Session

1. Read this `DESIGN.md`.
2. Read the memory entries in `~/.claude/projects/-home-juan-documents-creai-research-dev-assistant/memory/` for any deltas since this doc was written.
3. CLI source is in `src/dev_assistant/cli.py` — single file, simple, start there.
4. Slash command sources are in `.claude/commands/dev-*.md` — markdown with shell `!` calls into the CLI.
5. Recent `git log` shows what's been done and pending.

## Deferred / Next Up

- ~~Atlassian / Jira MCP path: `/dev-issue-new` that fetches from Jira before scaffolding the local issue workspace.~~ Superseded by `/dev-refine` (0.4.0), which fetches from Jira and scaffolds the workspace as its sub-stage 1.
- State transitions: `dev-assistant phase complete`, `lesson add` (would be invoked by `/dev-evaluate` once they exist).
- Promotion path: repo-specific lessons → global zone-1 updates. Lessons already carry a `promotion_candidate` flag; the promotion command itself is still missing.
- Parallel subtask execution via subagent fan-out (currently `/dev-execute` is per-subtask serial).
- Autonomous evaluator loop in `/dev-execute` sub-phase 2 — see `IDEAS.md`.
- Eventually: promote slash commands from project-local to global, package for distribution.
