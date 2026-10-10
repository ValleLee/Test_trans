"""A certified conversion remains reusable after a later failed attempt."""
from __future__ import annotations

import importlib.util
import json
import os
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
        (attempt / "review/final_audit.json").write_text(json.dumps({"status": audit}))
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


def test_batch_agent_timeout_interrupts_process_group_and_returns(tmp_path):
    import sys
    import time

    script = Path(__file__).resolve().parents[1] / "scripts/run_stage2_batch.py"
    spec = importlib.util.spec_from_file_location("run_stage2_batch_timeout", script)
    assert spec and spec.loader
    batch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(batch)
    log = tmp_path / "agent.log"
    command = [sys.executable, "-c", "import time; time.sleep(10)"]
    started = time.monotonic()
    code, timed_out = batch._run_agent_with_timeout(
        command, cwd=tmp_path, env=os.environ.copy(), log_path=log,
        timeout_seconds=0.1, interrupt_grace_seconds=2,
    )
    assert timed_out is True
    assert code == -2
    assert time.monotonic() - started < 5


def test_batch_stop_interrupts_managed_processes_and_prevents_queued_work(tmp_path, monkeypatch):
    import signal
    import subprocess

    script = Path(__file__).resolve().parents[1] / "scripts/run_stage2_batch.py"
    spec = importlib.util.spec_from_file_location("run_stage2_batch_stop", script)
    assert spec and spec.loader
    batch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(batch)
    batch._STOP_REQUESTED.clear()
    calls = []
    monkeypatch.setattr(batch.os, "killpg", lambda pid, sig: calls.append((pid, sig)))
    process = subprocess.Popen(["/bin/true"], start_new_session=True)
    batch._ACTIVE_PROCESSES[process.pid] = process
    batch._request_stop(signal.SIGTERM, None)
    assert batch._STOP_REQUESTED.is_set()
    assert calls == [(process.pid, signal.SIGINT)]
    batch._ACTIVE_PROCESSES.clear()
    process.wait()

    monkeypatch.setattr(batch, "ROOT", tmp_path)
    monkeypatch.setattr(batch, "initialize_conversion_workspace",
                        lambda _: (_ for _ in ()).throw(AssertionError("queued work must not start")))
    result = batch._run_one("instance_queued", tmp_path / "batch", 8)
    assert result["status"] == "cancelled"
    status = json.loads((tmp_path / "batch/instance_queued/status.json").read_text())
    assert status["status"] == "cancelled"
    batch._STOP_REQUESTED.clear()


def test_batch_main_marks_batch_paused_on_sigterm(tmp_path, monkeypatch):
    import signal
    import sys
    import threading
    import time

    script = Path(__file__).resolve().parents[1] / "scripts/run_stage2_batch.py"
    spec = importlib.util.spec_from_file_location("run_stage2_batch_main_pause", script)
    assert spec and spec.loader
    batch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(batch)
    batch._STOP_REQUESTED.clear()
    old_int = signal.getsignal(signal.SIGINT)
    old_term = signal.getsignal(signal.SIGTERM)
    ids_file = tmp_path / "ids.txt"
    ids_file.write_text("ignored-by-test\n")
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    monkeypatch.setattr(batch, "_read_ids", lambda _: ["instance_one", "instance_two"])
    monkeypatch.setattr(batch, "_accepted_final", lambda _: None)
    monkeypatch.setattr(sys, "argv", [str(script), "--ids-file", str(ids_file), "--workers", "1"])

    def worker(instance_id, *_args):
        batch._STOP_REQUESTED.wait(timeout=4)
        return {"instance_id": instance_id,
                "status": "interrupted" if batch._STOP_REQUESTED.is_set() else "complete"}

    monkeypatch.setattr(batch, "_run_one", worker)
    timer = threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGTERM))
    timer.start()
    try:
        assert batch.main() == 130
    finally:
        timer.cancel()
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)
    batches = list((tmp_path / "data/stage2_batches").glob("*/batch.json"))
    assert len(batches) == 1
    manifest = json.loads(batches[0].read_text())
    assert manifest["status"] == "paused"
    batch._STOP_REQUESTED.clear()
