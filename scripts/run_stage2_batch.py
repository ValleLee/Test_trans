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
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swepro_trans.layout import initialize_conversion_workspace  # noqa: E402
from swepro_trans.validation.final_audit import _selector_list  # noqa: E402


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


def _run_one(instance_id: str, output: Path, max_revisions: int) -> dict:
    task = ROOT / "tasks" / instance_id
    directory = output / instance_id
    directory.mkdir(parents=True, exist_ok=True)
    result = {"instance_id": instance_id, "started_at_utc": datetime.now(timezone.utc).isoformat()}
    status = directory / "status.json"
    try:
        existing = _accepted_final(instance_id)
        if existing is not None:
            result["status"] = "already_converted"
            result["existing_final"] = str(existing.relative_to(ROOT))
            return result
        initialized = initialize_conversion_workspace(task)
        attempt = Path(initialized["attempt_root"])
        revision = attempt / "intermediate/converter/revisions/rev_001"
        result["attempt"] = attempt.name
        _write(status, result)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        python = str(ROOT / ".venv/bin/python")
        agent_cmd = [python, "-m", "swepro_trans", "agent", "--task-root", str(attempt), "--revision", str(revision)]
        with (directory / "agent.log").open("w", encoding="utf-8") as log:
            agent = subprocess.run(agent_cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
        result["agent_exit_code"] = agent.returncode
        # The pipeline owns the artifact contract and its repair loop. A model
        # may hit its step limit after leaving only a partial revision; route
        # that revision through the contract gate so the missing files become
        # concrete repair feedback instead of ending the task here.
        if not revision.is_dir():
            result["status"] = "agent_failed"
            result["error"] = "agent did not create a revision directory"
            return result
        _write(status, result)
        pipeline_cmd = [python, "-m", "swepro_trans", "pipeline", "--task-root", str(attempt),
                        "--revision", str(revision), "--max-revisions", str(max_revisions)]
        with (directory / "pipeline.log").open("w", encoding="utf-8") as log:
            pipeline = subprocess.run(pipeline_cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
        result["pipeline_exit_code"] = pipeline.returncode
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
    parser.add_argument("--plan", action="store_true", help="validate the list without creating attempts")
    args = parser.parse_args()
    if not 1 <= args.workers <= 10:
        parser.error("workers must be between 1 and 10")
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
    _write(output / "batch.json", {"ids": ids, "to_run": to_run,
                                   "already_converted": existing, "workers": args.workers,
                                   "max_revisions": args.max_revisions})
    failed = 0
    for instance_id, final in existing.items():
        print(json.dumps({"instance_id": instance_id, "status": "already_converted",
                          "existing_final": final}, ensure_ascii=False), flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run_one, instance_id, output, args.max_revisions): instance_id
                   for instance_id in to_run}
        for future in as_completed(futures):
            result = future.result()
            print(json.dumps(result, ensure_ascii=False), flush=True)
            failed += result.get("status") not in {"complete", "already_converted"}
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
