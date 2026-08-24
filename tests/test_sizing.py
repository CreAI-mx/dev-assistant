"""Tests for diff-size measurement (the code-economy strategy's substrate)."""
from __future__ import annotations

import pytest

from dev_assistant import sizing


@pytest.mark.parametrize(
    ("added", "expected"),
    [(0, "S"), (50, "S"), (51, "M"), (150, "M"), (151, "L"), (400, "L"), (401, "XL")],
)
def test_band_boundaries(added: int, expected: str) -> None:
    assert sizing.band_for(added) == expected


def test_ceiling_for_is_case_insensitive_and_none_for_xl() -> None:
    assert sizing.ceiling_for("m") == 150
    assert sizing.ceiling_for("L") == 400
    assert sizing.ceiling_for("XL") is None
    assert sizing.ceiling_for("") is None


def test_overshoot_allows_the_tolerance_band() -> None:
    # M ceiling is 150; 25% tolerance puts the trigger just above 187.
    assert sizing.is_overshoot(150, "M") is False
    assert sizing.is_overshoot(187, "M") is False
    assert sizing.is_overshoot(200, "M") is True


def test_overshoot_needs_a_plan_to_overshoot() -> None:
    """No planned band means nothing to argue with — never an overshoot."""
    assert sizing.is_overshoot(5_000, None) is False
    assert sizing.is_overshoot(5_000, "XL") is False


NUMSTAT = "\n".join(
    [
        "40\t5\tsrc/dev_assistant/cli.py",
        "30\t0\ttests/test_cli.py",
        "12\t2\tdocs/user-guide.md",
        "900\t0\tpoetry.lock",
        "-\t-\tdocs/tui.png",
    ]
)


def test_summarize_splits_buckets_and_drops_noise() -> None:
    size = sizing.summarize_numstat(NUMSTAT)

    assert size.bucket("src").added == 40
    assert size.bucket("test").added == 30
    assert size.bucket("docs").added == 12
    assert size.added == 82           # lockfile excluded, binary uncounted
    assert size.deleted == 7
    assert size.net == 75
    assert size.files == 3
    assert size.band == "M"
    assert size.excluded == ["poetry.lock"]
    assert size.binary == ["docs/tui.png"]


def test_deletions_are_never_charged() -> None:
    """A change that removes far more than it adds still bands by what it adds."""
    size = sizing.summarize_numstat("10\t900\tsrc/old.py")
    assert size.added == 10
    assert size.net == -890
    assert size.band == "S"


def test_extra_excludes_are_honored() -> None:
    size = sizing.summarize_numstat(NUMSTAT, [*sizing.DEFAULT_EXCLUDES, "docs/*"])
    assert size.bucket("docs").files == 0
    assert "docs/user-guide.md" in size.excluded


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/test_cli.py", "test"),
        ("src/pkg/thing_test.py", "test"),
        ("web/app.spec.ts", "test"),
        ("README.md", "docs"),
        ("src/pkg/thing.py", "src"),
    ],
)
def test_classify(path: str, expected: str) -> None:
    assert sizing.classify(path) == expected


def test_summarize_ignores_malformed_rows() -> None:
    size = sizing.summarize_numstat("garbage\n\n7\t1\tsrc/a.py\nx\ty\tsrc/b.py\n")
    assert size.added == 7
    assert size.files == 1


def test_render_states_the_verdict() -> None:
    size = sizing.summarize_numstat("200\t0\tsrc/a.py")
    assert "over budget" in "\n".join(sizing.render(size, "M"))
    assert "within budget" in "\n".join(sizing.render(size, "L"))
    assert "no planned size" in "\n".join(sizing.render(size, None))
