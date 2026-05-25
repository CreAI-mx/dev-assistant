# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). While the project is in alpha (`0.x`), breaking changes may land in any minor version.

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
