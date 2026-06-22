"""Tests for the read-only TUI: workspace scanning, derived state, rendering.

The model and render layers are pure and tested directly. The Textual app gets
a headless smoke test via Pilot."""
from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from dev_assistant.tui import gitinfo, model, render


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _rtext(renderable, width: int = 100) -> str:
    """Render a Rich renderable to plain text for assertions."""
    con = Console(width=width, force_terminal=False, no_color=True)
    with con.capture() as cap:
        con.print(renderable)
    return cap.get()


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A `.dev-assistant/` workspace mirroring real phase shapes: execution as
    numbered subtask folders, feedback as sub-N/round-NN folders, a plan.md with
    rich frontmatter, a review with two rounds, lessons + strategy override."""
    root = tmp_path / "myrepo" / ".dev-assistant"

    # Issue 1 — in feedback phase, sub-branches mode.
    i1 = root / "issues" / "VN-1"
    _write(
        i1 / "issue.md",
        "---\nid: VN-1\ntitle: '\"Quoted\" title'\n"
        "created: 2026-06-10T10:00:00+00:00\nstatus: active\nexperimental: false\n---\n\n"
        "## Description\n\nDo the thing.\n",
    )
    _write(i1 / "refinement" / "report.md", "# refine\n")
    _write(i1 / "gathering" / "objectives.md", "# objs\n")
    _write(
        i1 / "plan" / "plan.md",
        "---\nissue: VN-1\nbranching_mode: sub-branches\ntotal_subtasks: 2\n"
        "total_commits: 5\nbranch_name: feat/VN-1-thing\nbranch_created: true\n"
        "target_branch: develop\npr_url: https://github.com/x/y/pull/10\npr_state: draft\n"
        "gh_issue_created: false\nreview_groups:\n  - sub-1: [01]\n  - sub-2: [02]\n"
        "last_feedback_round: sub-2/01\n---\n\n# Plan\n",
    )
    _write(i1 / "execution" / "01-scaffold" / "impl-plan.md", "# 01\n")
    _write(i1 / "execution" / "01-scaffold" / "execution-notes.md", "# notes\n")
    _write(i1 / "execution" / "02-algo" / "impl-plan.md", "# 02\n")
    _write(i1 / "feedback" / "sub-1" / "round-01" / "report.md", "# r1\n")
    _write(i1 / "feedback" / "sub-1" / "round-02" / "report.md", "# r2\n")
    _write(i1 / "feedback" / "sub-2" / "round-01" / "report.md", "# r1\n")
    (i1 / "evaluation").mkdir()

    # Issue 2 — only gathering done, experimental.
    i2 = root / "issues" / "VN-2"
    _write(
        i2 / "issue.md",
        "---\nid: VN-2\ntitle: Second\n"
        "created: 2026-06-20T10:00:00+00:00\nstatus: active\nexperimental: true\n---\n\nDesc\n",
    )
    _write(i2 / "gathering" / "objectives.md", "# o\n")
    for ph in ("refinement", "plan", "execution", "feedback", "evaluation"):
        (i2 / ph).mkdir(parents=True)

    # Archived issue — fully complete (evaluation has content).
    a1 = root / "archive" / "issues" / "VN-0"
    _write(
        a1 / "issue.md",
        "---\nid: VN-0\ntitle: Old\ncreated: 2026-05-01T10:00:00+00:00\n"
        "status: archived\nexperimental: false\n---\n\nDone.\n",
    )
    for ph in ("refinement", "gathering", "plan", "execution", "feedback", "evaluation"):
        _write(a1 / ph / "x.md", "# x\n")

    # Review with two rounds (3 comments total; summary.md excluded).
    rv = root / "reviews" / "pr-50"
    _write(
        rv / "review.md",
        "---\npr: 50\npr_url: https://github.com/x/y/pull/50\ntitle: A review\n"
        "last_verdict: APPROVE\nstatus: active\n---\n",
    )
    _write(rv / "round-01" / "comments" / "f1.md", "#\n")
    _write(rv / "round-01" / "comments" / "f2.md", "#\n")
    _write(rv / "round-01" / "comments" / "summary.md", "#\n")
    _write(rv / "round-01" / "report.md", "#\n")
    _write(rv / "round-02" / "comments" / "f3.md", "#\n")

    _write(root / "lessons" / "2026-06-01-vn-0-thing.md", "# lesson\n")
    _write(root / "repo-context.md", "# context\n")
    _write(root / "strategies" / "branching-strategy.md", "# custom\n")
    return root


# --- frontmatter --------------------------------------------------------------


def test_parse_frontmatter_skips_nested_lists():
    text = "---\nkey: val\nreview_groups:\n  - sub-1: [01]\n  - sub-2: [02]\nother: x\n---\nbody\n"
    meta, body = model.parse_frontmatter(text)
    assert meta == {"key": "val", "review_groups": "", "other": "x"}
    assert body == "body"


def test_clean_strips_matching_quote_pair():
    meta, _ = model.parse_frontmatter("---\ntitle: '\"Apply\" Strategy'\n---\n")
    # Outer single-quote pair removed; inner double quotes preserved.
    assert model._clean(meta["title"]) == '"Apply" Strategy'


def test_parse_dt_handles_null_and_z():
    assert model._parse_dt("null") is None
    assert model._parse_dt("2026-06-22T17:10:41Z") is not None


# --- humanize -----------------------------------------------------------------


@pytest.mark.parametrize(
    "seconds,expected",
    [(30, "just now"), (120, "2m"), (3 * 3600, "3h"), (3 * 86400, "3d")],
)
def test_humanize_age_buckets(seconds, expected):
    from datetime import datetime, timedelta, timezone

    ref = datetime(2026, 6, 22, tzinfo=timezone.utc)
    assert model.humanize_age(ref - timedelta(seconds=seconds), ref=ref) == expected


# --- scanning -----------------------------------------------------------------


def test_load_workspace_counts(workspace):
    ws = model.load_workspace(workspace)
    assert ws.repo_name == "myrepo"
    assert ws.repo_root == workspace.parent
    assert len(ws.active_issues) == 2
    assert len(ws.archived_issues) == 1
    assert len(ws.reviews) == 1
    assert ws.lessons == ["2026-06-01-vn-0-thing.md"]
    assert ws.has_repo_context is True
    assert ws.custom_strategies == ["branching-strategy"]


def test_six_phase_pipeline(workspace):
    ws = model.load_workspace(workspace)
    vn1 = {i.id: i for i in ws.active_issues}["VN-1"]
    assert vn1.total_phases == 6
    assert [p.name for p in vn1.phases] == list(model.PHASE_ORDER)


def test_execution_subtasks_count_as_content(workspace):
    """Regression: execution holds subtask folders, not files."""
    ws = model.load_workspace(workspace)
    vn1 = {i.id: i for i in ws.active_issues}["VN-1"]
    exec_phase = next(p for p in vn1.phases if p.name == "execution")
    assert exec_phase.has_content is True
    assert exec_phase.subphase_count == 2
    assert {sp.name for sp in exec_phase.subphases} == {"01-scaffold", "02-algo"}


def test_feedback_rounds_scanned(workspace):
    ws = model.load_workspace(workspace)
    vn1 = {i.id: i for i in ws.active_issues}["VN-1"]
    fb = next(p for p in vn1.phases if p.name == "feedback")
    assert fb.has_content is True
    assert fb.subphase_count == 2
    assert fb.total_rounds == 3
    sub1 = next(sp for sp in fb.subphases if sp.name == "sub-1")
    assert sub1.round_count == 2


def test_current_phase_is_feedback(workspace):
    ws = model.load_workspace(workspace)
    vn1 = {i.id: i for i in ws.active_issues}["VN-1"]
    assert vn1.current_phase.name == "feedback"
    assert vn1.completed_count == 5  # all but evaluation
    assert vn1.is_complete is False


def test_phase_states(workspace):
    ws = model.load_workspace(workspace)
    vn1 = {i.id: i for i in ws.active_issues}["VN-1"]
    states = {p.name: vn1.phase_state(p) for p in vn1.phases}
    assert states["plan"] == "done"
    assert states["execution"] == "done"
    assert states["feedback"] == "active"
    assert states["evaluation"] == "pending"


def test_subphase_active_from_last_feedback_round(workspace):
    ws = model.load_workspace(workspace)
    vn1 = {i.id: i for i in ws.active_issues}["VN-1"]
    fb = next(p for p in vn1.phases if p.name == "feedback")
    assert render._subphase_state(vn1, fb, "sub-1", "active") == "done"
    assert render._subphase_state(vn1, fb, "sub-2", "active") == "active"


def test_archived_issue_complete(workspace):
    ws = model.load_workspace(workspace)
    arch = ws.archived_issues[0]
    assert arch.id == "VN-0"
    assert arch.is_complete is True


def test_plan_meta(workspace):
    ws = model.load_workspace(workspace)
    vn1 = {i.id: i for i in ws.active_issues}["VN-1"]
    plan = vn1.plan
    assert plan.branching_mode == "sub-branches"
    assert plan.total_subtasks == 2
    assert plan.total_commits == 5
    assert plan.branch_name == "feat/VN-1-thing"
    assert plan.branch_created is True
    assert plan.pr_url == "https://github.com/x/y/pull/10"
    assert plan.pr_state == "draft"
    assert plan.gh_issue_created is False
    assert plan.review_groups == ["sub-1", "sub-2"]
    assert plan.last_feedback_round == "sub-2/01"
    assert plan.published is False  # draft is not published


def test_review_scan(workspace):
    ws = model.load_workspace(workspace)
    rv = ws.reviews[0]
    assert rv.pr == "50"
    assert rv.round_count == 2
    assert rv.last_verdict == "APPROVE"
    # 2 comments in round-01 (summary excluded) + 1 in round-02.
    assert rv.total_comments == 3


def test_quoted_title_unmangled(workspace):
    ws = model.load_workspace(workspace)
    vn1 = {i.id: i for i in ws.active_issues}["VN-1"]
    assert vn1.title == '"Quoted" title'


def test_phase_distribution(workspace):
    ws = model.load_workspace(workspace)
    dist = ws.phase_distribution
    assert dist["feedback"] == 1   # VN-1
    assert dist["gathering"] == 1  # VN-2
    assert dist["complete"] == 0


def test_find_workspace_walks_parents(workspace):
    nested = workspace.parent / "src" / "deep"
    nested.mkdir(parents=True)
    assert model.find_workspace(nested) == workspace.resolve()


def test_find_workspace_none(tmp_path):
    assert model.find_workspace(tmp_path) is None


# --- git ----------------------------------------------------------------------


def test_git_info_non_repo(tmp_path):
    info = gitinfo.load_git_info(tmp_path)
    assert info.is_repo is False
    assert info.branches == []


def test_git_info_real_repo():
    repo = Path(__file__).resolve().parents[1]
    info = gitinfo.load_git_info(repo)
    assert info.is_repo is True
    assert info.current_branch  # some branch name


def test_git_sub_branches():
    info = gitinfo.GitInfo(
        is_repo=True,
        branches=["feat/X", "feat/X-sub-1", "feat/X-sub-2", "develop"],
    )
    assert info.sub_branches_for("feat/X") == ["feat/X-sub-1", "feat/X-sub-2"]
    assert info.has_branch("feat/X") is True
    assert info.has_branch("nope") is False


# --- rendering ----------------------------------------------------------------


def test_render_overview(workspace):
    ws = model.load_workspace(workspace)
    out = _rtext(render.render_overview(ws))
    assert "myrepo" in out
    assert "VN-1" in out
    assert "VN-2" in out
    assert "pr-50" in out
    assert "feedback" in out  # phase distribution + current phase


def test_render_issue_timeline(workspace):
    ws = model.load_workspace(workspace)
    vn1 = {i.id: i for i in ws.active_issues}["VN-1"]
    out = _rtext(render.render_issue(vn1))
    assert '"Quoted" title' in out
    assert "Timeline" in out
    assert "01-scaffold" in out  # execution subtask in timeline
    assert "sub-1" in out and "sub-2" in out  # feedback sub-branches
    assert "draft" in out  # PR publish status
    assert "feat/VN-1-thing" in out  # branch in status panel


def test_render_review_rounds(workspace):
    ws = model.load_workspace(workspace)
    out = _rtext(render.render_review(ws.reviews[0]))
    assert "PR #50" in out
    assert "round-01" in out and "round-02" in out
    assert "APPROVE" in out


def test_progress_bar():
    assert render.progress_bar(3, 6) == "███···"
    assert render.progress_bar(0, 6) == "······"
    assert render.progress_bar(6, 6) == "██████"


def test_hbar_resolution():
    full = _rtext(render.hbar(10, 10, 10)).strip()
    empty = _rtext(render.hbar(0, 10, 10)).strip()
    assert "█" in full
    assert "█" not in empty


# --- app smoke test (headless) ------------------------------------------------


def test_app_boots(workspace):
    pytest.importorskip("textual")
    import asyncio

    from textual.widgets import ContentSwitcher

    from dev_assistant.tui.app import DashboardApp

    async def scenario():
        app = DashboardApp(workspace)
        async with app.run_test() as pilot:
            await pilot.pause()
            # Overview structured view shown on mount.
            assert app.query_one("#content", ContentSwitcher).current == "struct"

            # Navigate to a file leaf -> switches to the markdown viewer.
            tree = app.query_one("#nav")

            def walk(n):
                yield n
                for c in n.children:
                    yield from walk(c)

            file_node = next(
                n for n in walk(tree.root)
                if n.data and n.data.get("kind") == "file"
            )
            tree.select_node(file_node)
            await pilot.pause()
            assert app.query_one("#content", ContentSwitcher).current == "file"

            await pilot.press("o")  # back to overview
            await pilot.pause()
            assert app.query_one("#content", ContentSwitcher).current == "struct"
            await pilot.press("r")  # refresh
            await pilot.pause()

    asyncio.run(scenario())
