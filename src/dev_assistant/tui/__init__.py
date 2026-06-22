"""Read-only terminal dashboard for dev-assistant workspaces."""
from __future__ import annotations

from pathlib import Path


def run(workspace_root: Path) -> None:
    """Launch the dashboard. Imports Textual lazily so the core CLI does not
    require it unless the dashboard is actually used."""
    from .app import run as _run

    _run(workspace_root)
