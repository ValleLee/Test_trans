#!/usr/bin/env python3
"""Append one Stage 1 selected-100 task after independent certification."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "check/qualified_tasks.txt"
NEW = ROOT / "check/qualified_tasks_selected100_new_20261008.txt"
SELECTED = ROOT / "task_list/selected_100.txt"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def listed_ids(path: Path) -> set[str]:
    return set(re.findall(r"(?m)^\d+\. (instance_[^\s]+)$", path.read_text(encoding="utf-8")))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("instance_id")
    parser.add_argument("attempt")
    args = parser.parse_args()
    instance_id = args.instance_id
    attempt = ROOT / "runs" / instance_id / "attempts" / args.attempt
    if not attempt.is_dir():
        raise SystemExit(f"missing attempt: {attempt}")

    selected = {line.strip() for line in SELECTED.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")}
    if instance_id not in selected:
        raise SystemExit("task is not in Stage 1 selected-100")

    state = read_json(attempt / "intermediate/control/state.json")
    independent = read_json(attempt / "review/independent_audit.json")
    final = read_json(attempt / "review/final_audit.json")
    metrics = read_json(attempt / "review/metrics.json")
    final_checks = final.get("checks", {})
    p2p_policy = final_checks.get("p2p_policy", {})
    audit_checks = independent.get("checks", {})

    if (state.get("status") != "accepted" or independent.get("status") != "PASS"
            or final.get("status") != "PASS"
            or metrics.get("acceptance") != "accepted"
            or not metrics.get("final_packaged")):
        raise SystemExit("attempt is not framework-accepted, independently audited PASS, and packaged")
    if independent.get("revision") not in (None, metrics.get("revision")):
        raise SystemExit("independent audit revision does not match the packaged revision")
    if final.get("revision") not in (None, metrics.get("revision")):
        raise SystemExit("final audit revision does not match the packaged revision")
    if p2p_policy.get("excluded") != 0:
        raise SystemExit("final audit reports excluded original P2P selectors")
    if "original_p2p_exact_and_unexcluded" in audit_checks:
        exact_p2p = audit_checks["original_p2p_exact_and_unexcluded"] in (True, "PASS")
    else:
        exact_p2p = (audit_checks.get("p2p_order_and_values_preserved") is True
                     and audit_checks.get("p2p_excluded") == 0)
    if not exact_p2p:
        raise SystemExit("independent audit did not confirm exact original P2P preservation")
    if audit_checks.get("instruction_p_only") not in (True, "PASS"):
        raise SystemExit("independent audit did not confirm the final instruction is P-only")

    for path in (ORIGINAL, NEW):
        if instance_id in listed_ids(path):
            raise SystemExit(f"already listed in {path}")
    content = NEW.read_text(encoding="utf-8")
    match = re.search(r"新增合格任务数：(\d+)（[^）]*）", content)
    if not match:
        raise SystemExit("selected-100 new cohort header is missing")
    current = int(match.group(1))
    if len(listed_ids(NEW)) != current:
        raise SystemExit("new cohort header count differs from entries")
    updated = content[:match.start(1)] + str(current + 1) + content[match.end(1):]
    updated = updated.rstrip() + (
        f"\n\n{current + 1:02d}. {instance_id}\n"
        f"    attempt: {args.attempt} | revision: {metrics['revision']}\n"
        f"    historical F2P: {metrics['f2p_count']} | "
        f"original P2P retained: {p2p_policy.get('retained')} | excluded: 0\n"
    )
    temporary = NEW.with_suffix(".txt.tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(NEW)
    print(f"new selected-100 qualified: {current + 1} ({instance_id})")


if __name__ == "__main__":
    main()
