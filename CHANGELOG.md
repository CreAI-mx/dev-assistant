# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). While the project is in alpha (`0.x`), breaking changes may land in any minor version.

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
