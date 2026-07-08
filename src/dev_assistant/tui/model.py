"""Read-only data model for the dev-assistant TUI.

Pure functions and dataclasses that scan a `.dev-assistant/` workspace and
build an in-memory snapshot. No Textual import here on purpose — this layer is
fully unit-testable without a terminal, and the app layer renders it.

Phase shapes seen in real workspaces:
  - refinement / gathering / plan / merge / evaluation : flat files
  - execution                                  : numbered subtask subfolders, each with files
  - feedback                                   : sub-N subfolders, each with round-NN subfolders
The scanner models all of them through Phase -> SubPhase -> Round.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_DIRNAME = ".dev-assistant"

# Full author-side pipeline, in order. `refinement` (phase 0) and `feedback`
# are optional, so an empty folder there does not mean "not started"; `merge`
# is absent on pre-0.6 and experimental issues.
PHASE_ORDER = ("refinement", "gathering", "plan", "execution", "feedback", "merge", "evaluation")

PHASE_LABELS = {
    "refinement": "refine",
    "gathering": "gather",
    "plan": "plan",
    "execution": "exec",
    "feedback": "feedback",
    "merge": "merge",
    "evaluation": "eval",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a markdown document into (frontmatter dict, body).

    Handles the simple `key: value` frontmatter dev-assistant writes between a
    pair of `---` fences. Only top-level (non-indented) keys are captured;
    indented continuation/nested lines (e.g. YAML list items under a key) are
    skipped rather than mis-parsed. Not a full YAML parser.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    meta: dict[str, str] = {}
    closing = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing = i
            break
        raw = lines[i]
        if not raw or raw[0] in (" ", "\t", "-"):
            continue  # nested / list continuation — skip
        if ":" in raw:
            key, _, value = raw.partition(":")
            meta[key.strip()] = value.strip()
    if closing is None:
        return {}, text
    body = "\n".join(lines[closing + 1 :]).strip()
    return meta, body


def _parse_dt(value: str | None) -> datetime | None:
    if not value or value.lower() in ("null", "none", ""):
        return None
    value = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _as_bool(value: str | None) -> bool:
    return (value or "").strip().lower() == "true"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    # Strip a single matching outer quote pair (YAML-quoted scalar).
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    if value.lower() in ("null", "none", ""):
        return None
    return value


def humanize_age(dt: datetime | None, *, ref: datetime | None = None) -> str:
    """Compact human duration since `dt` (e.g. '3d', '5h', '12m', 'just now')."""
    if dt is None:
        return "—"
    ref = ref or _now()
    seconds = int((ref - dt).total_seconds())
    if seconds < 0:
        return "—"
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    if days < 14:
        return f"{days}d"
    weeks = days // 7
    if weeks < 9:
        return f"{weeks}w"
    return f"{days // 30}mo"


def _tree_latest_mtime(path: Path) -> datetime | None:
    """Most recent mtime of any file anywhere under `path` (or the file itself)."""
    if path.is_file():
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    if not path.is_dir():
        return None
    latest: float | None = None
    for child in path.rglob("*"):
        if child.is_file():
            mtime = child.stat().st_mtime
            if latest is None or mtime > latest:
                latest = mtime
    return datetime.fromtimestamp(latest, tz=timezone.utc) if latest else None


@dataclass
class Round:
    name: str
    files: list[str]
    path: Path
    last_modified: datetime | None

    @property
    def has_content(self) -> bool:
        return bool(self.files)


@dataclass
class SubPhase:
    """A subtask folder (execution) or a sub-branch folder (feedback)."""

    name: str
    files: list[str]
    rounds: list[Round]
    path: Path
    last_modified: datetime | None

    @property
    def has_content(self) -> bool:
        return bool(self.files) or any(r.has_content for r in self.rounds)

    @property
    def round_count(self) -> int:
        return len(self.rounds)


@dataclass
class PhaseStatus:
    name: str
    files: list[str]
    subphases: list[SubPhase]
    path: Path
    last_modified: datetime | None

    @property
    def label(self) -> str:
        return PHASE_LABELS.get(self.name, self.name)

    @property
    def has_content(self) -> bool:
        return bool(self.files) or any(sp.has_content for sp in self.subphases)

    @property
    def subphase_count(self) -> int:
        return len(self.subphases)

    @property
    def total_rounds(self) -> int:
        return sum(sp.round_count for sp in self.subphases)

    @property
    def artifact_count(self) -> int:
        """Total leaf files across this phase (direct + nested)."""
        n = len(self.files)
        for sp in self.subphases:
            n += len(sp.files)
            for r in sp.rounds:
                n += len(r.files)
        return n


@dataclass
class PlanMeta:
    """State recorded in plan/plan.md frontmatter — the workspace's own record
    of branch / PR / external status, written by the slash commands."""

    branching_mode: str | None = None
    flow: str | None = None
    total_subtasks: int | None = None
    total_commits: int | None = None
    branch_name: str | None = None
    branch_created: bool = False
    target_branch: str | None = None
    pr_url: str | None = None
    pr_state: str | None = None
    develop_pr_url: str | None = None
    merge_commit: str | None = None
    gh_issue_created: bool = False
    review_groups: list[str] = field(default_factory=list)
    last_feedback_round: str | None = None
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def published(self) -> bool:
        return bool(self.pr_url) and (self.pr_state or "").lower() in (
            "open",
            "ready",
            "merged",
        )


@dataclass
class Issue:
    id: str
    title: str
    created: datetime | None
    status: str
    experimental: bool
    description: str
    archived: bool
    phases: list[PhaseStatus]
    plan: PlanMeta
    path: Path

    @property
    def completed_count(self) -> int:
        return sum(1 for p in self.phases if p.has_content)

    @property
    def total_phases(self) -> int:
        return len(self.phases)

    @property
    def current_phase(self) -> PhaseStatus | None:
        active = [p for p in self.phases if p.has_content]
        return active[-1] if active else None

    def phase_state(self, phase: PhaseStatus) -> str:
        """'done' | 'active' | 'pending' for the timeline."""
        current = self.current_phase
        if current is None:
            return "pending"
        cur_idx = self.phases.index(current)
        idx = self.phases.index(phase)
        if idx < cur_idx:
            return "done"
        if idx == cur_idx:
            return "done" if self.is_complete else "active"
        return "pending"

    @property
    def next_phase(self) -> PhaseStatus | None:
        current = self.current_phase
        if current is None:
            return self.phases[0] if self.phases else None
        idx = self.phases.index(current)
        for p in self.phases[idx + 1 :]:
            if not p.has_content:
                return p
        return None

    @property
    def is_complete(self) -> bool:
        # Complete when the evaluation phase has content.
        evaluation = next((p for p in self.phases if p.name == "evaluation"), None)
        return bool(evaluation and evaluation.has_content)

    @property
    def last_activity(self) -> datetime | None:
        times = [p.last_modified for p in self.phases if p.last_modified]
        return max(times) if times else self.created

    def age(self, ref: datetime | None = None) -> str:
        return humanize_age(self.created, ref=ref)

    def time_in_phase(self, ref: datetime | None = None) -> str:
        current = self.current_phase
        anchor = current.last_modified if current else self.created
        return humanize_age(anchor, ref=ref)


@dataclass
class Review:
    pr: str
    pr_url: str
    title: str
    last_verdict: str
    status: str
    rounds: list[Round]
    path: Path
    last_modified: datetime | None

    @property
    def round_count(self) -> int:
        return len(self.rounds)

    @property
    def total_comments(self) -> int:
        return sum(_count_comments(r.path) for r in self.rounds)

    def age(self, ref: datetime | None = None) -> str:
        return humanize_age(self.last_modified, ref=ref)


@dataclass
class Workspace:
    root: Path
    repo_name: str
    repo_root: Path
    issues: list[Issue] = field(default_factory=list)
    reviews: list[Review] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    has_repo_context: bool = False
    custom_strategies: list[str] = field(default_factory=list)

    @property
    def active_issues(self) -> list[Issue]:
        return [i for i in self.issues if not i.archived]

    @property
    def archived_issues(self) -> list[Issue]:
        return [i for i in self.issues if i.archived]

    @property
    def phase_distribution(self) -> dict[str, int]:
        dist = {name: 0 for name in PHASE_ORDER}
        dist["complete"] = 0
        dist["empty"] = 0
        for issue in self.active_issues:
            if issue.is_complete:
                dist["complete"] += 1
            elif issue.current_phase is None:
                dist["empty"] += 1
            else:
                dist[issue.current_phase.name] += 1
        return dist


# --- scanning -----------------------------------------------------------------


def _files_in(directory: Path) -> list[str]:
    if not directory.is_dir():
        return []
    return sorted(p.name for p in directory.iterdir() if p.is_file())


def _count_comments(round_dir: Path) -> int:
    comments = round_dir / "comments"
    if not comments.is_dir():
        return 0
    return sum(
        1 for p in comments.iterdir() if p.is_file() and p.name != "summary.md"
    )


def _scan_rounds(parent: Path) -> list[Round]:
    rounds: list[Round] = []
    for d in sorted(p for p in parent.iterdir() if p.is_dir() and p.name.startswith("round-")):
        # round artifacts may be nested (comments/, clusters/); collect leaf names shallowly.
        rounds.append(
            Round(
                name=d.name,
                files=_files_in(d),
                path=d,
                last_modified=_tree_latest_mtime(d),
            )
        )
    return rounds


def _scan_subphases(phase_dir: Path) -> list[SubPhase]:
    subs: list[SubPhase] = []
    for d in sorted(p for p in phase_dir.iterdir() if p.is_dir()):
        rounds = _scan_rounds(d)
        subs.append(
            SubPhase(
                name=d.name,
                files=_files_in(d),
                rounds=rounds,
                path=d,
                last_modified=_tree_latest_mtime(d),
            )
        )
    return subs


def _scan_phases(issue_dir: Path) -> list[PhaseStatus]:
    phases: list[PhaseStatus] = []
    for name in PHASE_ORDER:
        phase_dir = issue_dir / name
        files: list[str] = []
        subphases: list[SubPhase] = []
        if phase_dir.is_dir():
            files = _files_in(phase_dir)
            subphases = _scan_subphases(phase_dir)
        phases.append(
            PhaseStatus(
                name=name,
                files=files,
                subphases=subphases,
                path=phase_dir,
                last_modified=_tree_latest_mtime(phase_dir),
            )
        )
    return phases


def _parse_review_groups(plan_md: Path) -> list[str]:
    """Pull `sub-N` group names out of the plan's review_groups YAML list."""
    if not plan_md.is_file():
        return []
    groups: list[str] = []
    in_block = False
    for line in plan_md.read_text().splitlines():
        if line.strip() == "---" and in_block:
            break
        if line.startswith("review_groups:"):
            in_block = True
            continue
        if in_block:
            m = re.match(r"\s*-\s*(sub-\w+)\s*:", line)
            if m:
                groups.append(m.group(1))
            elif line and not line[0].isspace():
                in_block = False
    return groups


def _load_plan_meta(issue_dir: Path) -> PlanMeta:
    plan_md = issue_dir / "plan" / "plan.md"
    if not plan_md.is_file():
        return PlanMeta()
    meta, _ = parse_frontmatter(plan_md.read_text())

    def _int(key: str) -> int | None:
        v = _clean(meta.get(key))
        try:
            return int(v) if v is not None else None
        except ValueError:
            return None

    return PlanMeta(
        branching_mode=_clean(meta.get("branching_mode")),
        flow=_clean(meta.get("flow")),
        total_subtasks=_int("total_subtasks"),
        total_commits=_int("total_commits"),
        branch_name=_clean(meta.get("branch_name") or meta.get("proposed_branch")),
        branch_created=_as_bool(meta.get("branch_created")),
        target_branch=_clean(meta.get("target_branch")),
        pr_url=_clean(meta.get("pr_url")),
        pr_state=_clean(meta.get("pr_state")),
        develop_pr_url=_clean(meta.get("develop_pr_url")),
        merge_commit=_clean(meta.get("merge_commit")),
        gh_issue_created=_as_bool(meta.get("gh_issue_created")),
        review_groups=_parse_review_groups(plan_md),
        last_feedback_round=_clean(meta.get("last_feedback_round")),
        raw=meta,
    )


def _load_issue(issue_dir: Path, *, archived: bool) -> Issue:
    issue_md = issue_dir / "issue.md"
    meta: dict[str, str] = {}
    body = ""
    if issue_md.is_file():
        meta, body = parse_frontmatter(issue_md.read_text())
    return Issue(
        id=_clean(meta.get("id")) or issue_dir.name,
        title=_clean(meta.get("title")) or issue_dir.name,
        created=_parse_dt(meta.get("created")),
        status=_clean(meta.get("status")) or ("archived" if archived else "active"),
        experimental=_as_bool(meta.get("experimental")),
        description=body,
        archived=archived,
        phases=_scan_phases(issue_dir),
        plan=_load_plan_meta(issue_dir),
        path=issue_dir,
    )


def _load_review(review_dir: Path) -> Review:
    review_md = review_dir / "review.md"
    meta: dict[str, str] = {}
    if review_md.is_file():
        meta, _ = parse_frontmatter(review_md.read_text())
    rounds = _scan_rounds(review_dir)
    return Review(
        pr=_clean(meta.get("pr")) or review_dir.name.replace("pr-", ""),
        pr_url=_clean(meta.get("pr_url")) or "",
        title=_clean(meta.get("title")) or "",
        last_verdict=_clean(meta.get("last_verdict")) or "—",
        status=_clean(meta.get("status")) or "active",
        rounds=rounds,
        path=review_dir,
        last_modified=_tree_latest_mtime(review_dir),
    )


def find_workspace(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        ws = candidate / WORKSPACE_DIRNAME
        if ws.is_dir():
            return ws
    return None


def load_workspace(root: Path) -> Workspace:
    """Build a full in-memory snapshot of a `.dev-assistant/` workspace."""
    root = root.resolve()

    issues: list[Issue] = []
    issues_dir = root / "issues"
    if issues_dir.is_dir():
        for issue_dir in sorted(p for p in issues_dir.iterdir() if p.is_dir()):
            issues.append(_load_issue(issue_dir, archived=False))

    archive_dir = root / "archive" / "issues"
    if archive_dir.is_dir():
        for issue_dir in sorted(p for p in archive_dir.iterdir() if p.is_dir()):
            issues.append(_load_issue(issue_dir, archived=True))

    reviews: list[Review] = []
    reviews_dir = root / "reviews"
    if reviews_dir.is_dir():
        for review_dir in sorted(p for p in reviews_dir.iterdir() if p.is_dir()):
            reviews.append(_load_review(review_dir))

    lessons: list[str] = []
    lessons_dir = root / "lessons"
    if lessons_dir.is_dir():
        # 0.6+ layout: category subfolders (process/, technical/, collaboration/)
        # plus a regenerated INDEX.md; pre-0.6 workspaces have flat files at the
        # root. Collect both as lessons-dir-relative paths, excluding the index.
        lessons = sorted(
            p.relative_to(lessons_dir).as_posix()
            for p in lessons_dir.rglob("*.md")
            if p.is_file() and p.name != "INDEX.md"
        )

    strategies: list[str] = []
    strategies_dir = root / "strategies"
    if strategies_dir.is_dir():
        strategies = sorted(
            p.stem for p in strategies_dir.iterdir() if p.is_file() and p.suffix == ".md"
        )

    return Workspace(
        root=root,
        repo_name=root.parent.name,
        repo_root=root.parent,
        issues=issues,
        reviews=reviews,
        lessons=lessons,
        has_repo_context=(root / "repo-context.md").is_file(),
        custom_strategies=strategies,
    )
