"""Read-only data model for the dev-assistant TUI.

Pure functions and dataclasses that scan a `.dev-assistant/` workspace and
build an in-memory snapshot. No Textual import here on purpose — this layer is
fully unit-testable without a terminal, and the app layer renders it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_DIRNAME = ".dev-assistant"

# The author-side phase pipeline, in order. `refinement` (phase 0) is optional,
# so an empty refinement folder does not mean "not started".
PHASE_ORDER = ("refinement", "gathering", "plan", "execution", "evaluation")

# Short labels for compact progress rendering.
PHASE_LABELS = {
    "refinement": "refine",
    "gathering": "gather",
    "plan": "plan",
    "execution": "exec",
    "evaluation": "eval",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a markdown document into (frontmatter dict, body).

    Handles the simple `key: value` frontmatter dev-assistant writes between a
    pair of `---` fences. Not a full YAML parser — values are kept as trimmed
    strings. If there is no leading frontmatter fence, returns ({}, text).
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
        if ":" in raw:
            key, _, value = raw.partition(":")
            meta[key.strip()] = value.strip()
    if closing is None:
        # Malformed (no closing fence) — treat the whole thing as body.
        return {}, text
    body = "\n".join(lines[closing + 1 :]).strip()
    return meta, body


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def humanize_age(dt: datetime | None, *, ref: datetime | None = None) -> str:
    """Compact human duration since `dt` (e.g. '3d', '5h', '12m', 'just now')."""
    if dt is None:
        return "—"
    ref = ref or _now()
    delta = ref - dt
    seconds = int(delta.total_seconds())
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


def _latest_mtime(directory: Path) -> datetime | None:
    if not directory.is_dir():
        return None
    latest: float | None = None
    for child in directory.iterdir():
        if child.is_file():
            mtime = child.stat().st_mtime
            if latest is None or mtime > latest:
                latest = mtime
    if latest is None:
        return None
    return datetime.fromtimestamp(latest, tz=timezone.utc)


@dataclass
class PhaseStatus:
    name: str
    files: list[str]
    last_modified: datetime | None

    @property
    def label(self) -> str:
        return PHASE_LABELS.get(self.name, self.name)

    @property
    def has_content(self) -> bool:
        return bool(self.files)


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
    path: Path

    @property
    def completed_count(self) -> int:
        return sum(1 for p in self.phases if p.has_content)

    @property
    def total_phases(self) -> int:
        return len(self.phases)

    @property
    def current_phase(self) -> PhaseStatus | None:
        """Furthest-along phase that has content (the active one)."""
        active = [p for p in self.phases if p.has_content]
        return active[-1] if active else None

    @property
    def next_phase(self) -> PhaseStatus | None:
        """First phase after the current one with no content yet."""
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
        return all(p.has_content for p in self.phases)

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
    last_verdict: str
    status: str
    rounds: int
    latest_round_comments: int
    last_modified: datetime | None
    path: Path

    def age(self, ref: datetime | None = None) -> str:
        return humanize_age(self.last_modified, ref=ref)


@dataclass
class Workspace:
    root: Path
    repo_name: str
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
        """Count of active issues whose current phase is each phase name."""
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


def _scan_phases(issue_dir: Path) -> list[PhaseStatus]:
    phases: list[PhaseStatus] = []
    for name in PHASE_ORDER:
        phase_dir = issue_dir / name
        files: list[str] = []
        if phase_dir.is_dir():
            files = sorted(p.name for p in phase_dir.iterdir() if p.is_file())
        phases.append(
            PhaseStatus(name=name, files=files, last_modified=_latest_mtime(phase_dir))
        )
    return phases


def _load_issue(issue_dir: Path, *, archived: bool) -> Issue:
    issue_md = issue_dir / "issue.md"
    meta: dict[str, str] = {}
    body = ""
    if issue_md.is_file():
        meta, body = parse_frontmatter(issue_md.read_text())
    experimental = meta.get("experimental", "false").strip().lower() == "true"
    return Issue(
        id=meta.get("id", issue_dir.name),
        title=meta.get("title", issue_dir.name),
        created=_parse_dt(meta.get("created")),
        status=meta.get("status", "archived" if archived else "active"),
        experimental=experimental,
        description=body,
        archived=archived,
        phases=_scan_phases(issue_dir),
        path=issue_dir,
    )


def _load_review(review_dir: Path) -> Review:
    review_md = review_dir / "review.md"
    meta: dict[str, str] = {}
    if review_md.is_file():
        meta, _ = parse_frontmatter(review_md.read_text())
    rounds = sorted(
        p for p in review_dir.iterdir() if p.is_dir() and p.name.startswith("round-")
    )
    latest_comments = 0
    if rounds:
        comments_dir = rounds[-1] / "comments"
        if comments_dir.is_dir():
            latest_comments = sum(
                1
                for p in comments_dir.iterdir()
                if p.is_file() and p.name != "summary.md"
            )
    return Review(
        pr=meta.get("pr", review_dir.name.replace("pr-", "")),
        pr_url=meta.get("pr_url", ""),
        last_verdict=meta.get("last_verdict", "—"),
        status=meta.get("status", "active"),
        rounds=len(rounds),
        latest_round_comments=latest_comments,
        last_modified=_latest_mtime(rounds[-1]) if rounds else _latest_mtime(review_dir),
        path=review_dir,
    )


def find_workspace(start: Path | None = None) -> Path | None:
    """Locate a `.dev-assistant/` directory at `start` or any parent."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        ws = candidate / WORKSPACE_DIRNAME
        if ws.is_dir():
            return ws
    return None


def load_workspace(root: Path) -> Workspace:
    """Build a full in-memory snapshot of a `.dev-assistant/` workspace."""
    root = root.resolve()
    repo_name = root.parent.name

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
        lessons = sorted(
            p.name for p in lessons_dir.iterdir() if p.is_file() and p.suffix == ".md"
        )

    strategies: list[str] = []
    strategies_dir = root / "strategies"
    if strategies_dir.is_dir():
        strategies = sorted(
            p.stem for p in strategies_dir.iterdir() if p.is_file() and p.suffix == ".md"
        )

    return Workspace(
        root=root,
        repo_name=repo_name,
        issues=issues,
        reviews=reviews,
        lessons=lessons,
        has_repo_context=(root / "repo-context.md").is_file(),
        custom_strategies=strategies,
    )
