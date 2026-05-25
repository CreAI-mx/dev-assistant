# Contributing

dev-assistant is in **alpha**. APIs, CLI flags, and slash-command behavior may change without notice. The codebase is small and the maintainer is one person — expect direct, opinionated feedback on PRs.

## Ground rules

- This is a CreAI-owned project; see [LICENSE](LICENSE) for the current rights status.
- Open an issue before starting non-trivial work. A 5-minute conversation saves a wasted afternoon.
- Keep PRs small and scoped to one concern. If you need more than three description bullets to explain it, split it.

## Local setup

Requires Python ≥ 3.10. Recommended path uses `pipx`; on Debian/Ubuntu without pipx see the README for the `--break-system-packages` workaround.

```bash
git clone <repo-url>
cd dev-assistant
python3 -m pip install --user -e ".[dev]"
```

The `-e` flag means edits to source apply immediately. `[dev]` pulls in `pytest`, `ruff`, and `build`.

## Day-to-day commands

```bash
ruff check .           # lint
ruff format .          # format
pytest                 # run tests
python -m build        # build wheel + sdist (sanity check)
dev-assistant --help   # smoke-test the CLI
```

CI runs the same `ruff check` and `pytest` on Python 3.10, 3.11, and 3.12 — make sure both pass locally before pushing.

## Filing issues

Use the issue templates under `.github/ISSUE_TEMPLATE/`:

- **Bug report** — something does the wrong thing. Include the command you ran, expected vs. actual behavior, and your Python version.
- **Feature request** — something missing. Describe the problem first, then your proposed solution. Link to the relevant phase (gather / plan / execute / feedback / evaluate) where it applies.

## Pull requests

Title format: `[<TICKET>] <imperative summary>` when there's a ticket, otherwise `<imperative summary>`. The PR template (`.github/PULL_REQUEST_TEMPLATE.md`) walks you through the rest.

Conventional commits on the branch (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) — these flow into the changelog.

## Scope

The project covers the five phases of a dev task: gather → plan → execute → feedback → evaluate. See [DESIGN.md](DESIGN.md) for the architecture and [IDEAS.md](IDEAS.md) for the deferred / next-up list. Proposals outside the five-phase model are welcome but expect more discussion before code.

## Code of conduct

By participating you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
