from pathlib import Path

import pytest

from swepro_trans.stage3 import parse_qualified_tasks


def test_parse_qualified_tasks_accepts_arbitrary_nonempty_cohort(tmp_path: Path):
    cohort = tmp_path / "cohort.txt"
    cohort.write_text(
        "01. instance_alpha\n    attempt: attempt_001 | revision: rev_002\n"
        "02. instance_beta\n    attempt: attempt_004 | revision: rev_007\n",
        encoding="utf-8",
    )

    assert parse_qualified_tasks(cohort) == [
        {"instance_id": "instance_alpha", "attempt": "attempt_001"},
        {"instance_id": "instance_beta", "attempt": "attempt_004"},
    ]


def test_parse_qualified_tasks_rejects_duplicate_instances(tmp_path: Path):
    cohort = tmp_path / "cohort.txt"
    cohort.write_text(
        "01. instance_alpha\n    attempt: attempt_001\n"
        "02. instance_alpha\n    attempt: attempt_002\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate"):
        parse_qualified_tasks(cohort)


def test_parse_qualified_tasks_rejects_empty_cohort(tmp_path: Path):
    cohort = tmp_path / "cohort.txt"
    cohort.write_text("# no tasks\n", encoding="utf-8")

    with pytest.raises(ValueError, match="at least one"):
        parse_qualified_tasks(cohort)
