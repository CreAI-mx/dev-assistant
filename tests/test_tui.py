"""Tests for the read-only TUI: workspace scanning, derived metrics, rendering.

The model and render layers are pure and tested directly. The Textual app gets
a headless smoke test via Pilot (skipped if textual is not installed)."""
from __future__ import annotations

from pathlib import Path

import pytest

from dev_assistant.tui import model, render


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A `.dev-assistant/` workspace with two active issues, one archived,
    one review and one lesson — exercising every branch of the scanner."""
    root = tmp_path / "myrepo" / ".dev-assistant"

    # Issue 1: in execution phase (refine→gather→plan→execution have content).
    i1 = root / "issues" / "PROJ-1"
    _write(
        i1 / "issue.md",
        "---\nid: PROJ-1\ntitle: First issue\n"
        "created: 2026-06-10T10:00:00+00:00\nstatus: active\nexperimental: false\n---\n\n"
        "## Description\n\nDo the thing.\n",
    )
    for phase in ("refinement", "gathering", "plan", "execution", "evaluation"):
        (i1 / phase).mkdir(parents=True)
    _write(i1 / "refinement" / "report.md", "# refine\n")
    _write(i1 / "gathering" / "objectives.md", "# objs\n")
    _write(i1 / "plan" / "plan.md", "# plan\n")
    _write(i1 / "execution" / "notes.md", "# exec\n")

    # Issue 2: experimental, only gathering done.
    i2 = root / "issues" / "PROJ-2"
    _write(
        i2 / "issue.md",
        "---\nid: PROJ-2\ntitle: Second [bracketed] issue\n"
        "created: 2026-06-20T10:00:00+00:00\nstatus: active\nexperimental: true\n---\n\n"
        "## Description\n\nExperimental work.\n",
    )
    for phase in ("refinement", "gathering", "plan", "execution", "evaluation"):
        (i2 / phase).mkdir(parents=True)
    _write(i2 / "gathering" / "objectives.md", "# objs\n")

    # Archived issue, fully complete.
    a1 = root / "archive" / "issues" / "PROJ-0"
    _write(
        a1 / "issue.md",
        "---\nid: PROJ-0\ntitle: Old issue\n"
        "created: 2026-05-01T10:00:00+00:00\nstatus: archived\nexperimental: false\n---\n\n"
        "## Description\n\nDone long ago.\n",
    )
    for phase in ("refinement", "gathering", "plan", "execution", "evaluation"):
        d = a1 / phase
        d.mkdir(parents=True)
        _write(d / "x.md", "# x\n")

    # A review with two rounds.
    rv = root / "reviews" / "pr-42"
    _write(
        rv / "review.md",
        "---\npr: 42\npr_url: https://github.com/x/y/pull/42\n"
        "last_reviewed_sha: abc123\nlast_verdict: approve\nstatus: active\n---\n",
    )
    _write(rv / "round-01" / "context.md", "# ctx\n")
    _write(rv / "round-02" / "comments" / "f1.md", "# finding\n")
    _write(rv / "round-02" / "comments" / "summary.md", "# summary\n")

    # A lesson.
    _write(root / "lessons" / "2026-06-01-proj-0-thing.md", "# lesson\n")

    # repo-context + a custom strategy.
    _write(root / "repo-context.md", "# context\n")
    _write(root / "strategies" / "branching-strategy.md", "# custom\n")

    return root


# --- frontmatter --------------------------------------------------------------


def test_parse_frontmatter_basic():
    meta, body = model.parse_frontmatter("---\nid: X\ntitle: Hi\n---\n\nBody text\n")
    assert meta == {"id": "X", "title": "Hi"}
    assert body == "Body text"


def test_parse_frontmatter_no_fence():
    meta, body = model.parse_frontmatter("just text\nmore")
    assert meta == {}
    assert body == "just text\nmore"


def test_parse_frontmatter_unclosed():
    meta, body = model.parse_frontmatter("---\nid: X\nno closing fence")
    assert meta == {}  # treated as malformed → whole thing is body


def test_parse_frontmatter_value_with_colon():
    meta, _ = model.parse_frontmatter("---\nurl: https://example.com/x\n---\n")
    assert meta["url"] == "https://example.com/x"


# --- humanize -----------------------------------------------------------------


def test_humanize_age_none():
    assert model.humanize_age(None) == "—"


@pytest.mark.parametrize(
    "seconds,expected",
    [(30, "just now"), (120, "2m"), (3 * 3600, "3h"), (3 * 86400, "3d")],
)
def test_humanize_age_buckets(seconds, expected):
    from datetime import datetime, timedelta, timezone

    ref = datetime(2026, 6, 22, tzinfo=timezone.utc)
    dt = ref - timedelta(seconds=seconds)
    assert model.humanize_age(dt, ref=ref) == expected


# --- workspace scanning -------------------------------------------------------


def test_load_workspace_counts(workspace):
    ws = model.load_workspace(workspace)
    assert ws.repo_name == "myrepo"
    assert len(ws.active_issues) == 2
    assert len(ws.archived_issues) == 1
    assert len(ws.reviews) == 1
    assert ws.lessons == ["2026-06-01-proj-0-thing.md"]
    assert ws.has_repo_context is True
    assert ws.custom_strategies == ["branching-strategy"]


def test_issue_progress(workspace):
    ws = model.load_workspace(workspace)
    by_id = {i.id: i for i in ws.active_issues}

    p1 = by_id["PROJ-1"]
    assert p1.completed_count == 4
    assert p1.current_phase.name == "execution"
    assert p1.next_phase.name == "evaluation"
    assert p1.is_complete is False
    assert p1.experimental is False

    p2 = by_id["PROJ-2"]
    assert p2.completed_count == 1
    assert p2.current_phase.name == "gathering"
    assert p2.experimental is True


def test_archived_issue_complete(workspace):
    ws = model.load_workspace(workspace)
    arch = ws.archived_issues[0]
    assert arch.id == "PROJ-0"
    assert arch.is_complete is True
    assert arch.next_phase is None


def test_phase_distribution(workspace):
    ws = model.load_workspace(workspace)
    dist = ws.phase_distribution
    assert dist["execution"] == 1
    assert dist["gathering"] == 1
    assert dist["complete"] == 0  # both active issues are mid-pipeline


def test_review_scan(workspace):
    ws = model.load_workspace(workspace)
    rv = ws.reviews[0]
    assert rv.pr == "42"
    assert rv.rounds == 2
    assert rv.last_verdict == "approve"
    # summary.md excluded from the comment count.
    assert rv.latest_round_comments == 1


def test_time_in_phase_uses_mtime(workspace):
    ws = model.load_workspace(workspace)
    p1 = {i.id: i for i in ws.active_issues}["PROJ-1"]
    # current phase is execution; its file mtime anchors time-in-phase.
    assert p1.current_phase.last_modified is not None


def test_find_workspace_walks_parents(workspace, tmp_path):
    nested = workspace.parent / "src" / "deep"
    nested.mkdir(parents=True)
    found = model.find_workspace(nested)
    assert found == workspace.resolve()


def test_find_workspace_none(tmp_path):
    assert model.find_workspace(tmp_path) is None


# --- rendering ----------------------------------------------------------------


def test_render_overview(workspace):
    ws = model.load_workspace(workspace)
    out = render.render_overview(ws)
    assert "myrepo — dev-assistant workspace" in out
    assert "PROJ-1" in out
    assert "PROJ-2" in out
    assert "pr-42" in out
    assert "⚗️" in out  # experimental flag on PROJ-2


def test_render_issue(workspace):
    ws = model.load_workspace(workspace)
    p1 = {i.id: i for i in ws.active_issues}["PROJ-1"]
    out = render.render_issue(p1)
    assert "PROJ-1 — First issue" in out
    assert "current: **execution**" in out
    assert "█" in out  # progress bar


def test_render_review(workspace):
    ws = model.load_workspace(workspace)
    out = render.render_review(ws.reviews[0])
    assert "PR #42 review" in out
    assert "approve" in out


def test_progress_bar():
    assert render.progress_bar(3, 5) == "███░░"
    assert render.progress_bar(0, 5) == "░░░░░"
    assert render.progress_bar(5, 5) == "█████"


# --- app smoke test (headless) ------------------------------------------------


def test_app_boots(workspace):
    pytest.importorskip("textual")
    import asyncio

    from dev_assistant.tui.app import DashboardApp

    async def scenario():
        app = DashboardApp(workspace)
        async with app.run_test() as pilot:
            await pilot.pause()
            # Overview should render on mount.
            detail = app.query_one("#detail")
            assert "dev-assistant workspace" in detail.source
            # Refresh action should not raise.
            await pilot.press("r")
            await pilot.pause()

    asyncio.run(scenario())
