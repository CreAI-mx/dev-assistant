# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). While the project is in alpha (`0.x`), breaking changes may land in any minor version.

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
