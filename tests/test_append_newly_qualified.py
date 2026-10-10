import json
from pathlib import Path

import pytest

from scripts import append_newly_qualified


TASK = "instance_demo__repo-123"


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _prepare(tmp_path: Path, monkeypatch, *, instruction_check="PASS") -> Path:
    monkeypatch.setattr(append_newly_qualified, "ROOT", tmp_path)
    original = tmp_path / "check/qualified_tasks.txt"
    new = tmp_path / "check/qualified_tasks_selected100_new_20261008.txt"
    selected = tmp_path / "task_list/selected_100.txt"
    original.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True, exist_ok=True)
    selected.parent.mkdir(parents=True, exist_ok=True)
    original.write_text("Original cohort\n", encoding="utf-8")
    new.write_text("新增合格任务数：0（仅统计 selected-100 任务）\n", encoding="utf-8")
    selected.write_text(TASK + "\n", encoding="utf-8")
    monkeypatch.setattr(append_newly_qualified, "ORIGINAL", original)
    monkeypatch.setattr(append_newly_qualified, "NEW", new)
    monkeypatch.setattr(append_newly_qualified, "SELECTED", selected)
    attempt = tmp_path / "runs" / TASK / "attempts/attempt_001"
    _write_json(attempt / "intermediate/control/state.json", {"status": "accepted"})
    _write_json(attempt / "review/independent_audit.json", {
        "status": "PASS",
        "revision": "rev_001",
        "checks": {
            "instruction_p_only": instruction_check,
            "original_p2p_exact_and_unexcluded": "PASS",
        },
    })
    _write_json(attempt / "review/final_audit.json", {
        "status": "PASS", "revision": "rev_001",
        "checks": {"p2p_policy": {"retained": 2, "excluded": 0}},
    })
    _write_json(attempt / "review/metrics.json", {
        "revision": "rev_001", "f2p_count": 3,
        "acceptance": "accepted", "final_packaged": True,
    })
    return new


def test_append_uses_selected_100_cohort_and_current_audit_schema(tmp_path, monkeypatch):
    new = _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr("sys.argv", ["append_newly_qualified.py", TASK, "attempt_001"])

    append_newly_qualified.main()

    content = new.read_text(encoding="utf-8")
    assert "新增合格任务数：1（仅统计 selected-100 任务）" in content
    assert f"01. {TASK}" in content
    assert "original P2P retained: 2 | excluded: 0" in content


def test_append_rejects_task_without_instruction_p_only_pass(tmp_path, monkeypatch):
    new = _prepare(tmp_path, monkeypatch, instruction_check="FAIL")
    monkeypatch.setattr("sys.argv", ["append_newly_qualified.py", TASK, "attempt_001"])

    with pytest.raises(SystemExit, match="P-only"):
        append_newly_qualified.main()

    assert "新增合格任务数：0" in new.read_text(encoding="utf-8")
