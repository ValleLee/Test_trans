"""A certified conversion remains reusable after a later failed attempt."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def test_batch_reuses_older_audited_pass_after_later_rejection(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / "scripts/run_stage2_batch.py"
    spec = importlib.util.spec_from_file_location("run_stage2_batch", script)
    assert spec and spec.loader
    batch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(batch)
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    instance_id = "instance_example"
    attempts = tmp_path / "runs" / instance_id / "attempts"
    for name, status, audit in (
        ("attempt_001", "accepted", "PASS"),
        ("attempt_002", "audit_rejected", "FAIL"),
    ):
        attempt = attempts / name
        (attempt / "final").mkdir(parents=True)
        (attempt / "final/instruction.md").write_text("P")
        (attempt / "final/task.toml").write_text("name = 'test'")
        (attempt / "intermediate/control").mkdir(parents=True)
        (attempt / "intermediate/control/state.json").write_text(json.dumps({"status": status}))
        (attempt / "review").mkdir(parents=True)
        (attempt / "review/independent_audit.json").write_text(json.dumps({"status": audit}))
    monkeypatch.setattr(batch, "initialize_conversion_workspace", lambda _: (_ for _ in ()).throw(AssertionError("must not allocate")))
    result = batch._run_one(instance_id, tmp_path / "batch", 1)
    assert result["status"] == "already_converted"
    assert result["existing_final"].endswith("attempt_001/final")
    assert sorted(p.name for p in attempts.iterdir()) == ["attempt_001", "attempt_002"]


def test_uncertified_legacy_acceptance_does_not_hide_newer_failed_attempt(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / "scripts/run_stage2_batch.py"
    spec = importlib.util.spec_from_file_location("run_stage2_batch_legacy_failure", script)
    assert spec and spec.loader
    batch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(batch)
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    attempts = tmp_path / "runs/instance_legacy/attempts"
    for name, status in (("attempt_001", "accepted"), ("attempt_002", "validation_failed")):
        root = attempts / name
        (root / "final").mkdir(parents=True)
        (root / "final/instruction.md").write_text("P")
        (root / "final/task.toml").write_text("name = 'test'")
        (root / "intermediate/control").mkdir(parents=True)
        (root / "intermediate/control/state.json").write_text(json.dumps({"status": status}))
    assert batch._accepted_final("instance_legacy") is None


def test_guarded_retry_preserves_certified_and_legacy_success(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / "scripts/run_guarded_stage2_retry.py"
    spec = importlib.util.spec_from_file_location("run_guarded_stage2_retry", script)
    assert spec and spec.loader
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    monkeypatch.setattr(guard, "ROOT", tmp_path)

    def attempt(instance, name, state, independent=None, final=None):
        root = tmp_path / "runs" / instance / "attempts" / name
        (root / "final").mkdir(parents=True)
        (root / "final/instruction.md").write_text("P")
        (root / "final/task.toml").write_text("name = 'test'")
        (root / "intermediate/control").mkdir(parents=True)
        (root / "intermediate/control/state.json").write_text(json.dumps({"status": state}))
        (root / "review").mkdir(parents=True)
        if independent is not None:
            (root / "review/independent_audit.json").write_text(json.dumps({"status": independent}))
        if final is not None:
            (root / "review/final_audit.json").write_text(json.dumps({"status": final}))

    attempt("legacy", "attempt_001", "accepted")
    attempt("legacy_failed", "attempt_001", "accepted")
    attempt("legacy_failed", "attempt_002", "validation_failed")
    attempt("certified", "attempt_001", "accepted", "PASS", "PASS")
    attempt("certified", "attempt_002", "audit_rejected", "FAIL", "FAIL")
    attempt("rejected", "attempt_001", "accepted", "FAIL", "FAIL")
    assert guard.completed_conversion("legacy")
    assert not guard.completed_conversion("legacy_failed")
    assert guard.completed_conversion("certified")
    assert not guard.completed_conversion("rejected")
    assert not guard.completed_conversion("new")
