# dev-assistant

[![Status: alpha](https://img.shields.io/badge/status-alpha-orange)](#project-status)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: TBD](https://img.shields.io/badge/license-TBD-lightgrey)](LICENSE)

> 🚧 **Alpha — APIs, CLI flags, and slash-command behavior may change without notice.**
> Single-user origin, now opening up to invited collaborators for feedback. Not for production use.

An AI-powered developer assistant. Standardizes how dev work moves through five stages: **gather → plan → execute → feedback → evaluate**. Two layers: a Python CLI for deterministic helpers, and Claude Code slash commands that drive the reasoning per phase.

See [DESIGN.md](DESIGN.md) for the architecture and rationale, and [IDEAS.md](IDEAS.md) for the deferred / next-up list.

## Quick start

```bash
# In any repo you want to use the assistant in:
dev-assistant init --with-context CONTRIBUTING.md  # optional: point at repo rules docs

# Wire the slash commands into this repo (creates a symlink in .claude/commands/)
dev-assistant commands install

# Create an issue workspace
dev-assistant issue create --id PROJ-123 --title "Refactor payments"
```

Then in Claude Code, walk the phases:

```
/dev-gather PROJ-123     # collect context → gathering/objectives.md
/dev-plan PROJ-123       # decompose into subtasks → plan/plan.md
/dev-execute PROJ-123    # implement one subtask per invocation; wrap-up opens the PR
/dev-feedback PROJ-123   # one round of PR review iteration per invocation
/dev-evaluate PROJ-123   # retro + lessons + close out externally
```

For experimental / sandbox work, add `--experimental` at `issue create` time to skip all external operations (no Jira, no GitHub, no PR).

`init` adds `.dev-assistant/` to the target repo's `.git/info/exclude` so the workspace folder is never committed.

## How it works

Five phase commands, each producing artifacts under `.dev-assistant/issues/<id>/`:

| Phase | Slash command | Primary outputs |
|---|---|---|
| Gather | `/dev-gather` | `gathering/report.md`, `gathering/objectives.md` |
| Plan | `/dev-plan` | `plan/plan.md`, `plan/report.md` |
| Execute | `/dev-execute` | Code commits, PR (one subtask per invocation, then wrap-up) |
| Feedback | `/dev-feedback` | One round of PR review iteration per invocation |
| Evaluate | `/dev-evaluate` | Retro + lessons + close-out + optional non-destructive archive |

Customizable per repo via `dev-assistant strategies customize <name>` for branching, PR template, comment style, etc. Repo-owned rules documents are pointed at via `.dev-assistant/repo-context.md` and re-read on every phase invocation so the source of truth stays in the target repo.

## Install

Requires Python ≥ 3.10.

### Recommended: pipx (when available)

```bash
pipx install -e /path/to/this/repo
```

The `-e` flag makes it an editable install — edits to the source apply immediately, no reinstall needed.

### On Debian/Ubuntu without pipx

If `pipx` isn't installed and `apt install pipx` isn't an option right now, you can install at user level with pip directly. Because Debian/Ubuntu mark the system Python as externally-managed (PEP 668), you'll need `--break-system-packages`. This only affects your user site, not system Python:

```bash
# One-time pip bootstrap if pip isn't available either
curl -sS https://bootstrap.pypa.io/get-pip.py | python3 - --user --break-system-packages

# Install dev-assistant editable
python3 -m pip install --user --break-system-packages -e /path/to/this/repo
```

Make sure `~/.local/bin` is on your `PATH` (it usually is on modern Ubuntu).

### Development install

For contributors — installs the `[dev]` extras (pytest, ruff, build):

```bash
python3 -m pip install --user -e ".[dev]"
```

## Project status

This project is in **alpha** (`0.x`). Treat it as a working prototype, not a stable tool. Specifically:

- **No backwards-compatibility guarantees.** Flags, command names, and on-disk artifacts may change between minor versions.
- **Single-user origins.** Battle-tested for one developer's workflow. Edge cases for team scenarios are not yet handled.
- **Local-only.** No telemetry, no remote services owned by this project. External calls (Jira, GitHub) go through your existing credentials.
- **License pending.** See [LICENSE](LICENSE). Currently all rights reserved; a formal license will be added in a future release.

What's next: see [IDEAS.md](IDEAS.md) and the open issues.

## Contributing

External contributors welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for setup, dev commands, and PR conventions. Please read the [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

To report a security concern privately, see [SECURITY.md](SECURITY.md).

## Releases

See [CHANGELOG.md](CHANGELOG.md) for the version history and what landed in each release.

## License

See [LICENSE](LICENSE). Currently no license is granted; the repository is shared in alpha for evaluation by invited collaborators only.
