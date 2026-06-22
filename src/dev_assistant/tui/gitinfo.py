"""Read-only local git introspection for the target repo.

Shells out to a handful of fast, side-effect-free git commands. Everything is
best-effort: a missing git binary, a non-repo directory, or a slow command all
degrade to `is_repo=False` rather than raising. No network, no writes.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

_TIMEOUT = 4


def _run(args: list[str], cwd: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


@dataclass
class GitInfo:
    is_repo: bool = False
    current_branch: str | None = None
    dirty_count: int = 0
    untracked_count: int = 0
    branches: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return self.dirty_count == 0 and self.untracked_count == 0

    def branches_for(self, issue_id: str) -> list[str]:
        return [b for b in self.branches if issue_id and issue_id in b]

    def sub_branches_for(self, branch_name: str | None) -> list[str]:
        """Sub-branches of a feature branch (named `<branch>-sub-N`)."""
        if not branch_name:
            return []
        prefix = f"{branch_name}-sub-"
        return sorted(b for b in self.branches if b.startswith(prefix))

    def has_branch(self, branch_name: str | None) -> bool:
        return bool(branch_name) and branch_name in self.branches


def load_git_info(repo_root: Path) -> GitInfo:
    if _run(["rev-parse", "--is-inside-work-tree"], repo_root) != "true":
        return GitInfo(is_repo=False)

    branch = _run(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)

    status = _run(["status", "--porcelain"], repo_root) or ""
    dirty = untracked = 0
    for line in status.splitlines():
        if line.startswith("??"):
            untracked += 1
        elif line.strip():
            dirty += 1

    branches_raw = _run(["branch", "--format=%(refname:short)"], repo_root) or ""
    branches = [b.strip() for b in branches_raw.splitlines() if b.strip()]

    return GitInfo(
        is_repo=True,
        current_branch=branch,
        dirty_count=dirty,
        untracked_count=untracked,
        branches=branches,
    )
