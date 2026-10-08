#!/usr/bin/env python3
"""Replace failed local-oracle tasks while keeping already selected passing tasks."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIST = ROOT / "task_list/selected_100.txt"
REJECTED = ROOT / "task_list/rejected_ids.txt"
RETAINED = ROOT / "task_list/retained_ids.txt"


def main() -> int:
    ids = [line for line in LIST.read_text().splitlines() if line]
    statuses = {}
    for instance_id in ids:
        path = ROOT / "data/stage1" / instance_id / "preflight/report.json"
        if not path.is_file():
            raise SystemExit(f"missing preflight report: {instance_id}")
        statuses[instance_id] = json.loads(path.read_text()).get("preflight", {}).get("status")
    incomplete = [i for i in ids if statuses[i] in (None, "not_run")]
    if incomplete:
        raise SystemExit(f"preflight incomplete for {len(incomplete)} IDs")
    failed = [i for i in ids if statuses[i] != "pass"]
    if not failed:
        print("All 100 selected tasks passed local oracle preflight.")
        return 0
    previous = set(REJECTED.read_text().splitlines()) if REJECTED.exists() else set()
    REJECTED.write_text("\n".join(sorted(previous | set(failed))) + "\n")
    RETAINED.write_text("\n".join(i for i in ids if i not in failed) + "\n")
    subprocess.run([sys.executable, str(ROOT / "task_list/select_v2_100.py")], check=True)
    new_ids = [i for i in LIST.read_text().splitlines() if i and i not in ids]
    print(f"Replaced {len(failed)} oracle failures with {len(new_ids)} new same-language candidates.")
    for i in failed:
        print("REJECTED", i)
    for i in new_ids:
        print("NEW", i)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
