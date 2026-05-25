"""Shared pytest fixtures for dev-assistant tests."""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dev_assistant.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli_app():
    return app


@pytest.fixture
def chdir_tmp(tmp_path: Path) -> Iterator[Path]:
    """Run the test with cwd set to a fresh tmp_path."""
    prev = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(prev)
