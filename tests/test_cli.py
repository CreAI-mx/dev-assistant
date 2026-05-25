"""Smoke tests for the dev-assistant CLI.

These tests verify that the top-level command help works and that the
init / issue create / issue archive flow produces the expected workspace
layout on disk. They use Typer's CliRunner so no subprocess is needed.
"""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dev_assistant.cli import WORKSPACE_DIRNAME, app


def test_help_lists_top_level_commands(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    output = result.stdout
    for expected in ("init", "issue", "commands", "strategies", "repo-context"):
        assert expected in output, f"expected '{expected}' in --help output:\n{output}"


def test_issue_help_lists_subcommands(runner: CliRunner) -> None:
    result = runner.invoke(app, ["issue", "--help"])
    assert result.exit_code == 0
    for expected in ("create", "set-flag", "archive", "show"):
        assert expected in result.stdout


def test_init_creates_workspace(runner: CliRunner, chdir_tmp: Path) -> None:
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.stdout + result.stderr

    workspace = chdir_tmp / WORKSPACE_DIRNAME
    assert workspace.is_dir()
    for sub in ("issues", "strategies", "lessons"):
        assert (workspace / sub).is_dir(), f"missing workspace subfolder: {sub}"


def test_init_is_idempotent(runner: CliRunner, chdir_tmp: Path) -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "already exists" in result.stdout


def test_issue_create_without_init_fails(runner: CliRunner, chdir_tmp: Path) -> None:
    result = runner.invoke(
        app, ["issue", "create", "--id", "FOO-1", "--title", "First"]
    )
    assert result.exit_code == 1
    assert "init" in (result.stderr + result.stdout)


def test_issue_create_produces_phase_folders_and_metadata(
    runner: CliRunner, chdir_tmp: Path
) -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(
        app,
        [
            "issue",
            "create",
            "--id",
            "FOO-1",
            "--title",
            "First issue",
            "--description",
            "Reproduce the bug.",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr

    issue_dir = chdir_tmp / WORKSPACE_DIRNAME / "issues" / "FOO-1"
    assert issue_dir.is_dir()
    for phase in ("gathering", "plan", "execution", "evaluation"):
        assert (issue_dir / phase).is_dir(), f"missing phase folder: {phase}"

    issue_md = (issue_dir / "issue.md").read_text()
    assert "id: FOO-1" in issue_md
    assert "title: First issue" in issue_md
    assert "experimental: false" in issue_md
    assert "Reproduce the bug." in issue_md


def test_experimental_flag_recorded(runner: CliRunner, chdir_tmp: Path) -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(
        app,
        [
            "issue",
            "create",
            "--id",
            "EXP-1",
            "--title",
            "Sandbox",
            "--experimental",
        ],
    )
    assert result.exit_code == 0
    issue_md = (
        chdir_tmp / WORKSPACE_DIRNAME / "issues" / "EXP-1" / "issue.md"
    ).read_text()
    assert "experimental: true" in issue_md


def test_issue_archive_moves_workspace(runner: CliRunner, chdir_tmp: Path) -> None:
    runner.invoke(app, ["init"])
    runner.invoke(app, ["issue", "create", "--id", "FOO-1", "--title", "First"])

    result = runner.invoke(app, ["issue", "archive", "--id", "FOO-1"])
    assert result.exit_code == 0, result.stdout + result.stderr

    source = chdir_tmp / WORKSPACE_DIRNAME / "issues" / "FOO-1"
    target = chdir_tmp / WORKSPACE_DIRNAME / "archive" / "issues" / "FOO-1"
    assert not source.exists(), "source workspace should have been moved"
    assert target.is_dir(), "archived workspace should exist at archive path"

    archived_md = (target / "issue.md").read_text()
    assert "status: archived" in archived_md
    assert "archived_at:" in archived_md
