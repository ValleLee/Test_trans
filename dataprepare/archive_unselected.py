#!/usr/bin/env python3
"""Reversibly move task directories outside the active 100-task selection."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    selected = set((ROOT / "task_list/selected_100.txt").read_text().splitlines())
    archive = ROOT / "data/unselected_tasks"
    archive.mkdir(parents=True, exist_ok=True)
    moved = []
    for task in sorted((ROOT / "tasks").iterdir()):
        if not task.is_dir() or task.name in selected:
            continue
        if (ROOT / "runs" / task.name).exists():
            raise RuntimeError(f"cannot archive task with an existing run: {task.name}")
        destination = archive / task.name
        if destination.exists():
            raise RuntimeError(f"archive already contains {task.name}; inspect manually")
        shutil.move(str(task), str(destination))
        moved.append(task.name)
    all_archived = sorted(p.name for p in archive.iterdir() if p.is_dir())
    (ROOT / "data/stage1/unselected_task_archive.json").write_text(
        json.dumps({"archive": "data/unselected_tasks",
                    "count": len(all_archived), "instance_ids": all_archived}, indent=2) + "\n"
    )
    print(f"moved {len(moved)} tasks; active {len(list((ROOT / 'tasks').iterdir()))}; archived {len(all_archived)}")


if __name__ == "__main__":
    main()
