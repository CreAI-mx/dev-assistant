"""Dev assistant CLI — Typer app and subcommands."""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

WORKSPACE_DIRNAME = ".dev-assistant"
WORKSPACE_SUBFOLDERS = ("issues", "reviews", "strategies", "lessons")
PHASE_SUBFOLDERS = ("refinement", "gathering", "plan", "execution", "evaluation")


class Autonomy(str, Enum):
    """How much user input the phase commands ask for on this issue.

    Controls the *approval* checkpoints only. Content questions (things only
    the user knows), the confirmation of external writes, and escalations
    (conflicts, failed criteria) fire at every level — see
    docs/interaction-map.md for the full map.
    """

    guided = "guided"
    balanced = "balanced"
    auto = "auto"


AUTONOMY_DEFAULT = Autonomy.balanced

AUTONOMY_SUMMARY = {
    Autonomy.guided: (
        "every checkpoint fires — each sub-stage approval, each external "
        "operation confirmed on its own"
    ),
    Autonomy.balanced: (
        "one approval checkpoint per phase, one batched confirmation for "
        "each phase's external operations"
    ),
    Autonomy.auto: (
        "no approval checkpoints — decisions are made and recorded in the "
        "phase report; external operations are still confirmed as one batch "
        "per phase"
    ),
}

app = typer.Typer(
    name="dev-assistant",
    help="Deterministic helper CLI for the dev-assistant slash commands.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)

issue_app = typer.Typer(
    help="Manage issue workspaces.",
    no_args_is_help=True,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)
app.add_typer(issue_app, name="issue")

review_app = typer.Typer(
    help="Manage PR review workspaces (reviewer side — someone else's PR).",
    no_args_is_help=True,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)
app.add_typer(review_app, name="review")

commands_app = typer.Typer(
    help="Manage the dev-assistant slash commands in the current repo.",
    no_args_is_help=True,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)
app.add_typer(commands_app, name="commands")

strategies_app = typer.Typer(
    help="Resolve and manage strategy files (per-repo overrides + source defaults).",
    no_args_is_help=True,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)
app.add_typer(strategies_app, name="strategies")

repo_context_app = typer.Typer(
    help="Manage the repo-context pointer file (.dev-assistant/repo-context.md).",
    no_args_is_help=True,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)
app.add_typer(repo_context_app, name="repo-context")


def _source_commands_dir() -> Path | None:
    """Locate the source `.claude/commands/` directory of this installed CLI.

    Works for editable installs where __file__ points back at the project
    source tree. Returns None if the directory can't be found (e.g. a
    non-editable install where __file__ is in site-packages).
    """
    # __file__ is .../src/dev_assistant/cli.py — repo root is three levels up.
    source_root = Path(__file__).resolve().parent.parent.parent
    candidate = source_root / ".claude" / "commands"
    return candidate if candidate.is_dir() else None


def _workspace_root(cwd: Path | None = None) -> Path:
    return (cwd or Path.cwd()) / WORKSPACE_DIRNAME


def _err(message: str) -> None:
    typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)


def _ok(message: str) -> None:
    typer.secho(message, fg=typer.colors.GREEN)


def _warn(message: str) -> None:
    typer.secho(message, fg=typer.colors.YELLOW)


def _ensure_excluded_from_git(repo_root: Path) -> bool:
    """Add WORKSPACE_DIRNAME/ to repo_root/.git/info/exclude if it's a git repo.

    Returns True if the exclude was applied (or already present), False if not
    a git repo.
    """
    git_dir = repo_root / ".git"
    if not git_dir.is_dir():
        return False
    exclude_file = git_dir / "info" / "exclude"
    exclude_file.parent.mkdir(parents=True, exist_ok=True)
    entry = f"{WORKSPACE_DIRNAME}/"
    if exclude_file.exists():
        existing_lines = exclude_file.read_text().splitlines()
        if entry in existing_lines:
            return True
        with exclude_file.open("a") as fh:
            if existing_lines and existing_lines[-1] != "":
                fh.write("\n")
            fh.write(f"{entry}\n")
    else:
        exclude_file.write_text(f"{entry}\n")
    return True


def _templates_dir() -> Path | None:
    """Locate the source `templates/` directory of this installed CLI."""
    source_root = Path(__file__).resolve().parent.parent.parent
    candidate = source_root / "templates"
    return candidate if candidate.is_dir() else None


@app.command()
def init(
    with_context: Annotated[
        list[str] | None,
        typer.Option(
            "--with-context",
            help=(
                "Repo-relative path to an existing rules document this repo expects "
                "dev-assistant to respect (e.g. data/README.md, CONTRIBUTING.md). "
                "Repeatable. Each path is added as a pointer in "
                ".dev-assistant/repo-context.md and re-read on every phase invocation. "
                "Paths are validated against the repo at init time."
            ),
        ),
    ] = None,
) -> None:
    """Scaffold the .dev-assistant/ workspace in the current directory.

    Strategy files are not seeded here — they're resolved at runtime via
    `dev-assistant strategies show <name>`, which falls back to the source
    default if the repo has no override. Run `dev-assistant strategies
    customize <name>` to opt in to per-repo customization.

    Use --with-context to register repo-specific rules documents at init time;
    you can also add or remove them later via `dev-assistant repo-context add /
    remove`.
    """
    cwd = Path.cwd()
    root = _workspace_root(cwd)
    if root.exists():
        _warn(f"{WORKSPACE_DIRNAME}/ already exists at {cwd} — nothing to do.")
        return

    for sub in WORKSPACE_SUBFOLDERS:
        (root / sub).mkdir(parents=True)

    excluded = _ensure_excluded_from_git(cwd)
    _ok(f"Initialized {WORKSPACE_DIRNAME}/ at {cwd}")
    if excluded:
        typer.echo(f"  added {WORKSPACE_DIRNAME}/ to .git/info/exclude")
    else:
        typer.echo("  (not a git repo — skipped git exclude)")

    if with_context:
        added, missing = _repo_context_seed(cwd, with_context)
        if added:
            typer.echo(
                f"  seeded repo-context.md with {len(added)} pointer(s): "
                f"{', '.join(added)}"
            )
        for path in missing:
            _warn(f"  --with-context path not found at {cwd / path} — skipped")


@issue_app.command("create")
def issue_create(
    issue_id: Annotated[
        str,
        typer.Option("--id", help="Issue identifier (e.g. Jira key 'PROJ-123' or slug)."),
    ],
    title: Annotated[
        str,
        typer.Option("--title", help="Short human-readable title for the issue."),
    ],
    description: Annotated[
        str | None,
        typer.Option("--description", help="Optional longer description."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite the issue folder if it already exists."),
    ] = False,
    experimental: Annotated[
        bool,
        typer.Option(
            "--experimental",
            help=(
                "Mark this issue as experimental. /dev-execute will skip all external "
                "operations (Jira subtask creation, GitHub issue creation, fetch, push, "
                "PR open, Jira comment) for this issue's lifecycle. Local artifacts "
                "are still produced normally. To flip an existing issue, edit "
                "the `experimental:` field in issue.md."
            ),
        ),
    ] = False,
    autonomy: Annotated[
        Autonomy,
        typer.Option(
            "--autonomy",
            help=(
                "How much input the phase commands ask for on this issue. "
                "'guided' fires every checkpoint (the pre-0.6 behavior); "
                "'balanced' (default) collapses each phase's approvals into "
                "one checkpoint and each phase's external operations into one "
                "batched confirmation; 'auto' drops the approval checkpoints "
                "entirely and records the decisions in the phase report. "
                "External writes are confirmed at every level. Change it later "
                "with `issue set-flag --autonomy`."
            ),
        ),
    ] = AUTONOMY_DEFAULT,
) -> None:
    """Create a new issue workspace with phase subfolders and metadata."""
    root = _workspace_root()
    if not root.is_dir():
        _err(
            f"{WORKSPACE_DIRNAME}/ not found in {Path.cwd()}. "
            f"Run `dev-assistant init` first."
        )
        raise typer.Exit(code=1)

    issue_dir = root / "issues" / issue_id
    if issue_dir.exists() and not force:
        _err(
            f"Issue '{issue_id}' already exists at {issue_dir}. "
            f"Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    if issue_dir.exists() and force:
        shutil.rmtree(issue_dir)

    issue_dir.mkdir(parents=True)
    for sub in PHASE_SUBFOLDERS:
        (issue_dir / sub).mkdir()

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    body = description.strip() if description else "_(no description provided)_"
    issue_md = (
        "---\n"
        f"id: {issue_id}\n"
        f"title: {title}\n"
        f"created: {created_at}\n"
        "status: active\n"
        f"experimental: {'true' if experimental else 'false'}\n"
        f"autonomy: {autonomy.value}\n"
        "---\n"
        "\n"
        "## Description\n"
        "\n"
        f"{body}\n"
    )
    (issue_dir / "issue.md").write_text(issue_md)

    _ok(f"Created issue '{issue_id}' at {issue_dir}")
    typer.echo(f"  autonomy: {autonomy.value} — {AUTONOMY_SUMMARY[autonomy]}")
    if experimental:
        typer.echo("  (experimental: external operations will be skipped during /dev-execute)")


@issue_app.command("set-flag")
def issue_set_flag(
    issue_id: Annotated[
        str,
        typer.Option("--id", help="Issue identifier."),
    ],
    experimental: Annotated[
        bool | None,
        typer.Option(
            "--experimental/--no-experimental",
            help=(
                "Set the experimental flag on this issue. When true, /dev-execute "
                "skips all external operations (Jira, GitHub, push, PR, comments) "
                "for this issue's lifecycle. Local artifacts are still produced "
                "normally."
            ),
        ),
    ] = None,
    autonomy: Annotated[
        Autonomy | None,
        typer.Option(
            "--autonomy",
            help=(
                "Set how much input the phase commands ask for on this issue: "
                "'guided' (every checkpoint), 'balanced' (one approval + one "
                "external batch per phase), or 'auto' (no approval checkpoints; "
                "external writes still confirmed as one batch per phase). Takes "
                "effect on the next phase invocation."
            ),
        ),
    ] = None,
) -> None:
    """Toggle flags on an existing issue's frontmatter.

    Supports `--experimental` / `--no-experimental` and `--autonomy`. Edits the
    issue.md file in place — inserts a field if absent, updates it if present.
    """
    if experimental is None and autonomy is None:
        _err(
            "No flag specified. Use --experimental / --no-experimental "
            "or --autonomy."
        )
        raise typer.Exit(code=1)

    root = _workspace_root()
    if not root.is_dir():
        _err(
            f"{WORKSPACE_DIRNAME}/ not found in {Path.cwd()}. "
            f"Run `dev-assistant init` first."
        )
        raise typer.Exit(code=1)

    issue_dir = root / "issues" / issue_id
    if not issue_dir.is_dir():
        _err(f"Issue '{issue_id}' not found at {issue_dir}.")
        raise typer.Exit(code=1)

    issue_md = issue_dir / "issue.md"
    if not issue_md.exists():
        _err(f"issue.md not found at {issue_md}.")
        raise typer.Exit(code=1)

    lines = issue_md.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        _err(f"issue.md at {issue_md} does not start with frontmatter (---).")
        raise typer.Exit(code=1)

    if not any(line.strip() == "---" for line in lines[1:]):
        _err(f"issue.md at {issue_md} has no closing frontmatter delimiter.")
        raise typer.Exit(code=1)

    if experimental is not None:
        lines = _set_frontmatter_field(
            lines, "experimental", "true" if experimental else "false"
        )
    if autonomy is not None:
        lines = _set_frontmatter_field(lines, "autonomy", autonomy.value)

    issue_md.write_text("\n".join(lines) + "\n")

    if experimental is not None:
        _ok(f"Set experimental={'true' if experimental else 'false'} on issue '{issue_id}'.")
        if experimental:
            typer.echo("  /dev-execute will skip all external operations for this issue.")
        else:
            typer.echo(
                "  /dev-execute will perform external operations normally "
                "(with per-op confirmations)."
            )
    if autonomy is not None:
        _ok(f"Set autonomy={autonomy.value} on issue '{issue_id}'.")
        typer.echo(f"  {AUTONOMY_SUMMARY[autonomy]}.")


def _set_frontmatter_field(lines: list[str], key: str, value: str) -> list[str]:
    """Set `key: value` inside the leading `---` frontmatter block.

    Updates the field in place when present, inserts it just before the closing
    delimiter when absent. Callers are responsible for having validated that the
    frontmatter block is well-formed.
    """
    lines = list(lines)
    closing_index = next(
        i for i in range(1, len(lines)) if lines[i].strip() == "---"
    )
    for i in range(1, closing_index):
        if lines[i].strip().startswith(f"{key}:"):
            lines[i] = f"{key}: {value}"
            return lines
    lines.insert(closing_index, f"{key}: {value}")
    return lines


@issue_app.command("archive")
def issue_archive(
    issue_id: Annotated[
        str,
        typer.Option("--id", help="Issue identifier to archive."),
    ],
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Replace an existing archive entry with the same id (otherwise refuse).",
        ),
    ] = False,
) -> None:
    """Move an issue workspace from issues/ to archive/issues/.

    Reversible (it's just a directory move). Updates issue.md frontmatter to
    record `status: archived` and `archived_at: <timestamp>`. Refuses if an
    archived entry with the same id already exists, unless --force is passed.
    """
    root = _workspace_root()
    if not root.is_dir():
        _err(
            f"{WORKSPACE_DIRNAME}/ not found in {Path.cwd()}. "
            f"Run `dev-assistant init` first."
        )
        raise typer.Exit(code=1)

    source = root / "issues" / issue_id
    if not source.is_dir():
        _err(f"Issue '{issue_id}' not found at {source}.")
        raise typer.Exit(code=1)

    archive_root = root / "archive" / "issues"
    target = archive_root / issue_id
    if target.exists():
        if not force:
            _err(
                f"Archive entry for '{issue_id}' already exists at {target}. "
                f"Use --force to overwrite."
            )
            raise typer.Exit(code=1)
        shutil.rmtree(target)

    archived_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    issue_md = source / "issue.md"
    if issue_md.exists():
        lines = issue_md.read_text().splitlines()
        if lines and lines[0].strip() == "---":
            closing_index = None
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    closing_index = i
                    break
            if closing_index is not None:
                status_index = None
                archived_index = None
                for i in range(1, closing_index):
                    stripped = lines[i].strip()
                    if stripped.startswith("status:") and status_index is None:
                        status_index = i
                    elif stripped.startswith("archived_at:") and archived_index is None:
                        archived_index = i
                if status_index is not None:
                    lines[status_index] = "status: archived"
                else:
                    lines.insert(closing_index, "status: archived")
                    closing_index += 1
                if archived_index is not None:
                    lines[archived_index] = f"archived_at: {archived_at}"
                else:
                    lines.insert(closing_index, f"archived_at: {archived_at}")
                issue_md.write_text("\n".join(lines) + "\n")

    archive_root.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))

    _ok(f"Archived '{issue_id}' to {target}")
    typer.echo("  (workspace moved; lessons in .dev-assistant/lessons/ are unaffected)")


def _resolve_autonomy(issue_md_text: str) -> tuple[Autonomy, str]:
    """Resolve the issue's autonomy level from its issue.md frontmatter.

    Issues created before the field existed resolve to `guided` — the behavior
    they were planned under — rather than to the current creation default.
    """
    for line in issue_md_text.splitlines():
        stripped = line.strip()
        if stripped == "---":
            continue
        if stripped.startswith("autonomy:"):
            raw = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            try:
                return Autonomy(raw), "from issue.md"
            except ValueError:
                return (
                    Autonomy.guided,
                    f"issue.md has an unrecognized value '{raw}' — falling back",
                )
    return Autonomy.guided, "field absent (pre-0.6 issue) — defaulting"


@issue_app.command("show")
def issue_show(
    issue_id: Annotated[
        str,
        typer.Option("--id", help="Issue identifier to inspect."),
    ],
) -> None:
    """Print the issue's metadata and phase progress.

    Designed to be called from slash commands to load context at the start of
    a phase. Output is plain markdown — the metadata frontmatter and body
    from issue.md, followed by a phase progress section.
    """
    root = _workspace_root()
    if not root.is_dir():
        _err(
            f"{WORKSPACE_DIRNAME}/ not found in {Path.cwd()}. "
            f"Run `dev-assistant init` first."
        )
        raise typer.Exit(code=1)

    issue_dir = root / "issues" / issue_id
    if not issue_dir.is_dir():
        _err(f"Issue '{issue_id}' not found at {issue_dir}.")
        raise typer.Exit(code=1)

    issue_md = issue_dir / "issue.md"
    if issue_md.exists():
        contents = issue_md.read_text()
        typer.echo(contents.rstrip("\n"))
    else:
        contents = ""
        typer.echo(f"(no issue.md at {issue_md})")

    level, source = _resolve_autonomy(contents)
    typer.echo()
    typer.echo("## Autonomy")
    typer.echo()
    typer.echo(f"- level: **{level.value}** ({source})")
    typer.echo(f"- meaning: {AUTONOMY_SUMMARY[level]}")
    typer.echo(
        "- unaffected at every level: content questions only the user can "
        "answer, confirmation of external writes, and escalations "
        "(conflicts, failing criteria, readiness blocks)"
    )

    typer.echo()
    typer.echo("## Phase progress")
    typer.echo()
    for phase in PHASE_SUBFOLDERS:
        phase_dir = issue_dir / phase
        if not phase_dir.is_dir():
            typer.echo(f"- {phase}: [missing folder]")
            continue
        files = sorted(p.name for p in phase_dir.iterdir() if p.is_file())
        if not files:
            typer.echo(f"- {phase}: [empty]")
        else:
            typer.echo(f"- {phase}: {', '.join(files)}")


@review_app.command("create")
def review_create(
    pr: Annotated[
        int,
        typer.Option("--pr", help="Pull request number on the current repo."),
    ],
    url: Annotated[
        str | None,
        typer.Option("--url", help="Full PR URL (recorded in review.md frontmatter)."),
    ] = None,
    title: Annotated[
        str | None,
        typer.Option("--title", help="PR title (recorded for quick identification)."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite the review folder if it already exists."),
    ] = False,
) -> None:
    """Create a PR review workspace at reviews/pr-<N>/.

    Reviewer-side counterpart of `issue create`: the workspace holds the
    artifacts /dev-review produces while reviewing someone else's PR. Round
    folders (round-NN/) are created by the slash command, not here.
    """
    root = _workspace_root()
    if not root.is_dir():
        _err(
            f"{WORKSPACE_DIRNAME}/ not found in {Path.cwd()}. "
            f"Run `dev-assistant init` first."
        )
        raise typer.Exit(code=1)

    review_dir = root / "reviews" / f"pr-{pr}"
    if review_dir.exists() and not force:
        _err(
            f"Review workspace for PR #{pr} already exists at {review_dir}. "
            f"Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    if review_dir.exists() and force:
        shutil.rmtree(review_dir)

    review_dir.mkdir(parents=True)

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    review_md = (
        "---\n"
        f"pr: {pr}\n"
        f"pr_url: {url or 'null'}\n"
        f"title: {title or 'null'}\n"
        f"created: {created_at}\n"
        "status: active\n"
        "last_reviewed_sha: null\n"
        "---\n"
        "\n"
        "## Review workspace\n"
        "\n"
        f"Artifacts for the review of PR #{pr}. One `round-NN/` folder per "
        "/dev-review invocation.\n"
    )
    (review_dir / "review.md").write_text(review_md)

    _ok(f"Created review workspace for PR #{pr} at {review_dir}")


@review_app.command("show")
def review_show(
    pr: Annotated[
        int,
        typer.Option("--pr", help="Pull request number to inspect."),
    ],
) -> None:
    """Print the review's metadata and round progress.

    Designed to be called from /dev-review to load context at the start of a
    round. Output is plain markdown — review.md verbatim, followed by a round
    progress section.
    """
    root = _workspace_root()
    if not root.is_dir():
        _err(
            f"{WORKSPACE_DIRNAME}/ not found in {Path.cwd()}. "
            f"Run `dev-assistant init` first."
        )
        raise typer.Exit(code=1)

    review_dir = root / "reviews" / f"pr-{pr}"
    if not review_dir.is_dir():
        _err(f"Review workspace for PR #{pr} not found at {review_dir}.")
        raise typer.Exit(code=1)

    review_md = review_dir / "review.md"
    if review_md.exists():
        typer.echo(review_md.read_text().rstrip("\n"))
    else:
        typer.echo(f"(no review.md at {review_md})")

    typer.echo()
    typer.echo("## Round progress")
    typer.echo()
    rounds = sorted(
        p for p in review_dir.iterdir() if p.is_dir() and p.name.startswith("round-")
    )
    if not rounds:
        typer.echo("- (no rounds yet)")
    for round_dir in rounds:
        files = sorted(p.name for p in round_dir.iterdir() if p.is_file())
        if not files:
            typer.echo(f"- {round_dir.name}: [empty]")
        else:
            typer.echo(f"- {round_dir.name}: {', '.join(files)}")


@strategies_app.command("show")
def strategies_show(
    name: Annotated[
        str,
        typer.Argument(help="Strategy name without .md extension, e.g. 'process-objectives'."),
    ],
) -> None:
    """Print the effective content of a strategy.

    Resolution order: per-repo override at .dev-assistant/strategies/<name>.md
    first, falling back to the source default at templates/<name>.md. Adds an
    HTML comment header noting which source was used.
    """
    filename = f"{name}.md"
    cwd = Path.cwd()
    override = cwd / WORKSPACE_DIRNAME / "strategies" / filename

    if override.is_file():
        typer.echo(f"<!-- source: override ({override}) -->")
        typer.echo(override.read_text().rstrip("\n"))
        return

    templates = _templates_dir()
    if templates is None:
        _err(
            "Could not locate the dev-assistant source templates/ directory. "
            "The CLI must be installed editable (e.g. `pip install -e <repo>`)."
        )
        raise typer.Exit(code=1)

    default = templates / filename
    if default.is_file():
        typer.echo(f"<!-- source: default ({default}) -->")
        typer.echo(default.read_text().rstrip("\n"))
        return

    _err(
        f"No strategy named '{name}' found. "
        f"Checked override at {override} and default at {default}."
    )
    raise typer.Exit(code=1)


@strategies_app.command("customize")
def strategies_customize(
    name: Annotated[
        str,
        typer.Argument(help="Strategy name to customize."),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite an existing override file."),
    ] = False,
) -> None:
    """Copy a source-default strategy into the per-repo workspace for editing.

    After this, the strategy resolves to the per-repo file. Delete the file
    to revert to the default.
    """
    filename = f"{name}.md"
    cwd = Path.cwd()
    root = _workspace_root(cwd)
    if not root.is_dir():
        _err(
            f"{WORKSPACE_DIRNAME}/ not found in {cwd}. "
            f"Run `dev-assistant init` first."
        )
        raise typer.Exit(code=1)

    templates = _templates_dir()
    if templates is None:
        _err("Could not locate the dev-assistant source templates/ directory.")
        raise typer.Exit(code=1)

    source = templates / filename
    if not source.is_file():
        _err(f"No template named '{name}' found at {source}.")
        raise typer.Exit(code=1)

    target = root / "strategies" / filename
    if target.exists() and not force:
        _err(
            f"Override already exists at {target}. Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    _ok(f"Copied default to {target}")
    typer.echo("  Edit this file to customize for this repo. Delete it to revert to the default.")


@commands_app.command("install")
def commands_install(
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Replace an existing .claude/commands target if it isn't already the right symlink.",
        ),
    ] = False,
) -> None:
    """Symlink the dev-assistant slash commands into the current repo.

    Creates `<cwd>/.claude/commands` as a symlink pointing back at the
    dev-assistant project's `.claude/commands/`. After running this, restart
    Claude Code in this directory and the `/dev-*` slash commands will appear.
    """
    source = _source_commands_dir()
    if source is None:
        _err(
            "Could not locate the dev-assistant source .claude/commands/ directory. "
            "The CLI must be installed editable (e.g. `pip install -e <repo>`)."
        )
        raise typer.Exit(code=1)

    cwd = Path.cwd()
    target_parent = cwd / ".claude"
    target = target_parent / "commands"
    target_parent.mkdir(exist_ok=True)

    if target.is_symlink():
        existing = target.readlink()
        if existing.resolve() == source.resolve():
            _ok(f"Already linked: {target} -> {source}")
            return
        if not force:
            _err(
                f"{target} is a symlink pointing to {existing}. "
                f"Use --force to replace."
            )
            raise typer.Exit(code=1)
        target.unlink()
    elif target.exists():
        if not force:
            _err(
                f"{target} already exists and is not a symlink. "
                f"Use --force to replace it with a symlink to the dev-assistant source."
            )
            raise typer.Exit(code=1)
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

    target.symlink_to(source)
    _ok(f"Linked {target} -> {source}")
    typer.echo("  (restart Claude Code in this directory to pick up the slash commands)")


REPO_CONTEXT_FILENAME = "repo-context.md"
_REPO_CONTEXT_PREAMBLE = """# Repo context

Pointers to rules this repo expects dev-assistant to respect. Every H2 below
is either a repo-relative file path (the file is inlined when read) or a
freeform section title (shown as-is). Re-read on every phase invocation, so
the referenced files stay current as they evolve.

Manage via `dev-assistant repo-context add / remove / list / show`.
"""


def _repo_context_path(cwd: Path | None = None) -> Path:
    return _workspace_root(cwd) / REPO_CONTEXT_FILENAME


def _repo_context_read(cwd: Path | None = None) -> str | None:
    path = _repo_context_path(cwd)
    if not path.exists():
        return None
    return path.read_text()


def _repo_context_write(text: str, cwd: Path | None = None) -> None:
    path = _repo_context_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text)


def _repo_context_entries(text: str) -> list[str]:
    """Return the H2 headers (without the leading `## ` marker), in order."""
    return [
        line[3:].strip()
        for line in text.splitlines()
        if line.startswith("## ")
    ]


def _repo_context_seed(cwd: Path, paths: list[str]) -> tuple[list[str], list[str]]:
    """Initialize repo-context.md with the given relative paths.

    Returns (added, missing). Paths that don't exist on disk are skipped and
    returned in `missing` — the caller surfaces a warning. Existing entries
    are de-duplicated.
    """
    added: list[str] = []
    missing: list[str] = []
    for raw in paths:
        rel = raw.strip()
        if not rel:
            continue
        if not (cwd / rel).exists():
            missing.append(rel)
            continue
        added.append(rel)

    if not added:
        return added, missing

    existing = _repo_context_read(cwd) or _REPO_CONTEXT_PREAMBLE
    existing_entries = set(_repo_context_entries(existing))
    new_entries = [p for p in added if p not in existing_entries]
    if not new_entries:
        return added, missing

    if not existing.endswith("\n"):
        existing += "\n"
    sections = [existing.rstrip() + "\n"]
    for path in new_entries:
        sections.append(f"\n## {path}\n\n_(no notes yet — `dev-assistant repo-context add {path} --note \"...\"` to annotate)_\n")
    _repo_context_write("".join(sections), cwd)
    return added, missing


@repo_context_app.command("show")
def repo_context_show() -> None:
    """Print the resolved repo-context: the pointer file plus inlined contents.

    For each H2 whose text resolves to an existing repo-relative file, the
    file's current content is inlined below the section. H2s that don't
    resolve are treated as freeform section titles and shown as-is. Output is
    designed to be loaded into a slash command's context block.
    """
    cwd = Path.cwd()
    text = _repo_context_read(cwd)
    if text is None:
        typer.echo("<!-- repo-context: no .dev-assistant/repo-context.md configured -->")
        typer.echo(
            "(No repo context configured. Run `dev-assistant repo-context add <path>` "
            "to register a rules document, or use `dev-assistant init --with-context "
            "<path>` at scaffold time.)"
        )
        return

    typer.echo(f"<!-- repo-context source: {_repo_context_path(cwd)} -->")
    typer.echo()

    lines = text.splitlines()
    out_buffer: list[str] = []
    pending_inline: Path | None = None
    pending_inline_label: str | None = None
    h2_re = re.compile(r"^##\s+(.+?)\s*$")

    def _flush_inline() -> None:
        nonlocal pending_inline, pending_inline_label
        if pending_inline is None:
            return
        if pending_inline.is_file():
            try:
                inlined = pending_inline.read_text()
            except OSError as exc:
                out_buffer.append(
                    f"\n<!-- inline error for {pending_inline_label}: {exc} -->\n"
                )
            else:
                out_buffer.append(
                    f"\n<!-- inlined from {pending_inline_label} (begins) -->\n"
                )
                out_buffer.append(inlined.rstrip("\n") + "\n")
                out_buffer.append(
                    f"<!-- inlined from {pending_inline_label} (ends) -->\n"
                )
        else:
            out_buffer.append(
                f"\n<!-- {pending_inline_label}: not a file in this repo — "
                f"treating as a freeform section title -->\n"
            )
        pending_inline = None
        pending_inline_label = None

    for line in lines:
        match = h2_re.match(line)
        if match:
            _flush_inline()
            out_buffer.append(line + "\n")
            candidate_label = match.group(1)
            candidate_path = cwd / candidate_label
            if candidate_path.is_file():
                pending_inline = candidate_path
                pending_inline_label = candidate_label
        else:
            out_buffer.append(line + "\n")

    _flush_inline()

    typer.echo("".join(out_buffer).rstrip("\n"))


@repo_context_app.command("list")
def repo_context_list() -> None:
    """List entries in repo-context.md, showing which resolve to a real file."""
    cwd = Path.cwd()
    text = _repo_context_read(cwd)
    if text is None:
        typer.echo("(no repo context configured)")
        return

    entries = _repo_context_entries(text)
    if not entries:
        typer.echo("(repo-context.md exists but contains no entries)")
        return

    for entry in entries:
        resolved = cwd / entry
        if resolved.is_file():
            typer.echo(f"  [file]     {entry}")
        elif resolved.exists():
            typer.echo(f"  [other]    {entry}  (path exists but is not a regular file)")
        elif "/" in entry or entry.endswith((".md", ".rst", ".txt")):
            typer.echo(f"  [MISSING]  {entry}  (looks like a path, but file not found)")
        else:
            typer.echo(f"  [section]  {entry}  (freeform title — no file resolution)")


@repo_context_app.command("add")
def repo_context_add(
    path: Annotated[
        str,
        typer.Argument(help="Repo-relative path to register (e.g. data/README.md)."),
    ],
    note: Annotated[
        str | None,
        typer.Option("--note", help="Short note to write under the entry."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Add the entry even if the target file doesn't exist yet.",
        ),
    ] = False,
) -> None:
    """Append a pointer to repo-context.md.

    Refuses if the target file doesn't exist, unless --force is passed (useful
    for intentional forward references). Creates repo-context.md with a
    standard preamble if it doesn't exist yet.
    """
    cwd = Path.cwd()
    root = _workspace_root(cwd)
    if not root.is_dir():
        _err(
            f"{WORKSPACE_DIRNAME}/ not found in {cwd}. "
            f"Run `dev-assistant init` first."
        )
        raise typer.Exit(code=1)

    target = cwd / path
    if not target.is_file() and not force:
        _err(
            f"Path '{path}' does not resolve to a file at {target}. "
            f"Use --force to add anyway."
        )
        raise typer.Exit(code=1)

    existing = _repo_context_read(cwd) or _REPO_CONTEXT_PREAMBLE
    existing_entries = _repo_context_entries(existing)
    if path in existing_entries:
        _warn(f"Entry '{path}' is already in repo-context.md — no change.")
        return

    if not existing.endswith("\n"):
        existing += "\n"
    body = note.strip() if note else "_(no notes yet)_"
    new_block = f"\n## {path}\n\n{body}\n"
    _repo_context_write(existing.rstrip() + "\n" + new_block, cwd)
    _ok(f"Added '{path}' to repo-context.md")


@repo_context_app.command("remove")
def repo_context_remove(
    path: Annotated[
        str,
        typer.Argument(help="Entry to remove (must match the H2 header verbatim)."),
    ],
) -> None:
    """Remove an entry (and its note section) from repo-context.md.

    Matches the H2 header text verbatim. The section runs from the matching
    `## <path>` line up to (but not including) the next `## ` line or end of
    file.
    """
    cwd = Path.cwd()
    text = _repo_context_read(cwd)
    if text is None:
        _err("No repo-context.md to remove from.")
        raise typer.Exit(code=1)

    lines = text.splitlines()
    target_header = f"## {path}"
    start = None
    for i, line in enumerate(lines):
        if line.rstrip() == target_header:
            start = i
            break
    if start is None:
        _err(f"Entry '{path}' not found in repo-context.md.")
        raise typer.Exit(code=1)

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break

    while start > 0 and lines[start - 1].strip() == "":
        start -= 1

    new_lines = lines[:start] + lines[end:]
    _repo_context_write("\n".join(new_lines).rstrip() + "\n", cwd)
    _ok(f"Removed '{path}' from repo-context.md")


@app.command("tui")
def tui(
    path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            help="Directory whose .dev-assistant/ workspace to open. "
            "Defaults to the current directory (searching parents).",
        ),
    ] = None,
) -> None:
    """Launch the read-only terminal dashboard for the workspace.

    Browse issues, phase progress, reviews and lessons, and read any artifact
    rendered as markdown — without leaving the terminal. Requires the optional
    `tui` extra: `pip install 'dev-assistant[tui]'`.
    """
    from dev_assistant.tui.model import find_workspace

    if path is not None:
        root = (path / WORKSPACE_DIRNAME) if path.name != WORKSPACE_DIRNAME else path
        if not root.is_dir():
            _err(f"{WORKSPACE_DIRNAME}/ not found under {path}.")
            raise typer.Exit(code=1)
    else:
        root = find_workspace()
        if root is None:
            _err(
                f"No {WORKSPACE_DIRNAME}/ found here or in any parent directory. "
                f"Run `dev-assistant init` first, or pass --path."
            )
            raise typer.Exit(code=1)

    from dev_assistant.tui import run as run_tui

    try:
        run_tui(root)
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        _err(
            "The dashboard requires the 'tui' extra. Install it with: "
            "pip install 'dev-assistant[tui]'"
        )
        _err(f"(import error: {exc})")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
