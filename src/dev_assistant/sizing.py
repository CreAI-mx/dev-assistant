"""Diff-size measurement for the code-economy strategy.

The phases talk about change size in bands (S / M / L), not raw line counts —
a band is coarse enough to be honest and specific enough to argue with. This
module turns `git diff --numstat` output into a banded summary. It is pure:
the caller supplies the numstat text, so the interesting logic is testable
without a repository.

Cost is measured in **added** lines. Deleted lines are reported separately and
never counted against a change: removing code is progress, not spend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch

# (band, inclusive ceiling of added lines). Anything above the last ceiling is
# XL, which the plan phase treats as "split this subtask", not as a size.
BANDS: tuple[tuple[str, int], ...] = (("S", 50), ("M", 150), ("L", 400))
OVER_BAND = "XL"

# How far a real diff may exceed its planned band's ceiling before /dev-execute
# treats it as an overshoot worth stopping for (after it has tried trimming).
OVERSHOOT_TOLERANCE = 0.25

# Paths whose size says nothing about how much code a human has to read.
DEFAULT_EXCLUDES: tuple[str, ...] = (
    "*.lock",
    "*.min.*",
    "*.map",
    "*-lock.json",
    "*.sum",
    "*.snap",
    "**/vendor/**",
    "**/node_modules/**",
    "**/dist/**",
    "**/build/**",
    "**/migrations/**",
    "**/__snapshots__/**",
    ".dev-assistant/**",
)

_TEST_MARKERS = ("test_", "_test.", "/tests/", "/test/", ".spec.", ".test.")
_DOC_SUFFIXES = (".md", ".rst", ".txt", ".adoc")


def band_for(added: int) -> str:
    """The band a given number of added lines falls into."""
    for name, ceiling in BANDS:
        if added <= ceiling:
            return name
    return OVER_BAND


def ceiling_for(band: str) -> int | None:
    """The inclusive added-line ceiling of a band, or None for XL/unknown."""
    for name, ceiling in BANDS:
        if name == band.strip().upper():
            return ceiling
    return None


def is_overshoot(added: int, planned_band: str | None) -> bool:
    """True when a real diff exceeds its planned band beyond the tolerance.

    An absent or unrecognized plan can't be overshot — the phases report the
    measured band instead of arguing with a budget that was never set.
    """
    ceiling = ceiling_for(planned_band or "")
    if ceiling is None:
        return False
    return added > ceiling * (1 + OVERSHOOT_TOLERANCE)


def classify(path: str) -> str:
    """Bucket a path as test / docs / src, for reporting only."""
    lowered = path.lower()
    if any(marker in lowered for marker in _TEST_MARKERS):
        return "test"
    if lowered.endswith(_DOC_SUFFIXES):
        return "docs"
    return "src"


def is_excluded(path: str, excludes: tuple[str, ...] | list[str]) -> bool:
    for pattern in excludes:
        if fnmatch(path, pattern):
            return True
        # `**/x/**` should also match a path that starts at that directory.
        if pattern.startswith("**/") and fnmatch(path, pattern[3:]):
            return True
    return False


@dataclass
class Bucket:
    added: int = 0
    deleted: int = 0
    files: int = 0


@dataclass
class DiffSize:
    buckets: dict[str, Bucket] = field(default_factory=dict)
    excluded: list[str] = field(default_factory=list)
    binary: list[str] = field(default_factory=list)

    @property
    def added(self) -> int:
        return sum(b.added for b in self.buckets.values())

    @property
    def deleted(self) -> int:
        return sum(b.deleted for b in self.buckets.values())

    @property
    def files(self) -> int:
        return sum(b.files for b in self.buckets.values())

    @property
    def net(self) -> int:
        return self.added - self.deleted

    @property
    def band(self) -> str:
        return band_for(self.added)

    def bucket(self, name: str) -> Bucket:
        return self.buckets.get(name, Bucket())


def summarize_numstat(
    numstat: str, excludes: tuple[str, ...] | list[str] = DEFAULT_EXCLUDES
) -> DiffSize:
    """Parse `git diff --numstat` output into a banded summary.

    Each line is `<added>\\t<deleted>\\t<path>`; binary files report `-` for both
    counts and are listed rather than counted.
    """
    result = DiffSize()
    for raw in numstat.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added_s, deleted_s, path = parts[0], parts[1], parts[-1]

        if is_excluded(path, excludes):
            result.excluded.append(path)
            continue
        if added_s == "-" or deleted_s == "-":
            result.binary.append(path)
            continue

        try:
            added, deleted = int(added_s), int(deleted_s)
        except ValueError:
            continue

        bucket = result.buckets.setdefault(classify(path), Bucket())
        bucket.added += added
        bucket.deleted += deleted
        bucket.files += 1
    return result


def render(size: DiffSize, planned_band: str | None = None) -> list[str]:
    """Human-readable lines for the CLI and for a phase to paste into a report."""
    lines = [
        f"Added {size.added} · deleted {size.deleted} · net {size.net:+d} "
        f"across {size.files} file{'s' if size.files != 1 else ''}",
    ]
    for name in ("src", "test", "docs"):
        b = size.bucket(name)
        if b.files:
            lines.append(f"  {name:<5} +{b.added:<6} -{b.deleted:<6} ({b.files} files)")
    if size.excluded:
        lines.append(f"  excluded: {len(size.excluded)} file(s) — {', '.join(size.excluded[:3])}"
                     + (" …" if len(size.excluded) > 3 else ""))
    if size.binary:
        lines.append(f"  binary (uncounted): {len(size.binary)} file(s)")

    if planned_band:
        planned = planned_band.strip().upper()
        verdict = "over" if is_overshoot(size.added, planned) else "within"
        ceiling = ceiling_for(planned)
        budget = f"{planned} (≤{ceiling} added)" if ceiling else planned
        lines.append(f"Band {size.band} vs planned {budget} — {verdict} budget")
    else:
        lines.append(f"Band {size.band} (no planned size recorded)")
    return lines
