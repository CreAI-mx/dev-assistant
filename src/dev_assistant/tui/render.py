"""Pure markdown renderers for the TUI detail pane.

Each function turns a model object into a markdown string. Kept separate from
the Textual app so the formatting is unit-testable without a terminal.
"""
from __future__ import annotations

from datetime import datetime

from .model import PHASE_ORDER, Issue, Review, Workspace


def progress_bar(completed: int, total: int) -> str:
    filled = "█" * completed
    empty = "░" * max(0, total - completed)
    return f"{filled}{empty}"


def _verdict_mark(verdict: str) -> str:
    v = verdict.lower()
    if "approve" in v:
        return "✓"
    if "request" in v or "block" in v or "change" in v:
        return "✗"
    if "comment" in v:
        return "💬"
    return "·"


def render_overview(ws: Workspace, *, ref: datetime | None = None) -> str:
    active = ws.active_issues
    archived = ws.archived_issues
    open_reviews = [r for r in ws.reviews if r.status != "closed"]

    lines: list[str] = []
    lines.append(f"# {ws.repo_name} — dev-assistant workspace")
    lines.append("")
    lines.append(f"`{ws.root}`")
    lines.append("")

    lines.append("## Rollups")
    lines.append("")
    lines.append("| metric | count |")
    lines.append("|---|---|")
    lines.append(f"| Active issues | {len(active)} |")
    lines.append(f"| Archived issues | {len(archived)} |")
    lines.append(f"| Reviews (open) | {len(ws.reviews)} ({len(open_reviews)}) |")
    lines.append(f"| Lessons archived | {len(ws.lessons)} |")
    lines.append(f"| Repo context | {'yes' if ws.has_repo_context else 'no'} |")
    custom = ", ".join(ws.custom_strategies) if ws.custom_strategies else "none"
    lines.append(f"| Custom strategies | {custom} |")
    lines.append("")

    dist = ws.phase_distribution
    lines.append("## Phase distribution (active issues)")
    lines.append("")
    lines.append("| phase | issues |")
    lines.append("|---|---|")
    for name in PHASE_ORDER:
        if dist.get(name):
            lines.append(f"| {name} | {dist[name]} |")
    if dist.get("complete"):
        lines.append(f"| ✅ complete | {dist['complete']} |")
    if dist.get("empty"):
        lines.append(f"| (not started) | {dist['empty']} |")
    if not active:
        lines.append("| _no active issues_ | |")
    lines.append("")

    lines.append("## Active issues")
    lines.append("")
    if active:
        lines.append("| id | progress | current | age | in phase |")
        lines.append("|---|---|---|---|---|")
        for i in active:
            cur = "✅ done" if i.is_complete else (
                i.current_phase.label if i.current_phase else "—"
            )
            flag = " ⚗️" if i.experimental else ""
            bar = progress_bar(i.completed_count, i.total_phases)
            lines.append(
                f"| **{i.id}**{flag} | `{bar}` {i.completed_count}/{i.total_phases} "
                f"| {cur} | {i.age(ref)} | {i.time_in_phase(ref)} |"
            )
    else:
        lines.append("_None. Create one with_ `dev-assistant issue create`.")
    lines.append("")

    if ws.reviews:
        lines.append("## Reviews")
        lines.append("")
        lines.append("| pr | verdict | rounds | comments | age |")
        lines.append("|---|---|---|---|---|")
        for r in ws.reviews:
            lines.append(
                f"| pr-{r.pr} | {_verdict_mark(r.last_verdict)} {r.last_verdict} "
                f"| {r.rounds} | {r.latest_round_comments} | {r.age(ref)} |"
            )
        lines.append("")

    return "\n".join(lines)


def render_issue(issue: Issue, *, ref: datetime | None = None) -> str:
    lines: list[str] = []
    lines.append(f"# {issue.id} — {issue.title}")
    lines.append("")

    badges = [f"`{issue.status}`"]
    if issue.experimental:
        badges.append("⚗️ experimental")
    if issue.archived:
        badges.append("📦 archived")
    badges.append(f"created {issue.age(ref)} ago")
    lines.append(" · ".join(badges))
    lines.append("")

    bar = progress_bar(issue.completed_count, issue.total_phases)
    if issue.is_complete:
        cur = "all phases complete ✅"
    elif issue.current_phase:
        cur = f"current: **{issue.current_phase.name}** ({issue.time_in_phase(ref)} in phase)"
        if issue.next_phase:
            cur += f" → next: {issue.next_phase.name}"
    else:
        cur = "not started"
    lines.append("## Progress")
    lines.append("")
    lines.append(f"`{bar}` {issue.completed_count}/{issue.total_phases} — {cur}")
    lines.append("")

    lines.append("| phase | files | last activity |")
    lines.append("|---|---|---|")
    for p in issue.phases:
        mark = "●" if p.has_content else "○"
        files = ", ".join(p.files) if p.files else "_empty_"
        last = _humanize(p.last_modified, ref)
        lines.append(f"| {mark} {p.name} | {files} | {last} |")
    lines.append("")

    lines.append("## Description")
    lines.append("")
    lines.append(issue.description or "_(no description)_")
    lines.append("")
    lines.append("---")
    lines.append("_Expand this issue in the tree to read individual phase files._")
    return "\n".join(lines)


def render_review(review: Review, *, ref: datetime | None = None) -> str:
    lines: list[str] = []
    lines.append(f"# PR #{review.pr} review")
    lines.append("")
    badges = [f"`{review.status}`", f"{_verdict_mark(review.last_verdict)} {review.last_verdict}"]
    lines.append(" · ".join(badges))
    lines.append("")
    if review.pr_url:
        lines.append(f"<{review.pr_url}>")
        lines.append("")
    lines.append("| field | value |")
    lines.append("|---|---|")
    lines.append(f"| Rounds | {review.rounds} |")
    lines.append(f"| Drafted comments (latest round) | {review.latest_round_comments} |")
    lines.append(f"| Last verdict | {review.last_verdict} |")
    lines.append(f"| Last activity | {_humanize(review.last_modified, ref)} |")
    lines.append("")
    lines.append("_Expand this review in the tree to read round artifacts._")
    return "\n".join(lines)


def _humanize(dt: datetime | None, ref: datetime | None) -> str:
    from .model import humanize_age

    return humanize_age(dt, ref=ref)
