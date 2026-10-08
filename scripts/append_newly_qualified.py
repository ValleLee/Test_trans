#!/usr/bin/env python3
"""Append one independently certified Stage 2 task to the current cohort list."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "check/qualified_tasks.txt"
NEW = ROOT / "check/qualified_tasks_new_20261008.txt"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("instance_id")
    parser.add_argument("attempt")
    args = parser.parse_args()
    instance_id = args.instance_id
    attempt = ROOT / "runs" / instance_id / "attempts" / args.attempt
    if not attempt.is_dir():
        raise SystemExit(f"missing attempt: {attempt}")
    state = read_json(attempt / "intermediate/control/state.json")
    independent = read_json(attempt / "review/independent_audit.json")
    external = read_json(attempt / "review/external_audit_20261008.json")
    final = read_json(attempt / "review/final_audit.json")
    metrics = read_json(attempt / "review/metrics.json")
    policy = final.get("checks", {}).get("p2p_policy", {})
    if (state.get("status") != "accepted" or independent.get("status") != "PASS"
            or external.get("status") != "PASS"
            or final.get("status") != "PASS" or policy.get("excluded") != 0
            or metrics.get("acceptance") != "accepted" or not metrics.get("final_packaged")):
        raise SystemExit("attempt is not independently qualified with all original P2P retained")
    for path in (ORIGINAL, NEW):
        if re.search(rf"(?m)^\d+\. {re.escape(instance_id)}$", path.read_text(encoding="utf-8")):
            raise SystemExit(f"already listed in {path}")
    content = NEW.read_text(encoding="utf-8")
    match = re.search(r"新增合格任务数：(\d+)（按 instance 去重）", content)
    if not match:
        raise SystemExit("new cohort header is missing")
    current = int(match.group(1))
    if len(re.findall(r"(?m)^\d+\. instance_", content)) != current:
        raise SystemExit("new cohort header count differs from entries")
    updated = content.replace(match.group(0), f"新增合格任务数：{current + 1}（按 instance 去重）", 1)
    updated = updated.rstrip() + (
        f"\n\n{current + 1:02d}. {instance_id}\n"
        f"    attempt: {args.attempt} | revision: {metrics['revision']}\n"
        f"    historical F2P: {metrics['f2p_count']} | "
        f"original P2P retained: {policy['original']} | excluded: 0\n"
    )
    temporary = NEW.with_suffix(".txt.tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(NEW)
    print(f"newly qualified: {current + 1} ({instance_id})")


if __name__ == "__main__":
    main()
