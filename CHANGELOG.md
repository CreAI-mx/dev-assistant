# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). While the project is in alpha (`0.x`), breaking changes may land in any minor version.

## [Unreleased]

Adds the merge phase (explicit close of the review loop), first-class hotfix handling, autonomy levels for how much the phases ask you, a code-economy standard that bounds how much code a phase writes, remote-state verification in reports, and a reorganized lessons archive.

### Added

- **Autonomy levels.** A new `autonomy: guided | balanced | auto` field in `issue.md`, set with `dev-assistant issue create --autonomy` and changed with `issue set-flag --autonomy`, controls how many times a phase stops for input. `guided` is the pre-0.6 behavior (every sub-stage approval, every external operation confirmed on its own — around 75 stops across a full issue); **`balanced` is the new default** and collapses each phase's approvals into a single checkpoint and each phase's external operations into one batched confirmation (~20); `auto` drops the approval checkpoints entirely and records what was decided instead (~12). Three things are floors at every level: questions only the user can answer (refine's exploration conversation, gather's direct input — `auto` asks them as one block rather than one at a time), confirmation of every external write (merge is confirmed once per PR, always), and escalations (conflicts, failing criteria, readiness ✗). Below `guided`, every phase report gains a **`## Decided without review`** section listing what the assistant settled alone. A trailing `--guided` / `--balanced` / `--auto` token on any phase command overrides the level for one invocation; issues created before the field existed resolve to `guided`. `/dev-review` is unaffected — its selection gate and batch approval are the point of the command.
- **Code economy.** A new `code-economy` strategy bounds change size, and the pipeline measures against it instead of eyeballing. Subtasks are sized in bands — `S` ≤50 added lines, `M` ≤150, `L` ≤400 (written reason required), `XL` means split — with deletions never charged and generated output excluded. `/dev-plan` sizes every subtask, totals them, and records what the plan **deliberately left out**; `/dev-execute` measures each commit before it lands, runs one automatic trim pass when it is over, and stops to ask only if it is still over (an escalation, so it fires at every autonomy level); a new **reduction pass** at wrap-up (sub-phase 4.2b) reads the issue's whole diff as one change, removes what keeps every passing criterion green, and commits it as one budget-exempt `refactor` commit; `/dev-feedback` sizes each cluster's fix, so an `L` "fix" for a review comment becomes a follow-up ticket instead of a bigger commit; `/dev-review` gains a fourth background reviewer dimension (**economy**) producing `bloat` findings that must name the smaller alternative; `/dev-evaluate` compares planned to landed and turns a recurring mis-size into a promoted lesson. The readability counterweight is explicit: when the shorter version takes longer to explain, the longer one wins, and clever compression is flagged exactly like bloat.
- **`dev-assistant issue size --id <id>`** — measures the diff and bands it against the plan. `--worktree` sizes uncommitted work (tracked changes plus untracked files) so a commit can be sized before it is made, `--band` compares against one subtask's budget, `--exclude` adds repo-specific noise patterns. Pure logic in `dev_assistant/sizing.py`.
- **`docs/interaction-map.md`** — the complete inventory of every point in the lifecycle where a command stops for the user, classified by kind (content / approval / external / escalation), with file references and what each autonomy level does to it.
- **`/dev-merge <issue-id>`** — the previously missing step between feedback rounds and evaluate. Verifies merge readiness against live GitHub state (approvals, CI, unresolved threads, deferred clusters, branch sync, base-branch match) as one ✗-blocks-by-default checklist, builds the merge-commit message with the trackable `[<TICKET>] <summary> (#<PR>)` subject, merges with a **merge commit** (never squash/rebase-merge — commit SHAs referenced in Jira comments, review replies, and phase artifacts stay valid), deletes the branch (remote + local), optionally comments on Jira, and writes `merge/report.md`. Idempotent on re-run (already-merged PRs skip to state/report). The merge-commit policy is now rule 12 of the default branching strategy.
- **Hotfix flow.** `/dev-plan` sub-stage 4 now decides `flow: feature | hotfix`. A hotfix forces `hotfix/<TICKET>-<slug>` off `uat`, `single-branch` mode, 1–2 subtasks, `fix` commits; `/dev-execute` wrap-up gains sub-phase 4.5b (opens the `develop` sync PR — per the strategy every hotfix needs two PRs); `/dev-merge` walks both PRs (`uat` first, branch deleted only after both merge).
- **Commit map in the PR body.** `/dev-execute` wrap-up appends a `## Commit map` table (commit ↔ subtask ↔ Jira subtask key ↔ subject) so reviewers can review commit-by-commit; `/dev-feedback` 5.5 appends a row per review-fix commit. Added to `pr-template`.
- **Auto-assignment.** GH issues are created with `--assignee @me`; Jira subtasks are assigned to the currently authenticated Jira user (account ID resolved via `atlassianUserInfo` at creation time). Always the user running the phase — never a hardcoded name.
- **User guide** (`docs/user-guide.md`) — setup, an experimental-mode dry run as the recommended first contact (nothing leaves the machine), a phase-by-phase lifecycle walkthrough (what you're asked, what lands on disk), key concepts (strategies, repo context, flows, branching modes, the confirmation principle), workspace layout, CLI reference, and a troubleshooting FAQ. README now links to it.
- **Remote-state verification in reports.** `/dev-feedback` gains sub-phase 5.6 (were the replies actually posted? branch in sync? threads really resolved? current review decision?) and records a `remote_state` block + section in the round report. `/dev-evaluate` sub-phase 1 now verifies PR/merge-commit, posted replies, GH issue state, branch cleanup, and Jira statuses against remote reality; the retro gains a "Remote state" section where local-vs-remote discrepancies are findings.

### Changed

- **`dev-assistant issue show` reports the resolved autonomy level** in an `## Autonomy` block, so every phase command receives it through the context block it already runs. The TUI issue panel shows the level as a badge beside `experimental`.
- **Base branch is resolved, not assumed.** `/dev-plan` records `target_branch` resolved from the branching strategy (stating where the value came from); `/dev-execute` verifies `origin/<target_branch>` exists before branching, uses it for every branch/rebase/PR operation, and verifies the created PR's `baseRefName`; `/dev-feedback` pre-flight check 8 stops on base mismatch.
- **Lessons archive reorganized** (`/dev-evaluate` 5.2): category subfolders (`process/`, `technical/`, `collaboration/`), semantic dedupe — a recurring lesson updates the existing file's `## Recurrences` instead of creating a near-duplicate (2+ recurrences auto-flags promotion) — and a regenerated `INDEX.md` with a promotion-candidates view. Pre-0.6 flat files are migrated into category folders on the next archive run.
- `/dev-feedback` final report surfaces the review decision and points to `/dev-merge` when approved, and reminds that Slack-channel feedback can be pasted into the next round.
- **TUI updated for the new pipeline and layout**: `merge` appears in the phase order, timeline, and pipeline distribution (hidden on issues that never ran it, like pre-0.6 and experimental ones); the lessons pane reads the categorized `lessons/<category>/` layout (flat pre-0.6 files still work, `INDEX.md` excluded); the issue status panel shows the hotfix flow with its sync-PR state and the merge commit once merged (`flow`, `develop_pr_url`, `merge_commit` from `plan.md`).

### Fixed

- `/dev-execute VN-788 2` no longer crashes: the embedded `dev-assistant issue show` call now receives only the issue ID (`$1`), not the full argument string. Same fix applied to `/dev-feedback`.
- **TUI now shows main-PR feedback rounds.** In single-branch mode rounds live directly at `feedback/round-NN/`, but the scanner only looked for rounds one level down (`feedback/sub-N/round-NN/`), so those folders were modeled as sub-branches: the phase read `N sub-branches · 0 rounds` and no round appeared in the timeline. Phases now carry their own rounds alongside subphases, and `round-*` folders are no longer mistaken for sub-branches.
- **TUI now shows feedback clusters.** A round's `clusters/<id>-<slug>/` folders were never scanned — clusters were absent from every count (`artifact_count` undercounted the whole phase) and, in single-branch mode, their `impl-plan.md` / `reply.md` artifacts were unreachable in the nav tree. Rounds now model their clusters, the timeline and tree show cluster counts, and round nodes expose any nested folder (`clusters/`, `comments/`) instead of only flat files.
- The subphase-state helper no longer misreads a bare `last_feedback_round: NN` (what the commands actually write for a main-PR round) as a `sub-N` name.

## [0.5.0] - 2026-06-23

Migrates the default branching strategy from the v1.x sprint-version model to **v2.0** (sprint-driven, trunk-friendly), matching the Akinator engine team's Contributing wiki, and ships an experimental read-only **terminal dashboard**. **Breaking** for in-flight issues planned under the old model — see *Migration*.

### Added

- **Terminal dashboard (`dev-assistant tui`).** Read-only Textual UI for browsing a repo's `.dev-assistant/` workspace — issues, phases, subtasks/sub-branches, review rounds, and lessons — driven by the artifacts on disk plus live git/PR introspection (it never writes). A navigation tree drills into a detail pane showing workspace rollups and a pipeline distribution chart, per-issue timelines with state dots, a status panel (branch, sub-branches, PR publish state, GitHub issue link, commits from `plan.md` + git), review breakdowns, and a raw markdown viewer. Monochrome output (no emoji). Requires the optional `[tui]` extra (`pip install -e ".[tui]"`). Experimental.

### Changed

- **`branching-strategy.md` rewritten to v2.0.** Removed the `version/x.y.z` sprint branch as a batch gate: feature branches now branch off `develop` and merge directly back into `develop`. Added the permanent `uat` branch, the `hotfix/<TICKET>-<slug>` flow (two PRs: `uat` + `develop`), and the `--xrepo` cross-repo branch suffix (same branch name across repos, coordinated merge). `uat` / `hotfix` / `--xrepo` are documented in the strategy; the commands still drive the normal `feat → develop` flow.
- **Draft PR opens at the *start* of execution, not at wrap-up.** Per v2.0, work begins by opening a draft PR — the start-of-work signal. `/dev-execute` sub-phase 1b now branches off `origin/develop` and makes an empty `chore: open draft pr feat/<TICKET>-<slug>` commit (so the branch diverges from `develop` and the PR has a base); a new **sub-phase 1c** pushes and opens the draft PR → `develop` (each external op confirmed). Wrap-up (4.5) now refreshes the PR body and marks it **Ready for review** (`gh pr ready`) instead of opening it — falling back to a fresh open if 1c was declined.
- `/dev-plan`: `target_version: latest` frontmatter replaced with `target_branch: develop`; branching-mode descriptions updated (draft PR at start, Ready at wrap-up). `/dev-execute` wrap-up report frontmatter `target_version` → `target_branch`.
- Wrap-up rebases onto `origin/develop` (was the latest `version/x.y.z`). Sub-PRs still target the parent feature branch; in `sub-branches` mode the parent draft PR opens at start and is marked Ready once all sub-PRs merge.
- Templates updated to target `develop`: `gh-issue-template` (branch target), `team-update-template` (Targeting line + wrap-up framing), `comment-style` (PR-ready example). `pr-template` is now consumed twice by `/dev-execute` — at draft-PR open (scope/plan framing) and at wrap-up (finished-work framing).

### Migration

- Plans written before 0.5.0 with `target_version: latest` still work: `/dev-execute` branches off `develop` regardless, and wrap-up 4.5 opens the PR fresh as Ready if no draft `pr_url` was recorded. Repos that still use a `version/x.y.z` sprint branch should run `dev-assistant strategies customize branching-strategy` and keep the v1.x flow in their per-repo override.

## [0.4.0] - 2026-06-10

Adds the refine phase (phase 0): the previously-unmodeled step where a thin ticket is thought through and rewritten before any gathering happens.

### Added

- **`/dev-refine <issue-id>`** — optional phase 0 for tickets that arrive without enough detail. Five sub-stages: **load** (fetch the ticket from Jira via the Atlassian MCP, paste fallback; scaffolds the issue workspace if it doesn't exist — refine is usually the first phase to touch a ticket), **exploration** (an intense open conversation: the real ask vs. the ticket's text, feasibility grounded in actual repo reads, 2–4 genuinely different candidate directions with trade-offs, scope edges, constraints), **narrowing** (chosen direction, alternatives set aside with honest reasons, surviving open questions — "split this ticket" and "don't do it" are valid outcomes), **rewrite proposal** (new title + description side-by-side with the originals, iterated to explicit approval), **apply + report** (updates the Jira title/description — the phase's only external write, gated on approval and skipped for experimental issues; syncs local `issue.md`; writes `refinement/report.md`). The GH issue is untouched — it is still created at `/dev-execute`. Model: Opus.
- `refinement/report.md` — extensive by design: original ticket verbatim, the exploration narrative, alternatives considered, decision rationale, refined ticket text, and open questions handed to gather. The only record of the refinement conversation.
- `/dev-gather` now lists the refinement report as a source candidate (proposed first when present), treats its decisions as settled unless reopened, seeds open questions from it, and skips Direct-input questions it already answers.
- `issue create` now scaffolds a `refinement/` phase folder; `issue show` reports its progress. Workspaces created before 0.4.0 show `refinement: [missing folder]`, which is harmless — `/dev-refine` is optional and writes create the folder on demand.

### Changed

- DESIGN.md: the lifecycle is now "five stages plus phase 0"; the deferred `/dev-issue-new` idea is superseded by `/dev-refine` sub-stage 1 (fetch from Jira → confirm → scaffold).

## [0.3.0] - 2026-06-03

Adds the reviewer side: reviewing *someone else's* PR, the mirror image of `/dev-feedback`.

### Added

- **`/dev-review <pr-number-or-url>`** — review a PR in five sub-phases: **gather** (PR description + linked GH issue + linked Jira ticket, then commits / diff / CI / checkout / blast radius, distilled into objectives), **brief + Q&A** (a plain-words `understanding.md`; three background Sonnet reviewers — correctness, tests, conventions — start immediately while the user asks questions; questions can become findings, corrections update the brief), **deep review** (the objective-coverage pass waits for the discussion and is informed by it — hybrid sequencing; findings merged, orchestrator-verified, classified with the `/dev-feedback` taxonomy extended with `blocking-objective` ranked above bugs), **select** (the user picks exactly which findings post — unselected findings never reach GitHub), **post** (everything submits atomically as one GitHub review: one notification, verdict chosen by the user). Read-only by design — no commits, no pushes; the only external write is the gated review submission. Re-invokable: later rounds review only the delta since `last_reviewed_sha`.
- CLI: `dev-assistant review create --pr <n> [--url] [--title] [--force]` and `review show --pr <n>` — reviewer-side counterparts of `issue create` / `issue show`. Workspaces live at `.dev-assistant/reviews/pr-<n>/` with one `round-NN/` folder per invocation (`context.md`, `understanding.md`, `findings.md`, `comments/`, `report.md`).
- `comment-style.md` strategy: review attribution footer — one line at the end of the review summary (never per-comment): *Drafted with dev-assistant · each comment human-approved*.
- `init` now scaffolds `reviews/` alongside `issues/`; `/dev-review` creates it on demand in repos initialized before 0.3.0.
- 5 new CLI tests (13 total).

## [0.2.0] - 2026-06-02

Adds an opt-in per-issue branching mode so large issues can land as several small PRs instead of one big one.

### Added

- **Sub-branches mode** — per-issue choice between `single-branch` (default, unchanged: subtasks land as commits on one `feat/<TICKET>-<slug>` branch, one PR at wrap-up) and `sub-branches` (each subtask gets its own `feat/<TICKET>-<slug>-sub-N` branch with a sub-PR targeting the parent feature branch, opened at subtask completion; the parent PR opens at wrap-up once all sub-PRs are merged). Decided in `/dev-plan` sub-stage 4, recorded as `branching_mode` in `plan.md` frontmatter; `/dev-plan` recommends `sub-branches` when the commit estimate pushes past the 8–10 band or subtasks are independently reviewable.
- `/dev-execute` sub-phase 3.8 (sub-branches mode only): at subtask completion — rebase onto the parent feature branch, push, open the sub-PR, optionally comment the link on the Jira subtask. All external ops individually confirmed. Starting subtask N+1 before sub-N's PR merges offers **wait** or **stack** (`stacked_on` recorded; untangled by rebase once the prior sub-PR merges).
- `/dev-feedback <issue-id> [subtask-n]` — review rounds can target a subtask's sub-PR; rounds are tracked per PR (`feedback/sub-<N>/round-NN/` vs `feedback/round-NN/` for the main PR).
- Wrap-up pre-flight (sub-branches mode) requires every sub-PR merged before the parent `feat → version` PR opens; the parent PR body lists the merged sub-PRs.

### Changed

- The ≤10 total-commit planning backstop is waived in `sub-branches` mode (each sub-PR is ≤3 commits by construction); exceeding it in `single-branch` mode now prompts a mode switch or issue split instead of failing.
- `branching-strategy.md` rule 2 clarified: "one Jira ticket = one GitHub issue" refers to the **parent** ticket — Jira subtasks never get their own GH issue or sprint-checklist item; in sub-branches mode they map to sub-branches/sub-PRs that all reference the same GH issue.
- `jira-subtask-template.md`: in sub-branches mode the sub-PR link may be added to the Jira subtask as a later comment (the description still carries no PR link at creation).

### Compatibility

- Plans written before 0.2.0 (no `branching_mode` field) are treated as `single-branch`.
- Experimental mode forces `single-branch` behavior (sub-PRs require external operations).

## [0.1.0] - 2026-05-25

Initial alpha release shared with invited collaborators for feedback.

### Phase commands

- Five Claude Code slash commands: `/dev-gather`, `/dev-plan`, `/dev-execute`, `/dev-feedback`, `/dev-evaluate`. One per stage, re-invokable, with per-phase output artifacts under `.dev-assistant/issues/<id>/`.

### CLI

- `dev-assistant` (Typer-based): `init`, `issue create / set-flag / archive / show`, `strategies show / customize`, `commands install`, `repo-context add / list / show / remove`.
- Repo-context pointer file (`.dev-assistant/repo-context.md`) listing the target repo's own rules documents; re-read on every phase invocation so the source of truth stays in the repo.
- Non-destructive `issue archive` — workspaces move to `.dev-assistant/archive/issues/<id>/` rather than being wiped.
- Experimental mode (`--experimental` at issue creation, or `issue set-flag` later) suppresses all external operations (Jira, GitHub, push, PR, comments).
- `init` adds `.dev-assistant/` to the target repo's `.git/info/exclude` so workspaces are never committed by the target repo.

### Strategy templates

- Eight customizable templates: branching, PR shape, comment style, GH issue template, Jira subtask template, team-update template, output style, process objectives. Per-repo customization via `dev-assistant strategies customize <name>`.

### Repository scaffolding

- Root docs: `LICENSE` placeholder (TBD), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (links to Contributor Covenant v2.1), `SECURITY.md`, this `CHANGELOG.md`.
- `.github/` metadata: bug-report and feature-request issue templates, PR template, CI workflow (ruff + pytest on Python 3.10 / 3.11 / 3.12 + build), Dependabot config (weekly pip + actions).
- `pyproject.toml`: authors, classifiers (`Development Status :: 3 - Alpha`), keywords, project URLs, `[dev]` extras (pytest, ruff, build), Ruff and pytest configuration.
- `tests/` with 8 CLI smoke tests via pytest + Typer's `CliRunner`.
