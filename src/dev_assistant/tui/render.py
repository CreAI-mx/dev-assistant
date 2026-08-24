"""Rich renderables for the TUI detail pane.

Structured views (overview, issue timeline, review) are built as Rich
renderables so phase state can be colored and graphs drawn. Raw artifact files
are rendered separately as markdown by the app. Kept import-light and mostly
pure so the formatting helpers stay unit-testable.
"""
from __future__ import annotations

from datetime import datetime

from rich.console import Group, RenderableType
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from . import theme
from .gitinfo import GitInfo
from .model import Issue, PhaseStatus, Review, Round, Workspace, humanize_age

# --- small primitives ---------------------------------------------------------


def progress_bar(completed: int, total: int) -> str:
    """Plain-string block bar for tree labels."""
    completed = max(0, min(completed, total))
    return theme.BAR_FULL * completed + "·" * (total - completed)


def hbar(value: float, maxval: float, width: int = 18) -> Text:
    """Horizontal bar with sub-cell (eighths) resolution."""
    if maxval <= 0:
        return Text(theme.BAR_EMPTY * width, style=theme.STYLE_DIM)
    filled = (value / maxval) * width
    full = int(filled)
    rem = filled - full
    eighth = theme.BAR_PARTIALS[round(rem * 8)] if full < width else ""
    bar = theme.BAR_FULL * full + eighth
    bar = bar.ljust(width, theme.BAR_EMPTY)
    return Text(bar, style=theme.STYLE_ACCENT)


def _verdict_text(verdict: str) -> Text:
    v = verdict.lower()
    if "approve" in v:
        return Text(f"{theme.ICON_OK} {verdict}", style=theme.STYLE_OK)
    if "request" in v or "block" in v or "change" in v:
        return Text(f"{theme.ICON_FAIL} {verdict}", style=theme.STYLE_FAIL)
    return Text(f"{theme.ICON_NEUTRAL} {verdict}", style=theme.STYLE_DIM)


def _h(text: str) -> Text:
    return Text(text, style="bold")


# --- overview -----------------------------------------------------------------


def render_overview(
    ws: Workspace, *, git: GitInfo | None = None, ref: datetime | None = None
) -> RenderableType:
    active = ws.active_issues
    open_reviews = [r for r in ws.reviews if r.status != "closed"]

    parts: list[RenderableType] = []
    title = Text()
    title.append(ws.repo_name, style="bold cyan")
    title.append("  dev-assistant workspace", style="dim")
    parts.append(title)
    parts.append(Text(str(ws.root), style="dim"))
    parts.append(Text())

    # Rollups.
    roll = Table.grid(padding=(0, 2))
    roll.add_column(justify="right", style="bold")
    roll.add_column()
    roll.add_row(str(len(active)), Text("active issues"))
    roll.add_row(str(len(ws.archived_issues)), Text("archived", style="dim"))
    roll.add_row(str(len(open_reviews)), Text("open reviews"))
    roll.add_row(str(len(ws.lessons)), Text("lessons"))
    git_line = Text("—", style="dim")
    if git and git.is_repo:
        git_line = Text(f"{theme.ICON_BRANCH} {git.current_branch or '?'}", style="cyan")
        if git.clean:
            git_line.append("  clean", style="green")
        else:
            git_line.append(
                f"  {git.dirty_count} changed, {git.untracked_count} untracked",
                style="yellow",
            )
    roll.add_row("", git_line)
    parts.append(roll)
    parts.append(Text())

    # Phase distribution bar chart.
    parts.append(_h("Pipeline distribution (active issues)"))
    dist = ws.phase_distribution
    rows = [(name, dist.get(name, 0)) for name in (
        "refinement", "gathering", "plan", "execution", "feedback", "merge", "evaluation")]
    rows.append(("complete", dist.get("complete", 0)))
    maxval = max((c for _, c in rows), default=0) or 1
    chart = Table.grid(padding=(0, 1))
    chart.add_column(justify="right", style="dim", width=10)
    chart.add_column()
    chart.add_column(justify="right")
    for name, count in rows:
        if count == 0:
            continue
        chart.add_row(name, hbar(count, maxval, 22), str(count))
    if not active:
        chart.add_row("", Text("no active issues", style="dim"), "")
    parts.append(chart)
    parts.append(Text())

    # Active issues table.
    parts.append(_h("Active issues"))
    if active:
        tbl = Table(expand=False, pad_edge=False, box=None, padding=(0, 2))
        tbl.add_column("id", style="bold cyan")
        tbl.add_column("progress")
        tbl.add_column("phase")
        tbl.add_column("age", justify="right", style="dim")
        tbl.add_column("in phase", justify="right", style="dim")
        for i in active:
            bar = Text(progress_bar(i.completed_count, i.total_phases), style="green")
            bar.append(f" {i.completed_count}/{i.total_phases}", style="dim")
            cur = (
                Text("complete", style="green")
                if i.is_complete
                else Text(
                    i.current_phase.label if i.current_phase else "—",
                    style=theme.STYLE_ACTIVE,
                )
            )
            idtxt = Text(i.id)
            if i.experimental:
                idtxt.append(" exp", style="yellow")
            tbl.add_row(idtxt, bar, cur, i.age(ref), i.time_in_phase(ref))
        parts.append(tbl)
    else:
        parts.append(Text("None. Create one with `dev-assistant issue create`.", style="dim"))
    parts.append(Text())

    # Reviews.
    if ws.reviews:
        parts.append(_h("Reviews"))
        rtbl = Table(expand=False, pad_edge=False, box=None, padding=(0, 2))
        rtbl.add_column("pr", style="bold magenta")
        rtbl.add_column("verdict")
        rtbl.add_column("rounds", justify="right")
        rtbl.add_column("comments", justify="right")
        rtbl.add_column("age", justify="right", style="dim")
        for r in ws.reviews:
            rtbl.add_row(
                f"pr-{r.pr}",
                _verdict_text(r.last_verdict),
                str(r.round_count),
                str(r.total_comments),
                r.age(ref),
            )
        parts.append(rtbl)

    return Group(*parts)


# --- issue timeline -----------------------------------------------------------


def _subphase_state(issue: Issue, phase: PhaseStatus, sub_name: str, phase_state: str) -> str:
    if phase_state == "done":
        return "done"
    if phase_state == "pending":
        return "pending"
    # Active phase — try to locate the active subphase. `last_feedback_round` is
    # `sub-N/NN` in sub-branches mode and a bare `NN` for a main-PR round (which
    # names no sub-branch, so it falls through to the positional default).
    last = issue.plan.last_feedback_round
    if phase.name == "feedback" and last and "/" in last:
        active_sub = last.split("/", 1)[0]
        names = [sp.name for sp in phase.subphases]
        if sub_name == active_sub:
            return "active"
        if active_sub in names and sub_name in names:
            return "done" if names.index(sub_name) < names.index(active_sub) else "pending"
    # default: the last-by-name subphase is active.
    names = [sp.name for sp in phase.subphases]
    if names and sub_name == names[-1]:
        return "active"
    return "done"


def _round_line(rnd: Round, state: str, depth: int) -> Text:
    """One `round-NN` timeline row, with its cluster/file counts."""
    line = Text()
    line.append(f"{theme.ICON_VBAR} " * depth, style="grey37")
    line.append_text(_dot(state))
    line.append(" ")
    line.append(rnd.name, style=theme.state_style(state))
    detail = []
    if rnd.cluster_count:
        detail.append(f"{rnd.cluster_count} cluster{'s' if rnd.cluster_count != 1 else ''}")
    if rnd.files:
        detail.append(f"{len(rnd.files)} file{'s' if len(rnd.files) != 1 else ''}")
    if detail:
        line.append(f"   {' · '.join(detail)}", style="dim")
    return line


def _round_states(rounds: list[Round], phase_state: str) -> list[str]:
    """State per round: all done in a finished phase, last one active otherwise."""
    if phase_state != "active" or not rounds:
        return [phase_state] * len(rounds)
    return ["done"] * (len(rounds) - 1) + ["active"]


def _dot(state: str) -> Text:
    return Text(theme.state_icon(state), style=theme.state_style(state))


def render_issue(
    issue: Issue, *, git: GitInfo | None = None, ref: datetime | None = None
) -> RenderableType:
    parts: list[RenderableType] = []

    header = Text()
    header.append(issue.id, style="bold cyan")
    header.append(f"  {issue.title}")
    parts.append(header)

    badges = Text()
    badges.append(issue.status, style="green" if issue.status == "active" else "dim")
    badges.append("  ·  ", style="dim")
    badges.append(
        f"autonomy {issue.autonomy}",
        style="dim" if issue.autonomy == "guided" else "yellow",
    )
    if issue.experimental:
        badges.append("  ·  ", style="dim")
        badges.append("experimental", style="yellow")
    if issue.archived:
        badges.append("  ·  ", style="dim")
        badges.append("archived", style="dim")
    badges.append("  ·  ", style="dim")
    badges.append(f"created {issue.age(ref)} ago", style="dim")
    parts.append(badges)
    parts.append(Text())

    # Progress summary line.
    bar = Text(progress_bar(issue.completed_count, issue.total_phases), style="green")
    bar.append(f"  {issue.completed_count}/{issue.total_phases} phases", style="dim")
    parts.append(bar)
    parts.append(Text())

    # Status panel (git + publish), all best-effort.
    parts.append(_h("Status"))
    parts.append(_status_table(issue, git))
    parts.append(Text())

    # Timeline.
    parts.append(_h("Timeline"))
    parts.append(_timeline(issue, ref))

    return Group(*parts)


def _status_table(issue: Issue, git: GitInfo | None) -> RenderableType:
    plan = issue.plan
    t = Table.grid(padding=(0, 2))
    t.add_column(style="dim", justify="right")
    t.add_column()

    # Subtasks.
    exec_phase = next((p for p in issue.phases if p.name == "execution"), None)
    n_sub = plan.total_subtasks or (exec_phase.subphase_count if exec_phase else 0)
    t.add_row("subtasks", Text(str(n_sub) if n_sub else "—"))

    # Branch + sub-branches (live git, falling back to recorded plan state).
    if git and git.is_repo:
        branch = plan.branch_name
        exists = git.has_branch(branch)
        live_subs = git.sub_branches_for(branch)
        btxt = Text()
        if branch:
            btxt.append(f"{theme.ICON_BRANCH} {branch}", style="cyan")
            btxt.append("  exists" if exists else "  not created", style="green" if exists else "yellow")
        else:
            btxt.append("—", style="dim")
        t.add_row("branch", btxt)
        if plan.branching_mode == "sub-branches" or live_subs:
            groups = plan.review_groups
            sub_txt = Text(f"{len(live_subs)} live", style="cyan")
            if groups:
                sub_txt.append(f"  (planned: {', '.join(groups)})", style="dim")
            t.add_row("sub-branches", sub_txt)
        repo_txt = Text(f"{theme.ICON_BRANCH} on {git.current_branch}", style="dim")
        repo_txt.append("  clean" if git.clean else f"  {git.dirty_count} changed",
                        style="green" if git.clean else "yellow")
        t.add_row("working tree", repo_txt)
    else:
        if plan.branch_name:
            t.add_row("branch", Text(f"{theme.ICON_BRANCH} {plan.branch_name} (recorded)", style="dim"))

    if plan.total_commits:
        t.add_row("commits", Text(str(plan.total_commits)))

    # Publish status.
    t.add_row("PR", _pr_status(plan))
    if plan.flow == "hotfix":
        sync = Text("hotfix", style="magenta")
        if plan.develop_pr_url:
            sync.append(f"  sync PR: {plan.develop_pr_url}", style="dim")
        else:
            sync.append("  sync PR not opened", style="yellow")
        t.add_row("flow", sync)
    if plan.merge_commit:
        t.add_row("merged as", Text(plan.merge_commit, style="green"))
    gh = Text(f"{theme.ICON_OK} created", style="green") if plan.gh_issue_created else Text(
        "not created", style="dim")
    t.add_row("gh issue", gh)

    return t


def _pr_status(plan) -> Text:
    if not plan.pr_url:
        return Text(f"{theme.ICON_WARN} not opened", style="yellow")
    state = (plan.pr_state or "").lower()
    txt = Text()
    if state == "merged":
        txt.append(f"{theme.ICON_OK} merged", style="green")
    elif state == "draft":
        txt.append(f"{theme.ICON_NEUTRAL} draft (not yet published)", style="yellow")
    elif state in ("open", "ready"):
        txt.append(f"{theme.ICON_OK} open", style="green")
    else:
        txt.append(state or "open", style="cyan")
    txt.append(f"  {plan.pr_url}", style="dim")
    return txt


def _timeline(issue: Issue, ref: datetime | None) -> RenderableType:
    lines: list[Text] = []
    for phase in issue.phases:
        state = issue.phase_state(phase)
        # Skip optional phases that never started (merge is also absent on
        # pre-0.6 and experimental issues).
        if not phase.has_content and phase.name in ("refinement", "feedback", "merge"):
            continue

        line = Text()
        line.append_text(_dot(state))
        line.append(" ")
        line.append(f"{phase.label:<9}", style=theme.state_style(state))
        line.append(f"  {state:<8}", style="dim")
        meta = _phase_meta(phase)
        if meta:
            line.append(f"  {meta}", style="dim")
        if phase.last_modified:
            line.append(f"   {humanize_age(phase.last_modified, ref=ref)}", style="grey37")
        lines.append(line)

        # Rounds sitting directly under the phase (single-branch / main-PR feedback).
        for rnd, rstate in zip(
            phase.rounds, _round_states(phase.rounds, state), strict=True
        ):
            if not rnd.has_content:
                continue
            lines.append(_round_line(rnd, rstate, depth=1))

        # Subphases, each with its own rounds.
        for sp in phase.subphases:
            if not sp.has_content:
                continue
            sub_state = _subphase_state(issue, phase, sp.name, state)
            sline = Text()
            sline.append(f"{theme.ICON_VBAR} ", style="grey37")
            sline.append_text(_dot(sub_state))
            sline.append(" ")
            sline.append(sp.name, style=theme.state_style(sub_state))
            detail = []
            if sp.round_count:
                detail.append(f"{sp.round_count} round{'s' if sp.round_count != 1 else ''}")
            if sp.files:
                detail.append(f"{len(sp.files)} file{'s' if len(sp.files) != 1 else ''}")
            if detail:
                sline.append(f"   {' · '.join(detail)}", style="dim")
            lines.append(sline)

            for rnd, rstate in zip(
                sp.rounds, _round_states(sp.rounds, sub_state), strict=True
            ):
                if not rnd.has_content:
                    continue
                lines.append(_round_line(rnd, rstate, depth=2))

    return Group(*lines) if lines else Text("no phases yet", style="dim")


def _phase_meta(phase: PhaseStatus) -> str:
    if phase.name == "execution" and phase.subphase_count:
        return f"{phase.subphase_count} subtasks"
    if phase.name == "feedback" and (phase.subphases or phase.rounds):
        bits = []
        if phase.subphase_count:
            bits.append(f"{phase.subphase_count} sub-branches")
        n = phase.total_rounds
        bits.append(f"{n} round{'s' if n != 1 else ''}")
        if phase.total_clusters:
            c = phase.total_clusters
            bits.append(f"{c} cluster{'s' if c != 1 else ''}")
        return " · ".join(bits)
    if phase.files:
        n = len(phase.files)
        return f"{n} file{'s' if n != 1 else ''}"
    return ""


# --- review -------------------------------------------------------------------


def render_review(review: Review, *, ref: datetime | None = None) -> RenderableType:
    parts: list[RenderableType] = []
    header = Text()
    header.append(f"PR #{review.pr}", style="bold magenta")
    if review.title:
        header.append(f"  {review.title}")
    parts.append(header)

    sub = Text()
    sub.append(review.status, style="green" if review.status == "active" else "dim")
    sub.append("  ·  ", style="dim")
    sub.append_text(_verdict_text(review.last_verdict))
    parts.append(sub)
    if review.pr_url:
        parts.append(Text(review.pr_url, style="dim"))
    parts.append(Text())

    parts.append(_h("Rounds"))
    if review.rounds:
        from .model import _count_comments

        tbl = Table(expand=False, pad_edge=False, box=None, padding=(0, 2))
        tbl.add_column("round", style="bold")
        tbl.add_column("comments", justify="right")
        tbl.add_column("artifacts")
        tbl.add_column("age", justify="right", style="dim")
        for r in review.rounds:
            arts = ", ".join(f for f in r.files if f.endswith(".md")) or "—"
            tbl.add_row(
                r.name,
                str(_count_comments(r.path)),
                Text(arts, style="dim"),
                humanize_age(r.last_modified, ref=ref),
            )
        parts.append(tbl)
    else:
        parts.append(Text("no rounds yet", style="dim"))
    parts.append(Text())
    parts.append(Rule(style="grey30"))
    parts.append(Text("Expand this review in the tree to read round artifacts.", style="dim"))
    return Group(*parts)
