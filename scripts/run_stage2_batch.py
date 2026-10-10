#!/usr/bin/env python3
"""Run an explicit Stage 2 task list with isolated attempts and bounded workers.

Use --plan to check the input without creating attempts. Published accepted tasks
are skipped; rejected attempts may be retried with a new attempt.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swepro_trans.layout import initialize_conversion_workspace  # noqa: E402
from swepro_trans.validation.final_audit import _selector_list  # noqa: E402


_STOP_REQUESTED = threading.Event()
_ACTIVE_LOCK = threading.Lock()
_ACTIVE_PROCESSES: dict[int, subprocess.Popen] = {}


def _request_stop(signum, _frame) -> None:
    """Stop dispatching work and interrupt every managed worker process."""
    _STOP_REQUESTED.set()
    with _ACTIVE_LOCK:
        processes = list(_ACTIVE_PROCESSES.values())
    for process in processes:
        try:
            os.killpg(process.pid, signal.SIGINT)
        except ProcessLookupError:
            pass


def _register_process(process: subprocess.Popen) -> bool:
    """Track a process unless a batch stop raced with its startup."""
    with _ACTIVE_LOCK:
        if _STOP_REQUESTED.is_set():
            try:
                os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
            return False
        _ACTIVE_PROCESSES[process.pid] = process
        return True


def _unregister_process(process: subprocess.Popen) -> None:
    with _ACTIVE_LOCK:
        _ACTIVE_PROCESSES.pop(process.pid, None)


def _read_ids(path: Path) -> list[str]:
    ids = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
           if line.strip() and not line.lstrip().startswith("#")]
    if len(ids) != len(set(ids)):
        raise ValueError("task list contains duplicate instance IDs")
    if not ids:
        raise ValueError("task list is empty")
    for instance_id in ids:
        if Path(instance_id).name != instance_id or instance_id in {".", ".."}:
            raise ValueError(f"invalid instance ID: {instance_id!r}")
        if not (ROOT / "tasks" / instance_id / "original/task.toml").is_file():
            raise FileNotFoundError(f"Stage 1 task is unavailable: {instance_id}")
        source = ROOT / "runs" / instance_id / "source/problem_statement.md"
        staged = ROOT / "data/stage1" / instance_id / "source/problem_statement.md"
        if not source.is_file() and not staged.is_file():
            raise FileNotFoundError(f"Stage 1 source is unavailable: {instance_id}")
    return ids



def _accepted_final(instance_id: str) -> Path | None:
    """Reuse only a fully audited conversion preserving every original P2P selector."""
    attempts = ROOT / "runs" / instance_id / "attempts"
    published: list[Path] = []
    for attempt in sorted(attempts.glob("attempt_*")):
        final = attempt / "final"
        state_path = attempt / "intermediate/control/state.json"
        if not (final / "instruction.md").is_file() or not (final / "task.toml").is_file():
            continue
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if state.get("status") == "accepted":
            published.append(attempt)
    if not published:
        return None

    def audit_status(attempt: Path, name: str) -> str | None:
        path = attempt / "review" / name
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("status")
        except (OSError, ValueError):
            return "INVALID"

    original_config = _load_state(ROOT / "tasks" / instance_id / "original/tests/config.json")
    original_p2p = _selector_list(original_config, "pass_to_pass", "pass_to_pass_tests")

    # Certification alone did not guarantee full P2P retention in older runs.
    # Preserve the original selector sequence exactly; converted regressions
    # may only be appended after it.
    for attempt in reversed(published):
        candidate_config = _load_state(attempt / "final/tests/config.json")
        candidate_p2p = _selector_list(candidate_config, "pass_to_pass", "pass_to_pass_tests")
        external_audits = [audit_status(attempt, path.name)
                           for path in (attempt / "review").glob("external_audit*.json")]
        if (audit_status(attempt, "independent_audit.json") == "PASS"
                and audit_status(attempt, "final_audit.json") == "PASS"
                and not any(status in {"FAIL", "INVALID"} for status in external_audits)
                and candidate_p2p[:len(original_p2p)] == original_p2p):
            return attempt / "final"
    return None


def _load_state(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _run_agent_with_timeout(
    command: list[str], *, cwd: Path, env: dict[str, str], log_path: Path,
    timeout_seconds: int, interrupt_grace_seconds: int = 30,
) -> tuple[int, bool]:
    """Run one converter session with a total deadline and graceful cleanup."""
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        if not _register_process(process):
            return process.wait(), False
        try:
            return process.wait(timeout=timeout_seconds), False
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
            try:
                return process.wait(timeout=interrupt_grace_seconds), True
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    return process.wait(timeout=5), True
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    return process.wait(), True
        finally:
            _unregister_process(process)


def _run_one(instance_id: str, output: Path, max_revisions: int, agent_timeout_seconds: int = 3600) -> dict:
    task = ROOT / "tasks" / instance_id
    directory = output / instance_id
    directory.mkdir(parents=True, exist_ok=True)
    result = {"instance_id": instance_id, "status": "preparing", "phase": "workspace",
              "started_at_utc": datetime.now(timezone.utc).isoformat()}
    status = directory / "status.json"
    try:
        if _STOP_REQUESTED.is_set():
            result["status"] = "cancelled"
            result["phase"] = "not_started"
            return result
        existing = _accepted_final(instance_id)
        if existing is not None:
            result["status"] = "already_converted"
            result["existing_final"] = str(existing.relative_to(ROOT))
            return result
        initialized = initialize_conversion_workspace(task)
        attempt = Path(initialized["attempt_root"])
        revision = attempt / "intermediate/converter/revisions/rev_001"
        result["attempt"] = attempt.name
        result["status"] = "agent_running"
        result["phase"] = "converter"
        result["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        _write(status, result)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        python = str(ROOT / ".venv/bin/python")
        agent_cmd = [python, "-m", "swepro_trans", "agent", "--task-root", str(attempt), "--revision", str(revision)]
        agent_exit_code, agent_timed_out = _run_agent_with_timeout(
            agent_cmd, cwd=ROOT, env=env, log_path=directory / "agent.log",
            timeout_seconds=agent_timeout_seconds,
        )
        result["agent_exit_code"] = agent_exit_code
        result["agent_timed_out"] = agent_timed_out
        result["agent_timeout_seconds"] = agent_timeout_seconds
        if _STOP_REQUESTED.is_set():
            result["status"] = "interrupted"
            result["phase"] = "converter"
            return result
        # The pipeline owns the artifact contract and its repair loop. A model
        # may hit its step limit after leaving only a partial revision; route
        # that revision through the contract gate so the missing files become
        # concrete repair feedback instead of ending the task here.
        if not revision.is_dir():
            result["status"] = "agent_failed"
            result["error"] = "agent did not create a revision directory"
            return result
        result["status"] = "pipeline_running"
        result["phase"] = "validation_and_repair"
        result["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        _write(status, result)
        pipeline_cmd = [python, "-m", "swepro_trans", "pipeline", "--task-root", str(attempt),
                        "--revision", str(revision), "--max-revisions", str(max_revisions)]
        with (directory / "pipeline.log").open("w", encoding="utf-8") as log:
            pipeline = subprocess.Popen(pipeline_cmd, cwd=ROOT, env=env, stdout=log,
                                        stderr=subprocess.STDOUT, start_new_session=True)
            if not _register_process(pipeline):
                pipeline.wait()
                result["status"] = "interrupted"
                result["phase"] = "validation_and_repair"
                return result
            try:
                pipeline_exit_code = pipeline.wait()
            finally:
                _unregister_process(pipeline)
        result["pipeline_exit_code"] = pipeline_exit_code
        if _STOP_REQUESTED.is_set():
            result["status"] = "interrupted"
            result["phase"] = "validation_and_repair"
            return result
        report_path = attempt / "intermediate/validation/stage2_pipeline.json"
        if report_path.is_file():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            result["pipeline_status"] = report.get("status")
            result["revision"] = report.get("revision")
        result["status"] = "complete" if pipeline.returncode == 0 and result.get("pipeline_status") == "complete" else "needs_review"
    except Exception as exc:
        result["status"] = "runner_error"
        result["error"] = repr(exc)
    finally:
        result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        _write(status, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids-file", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--max-revisions", type=int, default=8)
    parser.add_argument("--agent-timeout-seconds", type=int, default=3600,
                        help="maximum wall time for the initial converter session")
    parser.add_argument("--plan", action="store_true", help="validate the list without creating attempts")
    args = parser.parse_args()
    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)
    if not 1 <= args.workers <= 10:
        parser.error("workers must be between 1 and 10")
    if args.agent_timeout_seconds <= 0:
        parser.error("agent-timeout-seconds must be positive")
    ids = _read_ids(args.ids_file.resolve())
    existing = {instance_id: str(final.relative_to(ROOT)) for instance_id in ids
                if (final := _accepted_final(instance_id)) is not None}
    to_run = [instance_id for instance_id in ids if instance_id not in existing]
    if args.plan:
        print(json.dumps({"count": len(ids), "workers": args.workers, "ids": ids,
                          "already_converted": existing, "to_run": to_run}, ensure_ascii=False, indent=2))
        return 0
    batch = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "data/stage2_batches" / f"{args.ids_file.stem}_{batch}"
    output.mkdir(parents=True, exist_ok=False)
    _write(output / "batch.json", {"status": "running", "started_at_utc": datetime.now(timezone.utc).isoformat(),
                                   "ids": ids, "to_run": to_run, "already_converted": existing,
                                   "workers": args.workers, "max_revisions": args.max_revisions})
    failed = 0
    for instance_id, final in existing.items():
        print(json.dumps({"instance_id": instance_id, "status": "already_converted",
                          "existing_final": final}, ensure_ascii=False), flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run_one, instance_id, output, args.max_revisions, args.agent_timeout_seconds): instance_id
                   for instance_id in to_run}
        for future in as_completed(futures):
            result = future.result()
            print(json.dumps(result, ensure_ascii=False), flush=True)
            failed += result.get("status") not in {"complete", "already_converted"}
    if _STOP_REQUESTED.is_set():
        batch_state = _load_state(output / "batch.json")
        batch_state.update({"status": "paused", "paused_at_utc": datetime.now(timezone.utc).isoformat(),
                            "pause_signal": "SIGINT or SIGTERM"})
        _write(output / "batch.json", batch_state)
        return 130
    batch_state = _load_state(output / "batch.json")
    batch_state.update({"status": "complete" if failed == 0 else "finished_with_errors",
                        "finished_at_utc": datetime.now(timezone.utc).isoformat()})
    _write(output / "batch.json", batch_state)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
